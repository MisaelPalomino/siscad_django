from ..comunes.imports import *
from django.http import HttpResponse
import pandas as pd
import io
from datetime import datetime, timedelta
import os
from django.conf import settings


def subir_silabo(request):
    if "email" not in request.session:
        return redirect("login")

    profesor = get_object_or_404(Profesor, email=request.session["email"])

    # Obtener grupos de teoría con información de silabos existentes
    grupos_teoria = GrupoTeoria.objects.filter(profesor=profesor).select_related(
        "curso"
    )

    cursos_con_silabo = []
    for grupo in grupos_teoria:
        silabo_existente = Silabo.objects.filter(grupo_teoria=grupo).first()
        cursos_con_silabo.append(
            {
                "id": grupo.curso.id,
                "nombre": grupo.curso.nombre,
                "tipo": "Teoría",
                "turno": grupo.turno,
                "grupo_id": grupo.id,
                "codigo_curso": grupo.curso.codigo or "0000",
                "silabo_existente": silabo_existente,
                "temas_count": Tema.objects.filter(silabo=silabo_existente).count()
                if silabo_existente
                else 0,
            }
        )

    if request.method == "POST":
        grupo_id = request.POST.get("grupo_id")
        archivo_silabo = request.FILES.get("archivo_silabo")
        archivo_excel = request.FILES.get("archivo_excel")

        if not grupo_id:
            messages.error(request, "Debe seleccionar un grupo")
            return redirect("subir_silabo")

        grupo_teoria = get_object_or_404(GrupoTeoria, id=grupo_id, profesor=profesor)

        # Procesar archivo de silabo PDF
        if archivo_silabo:
            try:
                # Crear carpeta por código de curso si no existe
                codigo_curso = grupo_teoria.curso.codigo or "0000"
                carpeta_curso = f"archivos/Silabos/{codigo_curso}"
                ruta_completa = os.path.join(settings.MEDIA_ROOT, carpeta_curso)

                # Crear directorio si no existe
                os.makedirs(ruta_completa, exist_ok=True)

                # Generar nombre del archivo: silabo-codigocurso-turno.pdf
                nuevo_nombre = f"silabo-{codigo_curso}-{grupo_teoria.turno}.pdf"
                ruta_archivo = os.path.join(carpeta_curso, nuevo_nombre)

                # Crear o actualizar silabo
                silabo, created = Silabo.objects.get_or_create(
                    grupo_teoria=grupo_teoria,
                    defaults={
                        "nombre": f"Silabo {grupo_teoria.curso.nombre} - {grupo_teoria.turno}",
                        "archivo": archivo_silabo,
                    },
                )

                if not created:
                    # Si ya existe, eliminar el archivo anterior y actualizar
                    if silabo.archivo:
                        # Eliminar archivo físico anterior
                        if os.path.exists(silabo.archivo.path):
                            os.remove(silabo.archivo.path)
                    silabo.archivo = archivo_silabo
                    silabo.save()

                # Forzar el guardado con el nuevo nombre y ruta
                silabo.archivo.name = ruta_archivo
                silabo.save()

                messages.success(request, "Silabo subido correctamente")

            except Exception as e:
                messages.error(request, f"Error al subir el silabo: {str(e)}")
                return redirect("subir_silabo")

        # Procesar archivo Excel de temas
        if archivo_excel:
            try:
                # Verificar que existe silabo primero
                silabo = Silabo.objects.filter(grupo_teoria=grupo_teoria).first()
                if not silabo:
                    messages.error(
                        request,
                        "Primero debe subir el silabo PDF antes de procesar los temas",
                    )
                    return redirect("subir_silabo")

                temas_creados = procesar_excel_temas(
                    request, archivo_excel, grupo_teoria
                )
                messages.success(
                    request, f"{len(temas_creados)} temas procesados correctamente"
                )

            except Exception as e:
                messages.error(request, f"Error al procesar el Excel: {str(e)}")
                return redirect("subir_silabo")

        return redirect("subir_silabo")

    context = {
        "cursos": cursos_con_silabo,
    }
    return render(request, "siscad/profesor/subir_silabo.html", context)


def procesar_excel_temas(request, archivo_excel, grupo_teoria):
    """
    Procesa el archivo Excel de temas y distribuye las fechas equitativamente
    """
    try:
        # Leer el archivo Excel
        df = pd.read_excel(archivo_excel)

        # Validar columnas requeridas
        columnas_requeridas = ["numero_tema", "nombre_tema"]
        for columna in columnas_requeridas:
            if columna not in df.columns:
                raise ValueError(f"La columna '{columna}' es requerida en el Excel")

        # Validar que los números de tema sean únicos y secuenciales
        if not df["numero_tema"].is_unique:
            raise ValueError("Los números de tema deben ser únicos")

        if not all(df["numero_tema"].diff().dropna() == 1):
            raise ValueError(
                "Los números de tema deben ser secuenciales (1, 2, 3, ...)"
            )

        # Obtener el silabo del grupo
        silabo = Silabo.objects.filter(grupo_teoria=grupo_teoria).first()
        if not silabo:
            raise ValueError(
                "Primero debe subir el silabo PDF antes de procesar los temas"
            )

        cantidad_temas = len(df)

        # Obtener fechas reales de las asistencias de TEORÍA del profesor para este grupo
        fechas_clase = obtener_fechas_teoria_reales(grupo_teoria)

        if not fechas_clase:
            raise ValueError("No se encontraron fechas de teoría para este curso")

        # Distribuir temas equitativamente entre las fechas disponibles
        fechas_distribuidas = distribuir_temas_equitativamente(
            cantidad_temas, fechas_clase
        )

        # Eliminar temas existentes para este silabo
        Tema.objects.filter(silabo=silabo).delete()

        # Crear nuevos temas con estado automático (HECHO/NO HECHO)
        temas_creados = []
        fecha_actual = datetime.now().date()

        for index, row in df.iterrows():
            numero_tema = int(row["numero_tema"])
            nombre_tema = row["nombre_tema"]
            fecha_tema = fechas_distribuidas[index]

            # Determinar estado automáticamente: si la fecha ya pasó -> HECHO, sino -> NO HECHO
            estado_tema = "H" if fecha_tema < fecha_actual else "N"

            tema = Tema.objects.create(
                nombre=nombre_tema,
                silabo=silabo,
                estado=estado_tema,
                fecha=fecha_tema,
                grupo_teoria=grupo_teoria,
            )
            temas_creados.append(tema)

        return temas_creados

    except Exception as e:
        raise Exception(f"Error al procesar Excel: {str(e)}")


def distribuir_temas_equitativamente(cantidad_temas, fechas_clase):
    """
    Distribuye los temas equitativamente entre las fechas disponibles
    Respetando el orden secuencial de los temas
    """
    if not fechas_clase or cantidad_temas == 0:
        return []

    cantidad_fechas = len(fechas_clase)
    fechas_distribuidas = []

    # Caso 1: Misma cantidad de temas y fechas
    if cantidad_temas == cantidad_fechas:
        return fechas_clase

    # Caso 2: Más temas que fechas - Distribuir múltiples temas por fecha
    elif cantidad_temas > cantidad_fechas:
        temas_por_fecha = cantidad_temas // cantidad_fechas
        temas_extra = cantidad_temas % cantidad_fechas

        for i, fecha in enumerate(fechas_clase):
            # Calcular cuántos temas van en esta fecha
            cantidad_en_fecha = temas_por_fecha + (1 if i < temas_extra else 0)

            # Agregar la fecha múltiples veces según la cantidad de temas
            fechas_distribuidas.extend([fecha] * cantidad_en_fecha)

        return fechas_distribuidas

    # Caso 3: Más fechas que temas - Distribuir temas equitativamente en el tiempo
    else:
        # Calcular intervalo para distribuir los temas a lo largo de todas las fechas
        intervalo = max(1, cantidad_fechas // cantidad_temas)

        for i in range(cantidad_temas):
            # Seleccionar fechas distribuidas equitativamente
            indice = min(i * intervalo, cantidad_fechas - 1)
            fechas_distribuidas.append(fechas_clase[indice])

        return fechas_distribuidas


def obtener_fechas_teoria_reales(grupo_teoria):
    """
    Obtiene las fechas reales de clase de TEORÍA basadas en las asistencias del profesor
    """
    try:
        # Obtener SOLO las asistencias de TEORÍA del profesor para este grupo
        asistencias = (
            AsistenciaProfesor.objects.filter(
                profesor=grupo_teoria.profesor,
                hora__grupo_teoria=grupo_teoria,
                hora__tipo="T",  # Solo teoría
            )
            .select_related("hora")
            .order_by("fecha")
        )

        if asistencias.exists():
            # Si hay asistencias de teoría registradas, usar esas fechas
            fechas_clase = list(asistencias.values_list("fecha", flat=True).distinct())
            return sorted(fechas_clase)

        else:
            # Si no hay asistencias, usar las horas programadas de TEORÍA para generar fechas
            return obtener_fechas_de_horario_teoria(grupo_teoria)

    except Exception as e:
        print(f"Error al obtener fechas de teoría reales: {str(e)}")
        return obtener_fechas_de_horario_teoria(grupo_teoria)


def obtener_fechas_de_horario_teoria(grupo_teoria):
    """
    Obtiene fechas basadas en el horario programado de TEORÍA del profesor
    """
    try:
        # Obtener SOLO horas de TEORÍA para este grupo
        horas_teoria = Hora.objects.filter(
            grupo_teoria=grupo_teoria,
            tipo="T",  # Solo teoría
        ).order_by("dia", "hora_inicio")

        if not horas_teoria:
            return []

        # Obtener el rango de fechas del semestre actual
        fecha_inicio, fecha_fin = obtener_rango_semestre_actual()

        if not fecha_inicio or not fecha_fin:
            # Si no hay rango definido, usar año académico por defecto
            año_actual = datetime.now().year
            fecha_inicio = datetime(año_actual, 3, 1).date()
            fecha_fin = datetime(año_actual, 12, 31).date()

        # Agrupar horas por día de la semana
        dias_clase = set()
        for hora in horas_teoria:
            dias_clase.add(hora.dia)

        # Ordenar días de la semana
        orden_dias = {"L": 0, "M": 1, "X": 2, "J": 3, "V": 4}
        dias_ordenados = sorted(dias_clase, key=lambda x: orden_dias.get(x, 5))

        # Generar fechas en el rango del semestre
        fecha_actual = fecha_inicio
        fechas_clase = []

        while fecha_actual <= fecha_fin:
            dia_semana_actual = fecha_actual.weekday()
            dia_letra_actual = obtener_letra_dia(dia_semana_actual)

            if dia_letra_actual in dias_ordenados:
                fechas_clase.append(fecha_actual)

            fecha_actual += timedelta(days=1)

        return fechas_clase

    except Exception as e:
        print(f"Error al obtener fechas de horario teoría: {str(e)}")
        return []


def obtener_rango_semestre_actual():
    """
    Intenta obtener el rango de fechas del semestre actual
    """
    try:
        # Buscar en las asistencias de TEORÍA existentes para determinar el rango
        asistencias = AsistenciaProfesor.objects.filter(
            hora__tipo="T"  # Solo teoría
        ).order_by("fecha")

        if asistencias.exists():
            fecha_inicio = asistencias.first().fecha
            fecha_fin = asistencias.last().fecha
            return fecha_inicio, fecha_fin

        # Si no hay asistencias, usar fechas por defecto del semestre
        año_actual = datetime.now().year
        mes_actual = datetime.now().month

        if mes_actual >= 1 and mes_actual <= 6:  # Primer semestre
            fecha_inicio = datetime(año_actual, 3, 1).date()
            fecha_fin = datetime(año_actual, 7, 31).date()
        else:  # Segundo semestre
            fecha_inicio = datetime(año_actual, 8, 1).date()
            fecha_fin = datetime(año_actual, 12, 31).date()

        return fecha_inicio, fecha_fin

    except Exception as e:
        print(f"Error al obtener rango semestre: {str(e)}")
        return None, None


def obtener_letra_dia(numero_dia):
    """
    Convierte número de día (0-6) a letra (L,M,X,J,V)
    """
    mapeo_dias = {
        0: "L",  # Lunes
        1: "M",  # Martes
        2: "X",  # Miércoles
        3: "J",  # Jueves
        4: "V",  # Viernes
    }
    return mapeo_dias.get(numero_dia)


def descargar_plantilla_silabo_excel(request, grupo_id):
    """
    Descarga una plantilla Excel para subir temas del silabo
    """
    try:
        # Verificar que el grupo existe y pertenece al profesor
        if "email" not in request.session:
            return redirect("login")

        profesor = get_object_or_404(Profesor, email=request.session["email"])
        grupo_teoria = get_object_or_404(GrupoTeoria, id=grupo_id, profesor=profesor)

        # Obtener información de fechas reales de TEORÍA para mostrar en la plantilla
        fechas_reales = obtener_fechas_teoria_reales(grupo_teoria)
        total_fechas = len(fechas_reales)

        # Crear DataFrame con temas predefinidos
        data = {
            "numero_tema": list(range(1, 21)),
            "nombre_tema": [
                "Introducción al curso y presentación del silabo",
                "Fundamentos teóricos y marco conceptual",
                "Metodologías de investigación aplicada al área",
                "Herramientas y tecnologías básicas requeridas",
                "Análisis de casos de estudio I: Aplicaciones prácticas",
                "Desarrollo de habilidades técnicas fundamentales",
                "Evaluación formativa y retroalimentación inicial",
                "Profundización en conceptos avanzados",
                "Técnicas de análisis y resolución de problemas",
                "Aplicación de herramientas especializadas",
                "Proyecto integrador: Planificación y diseño",
                "Análisis de casos de estudio II: Situaciones complejas",
                "Desarrollo de competencias profesionales",
                "Trabajo en equipo y colaboración efectiva",
                "Evaluación intermedia y ajuste de estrategias",
                "Innovación y tendencias actuales en el campo",
                "Optimización y mejora de procesos",
                "Proyecto integrador: Implementación y desarrollo",
                "Presentación de resultados y comunicación efectiva",
                "Evaluación final, conclusiones y cierre del curso",
            ],
        }

        df = pd.DataFrame(data)

        # Crear output
        output = io.BytesIO()

        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            # Hoja de temas
            df.to_excel(writer, sheet_name="Temas", index=False)

            # Hoja de instrucciones
            instrucciones_data = {
                "COLUMNA": ["numero_tema", "nombre_tema"],
                "DESCRIPCIÓN": [
                    "Número secuencial del tema (1, 2, 3, ...). Debe ser único y en orden.",
                    "Nombre descriptivo del tema. Puede modificar los nombres predefinidos según su curso.",
                ],
                "REQUERIDO": ["SÍ", "SÍ"],
                "EJEMPLO": ["1", "Introducción al curso y presentación del silabo"],
            }

            instrucciones_df = pd.DataFrame(instrucciones_data)
            instrucciones_df.to_excel(writer, sheet_name="Instrucciones", index=False)

            # Hoja de información del curso
            info_curso = [
                f"Curso: {grupo_teoria.curso.nombre}",
                f"Código: {grupo_teoria.curso.codigo or '0000'}",
                f"Turno: {grupo_teoria.turno}",
                f"Profesor: {profesor.nombre}",
                f"Fechas de TEORÍA disponibles: {total_fechas}",
                f"Primera fecha: {fechas_reales[0] if fechas_reales else 'No definida'}",
                f"Última fecha: {fechas_reales[-1] if fechas_reales else 'No definida'}",
                "",
                "DISTRIBUCIÓN AUTOMÁTICA DE FECHAS:",
                f"- Se utilizarán las {total_fechas} fechas de TEORÍA",
                "- Distribución EQUITATIVA y ORDENADA de temas",
                "- Estados automáticos: HECHO si la fecha ya pasó, NO HECHO si es futura",
                "",
                "EJEMPLOS DE DISTRIBUCIÓN:",
                f"- 20 temas + {total_fechas} fechas: Distribución optimizada",
                "- Más temas que fechas: Múltiples temas por fecha",
                "- Más fechas que temas: Temas distribuidos en el tiempo",
                "",
                "IMPORTANTE:",
                "- Los temas mantendrán su orden secuencial",
                "- La distribución respeta las fechas reales de teoría",
                "- Puede modificar los nombres de temas según su plan de estudios",
            ]

            info_df = pd.DataFrame({"INFORMACIÓN DEL CURSO": info_curso})
            info_df.to_excel(writer, sheet_name="Información", index=False)

            # Ajustar el ancho de las columnas
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
        filename = f"plantilla_temas_{grupo_teoria.curso.codigo or '0000'}_{grupo_teoria.turno}.xlsx"
        response["Content-Disposition"] = f'attachment; filename="{filename}"'

        return response

    except Exception as e:
        messages.error(request, f"Error al generar plantilla: {str(e)}")
        return redirect("subir_silabo")
