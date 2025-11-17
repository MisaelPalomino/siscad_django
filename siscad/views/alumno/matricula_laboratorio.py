from ..comunes.imports import *


def matricula_laboratorio(request):
    # 1. Obtener el alumno logueado
    if "email" not in request.session:
        return redirect("login")

    email = request.session["email"]

    try:
        alumno = Alumno.objects.get(email=email)
    except Alumno.DoesNotExist:
        messages.error(request, "Alumno no encontrado.")
        return redirect("login")
    except Alumno.MultipleObjectsReturned:
        alumno = Alumno.objects.filter(email=email).first()

    # 2. Obtener los cursos matriculados
    matriculas_curso = MatriculaCurso.objects.filter(
        alumno_id=alumno.id
    ).select_related("curso")

    if not matriculas_curso:
        messages.warning(request, "No tienes cursos matriculados.")
        return redirect("inicio_alumno")

    # 3. Procesar matrícula de laboratorio
    if request.method == "POST":
        grupo_lab_id = request.POST.get("grupo_laboratorio")

        if not grupo_lab_id:
            messages.error(request, "Debes seleccionar un grupo de laboratorio.")
            return redirect("matricula_laboratorio")

        try:
            with transaction.atomic():
                grupo_lab = GrupoLaboratorio.objects.select_related(
                    "grupo_teoria__curso", "profesor"
                ).get(id=grupo_lab_id)

                # Verificar que el alumno esté matriculado en el curso correspondiente
                matricula_curso = matriculas_curso.filter(
                    curso_id=grupo_lab.grupo_teoria.curso_id
                ).first()

                if not matricula_curso:
                    messages.error(request, "No estás matriculado en este curso.")
                    return redirect("matricula_laboratorio")

                # Verificar si ya está matriculado en un laboratorio de ese curso
                matricula_existente = MatriculaLaboratorio.objects.filter(
                    alumno_id=alumno.id,
                    grupo_laboratorio__grupo_teoria__curso_id=grupo_lab.grupo_teoria.curso_id,
                ).exists()

                if matricula_existente:
                    messages.error(
                        request,
                        f"Ya estás matriculado en un laboratorio de {grupo_lab.grupo_teoria.curso.nombre}.",
                    )
                    return redirect("matricula_laboratorio")

                # Verificar cupos
                if grupo_lab.cupos <= 0:
                    messages.error(
                        request,
                        "No hay cupos disponibles en este grupo de laboratorio.",
                    )
                    return redirect("matricula_laboratorio")

                # Crear matrícula
                matricula_lab = MatriculaLaboratorio(
                    alumno_id=alumno.id, grupo_laboratorio_id=grupo_lab.id
                )
                matricula_lab.save()

                # Actualizar cupos
                grupo_lab.cupos -= 1
                grupo_lab.save()

                generar_asistencias_laboratorio(alumno, grupo_lab)

                messages.success(
                    request,
                    f"Te has matriculado exitosamente en el laboratorio de {grupo_lab.grupo_teoria.curso.nombre} y se generaron tus asistencias.",
                )
                return redirect("matricula_laboratorio")

        except GrupoLaboratorio.DoesNotExist:
            messages.error(request, "El grupo de laboratorio seleccionado no existe.")
        except Exception as e:
            messages.error(request, f"Error al realizar la matrícula: {str(e)}")

    # 4. Obtener laboratorios disponibles
    laboratorios_disponibles = []

    for matricula in matriculas_curso:
        curso = matricula.curso
        turno_alumno = matricula.turno

        grupos_lab = (
            GrupoLaboratorio.objects.select_related("grupo_teoria__curso", "profesor")
            .filter(
                grupo_teoria__curso_id=curso.id,
                cupos__gt=0,
            )
            .exclude(matriculas_laboratorio__alumno_id=alumno.id)
        )

        grupos_compatibles = [
            g
            for g in grupos_lab
            if g.grupo == turno_alumno or g.grupo not in ["A", "B", "C"]
        ]

        if grupos_compatibles:
            laboratorios_disponibles.append(
                {
                    "curso": curso,
                    "turno_alumno": turno_alumno,
                    "grupos": grupos_compatibles,
                    "ya_matriculado": MatriculaLaboratorio.objects.filter(
                        alumno_id=alumno.id,
                        grupo_laboratorio__grupo_teoria__curso_id=curso.id,
                    ).exists(),
                }
            )

    # 5. Matrículas actuales
    matriculas_lab_actuales = MatriculaLaboratorio.objects.filter(
        alumno_id=alumno.id
    ).select_related(
        "grupo_laboratorio__grupo_teoria__curso", "grupo_laboratorio__profesor"
    )

    context = {
        "alumno": alumno,
        "laboratorios_disponibles": laboratorios_disponibles,
        "matriculas_lab_actuales": matriculas_lab_actuales,
    }

    return render(request, "siscad/alumno/matricula_laboratorio.html", context)


def generar_asistencias_laboratorio(alumno, grupo_lab):
    """
    Genera asistencias para el laboratorio matriculado por el alumno,
    desde el 2 de septiembre 2025 hasta el 25 de diciembre 2025.
    Si el laboratorio tiene horas consecutivas (bloques), se genera una sola asistencia por bloque.
    """
    print(
        f"🔧 Generando asistencias de laboratorio para {alumno.nombre} - {grupo_lab.grupo_teoria.curso.nombre}"
    )

    # Rango de fechas
    fecha_inicio = date(2025, 9, 2)
    fecha_fin = date(2025, 12, 25)
    fecha_hoy = date.today()

    asistencias_creadas = 0

    # Obtener los horarios del grupo de laboratorio
    horarios_lab = (
        Hora.objects.filter(grupo_laboratorio=grupo_lab)
        .select_related("grupo_laboratorio__grupo_teoria__curso")
        .order_by("dia", "hora_inicio")
    )

    if not horarios_lab.exists():
        print(f"   ⚠️ No se encontraron horarios para el laboratorio {grupo_lab.id}")
        return 0

    # Mapear días
    dias_map = {
        "Monday": "L",
        "Tuesday": "M",
        "Wednesday": "X",
        "Thursday": "J",
        "Friday": "V",
    }

    # Recorrer días desde inicio a fin
    fecha_actual = fecha_inicio
    while fecha_actual <= fecha_fin:
        if fecha_actual.weekday() < 5:  # Solo lunes a viernes
            dia_codigo = dias_map.get(fecha_actual.strftime("%A"))

            # Horarios del laboratorio en ese día
            horarios_dia = [h for h in horarios_lab if h.dia == dia_codigo]
            if horarios_dia:
                # Agrupar bloques consecutivos
                horarios_dia.sort(key=lambda h: h.hora_inicio)
                bloques = []
                bloque_actual = [horarios_dia[0]]

                for i in range(1, len(horarios_dia)):
                    anterior = bloque_actual[-1]
                    actual = horarios_dia[i]
                    if actual.hora_inicio == anterior.hora_fin:
                        bloque_actual.append(actual)
                    else:
                        bloques.append(bloque_actual)
                        bloque_actual = [actual]
                bloques.append(bloque_actual)

                estado = "P" if fecha_actual <= fecha_hoy else "F"

                for bloque in bloques:
                    try:
                        hora_inicio = bloque[0].hora_inicio
                        hora_fin = bloque[-1].hora_fin
                        hora_referencia = bloque[0]

                        # Evitar duplicados
                        asistencia_existente = AsistenciaAlumno.objects.filter(
                            alumno=alumno,
                            fecha=fecha_actual,
                            hora__grupo_laboratorio=grupo_lab,
                        ).exists()

                        if asistencia_existente:
                            continue

                        # Crear asistencia
                        asistencia = AsistenciaAlumno(
                            alumno=alumno,
                            fecha=fecha_actual,
                            estado=estado,
                            hora=hora_referencia,
                        )
                        asistencia.save()
                        asistencias_creadas += 1

                        estado_display = "PRESENTE" if estado == "P" else "FALTA"
                        print(
                            f"   {fecha_actual} - {grupo_lab.grupo_teoria.curso.nombre} (Lab) - {estado_display}"
                        )

                    except Exception as e:
                        print(f"   ❌ Error generando asistencia {fecha_actual}: {e}")
                        continue

        fecha_actual += timedelta(days=1)

    print(f"✅ Total asistencias generadas: {asistencias_creadas}")
    return asistencias_creadas
