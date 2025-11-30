from django.shortcuts import render, get_object_or_404, redirect
from ..comunes.imports import *
from datetime import datetime, timedelta


def visualizar_avance_admin(request):
    # Obtener todos los profesores para el filtro
    profesores = Profesor.objects.all().order_by("nombre")

    profesor_seleccionado = None
    avance_cursos = []
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

    # Obtener parámetros del filtro
    profesor_id = request.GET.get("profesor_id")

    if profesor_id:
        profesor_seleccionado = get_object_or_404(Profesor, id=profesor_id)

        # Obtener los grupos de teoría que imparte el profesor
        grupos_teoria = GrupoTeoria.objects.filter(profesor=profesor_seleccionado)

        # Si no tiene grupos de teoría, buscar grupos de práctica/lab
        grupos_practica = GrupoPractica.objects.filter(profesor=profesor_seleccionado)
        grupos_laboratorio = GrupoLaboratorio.objects.filter(
            profesor=profesor_seleccionado
        )

        # Procesar grupos de teoría
        for grupo_teoria in grupos_teoria:
            curso = grupo_teoria.curso
            temas = Tema.objects.filter(grupo_teoria=grupo_teoria)

            total_temas = temas.count()
            temas_completados = temas.filter(estado="H").count()
            temas_pendientes = temas.filter(estado="N").count()

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

            # Calcular tiempo transcurrido y estimado
            estadisticas_tiempo = calcular_estadisticas_tiempo(temas)

            curso_data = {
                "tipo": "Teoría",
                "curso": curso.nombre,
                "turno": grupo_teoria.turno,
                "grupo_id": grupo_teoria.id,
                "total_temas": total_temas,
                "temas_completados": temas_completados,
                "temas_pendientes": temas_pendientes,
                "porcentaje_avance": round(porcentaje_avance, 2),
                "porcentaje_pendiente": round(100 - porcentaje_avance, 2),
                "estado_curso": estado_curso,
                "temas": temas.order_by("fecha"),
                "estadisticas_tiempo": estadisticas_tiempo,
            }
            avance_cursos.append(curso_data)

            # Actualizar estadísticas totales
            actualizar_estadisticas_totales(estadisticas_totales, curso_data)

        # Procesar grupos de práctica
        for grupo_practica in grupos_practica:
            grupo_teoria = grupo_practica.grupo_teoria
            curso = grupo_teoria.curso

            # Para práctica, usar los temas del grupo de teoría correspondiente
            temas = Tema.objects.filter(grupo_teoria=grupo_teoria)

            total_temas = temas.count()
            temas_completados = temas.filter(estado="H").count()
            temas_pendientes = temas.filter(estado="N").count()

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

            # Calcular tiempo transcurrido y estimado
            estadisticas_tiempo = calcular_estadisticas_tiempo(temas)

            curso_data = {
                "tipo": "Práctica",
                "curso": curso.nombre,
                "turno": grupo_practica.turno,
                "grupo_teoria_turno": grupo_teoria.turno,
                "grupo_id": grupo_teoria.id,
                "total_temas": total_temas,
                "temas_completados": temas_completados,
                "temas_pendientes": temas_pendientes,
                "porcentaje_avance": round(porcentaje_avance, 2),
                "porcentaje_pendiente": round(100 - porcentaje_avance, 2),
                "estado_curso": estado_curso,
                "temas": temas.order_by("fecha"),
                "estadisticas_tiempo": estadisticas_tiempo,
            }
            avance_cursos.append(curso_data)

            # Actualizar estadísticas totales
            actualizar_estadisticas_totales(estadisticas_totales, curso_data)

        # Procesar grupos de laboratorio
        for grupo_lab in grupos_laboratorio:
            grupo_teoria = grupo_lab.grupo_teoria
            curso = grupo_teoria.curso

            # Determinar el turno del laboratorio según el grupo
            turno_laboratorio = determinar_turno_laboratorio(grupo_lab.grupo)

            # Para laboratorio, usar los temas del grupo de teoría correspondiente al turno
            grupos_teoria_correspondientes = GrupoTeoria.objects.filter(
                curso=curso, turno=turno_laboratorio
            )

            # Obtener todos los temas de los grupos de teoría correspondientes
            temas_query = Tema.objects.filter(
                grupo_teoria__in=grupos_teoria_correspondientes
            )

            total_temas = temas_query.count()
            temas_completados = temas_query.filter(estado="H").count()
            temas_pendientes = temas_query.filter(estado="N").count()

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

            # Calcular tiempo transcurrido y estimado
            estadisticas_tiempo = calcular_estadisticas_tiempo(temas_query)

            curso_data = {
                "tipo": "Laboratorio",
                "curso": curso.nombre,
                "grupo_lab": grupo_lab.grupo,
                "turno_lab": turno_laboratorio,
                "grupo_teoria_turno": turno_laboratorio,
                "grupo_id": grupos_teoria_correspondientes.first().id
                if grupos_teoria_correspondientes.exists()
                else None,
                "total_temas": total_temas,
                "temas_completados": temas_completados,
                "temas_pendientes": temas_pendientes,
                "porcentaje_avance": round(porcentaje_avance, 2),
                "porcentaje_pendiente": round(100 - porcentaje_avance, 2),
                "estado_curso": estado_curso,
                "temas": temas_query.order_by("fecha"),
                "estadisticas_tiempo": estadisticas_tiempo,
            }
            avance_cursos.append(curso_data)

            # Actualizar estadísticas totales
            actualizar_estadisticas_totales(estadisticas_totales, curso_data)

    # Procesar cambios de estado de temas
    if request.method == "POST":
        tema_id = request.POST.get("tema_id")
        nuevo_estado = request.POST.get("estado")

        if tema_id and nuevo_estado:
            try:
                tema = Tema.objects.get(id=tema_id)
                tema.estado = nuevo_estado
                tema.save()
                messages.success(
                    request,
                    f"Tema '{tema.nombre}' marcado como {'HECHO' if nuevo_estado == 'H' else 'NO HECHO'}",
                )
                return redirect(f"{request.path}?profesor_id={profesor_id}")
            except Tema.DoesNotExist:
                messages.error(request, "El tema no existe")
            except Exception as e:
                messages.error(request, f"Error al actualizar el tema: {str(e)}")

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
        "profesores": profesores,
        "profesor_seleccionado": profesor_seleccionado,
        "avance_cursos": avance_cursos,
        "tiene_grupos": len(avance_cursos) > 0,
        "estadisticas_totales": estadisticas_totales,
        "fecha_actual": datetime.now().date(),
        "profesor_id": profesor_id,
    }

    return render(request, "siscad/admin/visualizar_avance_admin.html", context)


def actualizar_estadisticas_totales(estadisticas_totales, curso_data):
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


def calcular_estadisticas_tiempo(temas):
    """Calcula estadísticas de tiempo para un conjunto de temas"""
    if not temas.exists():
        return {
            "dias_transcurridos": 0,
            "dias_restantes": 0,
            "porcentaje_tiempo": 0,
            "fecha_inicio": None,
            "fecha_fin": None,
            "tendencia": "neutral",
        }

    # Ordenar temas por fecha
    temas_ordenados = temas.order_by("fecha")
    fecha_inicio = temas_ordenados.first().fecha
    fecha_fin = temas_ordenados.last().fecha
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
    temas_completados = temas.filter(estado="H").count()
    temas_totales = temas.count()
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


def determinar_turno_laboratorio(grupo_lab):
    """
    Determina el turno del laboratorio según el grupo.
    A y C -> Turno A
    B y D -> Turno B
    """
    if not grupo_lab:
        return "A"

    grupo_lab = str(grupo_lab).upper().strip()

    if grupo_lab in ["A", "C"]:
        return "A"
    elif grupo_lab in ["B", "D"]:
        return "B"
    else:
        # Por defecto, asumir turno A
        return "A"
