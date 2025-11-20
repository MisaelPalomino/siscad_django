from django.shortcuts import render, get_object_or_404, redirect
from ..comunes.imports import *
from datetime import datetime


def visualizar_progreso_estudiante(request):
    # Verificar si el usuario está logueado por sesión
    if "email" not in request.session:
        return redirect("login")

    estudiante = get_object_or_404(Alumno, email=request.session["email"])

    # Obtener las matrículas del estudiante
    matriculas_curso = MatriculaCurso.objects.filter(alumno=estudiante).select_related(
        "curso"
    )

    progreso_cursos = []
    estadisticas_totales = {
        "total_cursos": 0,
        "total_temas": 0,
        "total_completados": 0,
        "total_pendientes": 0,
        "porcentaje_total": 0,
        "cursos_completados": 0,
        "cursos_en_progreso": 0,
        "cursos_sin_iniciar": 0,
    }

    for matricula in matriculas_curso:
        curso = matricula.curso
        turno = matricula.turno

        # Obtener los temas del curso según el turno del estudiante
        temas_curso = obtener_temas_curso_estudiante(curso, turno, estudiante)

        total_temas = len(temas_curso)
        temas_completados = len([tema for tema in temas_curso if tema["estado"] == "H"])
        temas_pendientes = total_temas - temas_completados

        porcentaje_avance = (
            (temas_completados / total_temas * 100) if total_temas > 0 else 0
        )

        # Determinar estado del curso
        if porcentaje_avance == 0:
            estado_curso = "Sin iniciar"
        elif porcentaje_avance == 100:
            estado_curso = "Completado"
        else:
            estado_curso = "En progreso"

        # Calcular estadísticas de tiempo
        estadisticas_tiempo = calcular_estadisticas_tiempo_estudiante(temas_curso)

        curso_data = {
            "curso": curso.nombre,
            "codigo": curso.codigo or "0000",
            "turno": turno,
            "semestre": curso.semestre,
            "total_temas": total_temas,
            "temas_completados": temas_completados,
            "temas_pendientes": temas_pendientes,
            "porcentaje_avance": round(porcentaje_avance, 2),
            "porcentaje_pendiente": round(100 - porcentaje_avance, 2),
            "estado_curso": estado_curso,
            "temas": temas_curso,
            "estadisticas_tiempo": estadisticas_tiempo,
        }
        progreso_cursos.append(curso_data)

        # Actualizar estadísticas totales
        actualizar_estadisticas_totales_estudiante(estadisticas_totales, curso_data)

    # Calcular porcentaje total
    if estadisticas_totales["total_temas"] > 0:
        estadisticas_totales["porcentaje_total"] = round(
            (
                estadisticas_totales["total_completados"]
                / estadisticas_totales["total_temas"]
                * 100
            ),
            2,
        )

    context = {
        "estudiante": estudiante,
        "progreso_cursos": progreso_cursos,
        "tiene_cursos": len(progreso_cursos) > 0,
        "estadisticas_totales": estadisticas_totales,
        "fecha_actual": datetime.now().date(),
    }

    return render(request, "siscad/alumno/visualizar_progreso.html", context)


def obtener_temas_curso_estudiante(curso, turno, estudiante):
    """
    Obtiene los temas de un curso según el turno del estudiante
    """
    try:
        # Buscar grupos de teoría que coincidan con el curso y turno del estudiante
        grupos_teoria = GrupoTeoria.objects.filter(curso=curso, turno=turno)

        if not grupos_teoria.exists():
            return []

        # Obtener todos los temas de los grupos de teoría correspondientes
        temas_query = (
            Tema.objects.filter(grupo_teoria__in=grupos_teoria)
            .select_related("grupo_teoria")
            .order_by("fecha")
        )

        # Formatear los temas
        temas_formateados = []
        for tema in temas_query:
            temas_formateados.append(
                {
                    "id": tema.id,
                    "nombre": tema.nombre,
                    "fecha": tema.fecha,
                    "estado": tema.estado,
                    "estado_display": "HECHO" if tema.estado == "H" else "NO HECHO",
                    "grupo_teoria": tema.grupo_teoria.turno,
                    "es_pasado": tema.fecha < datetime.now().date(),
                }
            )

        return temas_formateados

    except Exception as e:
        print(f"Error al obtener temas para estudiante: {str(e)}")
        return []


def calcular_estadisticas_tiempo_estudiante(temas):
    """
    Calcula estadísticas de tiempo para los temas de un estudiante
    """
    if not temas:
        return {
            "dias_transcurridos": 0,
            "dias_restantes": 0,
            "porcentaje_tiempo": 0,
            "fecha_inicio": None,
            "fecha_fin": None,
            "tendencia": "neutral",
        }

    # Ordenar temas por fecha
    temas_ordenados = sorted(temas, key=lambda x: x["fecha"])

    if not temas_ordenados:
        return {
            "dias_transcurridos": 0,
            "dias_restantes": 0,
            "porcentaje_tiempo": 0,
            "fecha_inicio": None,
            "fecha_fin": None,
            "tendencia": "neutral",
        }

    fecha_inicio = temas_ordenados[0]["fecha"]
    fecha_fin = temas_ordenados[-1]["fecha"]
    fecha_actual = datetime.now().date()

    # Calcular días transcurridos y restantes
    total_dias = (fecha_fin - fecha_inicio).days
    dias_transcurridos = (fecha_actual - fecha_inicio).days

    # Asegurar que los valores estén en rangos válidos
    dias_transcurridos = max(0, min(dias_transcurridos, total_dias))
    dias_restantes = max(0, total_dias - dias_transcurridos)

    # Calcular porcentaje de tiempo
    porcentaje_tiempo = (dias_transcurridos / total_dias * 100) if total_dias > 0 else 0

    # Determinar tendencia
    temas_completados = len([tema for tema in temas if tema["estado"] == "H"])
    temas_totales = len(temas)
    porcentaje_avance = (
        (temas_completados / temas_totales * 100) if temas_totales > 0 else 0
    )

    if porcentaje_avance > porcentaje_tiempo + 10:
        tendencia = "adelantado"
    elif porcentaje_avance < porcentaje_tiempo - 10:
        tendencia = "atrasado"
    else:
        tendencia = "en_tiempo"

    return {
        "dias_transcurridos": dias_transcurridos,
        "dias_restantes": dias_restantes,
        "porcentaje_tiempo": round(porcentaje_tiempo, 2),
        "fecha_inicio": fecha_inicio,
        "fecha_fin": fecha_fin,
        "tendencia": tendencia,
    }


def actualizar_estadisticas_totales_estudiante(estadisticas_totales, curso_data):
    """Actualiza las estadísticas totales con los datos del curso"""
    estadisticas_totales["total_cursos"] += 1
    estadisticas_totales["total_temas"] += curso_data["total_temas"]
    estadisticas_totales["total_completados"] += curso_data["temas_completados"]
    estadisticas_totales["total_pendientes"] += curso_data["temas_pendientes"]

    # Contar cursos por estado
    if curso_data["estado_curso"] == "Completado":
        estadisticas_totales["cursos_completados"] += 1
    elif curso_data["estado_curso"] == "En progreso":
        estadisticas_totales["cursos_en_progreso"] += 1
    else:
        estadisticas_totales["cursos_sin_iniciar"] += 1
