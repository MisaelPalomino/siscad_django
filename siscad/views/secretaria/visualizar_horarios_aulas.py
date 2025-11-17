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

    horarios = Hora.objects.select_related(
        "aula",
        "grupo_teoria__curso",
        "grupo_practica__grupo_teoria__curso",
        "grupo_laboratorio__grupo_teoria__curso",
    ).order_by("aula__nombre", "hora_inicio")

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

        if h.grupo_teoria:
            curso = h.grupo_teoria.curso.nombre
            grupo = f"T{h.grupo_teoria.id}"
        elif h.grupo_practica:
            curso = h.grupo_practica.grupo_teoria.curso.nombre
            grupo = f"P{h.grupo_practica.id}"
        elif h.grupo_laboratorio:
            curso = h.grupo_laboratorio.grupo_teoria.curso.nombre
            grupo = f"L{h.grupo_laboratorio.id}"
        else:
            curso = "Receso"
            grupo = ""

        tabla_horarios[aula][bloque][dia] = f"{curso} ({grupo})"

    for aula in tabla_horarios:
        tabla_horarios[aula] = dict(
            sorted(tabla_horarios[aula].items(), key=lambda x: x[0])
        )

    context = {
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
    }

    return render(request, "siscad/secretaria/visualizar_horarios_aulas.html", context)