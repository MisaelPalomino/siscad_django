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
    grupos_teoria = GrupoTeoria.objects.filter(profesor=profesor).select_related("curso")
    
    cursos_con_silabo = []
    for grupo in grupos_teoria:
        silabo_existente = Silabo.objects.filter(grupo_teoria=grupo).first()
        cursos_con_silabo.append({
            "id": grupo.curso.id,
            "nombre": grupo.curso.nombre,
            "tipo": "Teoría",
            "turno": grupo.turno,
            "grupo_id": grupo.id,
            "codigo_curso": grupo.curso.codigo or "0000",
            "silabo_existente": silabo_existente,
            "temas_count": Tema.objects.filter(silabo=silabo_existente).count() if silabo_existente else 0
        })

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
                        "archivo": archivo_silabo
                    }
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
                    messages.error(request, "Primero debe subir el silabo PDF antes de procesar los temas")
                    return redirect("subir_silabo")
                    
                temas_creados = procesar_excel_temas(request, archivo_excel, grupo_teoria)
                messages.success(request, f"{len(temas_creados)} temas procesados correctamente")
                
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
    Procesa el archivo Excel de temas y distribuye las fechas automáticamente
    UTILIZANDO TODAS LAS FECHAS DISPONIBLES
    """
    try:
        # Leer el archivo Excel
        df = pd.read_excel(archivo_excel)
        
        # Validar columnas requeridas
        columnas_requeridas = ['numero_tema', 'nombre_tema']
        for columna in columnas_requeridas:
            if columna not in df.columns:
                raise ValueError(f"La columna '{columna}' es requerida en el Excel")

        # Validar que los números de tema sean únicos y secuenciales
        if not df['numero_tema'].is_unique:
            raise ValueError("Los números de tema deben ser únicos")
        
        if not all(df['numero_tema'].diff().dropna() == 1):
            raise ValueError("Los números de tema deben ser secuenciales (1, 2, 3, ...)")

        # Obtener el silabo del grupo
        silabo = Silabo.objects.filter(grupo_teoria=grupo_teoria).first()
        if not silabo:
            raise ValueError("Primero debe subir el silabo PDF antes de procesar los temas")

        # Obtener horas de teoría del profesor para este curso
        horas_teoria = obtener_horas_teoria_profesor(grupo_teoria)
        if not horas_teoria:
            raise ValueError("No se encontraron horas de teoría asignadas para este curso")

        cantidad_temas = len(df)
        
        # Calcular fechas distribuidas - SIEMPRE USANDO TODAS LAS FECHAS
        fechas_distribuidas = distribuir_fechas_temas_usar_todas(cantidad_temas, horas_teoria)
        
        # Eliminar temas existentes para este silabo
        Tema.objects.filter(silabo=silabo).delete()

        # Crear nuevos temas
        temas_creados = []
        for index, row in df.iterrows():
            numero_tema = int(row['numero_tema'])
            nombre_tema = row['nombre_tema']
            fecha_tema = fechas_distribuidas[index] if index < len(fechas_distribuidas) else datetime.now().date()

            tema = Tema.objects.create(
                nombre=nombre_tema,
                silabo=silabo,
                estado="N",  # No hecho por defecto
                fecha=fecha_tema,
                grupo_teoria=grupo_teoria
            )
            temas_creados.append(tema)

        return temas_creados

    except Exception as e:
        raise Exception(f"Error al procesar Excel: {str(e)}")

def obtener_horas_teoria_profesor(grupo_teoria):
    """
    Obtiene las horas de teoría asignadas al profesor para este grupo
    """
    try:
        # Buscar horas de teoría para este grupo
        horas = Hora.objects.filter(
            grupo_teoria=grupo_teoria,
            tipo="T"  # Teoría
        ).order_by('dia', 'hora_inicio')
        
        return list(horas)
    
    except Exception as e:
        print(f"Error al obtener horas de teoría: {str(e)}")
        return []

def distribuir_fechas_temas_usar_todas(cantidad_temas, horas_teoria):
    """
    Distribuye las fechas de los temas SIEMPRE USANDO TODAS LAS FECHAS DISPONIBLES
    """
    if not horas_teoria:
        return []

    # Obtener todas las fechas de clase disponibles
    fechas_clase = obtener_fechas_clase(horas_teoria, cantidad_temas)
    
    if not fechas_clase:
        return []

    # SIEMPRE usar todas las fechas disponibles
    cantidad_fechas = len(fechas_clase)
    
    if cantidad_temas <= cantidad_fechas:
        # Más fechas que temas: distribuir temas equitativamente entre todas las fechas
        # Cada tema ocupa al menos una fecha, algunos temas ocupan fechas extras
        fechas_distribuidas = []
        
        # Calcular cuántas fechas extras hay para distribuir
        fechas_extras = cantidad_fechas - cantidad_temas
        
        # Distribuir fechas extras entre los temas
        temas_con_extra = fechas_extras  # Cuántos temas tendrán fecha extra
        
        for i in range(cantidad_temas):
            # Cada tema tiene al menos una fecha
            fechas_distribuidas.append(fechas_clase[i])
            
            # Algunos temas obtienen fechas extras (las primeras fechas restantes)
            if i < temas_con_extra:
                fecha_extra_index = cantidad_temas + i
                if fecha_extra_index < cantidad_fechas:
                    fechas_distribuidas.append(fechas_clase[fecha_extra_index])
        
        return fechas_distribuidas
    else:
        # Más temas que fechas: distribuir equitativamente (como antes)
        fechas_distribuidas = []
        temas_por_fecha = cantidad_temas // cantidad_fechas
        temas_extra = cantidad_temas % cantidad_fechas
        
        for i, fecha in enumerate(fechas_clase):
            # Calcular cuántos temas van en esta fecha
            cantidad_en_fecha = temas_por_fecha + (1 if i < temas_extra else 0)
            
            # Agregar la fecha múltiples veces según la cantidad de temas
            fechas_distribuidas.extend([fecha] * cantidad_en_fecha)
        
        return fechas_distribuidas

def distribuir_fechas_temas_optimizado(cantidad_temas, horas_teoria):
    """
    Versión optimizada: Siempre usa TODAS las fechas disponibles
    """
    if not horas_teoria:
        return []

    # Obtener todas las fechas de clase
    fechas_clase = obtener_fechas_clase(horas_teoria, cantidad_temas)
    
    if not fechas_clase:
        return []

    cantidad_fechas = len(fechas_clase)
    fechas_distribuidas = []
    
    # Caso 1: Mismas fechas que temas
    if cantidad_temas == cantidad_fechas:
        return fechas_clase[:cantidad_temas]
    
    # Caso 2: Más fechas que temas - USAR TODAS LAS FECHAS
    elif cantidad_temas < cantidad_fechas:
        # Distribuir los temas entre todas las fechas
        # Cada tema ocupa al menos una fecha, algunos ocupan múltiples
        temas_asignados = 0
        fecha_index = 0
        
        while temas_asignados < cantidad_temas and fecha_index < cantidad_fechas:
            # Asignar esta fecha al tema actual
            fechas_distribuidas.append(fechas_clase[fecha_index])
            temas_asignados += 1
            fecha_index += 1
            
            # Si todavía hay temas y fechas, algunos temas ocupan fechas extras
            if temas_asignados < cantidad_temas and fecha_index < cantidad_fechas:
                # El tema actual ocupa una fecha extra
                fechas_distribuidas.append(fechas_clase[fecha_index])
                fecha_index += 1
        
        return fechas_distribuidas
    
    # Caso 3: Más temas que fechas - Distribuir equitativamente
    else:
        temas_por_fecha = cantidad_temas // cantidad_fechas
        temas_extra = cantidad_temas % cantidad_fechas
        
        for i, fecha in enumerate(fechas_clase):
            cantidad_en_fecha = temas_por_fecha + (1 if i < temas_extra else 0)
            fechas_distribuidas.extend([fecha] * cantidad_en_fecha)
        
        return fechas_distribuidas

def obtener_fechas_clase(horas_teoria, cantidad_temas_necesarias):
    """
    Obtiene las fechas reales de clase basadas en el horario del profesor
    """
    # Agrupar horas por día de la semana
    dias_clase = set()
    for hora in horas_teoria:
        dias_clase.add(hora.dia)
    
    # Ordenar días de la semana (Lunes a Viernes)
    orden_dias = {'L': 0, 'M': 1, 'X': 2, 'J': 3, 'V': 4}
    dias_ordenados = sorted(dias_clase, key=lambda x: orden_dias.get(x, 5))

    # Calcular fechas empezando desde hoy
    fecha_actual = datetime.now().date()
    fechas_clase = []
    
    # Obtener suficientes fechas para cubrir el semestre (aprox 16 semanas)
    semanas_semestre = 16
    max_fechas = len(dias_ordenados) * semanas_semestre
    
    while len(fechas_clase) < max_fechas:
        dia_semana_actual = fecha_actual.weekday()
        dia_letra_actual = obtener_letra_dia(dia_semana_actual)
        
        # Si este día hay clase, agregar la fecha
        if dia_letra_actual in dias_ordenados:
            fechas_clase.append(fecha_actual)
        
        # Pasar al siguiente día
        fecha_actual += timedelta(days=1)

    return fechas_clase

def obtener_letra_dia(numero_dia):
    """
    Convierte número de día (0-6) a letra (L,M,X,J,V)
    """
    mapeo_dias = {
        0: 'L',  # Lunes
        1: 'M',  # Martes
        2: 'X',  # Miércoles
        3: 'J',  # Jueves
        4: 'V',  # Viernes
    }
    return mapeo_dias.get(numero_dia)

def descargar_plantilla_silabo_excel(request, grupo_id):
    """
    Descarga una plantilla Excel para subir temas del silabo con 20 temas predefinidos
    """
    try:
        # Verificar que el grupo existe y pertenece al profesor
        if "email" not in request.session:
            return redirect("login")
            
        profesor = get_object_or_404(Profesor, email=request.session["email"])
        grupo_teoria = get_object_or_404(GrupoTeoria, id=grupo_id, profesor=profesor)

        # Crear DataFrame con 20 temas predefinidos para un curso completo
        data = {
            'numero_tema': list(range(1, 21)),
            'nombre_tema': [
                'Introducción al curso y presentación del silabo',
                'Fundamentos teóricos y marco conceptual',
                'Metodologías de investigación aplicada al área',
                'Herramientas y tecnologías básicas requeridas',
                'Análisis de casos de estudio I: Aplicaciones prácticas',
                'Desarrollo de habilidades técnicas fundamentales',
                'Evaluación formativa y retroalimentación inicial',
                'Profundización en conceptos avanzados',
                'Técnicas de análisis y resolución de problemas',
                'Aplicación de herramientas especializadas',
                'Proyecto integrador: Planificación y diseño',
                'Análisis de casos de estudio II: Situaciones complejas',
                'Desarrollo de competencias profesionales',
                'Trabajo en equipo y colaboración efectiva',
                'Evaluación intermedia y ajuste de estrategias',
                'Innovación y tendencias actuales en el campo',
                'Optimización y mejora de procesos',
                'Proyecto integrador: Implementación y desarrollo',
                'Presentación de resultados y comunicación efectiva',
                'Evaluación final, conclusiones y cierre del curso'
            ]
        }
        
        df = pd.DataFrame(data)

        # Crear output
        output = io.BytesIO()
        
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            # Hoja de temas
            df.to_excel(writer, sheet_name='Temas', index=False)
            
            # Hoja de instrucciones detalladas
            instrucciones_data = {
                'COLUMNA': ['numero_tema', 'nombre_tema'],
                'DESCRIPCIÓN': [
                    'Número secuencial del tema (1, 2, 3, ...). Debe ser único y en orden.',
                    'Nombre descriptivo del tema. Puede modificar los nombres predefinidos según su curso.'
                ],
                'REQUERIDO': ['SÍ', 'SÍ'],
                'EJEMPLO': ['1', 'Introducción al curso y presentación del silabo']
            }
            
            instrucciones_df = pd.DataFrame(instrucciones_data)
            instrucciones_df.to_excel(writer, sheet_name='Instrucciones', index=False)
            
            # Hoja de información del curso
            info_data = {
                'INFORMACIÓN DEL CURSO': [
                    f'Curso: {grupo_teoria.curso.nombre}',
                    f'Código: {grupo_teoria.curso.codigo or "0000"}',
                    f'Turno: {grupo_teoria.turno}',
                    f'Profesor: {profesor.nombre}',
                    f'Semestre: {grupo_teoria.curso.semestre}',
                    '',
                    'DISTRIBUCIÓN AUTOMÁTICA DE FECHAS:',
                    '- Sistema utiliza TODAS las fechas disponibles del horario',
                    '- 20 temas predefinidos para un curso completo',
                    '- Fechas distribuidas equitativamente',
                    '- Orden secuencial garantizado',
                    '- Fines de semana excluidos automáticamente',
                    '',
                    'EJEMPLOS DE DISTRIBUCIÓN:',
                    '- 20 temas + 20 fechas: 1 tema por fecha',
                    '- 20 temas + 10 fechas: 2 temas por fecha',
                    '- 20 temas + 30 fechas: Algunos temas ocupan fechas extras'
                ]
            }
            
            info_df = pd.DataFrame(info_data)
            info_df.to_excel(writer, sheet_name='Información', index=False)

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
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        filename = f"plantilla_temas_{grupo_teoria.curso.codigo or '0000'}_{grupo_teoria.turno}.xlsx"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        return response

    except Exception as e:
        messages.error(request, f"Error al generar plantilla: {str(e)}")
        return redirect("subir_silabo")