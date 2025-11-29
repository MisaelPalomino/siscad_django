from ..comunes.imports import *


def registrar_asistencia_alumnos_admin(request):
    if "email" not in request.session or request.session.get("rol") != "Administrador":
        return redirect("login")

    # Valores iniciales
    alumnos_asistencia = []
    fecha_seleccionada = timezone.localdate()
    hora_seleccionada = None
    grupo_seleccionado = None
    mensaje = ""

    # Obtener todos los grupos de teoría de cursos de semestres pares
    grupos = []
    for gt in GrupoTeoria.objects.filter(curso__semestre__in=[2, 4, 6, 8, 10]):
        grupos.append(
            {
                "id": gt.id,
                "nombre": f"{gt.curso.nombre} - Teoría {gt.turno} - Semestre {gt.curso.semestre}",
                "tipo": "teoria",
                "objeto": gt,
            }
        )

    if request.method == "POST":
        grupo_id = request.POST.get("grupo_id")
        grupo_tipo = request.POST.get("grupo_tipo")
        fecha_input = request.POST.get("fecha")
        usar_hora_actual = request.POST.get("usar_hora_actual")

        # Procesar fecha
        if fecha_input:
            try:
                fecha_seleccionada = datetime.strptime(fecha_input, "%Y-%m-%d").date()
            except ValueError:
                fecha_seleccionada = timezone.localdate()
        else:
            fecha_seleccionada = timezone.localdate()

        # Obtener el día de la semana correctamente considerando timezone
        fecha_tz = timezone.make_aware(
            datetime.combine(fecha_seleccionada, datetime.min.time())
        )
        dia_numero = (
            fecha_tz.weekday()
        )  # 0=Lunes, 1=Martes, 2=Miércoles, 3=Jueves, 4=Viernes
        dias_map = {
            0: "L",  # Lunes
            1: "M",  # Martes
            2: "X",  # Miércoles
            3: "J",  # Jueves
            4: "V",  # Viernes
        }
        dia_codigo = dias_map.get(dia_numero, "")

        print(
            f"DEBUG: Fecha: {fecha_seleccionada}, Día número: {dia_numero}, Día código: {dia_codigo}"
        )

        # Obtener grupo seleccionado
        if grupo_tipo and grupo_id:
            if grupo_tipo == "teoria":
                grupo_seleccionado = get_object_or_404(GrupoTeoria, id=grupo_id)

        # Determinar hora seleccionada automáticamente basada en el grupo y día
        if grupo_seleccionado and dia_codigo:
            hora_seleccionada = obtener_hora_para_grupo_admin(
                grupo_seleccionado, grupo_tipo, dia_codigo
            )
            print(f"DEBUG: Hora encontrada para el grupo: {hora_seleccionada}")

        # Si se usa hora actual, buscar la hora correspondiente
        if usar_hora_actual and grupo_seleccionado and dia_codigo:
            ahora = timezone.localtime()
            hora_actual = ahora.time()
            fecha_seleccionada = ahora.date()

            # Recalcular día de la semana con la fecha actual
            dia_numero_actual = ahora.weekday()
            dia_codigo_actual = dias_map.get(dia_numero_actual, "")

            if dia_codigo_actual:
                # Buscar hora actual para el grupo
                hora_seleccionada = obtener_hora_actual_para_grupo_admin(
                    grupo_seleccionado, grupo_tipo, dia_codigo_actual, hora_actual
                )
                print(f"DEBUG: Hora actual encontrada: {hora_seleccionada}")

        # Obtener alumnos según tipo de grupo
        if grupo_tipo and grupo_id and hora_seleccionada:
            alumnos = obtener_alumnos_para_grupo_admin(grupo_seleccionado, grupo_tipo)
            print(f"DEBUG: Alumnos encontrados: {alumnos.count()}")

            # Cargar asistencias existentes
            asistencias_existentes = AsistenciaAlumno.objects.filter(
                fecha=fecha_seleccionada, hora=hora_seleccionada, alumno__in=alumnos
            )
            asistencia_dict = {a.alumno_id: a.estado for a in asistencias_existentes}

            # Crear lista de alumnos con su estado de asistencia
            alumnos_asistencia = []
            for alumno in alumnos:
                estado = asistencia_dict.get(alumno.id, "F")  # Por defecto Falta
                alumnos_asistencia.append(
                    {"alumno": alumno, "estado": estado, "id": alumno.id}
                )

            print(f"DEBUG: Alumnos para asistencia: {len(alumnos_asistencia)}")

        # Guardar asistencias
        if (
            "guardar_asistencia" in request.POST
            and grupo_seleccionado
            and hora_seleccionada
        ):
            for alumno_data in alumnos_asistencia:
                alumno_id = alumno_data["alumno"].id
                estado = request.POST.get(f"asistencia_{alumno_id}", "F")

                AsistenciaAlumno.objects.update_or_create(
                    alumno_id=alumno_id,
                    fecha=fecha_seleccionada,
                    hora=hora_seleccionada,
                    defaults={"estado": estado},
                )

            mensaje = "Asistencias guardadas correctamente"
            print("DEBUG: Asistencias guardadas correctamente")
            # Redirigir para evitar reenvío del formulario
            return redirect("registrar_asistencia_alumnos_admin")

    context = {
        "grupos": grupos,
        "alumnos_asistencia": alumnos_asistencia,
        "fecha": fecha_seleccionada,
        "hora": hora_seleccionada,
        "grupo_seleccionado": grupo_seleccionado,
        "mensaje": mensaje,
    }
    return render(request, "siscad/admin/registrar_asistencia_alumnos.html", context)


def obtener_hora_para_grupo_admin(grupo, grupo_tipo, dia_codigo):
    """
    Obtiene la hora automáticamente para un grupo en un día específico (versión admin)
    """
    try:
        if grupo_tipo == "teoria":
            # Buscar horas de teoría para este grupo en el día específico
            horas = Hora.objects.filter(
                grupo_teoria=grupo,
                dia=dia_codigo,
                tipo="T",  # Teoría
            ).order_by("hora_inicio")

            # Si hay múltiples horas, tomar la primera
            if horas.exists():
                return horas.first()

            # Si no encuentra hora específica, buscar cualquier hora para ese grupo y día
            horas = Hora.objects.filter(grupo_teoria=grupo, dia=dia_codigo)
            return horas.first() if horas.exists() else None

    except Exception as e:
        print(f"ERROR obteniendo hora para grupo admin: {e}")
        return None


def obtener_hora_actual_para_grupo_admin(grupo, grupo_tipo, dia_codigo, hora_actual):
    """
    Obtiene la hora actual para un grupo basado en la hora del sistema (versión admin)
    """
    try:
        if grupo_tipo == "teoria":
            horas = Hora.objects.filter(
                grupo_teoria=grupo,
                dia=dia_codigo,
                hora_inicio__lte=hora_actual,
                hora_fin__gte=hora_actual,
            )

            # Si encuentra una hora que coincide con la hora actual, usarla
            if horas.exists():
                return horas.first()

            # Si no encuentra hora actual, buscar la primera hora del día para ese grupo
            return obtener_hora_para_grupo_admin(grupo, grupo_tipo, dia_codigo)

    except Exception as e:
        print(f"ERROR obteniendo hora actual para grupo admin: {e}")
        return None


def obtener_alumnos_para_grupo_admin(grupo, grupo_tipo):
    """
    Obtiene los alumnos para un grupo específico (versión admin)
    """
    try:
        if grupo_tipo == "teoria":
            # Alumnos matriculados en el curso con el mismo turno
            alumnos = Alumno.objects.filter(
                matriculas_curso__curso=grupo.curso, matriculas_curso__turno=grupo.turno
            ).distinct()
            return alumnos

    except Exception as e:
        print(f"ERROR obteniendo alumnos para grupo admin: {e}")
        return Alumno.objects.none()
