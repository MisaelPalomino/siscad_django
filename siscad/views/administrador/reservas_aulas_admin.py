from ..comunes.imports import *


def reservar_aula_admin(request):
    # Verificar sesión de administrador
    if "email" not in request.session or request.session.get("rol") != "Administrador":
        return redirect("login")

    # Obtener todos los profesores
    profesores = Profesor.objects.all()
    profesor_seleccionado = None
    aulas = Aula.objects.all()
    horas_disponibles = []
    fecha_seleccionada = None
    dia_letra = None

    # -------------------- POST (reservar aula) --------------------
    if request.method == "POST":
        profesor_id = request.POST.get("profesor_id")
        aula_id = request.POST.get("aula_id")
        fecha = request.POST.get("fecha")
        hora_inicio = request.POST.get("hora_inicio")

        if not (profesor_id and aula_id and fecha and hora_inicio):
            messages.error(request, "Por favor completa todos los campos.")
            return render(
                request,
                "siscad/admin/reservar_aula_admin.html",
                {
                    "profesores": profesores,
                    "profesor_seleccionado": None,
                    "aulas": aulas,
                    "horas": [],
                    "fecha_seleccionada": None,
                    "dia_letra": None,
                },
            )

        profesor_seleccionado = get_object_or_404(Profesor, id=profesor_id)
        aula = get_object_or_404(Aula, id=aula_id)
        fecha_seleccionada = datetime.strptime(fecha, "%Y-%m-%d").date()

        # Día de la semana (L, M, X, J, V)
        dia_semana = fecha_seleccionada.weekday()
        if dia_semana >= 5:
            messages.error(request, "Solo puedes reservar entre lunes y viernes.")
            return redirect("reservar_aula_admin")

        letras_dia = ["L", "M", "X", "J", "V"]
        dia_letra = letras_dia[dia_semana]

        # Verificar que la hora esté libre
        hora_obj = get_object_or_404(
            Hora, aula=aula, dia=dia_letra, hora_inicio=hora_inicio, tipo__isnull=True
        )

        # Verificar conflictos con clases o reservas del profesor
        conflicto_profesor = Hora.objects.filter(
            Q(grupo_teoria__profesor=profesor_seleccionado)
            | Q(grupo_practica__profesor=profesor_seleccionado)
            | Q(grupo_laboratorio__profesor=profesor_seleccionado)
            | Q(reserva__profesor=profesor_seleccionado),
            dia=dia_letra,
            hora_inicio=hora_obj.hora_inicio,
        ).exists()

        if conflicto_profesor:
            messages.error(
                request,
                f"El profesor {profesor_seleccionado.nombre} tiene una clase o reserva en ese horario.",
            )
            return render(
                request,
                "siscad/admin/reservar_aula_admin.html",
                {
                    "profesores": profesores,
                    "profesor_seleccionado": profesor_seleccionado,
                    "aulas": aulas,
                    "horas": [],
                    "fecha_seleccionada": fecha_seleccionada,
                    "dia_letra": dia_letra,
                },
            )

        # Crear la reserva
        reserva = Reserva.objects.create(
            profesor=profesor_seleccionado,
            aula=aula,
            fecha=fecha_seleccionada,
            curso=Curso.objects.first(),
        )

        # Asignar la hora
        hora_obj.tipo = "R"
        hora_obj.reserva = reserva
        hora_obj.save()

        # Actualizar cantidad_reservas del profesor
        reservas_activas_count = Reserva.objects.filter(
            profesor=profesor_seleccionado,
            fecha__gte=date.today(),
        ).count()
        reservas_disponibles = 2 - reservas_activas_count
        profesor_seleccionado.cantidad_reservas = max(0, reservas_disponibles)
        profesor_seleccionado.save()

        messages.success(
            request,
            f"Reserva realizada con éxito para el profesor {profesor_seleccionado.nombre} en el aula {aula.nombre} el {fecha_seleccionada}.",
        )
        return redirect("reservar_aula_admin")

    # -------------------- GET (mostrar horas disponibles) --------------------
    if (
        request.GET.get("profesor_id")
        and request.GET.get("aula_id")
        and request.GET.get("fecha")
    ):
        profesor_id = request.GET.get("profesor_id")
        aula_id = request.GET.get("aula_id")
        fecha_str = request.GET.get("fecha")

        try:
            profesor_seleccionado = get_object_or_404(Profesor, id=profesor_id)
            fecha_seleccionada = datetime.strptime(fecha_str, "%Y-%m-%d").date()
        except ValueError:
            messages.error(request, "Fecha inválida.")
            return redirect("reservar_aula_admin")

        dia_semana = fecha_seleccionada.weekday()
        if dia_semana < 5:
            letras_dia = ["L", "M", "X", "J", "V"]
            dia_letra = letras_dia[dia_semana]
            aula = get_object_or_404(Aula, id=aula_id)
            horas_disponibles = Hora.objects.filter(
                aula=aula, dia=dia_letra, tipo__isnull=True
            ).order_by("hora_inicio")

    # -------------------- Contexto --------------------
    context = {
        "profesores": profesores,
        "profesor_seleccionado": profesor_seleccionado,
        "aulas": aulas,
        "horas": horas_disponibles,
        "fecha_seleccionada": fecha_seleccionada,
        "dia_letra": dia_letra,
    }

    return render(request, "siscad/admin/reservar_aula_admin.html", context)


def cancelar_reserva_admin(request):
    # Verificar sesión de administrador
    if "email" not in request.session or request.session.get("rol") != "Administrador":
        return redirect("login")

    # Obtener todos los profesores
    profesores = Profesor.objects.all()
    profesor_seleccionado = None
    reservas = []

    if request.method == "POST":
        # Cancelar reserva específica
        if "reserva_id" in request.POST:
            reserva_id = request.POST.get("reserva_id")
            reserva = get_object_or_404(Reserva, id=reserva_id)

            ahora = timezone.localtime().time()
            hoy = timezone.localdate()

            if reserva.fecha > hoy or (
                reserva.fecha == hoy
                and all(h.hora_inicio > ahora for h in reserva.horas.all())
            ):
                # Liberar las horas asociadas
                for h in reserva.horas.all():
                    h.tipo = None
                    h.reserva = None
                    h.save()

                # Eliminar la reserva
                profesor_reserva = reserva.profesor
                reserva.delete()

                # Actualizar cantidad_reservas del profesor
                reservas_activas_count = Reserva.objects.filter(
                    profesor=profesor_reserva,
                    fecha__gte=date.today(),
                ).count()
                reservas_disponibles = 2 - reservas_activas_count
                profesor_reserva.cantidad_reservas = max(0, reservas_disponibles)
                profesor_reserva.save()

                messages.success(request, "Reserva cancelada exitosamente.")
            else:
                messages.error(
                    request,
                    "No puedes cancelar una reserva que ya ha comenzado o cuya fecha ha pasado.",
                )

            return redirect("cancelar_reserva_admin")

        # Buscar reservas por profesor
        profesor_id = request.POST.get("profesor_id")
        if profesor_id:
            profesor_seleccionado = get_object_or_404(Profesor, id=profesor_id)
            reservas = Reserva.objects.filter(profesor=profesor_seleccionado).order_by(
                "-fecha"
            )

    # Limpiar reservas pasadas automáticamente
    hoy = timezone.localdate()
    ahora = timezone.localtime().time()

    reservas_pasadas = Reserva.objects.filter(fecha__lt=hoy)
    for reserva in reservas_pasadas:
        for h in reserva.horas.all():
            h.tipo = None
            h.reserva = None
            h.save()
        reserva.delete()

    # Limpiar reservas del día actual que ya terminaron
    reservas_hoy = Reserva.objects.filter(fecha=hoy)
    for reserva in reservas_hoy:
        horas_reserva = reserva.horas.all()
        if all(h.hora_fin < ahora for h in horas_reserva):
            for h in reserva.horas.all():
                h.tipo = None
                h.reserva = None
                h.save()
            reserva.delete()

    context = {
        "profesores": profesores,
        "profesor_seleccionado": profesor_seleccionado,
        "reservas": reservas,
    }

    return render(request, "siscad/admin/cancelar_reserva_admin.html", context)
