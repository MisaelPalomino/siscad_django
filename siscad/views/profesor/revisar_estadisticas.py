from ..comunes.imports import *


def calcular_nota_final(alumno, curso):
    """
    Calcula la nota final considerando sustitutorio y pesos dinámicos
    El sustitutorio reemplaza la nota más baja de los parciales 1 y 2
    IGNORA las notas que son -1 (no asignadas)
    """
    # Obtener todas las notas
    notas = Nota.objects.filter(alumno=alumno, curso=curso)

    # Separar por tipo, excluyendo -1
    continuas = {
        n.periodo: n
        for n in notas
        if n.tipo == "C" and n.valor is not None and n.valor >= 0
    }
    parciales = {
        n.periodo: n
        for n in notas
        if n.tipo == "P" and n.valor is not None and n.valor >= 0
    }
    sustitutorio = next(
        (n for n in notas if n.tipo == "S" and n.valor is not None and n.valor >= 0),
        None,
    )

    # Aplicar sustitutorio si existe y hay al menos 2 parciales con nota válida
    if (
        sustitutorio
        and sustitutorio.valor is not None
        and sustitutorio.valor >= 0
        and 1 in parciales
        and 2 in parciales
    ):
        # Encontrar el parcial más bajo entre P1 y P2
        if parciales[1].valor <= parciales[2].valor:
            # Reemplazar P1 temporalmente para el cálculo
            nota_original_p1 = parciales[1].valor
            parciales[1].valor = sustitutorio.valor
        else:
            # Reemplazar P2 temporalmente para el cálculo
            nota_original_p2 = parciales[2].valor
            parciales[2].valor = sustitutorio.valor

    # Calcular promedio ponderado
    total_puntos = 0
    total_pesos = 0

    # Sumar continuas (solo si tienen peso configurado y valor >= 0)
    for periodo in [1, 2, 3]:
        if periodo in continuas:
            peso = getattr(curso, f"peso_continua_{periodo}", 0)
            if peso > 0 and continuas[periodo].valor >= 0:
                total_puntos += continuas[periodo].valor * peso
                total_pesos += peso

    # Sumar parciales (solo si tienen peso configurado y valor >= 0)
    for periodo in [1, 2, 3]:
        if periodo in parciales:
            peso = getattr(curso, f"peso_parcial_{periodo}", 0)
            if peso > 0 and parciales[periodo].valor >= 0:
                total_puntos += parciales[periodo].valor * peso
                total_pesos += peso

    # Solo calcular si hay al menos una nota válida
    if total_pesos == 0:
        return -1  # Retorna -1 si no hay notas válidas

    nota_final = total_puntos / total_pesos

    # Restaurar notas originales si se aplicó sustitutorio
    if (
        sustitutorio
        and sustitutorio.valor is not None
        and sustitutorio.valor >= 0
        and 1 in parciales
        and 2 in parciales
    ):
        if "nota_original_p1" in locals():
            parciales[1].valor = nota_original_p1
        elif "nota_original_p2" in locals():
            parciales[2].valor = nota_original_p2

    return round(nota_final, 2)


def revisar_estadisticas(request):
    if "email" not in request.session:
        return redirect("login")

    profesor = get_object_or_404(Profesor, email=request.session["email"])

    grupos_teoria = GrupoTeoria.objects.filter(profesor=profesor)

    grupo_seleccionado = None
    estadisticas_generales = None
    estadisticas_detalladas = None
    estadisticas_avance = None
    alumnos_grupo = []

    if request.method == "POST":
        grupo_id = request.POST.get("grupo_id")

        if grupo_id:
            grupo_seleccionado = get_object_or_404(
                GrupoTeoria, id=grupo_id, profesor=profesor
            )

            # Obtener alumnos del grupo
            alumnos_grupo = MatriculaCurso.objects.filter(
                curso=grupo_seleccionado.curso, turno=grupo_seleccionado.turno
            ).select_related("alumno")

            # Procesar subida de exámenes
            if "subir_examenes" in request.POST and request.FILES.getlist(
                "archivos_examen"
            ):
                procesar_examenes(request, grupo_seleccionado)
                messages.success(request, "Exámenes subidos correctamente")
                return redirect("revisar_estadisticas")

            # Descargar Excel
            elif "descargar_excel" in request.POST:
                return descargar_estadisticas_excel(
                    request, grupo_seleccionado, alumnos_grupo
                )

            # Generar estadísticas
            else:
                estadisticas_generales = calcular_estadisticas_generales(
                    grupo_seleccionado, alumnos_grupo
                )
                estadisticas_detalladas = calcular_estadisticas_detalladas(
                    grupo_seleccionado, alumnos_grupo
                )
                estadisticas_avance = calcular_estadisticas_avance(
                    grupo_seleccionado, alumnos_grupo
                )

    context = {
        "grupos_teoria": grupos_teoria,
        "grupo_seleccionado": grupo_seleccionado,
        "estadisticas_generales": estadisticas_generales,
        "estadisticas_detalladas": estadisticas_detalladas,
        "estadisticas_avance": estadisticas_avance,
        "alumnos_grupo": alumnos_grupo,
    }

    return render(request, "siscad/profesor/revisar_estadisticas.html", context)


def calcular_estadisticas_generales(grupo_teoria, alumnos_grupo):
    """
    Calcula estadísticas generales del grupo - VERSIÓN CON -1
    """
    curso = grupo_teoria.curso
    notas_finales = []

    for matricula in alumnos_grupo:
        alumno = matricula.alumno
        nota_final = calcular_nota_final(alumno, curso)
        # Solo considerar notas válidas (>= 0)
        if nota_final is not None and nota_final >= 0:
            notas_finales.append(nota_final)

    if not notas_finales:
        return {
            "total_alumnos": len(alumnos_grupo),
            "total_con_nota": 0,
            "aprobados": 0,
            "desaprobados": 0,
            "tasa_aprobacion": 0,
            "nota_promedio": 0,
            "nota_maxima": 0,
            "nota_minima": 0,
            "alumno_maxima": None,
            "alumno_minima": None,
        }

    # Calcular estadísticas
    aprobados = sum(1 for nota in notas_finales if nota >= 10.5)
    desaprobados = len(notas_finales) - aprobados

    return {
        "total_alumnos": len(alumnos_grupo),
        "total_con_nota": len(notas_finales),
        "aprobados": aprobados,
        "desaprobados": desaprobados,
        "tasa_aprobacion": round((aprobados / len(notas_finales) * 100), 2),
        "nota_promedio": round(sum(notas_finales) / len(notas_finales), 2),
        "nota_maxima": max(notas_finales),
        "nota_minima": min(notas_finales),
        "alumno_maxima": obtener_alumno_nota_maxima(grupo_teoria, alumnos_grupo),
        "alumno_minima": obtener_alumno_nota_minima(grupo_teoria, alumnos_grupo),
    }


def calcular_estadisticas_detalladas(grupo_teoria, alumnos_grupo):
    """
    Calcula estadísticas detalladas por tipo de evaluación - VERSIÓN CON -1
    """
    curso = grupo_teoria.curso
    estadisticas = {"parciales": {}, "continuas": {}, "sustitutorios": {}}

    # Estadísticas de parciales
    for periodo in [1, 2, 3]:
        peso_parcial = getattr(curso, f"peso_parcial_{periodo}", 0)
        if peso_parcial > 0:
            notas_parcial = []
            alumnos_con_nota = 0
            alumnos_evaluados = 0

            for matricula in alumnos_grupo:
                nota = Nota.objects.filter(
                    alumno=matricula.alumno, curso=curso, tipo="P", periodo=periodo
                ).first()
                # Solo considerar notas válidas (>= 0)
                if nota and nota.valor is not None and nota.valor >= 0:
                    notas_parcial.append(nota.valor)
                    alumnos_con_nota += 1
                # Contar alumnos que tienen registro (aunque sea -1)
                if nota:
                    alumnos_evaluados += 1

            if notas_parcial:
                estadisticas["parciales"][f"P{periodo}"] = {
                    "promedio": round(sum(notas_parcial) / len(notas_parcial), 2),
                    "maxima": max(notas_parcial),
                    "minima": min(notas_parcial),
                    "total": len(notas_parcial),
                    "alumnos_con_nota": alumnos_con_nota,
                    "alumnos_evaluados": alumnos_evaluados,
                    "alumnos_sin_nota": len(alumnos_grupo) - alumnos_con_nota,
                    "peso": peso_parcial,
                    "tiene_datos": len(notas_parcial) > 0,
                }
            else:
                # Incluir período incluso sin notas válidas
                estadisticas["parciales"][f"P{periodo}"] = {
                    "promedio": 0,
                    "maxima": 0,
                    "minima": 0,
                    "total": 0,
                    "alumnos_con_nota": 0,
                    "alumnos_evaluados": alumnos_evaluados,
                    "alumnos_sin_nota": len(alumnos_grupo),
                    "peso": peso_parcial,
                    "tiene_datos": False,
                }

    # Estadísticas de continuas
    for periodo in [1, 2, 3]:
        peso_continua = getattr(curso, f"peso_continua_{periodo}", 0)
        if peso_continua > 0:
            notas_continua = []
            alumnos_con_nota = 0
            alumnos_evaluados = 0

            for matricula in alumnos_grupo:
                nota = Nota.objects.filter(
                    alumno=matricula.alumno, curso=curso, tipo="C", periodo=periodo
                ).first()
                # Solo considerar notas válidas (>= 0)
                if nota and nota.valor is not None and nota.valor >= 0:
                    notas_continua.append(nota.valor)
                    alumnos_con_nota += 1
                # Contar alumnos que tienen registro (aunque sea -1)
                if nota:
                    alumnos_evaluados += 1

            if notas_continua:
                estadisticas["continuas"][f"C{periodo}"] = {
                    "promedio": round(sum(notas_continua) / len(notas_continua), 2),
                    "maxima": max(notas_continua),
                    "minima": min(notas_continua),
                    "total": len(notas_continua),
                    "alumnos_con_nota": alumnos_con_nota,
                    "alumnos_evaluados": alumnos_evaluados,
                    "alumnos_sin_nota": len(alumnos_grupo) - alumnos_con_nota,
                    "peso": peso_continua,
                    "tiene_datos": len(notas_continua) > 0,
                }
            else:
                # Incluir período incluso sin notas válidas
                estadisticas["continuas"][f"C{periodo}"] = {
                    "promedio": 0,
                    "maxima": 0,
                    "minima": 0,
                    "total": 0,
                    "alumnos_con_nota": 0,
                    "alumnos_evaluados": alumnos_evaluados,
                    "alumnos_sin_nota": len(alumnos_grupo),
                    "peso": peso_continua,
                    "tiene_datos": False,
                }

    # Estadísticas de sustitutorios
    notas_sustitutorio = []
    alumnos_con_sustitutorio = 0
    alumnos_evaluados_sust = 0

    for matricula in alumnos_grupo:
        nota = Nota.objects.filter(
            alumno=matricula.alumno, curso=curso, tipo="S"
        ).first()
        # Solo considerar notas válidas (>= 0)
        if nota and nota.valor is not None and nota.valor >= 0:
            notas_sustitutorio.append(nota.valor)
            alumnos_con_sustitutorio += 1
        # Contar alumnos que tienen registro (aunque sea -1)
        if nota:
            alumnos_evaluados_sust += 1

    if notas_sustitutorio:
        estadisticas["sustitutorios"] = {
            "promedio": round(sum(notas_sustitutorio) / len(notas_sustitutorio), 2),
            "maxima": max(notas_sustitutorio),
            "minima": min(notas_sustitutorio),
            "total": len(notas_sustitutorio),
            "alumnos_con_nota": alumnos_con_sustitutorio,
            "alumnos_evaluados": alumnos_evaluados_sust,
            "alumnos_sin_nota": len(alumnos_grupo) - alumnos_con_sustitutorio,
            "tiene_datos": True,
        }
    else:
        estadisticas["sustitutorios"] = {
            "promedio": 0,
            "maxima": 0,
            "minima": 0,
            "total": 0,
            "alumnos_con_nota": 0,
            "alumnos_evaluados": alumnos_evaluados_sust,
            "alumnos_sin_nota": len(alumnos_grupo),
            "tiene_datos": False,
        }

    return estadisticas


def obtener_alumno_nota_maxima(grupo_teoria, alumnos_grupo):
    """Obtiene el alumno con la nota más alta - VERSIÓN CON -1"""
    curso = grupo_teoria.curso
    mejor_alumno = None
    mejor_nota = -1  # Iniciar con -1

    for matricula in alumnos_grupo:
        nota_final = calcular_nota_final(matricula.alumno, curso)
        # Solo considerar notas válidas (>= 0)
        if nota_final is not None and nota_final >= 0:
            if mejor_nota == -1 or nota_final > mejor_nota:
                mejor_nota = nota_final
                mejor_alumno = matricula.alumno

    return {"alumno": mejor_alumno, "nota": mejor_nota} if mejor_alumno else None


def obtener_alumno_nota_minima(grupo_teoria, alumnos_grupo):
    """Obtiene el alumno con la nota más baja - VERSIÓN CON -1"""
    curso = grupo_teoria.curso
    peor_alumno = None
    peor_nota = -1  # Iniciar con -1

    for matricula in alumnos_grupo:
        nota_final = calcular_nota_final(matricula.alumno, curso)
        # Solo considerar notas válidas (>= 0)
        if nota_final is not None and nota_final >= 0:
            if peor_nota == -1 or nota_final < peor_nota:
                peor_nota = nota_final
                peor_alumno = matricula.alumno

    return {"alumno": peor_alumno, "nota": peor_nota} if peor_alumno else None


def procesar_examenes(request, grupo_teoria):
    """
    Procesa la subida de exámenes PDF usando los alumnos con nota máxima y mínima
    """
    archivos = request.FILES.getlist("archivos_examen")
    tipo_examen = request.POST.get("tipo_examen")

    # Obtener alumnos del grupo
    alumnos_grupo = MatriculaCurso.objects.filter(
        curso=grupo_teoria.curso, turno=grupo_teoria.turno
    ).select_related("alumno")

    # Obtener alumnos con nota máxima y mínima
    alumno_maxima = obtener_alumno_nota_maxima(grupo_teoria, alumnos_grupo)
    alumno_minima = obtener_alumno_nota_minima(grupo_teoria, alumnos_grupo)

    # Determinar qué alumno(s) procesar según el tipo de examen
    alumnos_a_procesar = []

    if tipo_examen == "A" and alumno_maxima:  # Examen alta - alumno con máxima nota
        alumnos_a_procesar.append(alumno_maxima["alumno"])
    elif tipo_examen == "B" and alumno_minima:  # Examen baja - alumno con mínima nota
        alumnos_a_procesar.append(alumno_minima["alumno"])
    elif tipo_examen == "P":  # Examen promedio - todos los alumnos
        alumnos_a_procesar = [matricula.alumno for matricula in alumnos_grupo]

    if not alumnos_a_procesar:
        messages.error(request, "No se encontraron alumnos para procesar")
        return

    # Mapeo de tipos de examen para el nombre del archivo
    tipo_map = {"A": "alta", "P": "promedio", "B": "baja"}
    tipo_nombre = tipo_map.get(tipo_examen, "examen")
    curso_codigo = grupo_teoria.curso.codigo or "0000"

    archivos_procesados = 0
    errores = []

    # Crear diccionario para mapear archivos por DNI (si se suben múltiples)
    archivos_por_dni = {}

    for archivo in archivos:
        # Extraer DNI del nombre del archivo como respaldo
        import re

        dni_match = re.search(r"(\d{8})", archivo.name)
        if dni_match:
            dni = dni_match.group(1)
            archivos_por_dni[dni] = archivo

    # Procesar cada alumno
    for alumno in alumnos_a_procesar:
        try:
            # Buscar archivo por DNI del alumno
            archivo = archivos_por_dni.get(str(alumno.dni))

            if not archivo:
                # Si no se encuentra por DNI, usar el primer archivo disponible
                if archivos:
                    archivo = archivos[0]
                else:
                    errores.append(f"No hay archivos para el alumno {alumno.dni}")
                    continue

            # Generar nuevo nombre para el archivo
            nuevo_nombre = f"{alumno.dni}_{curso_codigo}_{tipo_nombre}.pdf"

            # Asignar el nuevo nombre al archivo
            archivo.name = nuevo_nombre

            # Crear o actualizar examen
            examen, created = Examen.objects.get_or_create(
                alumno=alumno,
                GrupoTeoria=grupo_teoria,
                tipo=tipo_examen,
                defaults={"archivo": archivo},
            )

            if not created:
                # Si ya existe, eliminar el archivo anterior y guardar el nuevo
                if examen.archivo:
                    examen.archivo.delete(save=False)
                examen.archivo = archivo
                examen.save()

            archivos_procesados += 1

        except Exception as e:
            errores.append(f"Error con alumno {alumno.dni}: {str(e)}")
            continue

    # Mostrar mensajes de resultado
    if archivos_procesados > 0:
        messages.success(
            request, f"Se procesaron {archivos_procesados} archivos correctamente"
        )

    if errores:
        messages.error(request, f"Errores: {', '.join(errores[:5])}")


def descargar_estadisticas_excel(request, grupo_teoria, alumnos_grupo):
    """
    Genera y descarga un Excel con las estadísticas - VERSIÓN CON -1
    """
    try:
        curso = grupo_teoria.curso

        # Crear DataFrame con datos de alumnos
        data = []
        for matricula in alumnos_grupo:
            alumno = matricula.alumno
            nota_final = calcular_nota_final(alumno, curso)

            # Obtener notas individuales (solo mostrar >= 0)
            notas_parciales = {1: "", 2: "", 3: ""}
            notas_continuas = {1: "", 2: "", 3: ""}
            nota_sustitutorio = ""

            for periodo in [1, 2, 3]:
                nota_parcial = Nota.objects.filter(
                    alumno=alumno, curso=curso, tipo="P", periodo=periodo
                ).first()
                if (
                    nota_parcial
                    and nota_parcial.valor is not None
                    and nota_parcial.valor >= 0
                ):
                    notas_parciales[periodo] = nota_parcial.valor

                nota_continua = Nota.objects.filter(
                    alumno=alumno, curso=curso, tipo="C", periodo=periodo
                ).first()
                if (
                    nota_continua
                    and nota_continua.valor is not None
                    and nota_continua.valor >= 0
                ):
                    notas_continuas[periodo] = nota_continua.valor

            nota_sust = Nota.objects.filter(
                alumno=alumno, curso=curso, tipo="S"
            ).first()
            if nota_sust and nota_sust.valor is not None and nota_sust.valor >= 0:
                nota_sustitutorio = nota_sust.valor

            # Determinar estado
            estado = "Sin nota"
            if nota_final is not None and nota_final >= 0:
                estado = "Aprobado" if nota_final >= 10.5 else "Desaprobado"

            data.append(
                {
                    "DNI": alumno.dni,
                    "Alumno": alumno.nombre,
                    "Parcial 1": notas_parciales[1],
                    "Parcial 2": notas_parciales[2],
                    "Parcial 3": notas_parciales[3],
                    "Continua 1": notas_continuas[1],
                    "Continua 2": notas_continuas[2],
                    "Continua 3": notas_continuas[3],
                    "Sustitutorio": nota_sustitutorio,
                    "Nota Final": nota_final
                    if nota_final is not None and nota_final >= 0
                    else "",
                    "Estado": estado,
                }
            )

        # Crear DataFrame principal
        df = pd.DataFrame(data)

        # Crear output
        output = io.BytesIO()

        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            # Hoja 1: Datos de alumnos
            df.to_excel(writer, sheet_name="Estadisticas_Alumnos", index=False)

            # Hoja 2: Resumen general
            resumen_data = []
            if data:
                # Solo considerar notas válidas (>= 0)
                notas_finales = [
                    d["Nota Final"]
                    for d in data
                    if d["Nota Final"] != "" and float(d["Nota Final"]) >= 0
                ]

                if notas_finales:
                    aprobados = sum(1 for d in data if d["Estado"] == "Aprobado")
                    desaprobados = sum(1 for d in data if d["Estado"] == "Desaprobado")
                    sin_nota = sum(1 for d in data if d["Estado"] == "Sin nota")

                    resumen_data.extend(
                        [
                            ["Total Alumnos", len(data)],
                            ["Con Nota Final", len(notas_finales)],
                            ["Sin Nota Final", sin_nota],
                            ["Aprobados", aprobados],
                            ["Desaprobados", desaprobados],
                            [
                                "Tasa Aprobación",
                                f"{(aprobados / len(notas_finales) * 100):.2f}%"
                                if notas_finales
                                else "0%",
                            ],
                            [
                                "Nota Promedio",
                                f"{sum(notas_finales) / len(notas_finales):.2f}"
                                if notas_finales
                                else "0.00",
                            ],
                            [
                                "Nota Máxima",
                                f"{max(notas_finales):.2f}"
                                if notas_finales
                                else "0.00",
                            ],
                            [
                                "Nota Mínima",
                                f"{min(notas_finales):.2f}"
                                if notas_finales
                                else "0.00",
                            ],
                        ]
                    )
                else:
                    resumen_data.extend(
                        [
                            ["Total Alumnos", len(data)],
                            ["Con Nota Final", 0],
                            ["Sin Nota Final", len(data)],
                            ["Aprobados", 0],
                            ["Desaprobados", 0],
                            ["Tasa Aprobación", "0%"],
                            ["Nota Promedio", "0.00"],
                            ["Nota Máxima", "0.00"],
                            ["Nota Mínima", "0.00"],
                        ]
                    )

            df_resumen = pd.DataFrame(resumen_data, columns=["Métrica", "Valor"])
            df_resumen.to_excel(writer, sheet_name="Resumen_General", index=False)

            # Ajustar el ancho de las columnas automáticamente
            for sheet_name in writer.sheets:
                worksheet = writer.sheets[sheet_name]
                for column in worksheet.columns:
                    max_length = 0
                    column_letter = column[0].column_letter
                    for cell in column:
                        try:
                            if len(str(cell.value)) > max_length:
                                max_length = len(str(cell.value))
                        except:
                            pass
                    adjusted_width = min(max_length + 2, 50)
                    worksheet.column_dimensions[column_letter].width = adjusted_width

        output.seek(0)

        # Crear respuesta HTTP
        response = HttpResponse(
            output.getvalue(),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        response["Content-Disposition"] = (
            f'attachment; filename="estadisticas_{grupo_teoria.curso.nombre}_{grupo_teoria.turno}.xlsx"'
        )

        return response

    except Exception as e:
        messages.error(request, f"Error al generar Excel: {str(e)}")
        return redirect("revisar_estadisticas")


def calcular_estadisticas_avance(grupo_teoria, alumnos_grupo):
    """
    Calcula estadísticas de avance por periodos para gráficos - VERSIÓN CON -1
    """
    curso = grupo_teoria.curso
    estadisticas_avance = {
        "parciales": {
            "periodos": [],
            "promedios": [],
            "tiene_datos": [],
            "alumnos_evaluados": [],
        },
        "continuas": {
            "periodos": [],
            "promedios": [],
            "tiene_datos": [],
            "alumnos_evaluados": [],
        },
    }

    # Estadísticas de avance de parciales
    for periodo in [1, 2, 3]:
        peso_parcial = getattr(curso, f"peso_parcial_{periodo}", 0)
        if peso_parcial > 0:
            notas_periodo = []
            alumnos_evaluados = 0

            for matricula in alumnos_grupo:
                nota = Nota.objects.filter(
                    alumno=matricula.alumno, curso=curso, tipo="P", periodo=periodo
                ).first()
                # Solo considerar notas válidas (>= 0)
                if nota and nota.valor is not None and nota.valor >= 0:
                    notas_periodo.append(nota.valor)
                    alumnos_evaluados += 1

            tiene_datos = len(notas_periodo) > 0
            promedio = (
                round(sum(notas_periodo) / len(notas_periodo), 2) if tiene_datos else 0
            )

            estadisticas_avance["parciales"]["periodos"].append(f"P{periodo}")
            estadisticas_avance["parciales"]["promedios"].append(promedio)
            estadisticas_avance["parciales"]["tiene_datos"].append(tiene_datos)
            estadisticas_avance["parciales"]["alumnos_evaluados"].append(
                alumnos_evaluados
            )

    # Estadísticas de avance de continuas
    for periodo in [1, 2, 3]:
        peso_continua = getattr(curso, f"peso_continua_{periodo}", 0)
        if peso_continua > 0:
            notas_periodo = []
            alumnos_evaluados = 0

            for matricula in alumnos_grupo:
                nota = Nota.objects.filter(
                    alumno=matricula.alumno, curso=curso, tipo="C", periodo=periodo
                ).first()
                # Solo considerar notas válidas (>= 0)
                if nota and nota.valor is not None and nota.valor >= 0:
                    notas_periodo.append(nota.valor)
                    alumnos_evaluados += 1

            tiene_datos = len(notas_periodo) > 0
            promedio = (
                round(sum(notas_periodo) / len(notas_periodo), 2) if tiene_datos else 0
            )

            estadisticas_avance["continuas"]["periodos"].append(f"C{periodo}")
            estadisticas_avance["continuas"]["promedios"].append(promedio)
            estadisticas_avance["continuas"]["tiene_datos"].append(tiene_datos)
            estadisticas_avance["continuas"]["alumnos_evaluados"].append(
                alumnos_evaluados
            )

    return estadisticas_avance
