from ..comunes.imports import *
from django.db import models


def registrar_asistencia_profesores_admin(request):
    if "email" not in request.session or request.session.get("rol") != "Administrador":
        return redirect("login")

    # Valores iniciales
    asistencias_data = []
    fecha_seleccionada = timezone.localdate()
    profesor_seleccionado = None
    mensaje = ""

    # Obtener todos los profesores
    profesores = Profesor.objects.all()

    if request.method == "POST":
        # Procesar fecha seleccionada
        fecha_input = request.POST.get("fecha")
        if fecha_input:
            try:
                fecha_seleccionada = datetime.strptime(fecha_input, "%Y-%m-%d").date()
            except ValueError:
                fecha_seleccionada = timezone.localdate()

        # Procesar profesor seleccionado
        profesor_id = request.POST.get("profesor_id")
        if profesor_id:
            profesor_seleccionado = get_object_or_404(Profesor, id=profesor_id)

        # Procesar guardado de asistencias
        if "guardar_asistencia" in request.POST and profesor_seleccionado:
            contador_actualizaciones = 0
            for key, value in request.POST.items():
                if key.startswith("asistencia_"):
                    # El formato es: asistencia_[asistencia_id]
                    asistencia_id = key.split("_")[1]

                    try:
                        # Actualizar asistencia existente
                        asistencia = AsistenciaProfesor.objects.get(
                            id=asistencia_id, profesor=profesor_seleccionado
                        )
                        asistencia.estado = value
                        asistencia.save()
                        contador_actualizaciones += 1
                    except AsistenciaProfesor.DoesNotExist:
                        print(f"Asistencia no encontrada: {asistencia_id}")
                    except Exception as e:
                        print(f"Error guardando asistencia profesor: {e}")

            mensaje = f"Asistencias guardadas correctamente. {contador_actualizaciones} registros actualizados."

    # Si hay un profesor seleccionado, obtener sus ASISTENCIAS EXISTENTES para esa fecha
    if profesor_seleccionado:
        # Obtener SOLO las asistencias que ya están registradas en la base de datos
        asistencias_existentes = (
            AsistenciaProfesor.objects.filter(
                profesor=profesor_seleccionado, fecha=fecha_seleccionada
            )
            .select_related(
                "hora__grupo_teoria__curso",
                "hora__grupo_practica__grupo_teoria__curso",
                "hora__grupo_laboratorio__grupo_teoria__curso",
                "hora__aula",
            )
            .order_by("hora__hora_inicio")
        )

        # Para cada asistencia existente, obtener la información
        for asistencia in asistencias_existentes:
            hora = asistencia.hora

            # Determinar el tipo de grupo y curso
            tipo_grupo = ""
            curso = None
            turno = ""

            if hora.grupo_teoria:
                tipo_grupo = "Teoría"
                curso = hora.grupo_teoria.curso
                turno = hora.grupo_teoria.turno
            elif hora.grupo_practica:
                tipo_grupo = "Práctica"
                curso = hora.grupo_practica.grupo_teoria.curso
                turno = hora.grupo_practica.turno
            elif hora.grupo_laboratorio:
                tipo_grupo = "Laboratorio"
                curso = hora.grupo_laboratorio.grupo_teoria.curso
                turno = hora.grupo_laboratorio.grupo
            else:
                # Si no tiene grupo asociado, usar información básica de la hora
                tipo_grupo = hora.get_tipo_display() if hora.tipo else "Sin tipo"
                curso = None
                turno = ""

            asistencias_data.append(
                {
                    "asistencia": asistencia,
                    "hora": hora,
                    "curso": curso,
                    "tipo_grupo": tipo_grupo,
                    "turno": turno,
                    "aula": hora.aula,
                    "estado": asistencia.estado,
                }
            )

    context = {
        "fecha_seleccionada": fecha_seleccionada,
        "profesores": profesores,
        "profesor_seleccionado": profesor_seleccionado,
        "asistencias_data": asistencias_data,
        "mensaje": mensaje,
    }

    return render(request, "siscad/admin/registrar_asistencia_profesores.html", context)
