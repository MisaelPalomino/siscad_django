from ..comunes.imports import *


def visualizar_horario_alumno_admin(request):
    # Obtener parámetros del filtro
    dni_alumno = request.GET.get("dni_alumno")
    alumno_seleccionado = None
    tabla_horarios = {}
    dias_lista = []
    tiene_laboratorios = False
    total_laboratorios = 0

    if dni_alumno:
        try:
            alumno_seleccionado = Alumno.objects.get(dni=dni_alumno)

            # 2. Obtener todas sus matrículas de curso
            matriculas_curso = MatriculaCurso.objects.filter(
                alumno=alumno_seleccionado
            ).select_related("curso")

            # 3. Obtener todas sus matrículas de laboratorio
            matriculas_lab = MatriculaLaboratorio.objects.filter(
                alumno=alumno_seleccionado
            ).select_related(
                "grupo_laboratorio__grupo_teoria__curso", "grupo_laboratorio__profesor"
            )

            # 4. Obtener todos los cursos inscritos y sus turnos (para teoría y práctica)
            cursos_turnos = {m.curso_id: m.turno for m in matriculas_curso}
            cursos_ids = list(cursos_turnos.keys())

            # 5. Obtener IDs de grupos de laboratorio matriculados (para laboratorios)
            grupos_lab_ids = [ml.grupo_laboratorio_id for ml in matriculas_lab]

            if not cursos_ids and not grupos_lab_ids:
                cursos_ids = []
                grupos_lab_ids = []

            # 6. Buscar horarios relacionados - INCLUYENDO LABORATORIOS
            horarios = (
                Hora.objects.select_related(
                    "aula",
                    "grupo_teoria__curso",
                    "grupo_practica__grupo_teoria__curso",
                    "grupo_laboratorio__grupo_teoria__curso",
                    "grupo_laboratorio__profesor",
                )
                .filter(
                    # Coincidencia con teoría del mismo turno
                    Q(
                        grupo_teoria__curso_id__in=cursos_ids,
                        grupo_teoria__turno__in=[
                            turno for turno in cursos_turnos.values()
                        ],
                    )
                    |
                    # Coincidencia con práctica del mismo turno
                    Q(
                        grupo_practica__grupo_teoria__curso_id__in=cursos_ids,
                        grupo_practica__turno__in=[
                            turno for turno in cursos_turnos.values()
                        ],
                    )
                    |
                    # Coincidencia con laboratorios matriculados
                    Q(grupo_laboratorio_id__in=grupos_lab_ids)
                )
                .order_by("dia", "hora_inicio")
            )

            # 7. Construir estructura para mostrar
            dias_lista = [
                ("L", "Lunes"),
                ("M", "Martes"),
                ("X", "Miércoles"),
                ("J", "Jueves"),
                ("V", "Viernes"),
            ]

            # Crear estructura de datos
            tabla_horarios = {}
            for h in horarios:
                bloque = f"{h.hora_inicio.strftime('%H:%M')} - {h.hora_fin.strftime('%H:%M')}"
                dia = h.dia

                # Determinar si el horario debe mostrarse (filtrado por turno para teoría/práctica)
                mostrar_horario = False
                info_curso = ""

                if h.grupo_teoria:
                    curso_id = h.grupo_teoria.curso_id
                    turno_horario = h.grupo_teoria.turno
                    turno_alumno = cursos_turnos.get(curso_id)

                    # Mostrar solo si el turno coincide
                    if turno_horario == turno_alumno:
                        mostrar_horario = True
                        curso = h.grupo_teoria.curso.nombre
                        grupo = f"T-{turno_horario}"
                        aula_info = f" ({h.aula.nombre})" if h.aula else ""
                        info_curso = f"{curso} {grupo}{aula_info}"

                elif h.grupo_practica:
                    curso_id = h.grupo_practica.grupo_teoria.curso_id
                    turno_horario = h.grupo_practica.turno
                    turno_alumno = cursos_turnos.get(curso_id)

                    # Mostrar solo si el turno coincide
                    if turno_horario == turno_alumno:
                        mostrar_horario = True
                        curso = h.grupo_practica.grupo_teoria.curso.nombre
                        grupo = f"P-{turno_horario}"
                        aula_info = f" ({h.aula.nombre})" if h.aula else ""
                        info_curso = f"{curso} {grupo}{aula_info}"

                elif h.grupo_laboratorio:
                    # Para laboratorios, mostrar siempre (ya están filtrados por matrícula)
                    mostrar_horario = True
                    curso = h.grupo_laboratorio.grupo_teoria.curso.nombre
                    grupo = f"L-{h.grupo_laboratorio.grupo}"
                    aula_info = f" ({h.aula.nombre})" if h.aula else ""
                    profesor_info = (
                        f" - {h.grupo_laboratorio.profesor.nombre}"
                        if h.grupo_laboratorio.profesor
                        else ""
                    )
                    info_curso = f"{curso} {grupo}{aula_info}{profesor_info}"

                # Si el horario debe mostrarse, agregarlo a la tabla
                if mostrar_horario and info_curso:
                    # Usar "Horario General" como clave única para simplificar
                    aula_key = "Horario General"

                    if aula_key not in tabla_horarios:
                        tabla_horarios[aula_key] = {}

                    if bloque not in tabla_horarios[aula_key]:
                        tabla_horarios[aula_key][bloque] = {
                            d: "" for d, _ in dias_lista
                        }

                    tabla_horarios[aula_key][bloque][dia] = info_curso

            # Ordenar por hora
            for aula in tabla_horarios:
                tabla_horarios[aula] = dict(
                    sorted(tabla_horarios[aula].items(), key=lambda x: x[0])
                )

            tiene_laboratorios = len(grupos_lab_ids) > 0
            total_laboratorios = len(grupos_lab_ids)

        except Alumno.DoesNotExist:
            messages.error(
                request, f"No se encontró ningún alumno con DNI: {dni_alumno}"
            )
        except Exception as e:
            messages.error(request, f"Error al cargar el horario: {str(e)}")

    context = {
        "alumno_seleccionado": alumno_seleccionado,
        "dni_alumno": dni_alumno or "",
        "dias_lista": dias_lista,
        "tabla_horarios": {
            aula: [
                {
                    "bloque": bloque,
                    "dias": [(dia, dias_data[dia]) for dia, _ in dias_lista],
                }
                for bloque, dias_data in bloques.items()
            ]
            for aula, bloques in tabla_horarios.items()
        },
        "tiene_laboratorios": tiene_laboratorios,
        "total_laboratorios": total_laboratorios,
    }

    return render(
        request, "siscad/admin/visualizar_horario_alumno_admin.html", context
    )
