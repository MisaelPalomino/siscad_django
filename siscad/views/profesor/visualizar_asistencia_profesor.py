from ..comunes.imports import *


def visualizar_asistencias_profesor(request):
    # 1. Obtener el profesor logueado
    if "email" not in request.session:
        return redirect("login")

    email = request.session["email"]

    try:
        profesor = Profesor.objects.get(email=email)
    except Profesor.DoesNotExist:
        return redirect("login")
    except Profesor.MultipleObjectsReturned:
        profesor = Profesor.objects.filter(email=email).first()

    # 2. Obtener cursos que enseña el profesor (teoría, práctica, laboratorio)
    cursos_ensenados = obtener_cursos_profesor(profesor)

    # 3. Procesar filtro por curso si se envió
    curso_seleccionado_id = request.GET.get("curso_id")
    curso_seleccionado = None
    asistencias_curso = []
    estadisticas_curso = {}

    if curso_seleccionado_id:
        try:
            curso_seleccionado = Curso.objects.get(id=curso_seleccionado_id)
            asistencias_curso = obtener_asistencias_curso_profesor(
                profesor, curso_seleccionado
            )
            estadisticas_curso = calcular_estadisticas_asistencias_profesor(
                asistencias_curso
            )
        except Curso.DoesNotExist:
            pass

    # 4. Preparar contexto
    context = {
        "profesor": profesor,
        "cursos_ensenados": cursos_ensenados,
        "curso_seleccionado": curso_seleccionado,
        "asistencias_curso": asistencias_curso,
        "estadisticas_curso": estadisticas_curso,
        "hoy": datetime.now().date(),
    }

    return render(
        request, "siscad/profesor/visualizar_asistencias_profesor.html", context
    )


def obtener_cursos_profesor(profesor):
    """
    Obtiene todos los cursos que enseña el profesor (teoría, práctica, laboratorio)
    """
    cursos = []

    # Cursos de teoría
    grupos_teoria = GrupoTeoria.objects.filter(profesor=profesor).select_related(
        "curso"
    )
    for grupo in grupos_teoria:
        cursos.append(
            {
                "id": grupo.curso.id,
                "nombre": grupo.curso.nombre,
                "tipo": "Teoría",
                "turno": grupo.turno,
                "grupo_id": grupo.id,
            }
        )

    # Cursos de práctica
    grupos_practica = GrupoPractica.objects.filter(profesor=profesor).select_related(
        "grupo_teoria__curso"
    )
    for grupo in grupos_practica:
        curso = grupo.grupo_teoria.curso
        # Solo agregar si no está ya en la lista
        if not any(c["id"] == curso.id and c["tipo"] == "Práctica" for c in cursos):
            cursos.append(
                {
                    "id": curso.id,
                    "nombre": curso.nombre,
                    "tipo": "Práctica",
                    "turno": grupo.turno,
                    "grupo_id": grupo.id,
                }
            )

    # Cursos de laboratorio
    grupos_lab = GrupoLaboratorio.objects.filter(profesor=profesor).select_related(
        "grupo_teoria__curso"
    )
    for grupo in grupos_lab:
        curso = grupo.grupo_teoria.curso
        # Solo agregar si no está ya en la lista
        if not any(c["id"] == curso.id and c["tipo"] == "Laboratorio" for c in cursos):
            cursos.append(
                {
                    "id": curso.id,
                    "nombre": curso.nombre,
                    "tipo": "Laboratorio",
                    "grupo_lab": grupo.grupo,
                    "grupo_id": grupo.id,
                }
            )

    return cursos


def obtener_asistencias_curso_profesor(profesor, curso):
    """
    Obtiene todas las asistencias del profesor para un curso específico
    """
    # Obtener asistencias relacionadas con este curso
    asistencias = (
        AsistenciaProfesor.objects.filter(profesor=profesor)
        .filter(
            Q(hora__grupo_teoria__curso=curso)
            | Q(hora__grupo_practica__grupo_teoria__curso=curso)
            | Q(hora__grupo_laboratorio__grupo_teoria__curso=curso)
        )
        .select_related(
            "hora__grupo_teoria__curso",
            "hora__grupo_practica__grupo_teoria__curso",
            "hora__grupo_laboratorio__grupo_teoria__curso",
        )
        .order_by("-fecha", "hora__hora_inicio")
    )

    # Formatear los datos para el template
    asistencias_formateadas = []
    for asistencia in asistencias:
        # Determinar tipo de clase y información
        tipo_clase = "Desconocido"
        detalle_clase = ""

        if asistencia.hora.grupo_teoria:
            tipo_clase = "Teoría"
            detalle_clase = f"T-{asistencia.hora.grupo_teoria.turno}"
        elif asistencia.hora.grupo_practica:
            tipo_clase = "Práctica"
            detalle_clase = f"P-{asistencia.hora.grupo_practica.turno}"
        elif asistencia.hora.grupo_laboratorio:
            tipo_clase = "Laboratorio"
            detalle_clase = f"L-{asistencia.hora.grupo_laboratorio.grupo}"

        asistencias_formateadas.append(
            {
                "fecha": asistencia.fecha,
                "dia_semana": asistencia.fecha.strftime("%A"),
                "hora_inicio": asistencia.hora.hora_inicio.strftime("%H:%M"),
                "hora_fin": asistencia.hora.hora_fin.strftime("%H:%M"),
                "tipo_clase": tipo_clase,
                "detalle_clase": detalle_clase,
                "estado": asistencia.estado,
                "estado_display": asistencia.get_estado_display(),
                "aula": asistencia.hora.aula.nombre
                if asistencia.hora.aula
                else "Sin aula",
                "es_pasado": asistencia.fecha < datetime.now().date(),
            }
        )

    return asistencias_formateadas


def calcular_estadisticas_asistencias_profesor(asistencias):
    """
    Calcula estadísticas de asistencias para un curso del profesor
    """
    if not asistencias:
        return {}

    total = len(asistencias)
    presentes = len([a for a in asistencias if a["estado"] == "P"])
    faltas = len([a for a in asistencias if a["estado"] == "F"])

    # Separar por tipo de clase
    teorias = [a for a in asistencias if a["tipo_clase"] == "Teoría"]
    practicas = [a for a in asistencias if a["tipo_clase"] == "Práctica"]
    laboratorios = [a for a in asistencias if a["tipo_clase"] == "Laboratorio"]

    # Calcular porcentajes
    porcentaje_asistencia = (presentes / total * 100) if total > 0 else 0

    return {
        "total": total,
        "presentes": presentes,
        "faltas": faltas,
        "porcentaje_asistencia": round(porcentaje_asistencia, 1),
        "teorias_total": len(teorias),
        "teorias_presentes": len([t for t in teorias if t["estado"] == "P"]),
        "practicas_total": len(practicas),
        "practicas_presentes": len([p for p in practicas if p["estado"] == "P"]),
        "laboratorios_total": len(laboratorios),
        "laboratorios_presentes": len([l for l in laboratorios if l["estado"] == "P"]),
    }
