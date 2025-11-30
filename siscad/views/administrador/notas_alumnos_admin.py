from ..comunes.imports import *


def notas_alumno_dni_admin(request):
    if "email" not in request.session or request.session.get("rol") != "Administrador":
        return redirect("login")

    alumno_encontrado = None
    notas_data = []
    estadisticas = {}
    mensaje = ""
    descargar_excel = request.POST.get("descargar_excel")

    if request.method == "POST":
        dni = request.POST.get("dni")

        if dni:
            try:
                alumno_encontrado = Alumno.objects.get(dni=dni)

                # Obtener todas las notas del alumno
                notas = (
                    Nota.objects.filter(alumno=alumno_encontrado)
                    .select_related("curso")
                    .order_by("curso__nombre", "tipo", "periodo")
                )

                # Organizar notas por curso
                cursos_dict = {}
                for nota in notas:
                    curso_nombre = nota.curso.nombre
                    if curso_nombre not in cursos_dict:
                        cursos_dict[curso_nombre] = {
                            "curso": nota.curso,
                            "notas_parciales": [],
                            "notas_continuas": [],
                            "notas_sustitutorio": [],
                        }

                    if nota.tipo == "P":
                        cursos_dict[curso_nombre]["notas_parciales"].append(nota)
                    elif nota.tipo == "C":
                        cursos_dict[curso_nombre]["notas_continuas"].append(nota)
                    elif nota.tipo == "S":
                        cursos_dict[curso_nombre]["notas_sustitutorio"].append(nota)

                # Calcular promedios por curso
                for curso_nombre, datos_curso in cursos_dict.items():
                    todas_notas_curso = (
                        datos_curso["notas_parciales"]
                        + datos_curso["notas_continuas"]
                        + datos_curso["notas_sustitutorio"]
                    )
                    promedio_curso = calcular_promedio_curso(
                        todas_notas_curso, datos_curso["curso"]
                    )

                    notas_data.append(
                        {
                            "curso": datos_curso["curso"],
                            "notas_parciales": datos_curso["notas_parciales"],
                            "notas_continuas": datos_curso["notas_continuas"],
                            "notas_sustitutorio": datos_curso["notas_sustitutorio"],
                            "promedio": promedio_curso,
                            "estado": determinar_estado(promedio_curso),
                        }
                    )

                # Calcular estadísticas generales del alumno
                estadisticas = calcular_estadisticas_alumno_general(notas_data)

                # Descargar Excel si se solicita
                if descargar_excel and notas_data:
                    return generar_excel_notas_alumno(
                        alumno_encontrado, notas_data, estadisticas
                    )

            except Alumno.DoesNotExist:
                mensaje = f"No se encontró ningún alumno con DNI: {dni}"
            except Exception as e:
                mensaje = f"Error al buscar alumno: {str(e)}"

    context = {
        "alumno_encontrado": alumno_encontrado,
        "notas_data": notas_data,
        "estadisticas": estadisticas,
        "mensaje": mensaje,
    }

    return render(request, "siscad/admin/notas_alumno_dni.html", context)


def calcular_estadisticas_alumno_general(notas_data):
    """Calcula estadísticas generales del alumno"""
    if not notas_data:
        return {
            "total_cursos": 0,
            "cursos_con_notas": 0,
            "cursos_aprobados": 0,
            "promedio_general": 0,
            "cursos_sin_notas": 0,
            "porcentaje_aprobados": 0,
        }

    cursos_con_notas = [
        curso_data for curso_data in notas_data if curso_data["promedio"] != -1
    ]
    cursos_aprobados = [
        curso_data for curso_data in cursos_con_notas if curso_data["promedio"] >= 10.5
    ]  # Cambiado a 10.5

    if cursos_con_notas:
        promedios_validos = [curso_data["promedio"] for curso_data in cursos_con_notas]
        promedio_general = statistics.mean(promedios_validos)
    else:
        promedio_general = 0

    return {
        "total_cursos": len(notas_data),
        "cursos_con_notas": len(cursos_con_notas),
        "cursos_aprobados": len(cursos_aprobados),
        "cursos_sin_notas": len(notas_data) - len(cursos_con_notas),
        "promedio_general": round(promedio_general, 2) if cursos_con_notas else 0,
        "porcentaje_aprobados": round(
            (len(cursos_aprobados) / len(cursos_con_notas)) * 100, 2
        )
        if cursos_con_notas
        else 0,
    }


def generar_excel_notas_alumno(alumno, notas_data, estadisticas):
    """Genera archivo Excel con las notas del alumno"""
    # Crear DataFrame con datos de notas
    data = []
    for curso_data in notas_data:
        curso = curso_data["curso"]

        # Combinar todas las notas del curso
        todas_notas = (
            curso_data["notas_parciales"]
            + curso_data["notas_continuas"]
            + curso_data["notas_sustitutorio"]
        )

        for nota in todas_notas:
            data.append(
                {
                    "Curso": curso.nombre,
                    "Semestre": curso.semestre,
                    "Tipo": nota.get_tipo_display(),
                    "Periodo": nota.periodo,
                    "Nota": nota.valor if nota.valor != -1 else "No registrada",
                    "Peso": nota.peso,
                }
            )

    df = pd.DataFrame(data)

    # Crear respuesta HTTP
    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    nombre_archivo = f"notas_{alumno.dni}_{alumno.nombre.replace(' ', '_')}.xlsx"
    response["Content-Disposition"] = f"attachment; filename={nombre_archivo}"

    # Escribir a Excel
    with pd.ExcelWriter(response, engine="openpyxl") as writer:
        # Hoja de notas detalladas
        df.to_excel(writer, sheet_name="Notas Detalladas", index=False)

        # Hoja de resumen por curso
        resumen_data = []
        for curso_data in notas_data:
            curso = curso_data["curso"]
            resumen_data.append(
                {
                    "Curso": curso.nombre,
                    "Semestre": curso.semestre,
                    "Promedio": curso_data["promedio"]
                    if curso_data["promedio"] != -1
                    else "Sin notas",
                    "Estado": curso_data["estado"],
                    "Notas Parciales": len(curso_data["notas_parciales"]),
                    "Notas Continuas": len(curso_data["notas_continuas"]),
                    "Notas Sustitutorio": len(curso_data["notas_sustitutorio"]),
                }
            )

        resumen_df = pd.DataFrame(resumen_data)
        resumen_df.to_excel(writer, sheet_name="Resumen por Curso", index=False)

        # Hoja de estadísticas
        stats_data = {
            "Estadística": [
                "Total Cursos Matriculados",
                "Cursos con Notas",
                "Cursos sin Notas",
                "Cursos Aprobados",
                "Promedio General",
                "% de Aprobación",
            ],
            "Valor": [
                estadisticas["total_cursos"],
                estadisticas["cursos_con_notas"],
                estadisticas["cursos_sin_notas"],
                estadisticas["cursos_aprobados"],
                estadisticas["promedio_general"],
                f"{estadisticas['porcentaje_aprobados']}%",
            ],
        }
        stats_df = pd.DataFrame(stats_data)
        stats_df.to_excel(writer, sheet_name="Estadísticas", index=False)

        # Ajustar anchos de columna
        for sheet_name in writer.sheets:
            worksheet = writer.sheets[sheet_name]
            if sheet_name == "Notas Detalladas":
                worksheet.column_dimensions["A"].width = 30
                worksheet.column_dimensions["B"].width = 10
                worksheet.column_dimensions["C"].width = 15
                worksheet.column_dimensions["D"].width = 10
                worksheet.column_dimensions["E"].width = 10
                worksheet.column_dimensions["F"].width = 10
            elif sheet_name == "Resumen por Curso":
                worksheet.column_dimensions["A"].width = 30
                worksheet.column_dimensions["B"].width = 10
                worksheet.column_dimensions["C"].width = 10
                worksheet.column_dimensions["D"].width = 15
                worksheet.column_dimensions["E"].width = 15
                worksheet.column_dimensions["F"].width = 15
                worksheet.column_dimensions["G"].width = 18
            else:
                worksheet.column_dimensions["A"].width = 25
                worksheet.column_dimensions["B"].width = 15

    return response


def calcular_promedio_curso(notas_alumno, curso):
    """Calcula el promedio de un alumno en un curso, considerando -1 como nota no registrada"""
    if not notas_alumno:
        return -1  # No tiene notas

    # Filtrar solo notas válidas (diferentes de -1 y no nulas)
    notas_validas = [
        nota.valor
        for nota in notas_alumno
        if nota.valor is not None and nota.valor != -1
    ]

    if not notas_validas:
        return -1  # Todas las notas son -1 o nulas

    # Calcular promedio simple (puedes ajustar la lógica según tus pesos)
    return statistics.mean(notas_validas)


def determinar_estado(promedio):
    """Determina el estado del alumno basado en su promedio"""
    if promedio == -1:
        return "Sin notas"
    elif promedio >= 10.5:
        return "Aprobado"
    elif promedio >= 21:
        return "En recuperación"
    else:
        return "Desaprobado"
