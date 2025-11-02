from .models import Reserva
from django.utils import timezone

def limpiar_reservas_expiradas():
    ahora = timezone.localtime()
    fecha_actual = ahora.date()
    hora_actual = ahora.time()

    reservas_pasadas = Reserva.objects.filter(fecha__lt=fecha_actual)
    reservas_hoy = Reserva.objects.filter(fecha=fecha_actual)

    for reserva in reservas_pasadas:
        reserva.delete()

    for reserva in reservas_hoy:
        if all(h.hora_fin < hora_actual for h in reserva.horas.all()):
            reserva.delete()
