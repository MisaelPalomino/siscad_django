from ..comunes.imports import *

def matricula_laboratorio_admin(request):
    # Verificar sesión de administrador
    if "email" not in request.session or request.session.get("rol") != "Administrador":
        return redirect("login")

    alumno_encontrado = None
    matriculas_curso = []
    laboratorios_disponibles = []
    matriculas_lab_actuales = []
    mensaje = ""
    dni_buscado = ""

    if request.method == "POST":
        # Buscar alumno por DNI
        if "dni" in request.POST:
            dni_buscado = request.POST.get("dni")
            
            if dni_buscado:
                try:
                    alumno_encontrado = Alumno.objects.get(dni=dni_buscado)
                    mensaje = f"Alumno encontrado: {alumno_encontrado.nombre}"
                    
                except Alumno.DoesNotExist:
                    mensaje = f"No se encontró ningún alumno con DNI: {dni_buscado}"
                except Exception as e:
                    mensaje = f"Error al buscar alumno: {str(e)}"

        # Procesar matrícula de laboratorio
        elif "grupo_laboratorio" in request.POST:
            dni_buscado = request.POST.get("dni_oculto")
            grupo_lab_id = request.POST.get("grupo_laboratorio")

            if not dni_buscado:
                mensaje = "Error: DNI no proporcionado."
            elif not grupo_lab_id:
                mensaje = "Debes seleccionar un grupo de laboratorio."
            else:
                try:
                    alumno_encontrado = Alumno.objects.get(dni=dni_buscado)
                    
                    with transaction.atomic():
                        grupo_lab = GrupoLaboratorio.objects.select_related(
                            "grupo_teoria__curso", "profesor"
                        ).get(id=grupo_lab_id)

                        # Verificar que el alumno esté matriculado en el curso correspondiente
                        matricula_curso = MatriculaCurso.objects.filter(
                            alumno_id=alumno_encontrado.id,
                            curso_id=grupo_lab.grupo_teoria.curso_id
                        ).first()

                        if not matricula_curso:
                            mensaje = "El alumno no está matriculado en este curso."
                        else:
                            # Verificar si ya está matriculado en un laboratorio de ese curso
                            matricula_existente = MatriculaLaboratorio.objects.filter(
                                alumno_id=alumno_encontrado.id,
                                grupo_laboratorio__grupo_teoria__curso_id=grupo_lab.grupo_teoria.curso_id,
                            ).first()

                            if matricula_existente:
                                # ELIMINAR MATRÍCULA ANTERIOR
                                grupo_lab_anterior = matricula_existente.grupo_laboratorio
                                
                                # Liberar cupo del laboratorio anterior
                                grupo_lab_anterior.cupos += 1
                                grupo_lab_anterior.save()
                                
                                # Eliminar asistencias del laboratorio anterior
                                AsistenciaAlumno.objects.filter(
                                    alumno=alumno_encontrado,
                                    hora__grupo_laboratorio=grupo_lab_anterior
                                ).delete()
                                
                                # Eliminar matrícula anterior
                                matricula_existente.delete()
                                mensaje_adicional = f" (se eliminó la matrícula anterior del grupo {grupo_lab_anterior.grupo})"
                            else:
                                mensaje_adicional = ""

                            # Verificar cupos
                            if grupo_lab.cupos <= 0:
                                mensaje = "No hay cupos disponibles en este grupo de laboratorio."
                            else:
                                # Crear matrícula
                                matricula_lab = MatriculaLaboratorio(
                                    alumno_id=alumno_encontrado.id, 
                                    grupo_laboratorio_id=grupo_lab.id
                                )
                                matricula_lab.save()

                                # Actualizar cupos
                                grupo_lab.cupos -= 1
                                grupo_lab.save()

                                # Generar asistencias
                                generar_asistencias_laboratorio(alumno_encontrado, grupo_lab)

                                mensaje = f"Matrícula realizada exitosamente en el laboratorio de {grupo_lab.grupo_teoria.curso.nombre} - Grupo {grupo_lab.grupo}{mensaje_adicional}."

                except Alumno.DoesNotExist:
                    mensaje = f"No se encontró ningún alumno con DNI: {dni_buscado}"
                except GrupoLaboratorio.DoesNotExist:
                    mensaje = "El grupo de laboratorio seleccionado no existe."
                except Exception as e:
                    mensaje = f"Error al realizar la matrícula: {str(e)}"

        # Cancelar matrícula existente
        elif "cancelar_matricula" in request.POST:
            dni_buscado = request.POST.get("dni_oculto")
            matricula_id = request.POST.get("cancelar_matricula")
            
            if not dni_buscado:
                mensaje = "Error: DNI no proporcionado."
            else:
                try:
                    alumno_encontrado = Alumno.objects.get(dni=dni_buscado)
                    
                    with transaction.atomic():
                        matricula_existente = MatriculaLaboratorio.objects.get(
                            id=matricula_id,
                            alumno_id=alumno_encontrado.id
                        )
                        
                        grupo_lab_anterior = matricula_existente.grupo_laboratorio
                        
                        # Liberar cupo del laboratorio anterior
                        grupo_lab_anterior.cupos += 1
                        grupo_lab_anterior.save()
                        
                        # Eliminar asistencias del laboratorio anterior
                        AsistenciaAlumno.objects.filter(
                            alumno=alumno_encontrado,
                            hora__grupo_laboratorio=grupo_lab_anterior
                        ).delete()
                        
                        # Eliminar matrícula anterior
                        matricula_existente.delete()
                        
                        mensaje = f"Matrícula cancelada exitosamente del laboratorio de {grupo_lab_anterior.grupo_teoria.curso.nombre} - Grupo {grupo_lab_anterior.grupo}."

                except Alumno.DoesNotExist:
                    mensaje = f"No se encontró ningún alumno con DNI: {dni_buscado}"
                except MatriculaLaboratorio.DoesNotExist:
                    mensaje = "La matrícula que intentas cancelar no existe."
                except Exception as e:
                    mensaje = f"Error al cancelar la matrícula: {str(e)}"

    # SIEMPRE cargar datos del alumno si está presente
    if alumno_encontrado or ('dni_oculto' in request.POST and request.POST.get('dni_oculto')):
        dni_actual = alumno_encontrado.dni if alumno_encontrado else request.POST.get('dni_oculto')
        
        try:
            alumno_encontrado = Alumno.objects.get(dni=dni_actual)
            
            # Obtener los cursos matriculados del alumno
            matriculas_curso = MatriculaCurso.objects.filter(
                alumno_id=alumno_encontrado.id
            ).select_related("curso")

            # Obtener matrículas de laboratorio actuales
            matriculas_lab_actuales = MatriculaLaboratorio.objects.filter(
                alumno_id=alumno_encontrado.id
            ).select_related(
                "grupo_laboratorio__grupo_teoria__curso", 
                "grupo_laboratorio__profesor"
            )

            # Obtener laboratorios disponibles (SIGUIENDO LA LÓGICA ORIGINAL)
            laboratorios_disponibles = []
            for matricula in matriculas_curso:
                curso = matricula.curso
                turno_alumno = matricula.turno

                # Verificar si ya está matriculado en este curso
                ya_matriculado_curso = MatriculaLaboratorio.objects.filter(
                    alumno_id=alumno_encontrado.id,
                    grupo_laboratorio__grupo_teoria__curso_id=curso.id,
                ).exists()

                # Obtener grupos disponibles (excluyendo al alumno actual)
                grupos_lab = (
                    GrupoLaboratorio.objects.select_related("grupo_teoria__curso", "profesor")
                    .filter(
                        grupo_teoria__curso_id=curso.id,
                        cupos__gt=0,
                    )
                    .exclude(matriculas_laboratorio__alumno_id=alumno_encontrado.id)
                )

                # Filtrar grupos compatibles con el turno
                grupos_compatibles = [
                    g for g in grupos_lab if g.grupo == turno_alumno
                ]

                # SIEMPRE mostrar el curso, incluso si no hay grupos disponibles
                laboratorios_disponibles.append({
                    "curso": curso,
                    "turno_alumno": turno_alumno,
                    "grupos": grupos_compatibles,
                    "ya_matriculado": ya_matriculado_curso,
                })

        except Alumno.DoesNotExist:
            mensaje = f"No se encontró ningún alumno con DNI: {dni_actual}"
        except Exception as e:
            mensaje = f"Error al cargar datos del alumno: {str(e)}"

    context = {
        'alumno_encontrado': alumno_encontrado,
        'matriculas_curso': matriculas_curso,
        'laboratorios_disponibles': laboratorios_disponibles,
        'matriculas_lab_actuales': matriculas_lab_actuales,
        'mensaje': mensaje,
        'dni_buscado': dni_buscado or (alumno_encontrado.dni if alumno_encontrado else ""),
    }

    return render(request, "siscad/admin/matricula_laboratorio_admin.html", context)

# Mantener la función generar_asistencias_laboratorio igual
def generar_asistencias_laboratorio(alumno, grupo_lab):
    """
    Genera asistencias para el laboratorio matriculado por el alumno,
    desde el 2 de septiembre 2025 hasta el 25 de diciembre 2025.
    """
    print(f"🔧 Generando asistencias de laboratorio para {alumno.nombre} - {grupo_lab.grupo_teoria.curso.nombre}")

    # Rango de fechas
    fecha_inicio = date(2025, 9, 2)
    fecha_fin = date(2025, 12, 25)
    fecha_hoy = date.today()

    asistencias_creadas = 0

    # Obtener los horarios del grupo de laboratorio
    horarios_lab = (
        Hora.objects.filter(grupo_laboratorio=grupo_lab)
        .select_related("grupo_laboratorio__grupo_teoria__curso")
        .order_by("dia", "hora_inicio")
    )

    if not horarios_lab.exists():
        print(f"   ⚠️ No se encontraron horarios para el laboratorio {grupo_lab.id}")
        return 0

    # Mapear días
    dias_map = {
        "Monday": "L",
        "Tuesday": "M",
        "Wednesday": "X",
        "Thursday": "J",
        "Friday": "V",
    }

    # Recorrer días desde inicio a fin
    fecha_actual = fecha_inicio
    while fecha_actual <= fecha_fin:
        if fecha_actual.weekday() < 5:  # Solo lunes a viernes
            dia_codigo = dias_map.get(fecha_actual.strftime("%A"))

            # Horarios del laboratorio en ese día
            horarios_dia = [h for h in horarios_lab if h.dia == dia_codigo]
            if horarios_dia:
                # Agrupar bloques consecutivos
                horarios_dia.sort(key=lambda h: h.hora_inicio)
                bloques = []
                bloque_actual = [horarios_dia[0]]

                for i in range(1, len(horarios_dia)):
                    anterior = bloque_actual[-1]
                    actual = horarios_dia[i]
                    if actual.hora_inicio == anterior.hora_fin:
                        bloque_actual.append(actual)
                    else:
                        bloques.append(bloque_actual)
                        bloque_actual = [actual]
                bloques.append(bloque_actual)

                estado = "P" if fecha_actual <= fecha_hoy else "F"

                for bloque in bloques:
                    try:
                        hora_inicio = bloque[0].hora_inicio
                        hora_fin = bloque[-1].hora_fin
                        hora_referencia = bloque[0]

                        # Evitar duplicados
                        asistencia_existente = AsistenciaAlumno.objects.filter(
                            alumno=alumno,
                            fecha=fecha_actual,
                            hora__grupo_laboratorio=grupo_lab,
                        ).exists()

                        if asistencia_existente:
                            continue

                        # Crear asistencia
                        asistencia = AsistenciaAlumno(
                            alumno=alumno,
                            fecha=fecha_actual,
                            estado=estado,
                            hora=hora_referencia,
                        )
                        asistencia.save()
                        asistencias_creadas += 1

                    except Exception as e:
                        print(f"   ❌ Error generando asistencia {fecha_actual}: {e}")
                        continue

        fecha_actual += timedelta(days=1)

    print(f"✅ Total asistencias generadas: {asistencias_creadas}")
    return asistencias_creadas