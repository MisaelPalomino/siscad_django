from ..comunes.imports import *


def reservar_aula(request):
    # Verificar sesión
    if "email" not in request.session:
        return redirect("login")

    profesor = get_object_or_404(Profesor, email=request.session["email"])

    # 🔹 Eliminar reservas pasadas automáticamente
    Reserva.objects.filter(fecha__lt=date.today()).delete()

    # 🔹 Contar reservas activas (de hoy o futuras)
    reservas_activas_count = Reserva.objects.filter(
        profesor=profesor,
        fecha__gte=date.today(),
    ).count()

    # 🔹 Verificar si alcanzó el límite de reservas activas
    if reservas_activas_count >= profesor.cantidad_reservas:
        messages.error(request, "Ya has alcanzado el máximo de reservas permitidas.")
        return render(
            request,
            "siscad/profesor/reservar_aula.html",
            {
                "aulas": Aula.objects.all(),
                "horas": [],
                "reservas": Reserva.objects.filter(profesor=profesor),
                "fecha_seleccionada": None,
                "dia_letra": None,
            },
        )

    aulas = Aula.objects.all()
    horas_disponibles = []
    fecha_seleccionada = None
    dia_letra = None

    # -------------------- POST (reservar aula) --------------------
    if request.method == "POST":
        aula_id = request.POST.get("aula_id")
        fecha = request.POST.get("fecha")
        hora_inicio = request.POST.get("hora_inicio")

        if not (aula_id and fecha and hora_inicio):
            messages.error(request, "Por favor completa todos los campos.")
            return render(
                request,
                "siscad/profesor/reservar_aula.html",
                {
                    "aulas": aulas,
                    "horas": [],
                    "reservas": Reserva.objects.filter(profesor=profesor),
                    "fecha_seleccionada": None,
                    "dia_letra": None,
                },
            )

        aula = get_object_or_404(Aula, id=aula_id)
        fecha_seleccionada = datetime.strptime(fecha, "%Y-%m-%d").date()

        # Día de la semana (L, M, X, J, V)
        dia_semana = fecha_seleccionada.weekday()
        if dia_semana >= 5:
            messages.error(request, "Solo puedes reservar entre lunes y viernes.")
            return redirect("reservar_aula")

        letras_dia = ["L", "M", "X", "J", "V"]
        dia_letra = letras_dia[dia_semana]

        # Verificar que la hora esté libre
        hora_obj = get_object_or_404(
            Hora, aula=aula, dia=dia_letra, hora_inicio=hora_inicio, tipo__isnull=True
        )

        # Verificar conflictos con clases o reservas del profesor
        conflicto_profesor = Hora.objects.filter(
            Q(grupo_teoria__profesor=profesor)
            | Q(grupo_practica__profesor=profesor)
            | Q(grupo_laboratorio__profesor=profesor)
            | Q(reserva__profesor=profesor),
            dia=dia_letra,
            hora_inicio=hora_obj.hora_inicio,
        ).exists()

        if conflicto_profesor:
            messages.error(request, "Tienes una clase o reserva en ese horario.")
            return render(
                request,
                "siscad/profesor/reservar_aula.html",
                {
                    "aulas": aulas,
                    "horas": [],
                    "reservas": Reserva.objects.filter(profesor=profesor),
                    "fecha_seleccionada": None,
                    "dia_letra": None,
                },
            )

        # Crear la reserva
        reserva = Reserva.objects.create(
            profesor=profesor,
            aula=aula,
            fecha=fecha_seleccionada,
            curso=Curso.objects.first(),  # Puedes ajustarlo
        )

        # Asignar la hora
        hora_obj.tipo = "R"
        hora_obj.reserva = reserva
        hora_obj.save()

        messages.success(
            request,
            f" Reserva realizada con éxito para el aula {aula.nombre} el {fecha_seleccionada}.",
        )
        return redirect("reservar_aula")

    # -------------------- GET (mostrar horas disponibles) --------------------
    if request.GET.get("aula_id") and request.GET.get("fecha"):
        aula_id = request.GET.get("aula_id")
        fecha_str = request.GET.get("fecha")

        try:
            fecha_seleccionada = datetime.strptime(fecha_str, "%Y-%m-%d").date()
        except ValueError:
            messages.error(request, "Fecha inválida.")
            return redirect("reservar_aula")

        dia_semana = fecha_seleccionada.weekday()
        if dia_semana < 5:
            letras_dia = ["L", "M", "X", "J", "V"]
            dia_letra = letras_dia[dia_semana]
            aula = get_object_or_404(Aula, id=aula_id)
            horas_disponibles = Hora.objects.filter(
                aula=aula, dia=dia_letra, tipo__isnull=True
            ).order_by("hora_inicio")

    # -------------------- Contexto --------------------
    reservas_profesor = Reserva.objects.filter(profesor=profesor).select_related("aula")

    context = {
        "aulas": aulas,
        "horas": horas_disponibles,
        "reservas": reservas_profesor,
        "fecha_seleccionada": fecha_seleccionada,
        "dia_letra": dia_letra,
    }

    return render(request, "siscad/profesor/reservar_aula.html", context)


def cancelar_reserva(request, reserva_id):
    profesor = get_object_or_404(Profesor, email=request.session["email"])
    reserva = get_object_or_404(Reserva, id=reserva_id, profesor=profesor)

    ahora = timezone.localtime().time()
    hoy = timezone.localdate()

    if reserva.fecha > hoy or (
        reserva.fecha == hoy and all(h.hora_inicio > ahora for h in reserva.horas.all())
    ):
        for h in reserva.horas.all():
            h.tipo = None
            h.reserva = None
            h.save()

        reserva.delete()
        profesor.cantidad_reservas += 1
        profesor.save()

        messages.success(request, " Reserva cancelada exitosamente.")
    else:
        messages.error(
            request,
            " No puedes cancelar una reserva que ya ha comenzado o cuya fecha ha pasado.",
        )

    return redirect("reservar_aula")


def ver_cancelar_reservas(request):
    profesor = get_object_or_404(Profesor, email=request.session["email"])
    ahora = timezone.localtime()
    fecha_actual = ahora.date()
    hora_actual = ahora.time()

    # Eliminar reservas cuya fecha ya pasó
    reservas_pasadas = Reserva.objects.filter(fecha__lt=fecha_actual)
    for reserva in reservas_pasadas:
        reserva.delete()

    # Eliminar reservas del día actual que ya terminaron
    reservas_hoy = Reserva.objects.filter(fecha=fecha_actual)
    for reserva in reservas_hoy:
        horas_reserva = reserva.horas.all()
        if all(h.hora_fin < hora_actual for h in horas_reserva):
            reserva.delete()

    # Mostrar solo reservas activas
    reservas = Reserva.objects.filter(profesor=profesor).order_by("-fecha")

    context = {
        "reservas": reservas,
        "profesor": profesor,
    }
    return render(request, "siscad/profesor/cancelar_reservas.html", context)
