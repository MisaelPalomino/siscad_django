from ..comunes.imports import *


def visualizar_horario_profesor(request):
    if "email" not in request.session:
        return redirect("login")

    profesor = get_object_or_404(Profesor, email=request.session["email"])

    hoy = date.today()
    dia_semana = hoy.weekday()  # lunes=0 ... domingo=6
    if dia_semana >= 5:  # si es sábado o domingo → próxima semana
        inicio_semana = hoy + timedelta(days=(7 - dia_semana))
    else:
        inicio_semana = hoy - timedelta(days=dia_semana)

    fin_semana = inicio_semana + timedelta(days=4)  # lunes a viernes

    reservas_semana = Reserva.objects.filter(
        profesor=profesor, fecha__range=(inicio_semana, fin_semana)
    ).select_related("aula")

    horarios = (
        Hora.objects.select_related(
            "aula",
            "grupo_teoria__curso",
            "grupo_practica__grupo_teoria__curso",
            "grupo_laboratorio__grupo_teoria__curso",
        )
        .filter(
            Q(grupo_teoria__profesor=profesor)
            | Q(grupo_practica__profesor=profesor)
            | Q(grupo_laboratorio__profesor=profesor)
        )
        .order_by("dia", "hora_inicio")
    )

    dias_lista = [
        ("L", "Lunes"),
        ("M", "Martes"),
        ("X", "Miércoles"),
        ("J", "Jueves"),
        ("V", "Viernes"),
    ]

    tabla_horarios = {}
    for h in horarios:
        bloque = f"{h.hora_inicio.strftime('%H:%M')} - {h.hora_fin.strftime('%H:%M')}"
        dia = h.dia

        aula_key = "Horario del Profesor"
        if aula_key not in tabla_horarios:
            tabla_horarios[aula_key] = {}
        if bloque not in tabla_horarios[aula_key]:
            tabla_horarios[aula_key][bloque] = {d: "" for d, _ in dias_lista}

        if h.grupo_teoria:
            curso = h.grupo_teoria.curso.nombre
            grupo = f"T-{h.grupo_teoria.turno}"
            tipo_info = "Teoría"
        elif h.grupo_practica:
            curso = h.grupo_practica.grupo_teoria.curso.nombre
            grupo = f"P-{h.grupo_practica.turno}"
            tipo_info = "Práctica"
        elif h.grupo_laboratorio:
            curso = h.grupo_laboratorio.grupo_teoria.curso.nombre
            grupo = f"L-{h.grupo_laboratorio.grupo}"
            tipo_info = "Laboratorio"
        else:
            curso, grupo, tipo_info = "Sin asignar", "", ""

        aula_info = f" ({h.aula.nombre})" if h.aula else ""
        info_curso = f"{curso} {grupo} - {tipo_info}{aula_info}"

        tabla_horarios[aula_key][bloque][dia] = info_curso

    for r in reservas_semana:
        dia_letra = ["L", "M", "X", "J", "V"][r.fecha.weekday()]
        horas_reserva = Hora.objects.filter(reserva=r)

        for h in horas_reserva:
            bloque = (
                f"{h.hora_inicio.strftime('%H:%M')} - {h.hora_fin.strftime('%H:%M')}"
            )
            aula_key = "Horario del Profesor"
            if aula_key not in tabla_horarios:
                tabla_horarios[aula_key] = {}
            if bloque not in tabla_horarios[aula_key]:
                tabla_horarios[aula_key][bloque] = {d: "" for d, _ in dias_lista}

            tabla_horarios[aula_key][bloque][dia_letra] = (
                f"🟢 Reserva ({r.aula.nombre})"
            )

    for aula in tabla_horarios:
        tabla_horarios[aula] = dict(
            sorted(tabla_horarios[aula].items(), key=lambda x: x[0])
        )

    total_reservas_activas = Reserva.objects.filter(
        profesor=profesor, fecha__gte=hoy
    ).count()
    reservas_disponibles = max(0, profesor.cantidad_reservas - total_reservas_activas)

    estadisticas = {
        "total_horarios": horarios.count(),
        "total_teoria": horarios.filter(grupo_teoria__profesor=profesor).count(),
        "total_practica": horarios.filter(grupo_practica__profesor=profesor).count(),
        "total_laboratorio": horarios.filter(
            grupo_laboratorio__profesor=profesor
        ).count(),
        "cursos_unicos": len(
            set(
                [h.grupo_teoria.curso_id for h in horarios if h.grupo_teoria]
                + [
                    h.grupo_practica.grupo_teoria.curso_id
                    for h in horarios
                    if h.grupo_practica
                ]
                + [
                    h.grupo_laboratorio.grupo_teoria.curso_id
                    for h in horarios
                    if h.grupo_laboratorio
                ]
            )
        ),
        "reservas_disponibles": reservas_disponibles,
        "reservas_activas": total_reservas_activas,
        "semana": f"{inicio_semana.strftime('%d/%m/%Y')} - {fin_semana.strftime('%d/%m/%Y')}",
    }

    context = {
        "profesor": profesor,
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
        "estadisticas": estadisticas,
    }

    return render(request, "siscad/profesor/visualizar_horario_profesor.html", context)
