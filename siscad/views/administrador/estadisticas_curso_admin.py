from ..comunes.imports import *
import statistics
import pandas as pd
from django.http import HttpResponse
from django.db.models import Q


def estadisticas_curso_admin(request):
    if "email" not in request.session or request.session.get("rol") != "Administrador":
        return redirect("login")

    cursos = Curso.objects.all()
    curso_seleccionado = None
    estadisticas = {}
    alumnos_data = []
    descargar_excel = request.POST.get("descargar_excel")

    if request.method == "POST":
        curso_id = request.POST.get("curso_id")

        if curso_id:
            curso_seleccionado = get_object_or_404(Curso, id=curso_id)

            # Obtener todos los alumnos matriculados en el curso
            matriculas = MatriculaCurso.objects.filter(
                curso=curso_seleccionado
            ).select_related("alumno")

            # Calcular estadísticas para cada alumno
            promedios_alumnos = []
            for matricula in matriculas:
                alumno = matricula.alumno
                notas_alumno = Nota.objects.filter(
                    alumno=alumno, curso=curso_seleccionado
                )

                promedio_alumno = calcular_promedio_curso(
                    notas_alumno, curso_seleccionado
                )

                alumnos_data.append(
                    {
                        "alumno": alumno,
                        "turno": matricula.turno,
                        "promedio": promedio_alumno,
                        "total_notas": notas_alumno.count(),
                        "estado": determinar_estado(promedio_alumno),
                    }
                )

                if promedio_alumno is not None and promedio_alumno != -1:
                    promedios_alumnos.append(promedio_alumno)

            # Calcular estadísticas generales del curso
            estadisticas = calcular_estadisticas_generales(
                promedios_alumnos, alumnos_data
            )

            # Descargar Excel si se solicita
            if descargar_excel and alumnos_data:
                return generar_excel_estadisticas_curso(
                    alumnos_data, curso_seleccionado, estadisticas
                )

    context = {
        "cursos": cursos,
        "curso_seleccionado": curso_seleccionado,
        "estadisticas": estadisticas,
        "alumnos_data": alumnos_data,
    }

    return render(request, "siscad/admin/estadisticas_curso.html", context)


def calcular_promedio_curso(notas_alumno, curso):
    """Calcula el promedio de un alumno en un curso, considerando -1 como nota no registrada"""
    if not notas_alumno.exists():
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


def calcular_estadisticas_generales(promedios_validos, alumnos_data):
    """Calcula estadísticas generales del curso"""
    if not promedios_validos:
        return {
            'total_alumnos': len(alumnos_data),
            'alumnos_con_notas': 0,
            'alumnos_sin_notas': len(alumnos_data),
            'promedio_curso': 0,
            'nota_maxima': 0,
            'nota_minima': 0,
            'aprobados': 0,
            'desaprobados': 0,
            'porcentaje_aprobados': 0
        }
    
    # Filtrar alumnos con notas válidas
    alumnos_con_notas = [alumno for alumno in alumnos_data if alumno['promedio'] != -1]
    alumnos_aprobados = [alumno for alumno in alumnos_con_notas if alumno['promedio'] >= 10.5]  # Cambiado a 10.5
    
    return {
        'total_alumnos': len(alumnos_data),
        'alumnos_con_notas': len(alumnos_con_notas),
        'alumnos_sin_notas': len(alumnos_data) - len(alumnos_con_notas),
        'promedio_curso': round(statistics.mean(promedios_validos), 2),
        'nota_maxima': round(max(promedios_validos), 2),
        'nota_minima': round(min(promedios_validos), 2),
        'aprobados': len(alumnos_aprobados),
        'desaprobados': len(alumnos_con_notas) - len(alumnos_aprobados),
        'porcentaje_aprobados': round((len(alumnos_aprobados) / len(alumnos_con_notas)) * 100, 2) if alumnos_con_notas else 0
    }


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


def generar_excel_estadisticas_curso(alumnos_data, curso, estadisticas):
    """Genera archivo Excel con las estadísticas del curso"""
    # Crear DataFrame con datos de alumnos
    data = []
    for alumno_data in alumnos_data:
        alumno = alumno_data["alumno"]
        data.append(
            {
                "DNI": alumno.dni,
                "Nombre": alumno.nombre,
                "Email": alumno.email,
                "CUI": alumno.cui,
                "Semestre": alumno.semestre_asignado,
                "Turno": alumno_data["turno"],
                "Promedio": alumno_data["promedio"]
                if alumno_data["promedio"] != -1
                else "Sin notas",
                "Estado": alumno_data["estado"],
                "Total Notas": alumno_data["total_notas"],
            }
        )

    df = pd.DataFrame(data)

    # Crear respuesta HTTP
    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    nombre_archivo = f"estadisticas_{curso.nombre.replace(' ', '_')}.xlsx"
    response["Content-Disposition"] = f"attachment; filename={nombre_archivo}"

    # Escribir a Excel
    with pd.ExcelWriter(response, engine="openpyxl") as writer:
        # Hoja de alumnos
        df.to_excel(writer, sheet_name="Alumnos", index=False)

        # Hoja de estadísticas
        stats_data = {
            "Estadística": [
                "Total Alumnos",
                "Alumnos con Notas",
                "Alumnos sin Notas",
                "Promedio del Curso",
                "Nota Máxima",
                "Nota Mínima",
                "Aprobados",
                "Desaprobados",
                "% Aprobados",
            ],
            "Valor": [
                estadisticas["total_alumnos"],
                estadisticas["alumnos_con_notas"],
                estadisticas["alumnos_sin_notas"],
                estadisticas["promedio_curso"],
                estadisticas["nota_maxima"],
                estadisticas["nota_minima"],
                estadisticas["aprobados"],
                estadisticas["desaprobados"],
                f"{estadisticas['porcentaje_aprobados']}%",
            ],
        }
        stats_df = pd.DataFrame(stats_data)
        stats_df.to_excel(writer, sheet_name="Estadísticas", index=False)

        # Ajustar anchos de columna
        for sheet_name in writer.sheets:
            worksheet = writer.sheets[sheet_name]
            if sheet_name == "Alumnos":
                worksheet.column_dimensions["A"].width = 15
                worksheet.column_dimensions["B"].width = 30
                worksheet.column_dimensions["C"].width = 25
                worksheet.column_dimensions["D"].width = 15
                worksheet.column_dimensions["E"].width = 10
                worksheet.column_dimensions["F"].width = 10
                worksheet.column_dimensions["G"].width = 10
                worksheet.column_dimensions["H"].width = 15
                worksheet.column_dimensions["I"].width = 12
            else:
                worksheet.column_dimensions["A"].width = 20
                worksheet.column_dimensions["B"].width = 15

    return response
