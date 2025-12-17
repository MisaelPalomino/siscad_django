from ..comunes.imports import *


def visualizar_horarios_aulas(request):
    dias = ["L", "M", "X", "J", "V"]
    dias_nombres = {
        "L": "Lunes",
        "M": "Martes",
        "X": "Miércoles",
        "J": "Jueves",
        "V": "Viernes",
    }

    dias_lista = [(clave, dias_nombres[clave]) for clave in dias]

    # Obtener todas las aulas para el filtro
    aulas = Aula.objects.all().order_by("nombre")

    # Obtener el aula seleccionada del parámetro GET
    aula_seleccionada = request.GET.get("aula")

    # Filtrar horarios por aula si se seleccionó una
    horarios = Hora.objects.select_related(
        "aula",
        "grupo_teoria__curso",
        "grupo_teoria__profesor",
        "grupo_practica__grupo_teoria__curso",
        "grupo_practica__profesor",
        "grupo_laboratorio__grupo_teoria__curso",
        "grupo_laboratorio__profesor",
        "reserva__profesor",
    ).order_by("aula__nombre", "hora_inicio")

    if aula_seleccionada:
        horarios = horarios.filter(aula__nombre=aula_seleccionada)

    tabla_horarios = {}

    for h in horarios:
        if not h.aula:
            continue

        aula = h.aula.nombre
        bloque = f"{h.hora_inicio.strftime('%H:%M')} - {h.hora_fin.strftime('%H:%M')}"
        dia = h.dia

        if aula not in tabla_horarios:
            tabla_horarios[aula] = {}

        if bloque not in tabla_horarios[aula]:
            tabla_horarios[aula][bloque] = {d: "" for d in dias}

        # Determinar curso, grupo y profesor
        if h.grupo_teoria:
            curso = h.grupo_teoria.curso.nombre
            grupo = f"T{h.grupo_teoria.turno}"
            profesor = (
                h.grupo_teoria.profesor.nombre
                if h.grupo_teoria.profesor
                else "Sin asignar"
            )
        elif h.grupo_practica:
            curso = h.grupo_practica.grupo_teoria.curso.nombre
            grupo = f"P{h.grupo_practica.turno}"
            profesor = (
                h.grupo_practica.profesor.nombre
                if h.grupo_practica.profesor
                else "Sin asignar"
            )
        elif h.grupo_laboratorio:
            curso = h.grupo_laboratorio.grupo_teoria.curso.nombre
            grupo = f"L{h.grupo_laboratorio.grupo}"
            profesor = (
                h.grupo_laboratorio.profesor.nombre
                if h.grupo_laboratorio.profesor
                else "Sin asignar"
            )
        elif h.reserva:
            curso = "Reserva"
            grupo = ""
            profesor = (
                h.reserva.profesor.nombre if h.reserva.profesor else "Sin asignar"
            )
        else:
            curso = "Receso"
            grupo = ""
            profesor = ""

        # Formatear la información con profesor
        info = f"{curso}"
        if grupo:
            info += f" ({grupo})"
        if profesor:
            info += f" - {profesor}"

        tabla_horarios[aula][bloque][dia] = info

    # Ordenar por bloque horario
    for aula in tabla_horarios:
        tabla_horarios[aula] = dict(
            sorted(tabla_horarios[aula].items(), key=lambda x: x[0])
        )

    context = {
        "dias_lista": dias_lista,
        "aulas": aulas,
        "aula_seleccionada": aula_seleccionada,
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
    }

    return render(request, "siscad/secretaria/visualizar_horarios_aulas.html", context)
