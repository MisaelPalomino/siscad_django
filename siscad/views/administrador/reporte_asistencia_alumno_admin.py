from ..comunes.imports import *
from django.http import HttpResponse
import pandas as pd
from datetime import datetime
from django.db import models


def reporte_asistencia_alumno_admin(request):
    # Obtener parámetros del filtro
    dni_alumno = request.GET.get('dni_alumno')
    curso_id = request.GET.get('curso_id')
    fecha_inicio = request.GET.get('fecha_inicio')
    fecha_fin = request.GET.get('fecha_fin')
    
    alumno_seleccionado = None
    cursos_alumno = []
    estadisticas = {}
    asistencias = []
    
    # Si se proporcionó DNI, buscar el alumno
    if dni_alumno:
        alumno_seleccionado = Alumno.objects.filter(dni=dni_alumno).first()
        
        if alumno_seleccionado:
            # Obtener cursos en los que está matriculado el alumno
            matriculas = MatriculaCurso.objects.filter(alumno=alumno_seleccionado).select_related('curso')
            cursos_alumno = [matricula.curso for matricula in matriculas]
            
            # Filtrar asistencias del alumno
            asistencias_query = AsistenciaAlumno.objects.filter(
                alumno=alumno_seleccionado
            ).select_related(
                'hora__grupo_teoria__curso',
                'hora__grupo_practica__grupo_teoria__curso',
                'hora__grupo_laboratorio__grupo_teoria__curso'
            ).order_by('-fecha')
            
            # Filtrar por curso si se seleccionó uno
            if curso_id:
                asistencias_query = asistencias_query.filter(
                    models.Q(hora__grupo_teoria__curso__id=curso_id) |
                    models.Q(hora__grupo_practica__grupo_teoria__curso__id=curso_id) |
                    models.Q(hora__grupo_laboratorio__grupo_teoria__curso__id=curso_id)
                )
            
            # Aplicar filtros de fecha si existen
            if fecha_inicio:
                asistencias_query = asistencias_query.filter(fecha__gte=fecha_inicio)
            if fecha_fin:
                asistencias_query = asistencias_query.filter(fecha__lte=fecha_fin)
            
            asistencias = asistencias_query
            
            # Calcular estadísticas
            total_asistencias = asistencias.count()
            if total_asistencias > 0:
                presentes = asistencias.filter(estado='P').count()
                faltas = asistencias.filter(estado='F').count()
                
                estadisticas = {
                    'total': total_asistencias,
                    'presentes': presentes,
                    'faltas': faltas,
                    'porcentaje_asistencia': (presentes / total_asistencias) * 100 if total_asistencias > 0 else 0,
                    'porcentaje_faltas': (faltas / total_asistencias) * 100 if total_asistencias > 0 else 0,
                }
    
    # Descargar Excel si se solicita
    if request.GET.get('descargar_excel') and alumno_seleccionado and asistencias:
        return generar_excel_asistencia(alumno_seleccionado, asistencias, estadisticas, curso_id)
    
    context = {
        'alumno_seleccionado': alumno_seleccionado,
        'cursos_alumno': cursos_alumno,
        'dni_alumno': dni_alumno or '',
        'curso_id': curso_id or '',
        'fecha_inicio': fecha_inicio or '',
        'fecha_fin': fecha_fin or '',
        'asistencias': asistencias,
        'estadisticas': estadisticas,
    }
    
    return render(request, 'siscad/admin/reporte_asistencia_alumno_admin.html', context)

def generar_excel_asistencia(alumno, asistencias, estadisticas, curso_id=None):
    # Crear DataFrame con los datos
    data = []
    for asistencia in asistencias:
        # Determinar el curso
        curso_nombre = "No especificado"
        tipo_sesion = "No especificado"
        
        if asistencia.hora.grupo_teoria:
            curso_nombre = asistencia.hora.grupo_teoria.curso.nombre
            tipo_sesion = "Teoría"
        elif asistencia.hora.grupo_practica:
            curso_nombre = asistencia.hora.grupo_practica.grupo_teoria.curso.nombre
            tipo_sesion = "Práctica"
        elif asistencia.hora.grupo_laboratorio:
            curso_nombre = asistencia.hora.grupo_laboratorio.grupo_teoria.curso.nombre
            tipo_sesion = "Laboratorio"
        
        data.append({
            'Fecha': asistencia.fecha.strftime('%d/%m/%Y'),
            'Curso': curso_nombre,
            'Tipo de Sesión': tipo_sesion,
            'Estado': 'Presente' if asistencia.estado == 'P' else 'Falta',
            'Día': asistencia.hora.get_dia_display(),
            'Hora Inicio': asistencia.hora.hora_inicio.strftime('%H:%M'),
            'Hora Fin': asistencia.hora.hora_fin.strftime('%H:%M'),
        })
    
    # Crear el DataFrame
    df = pd.DataFrame(data)
    
    # Crear respuesta HTTP con el Excel
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    filename = f"asistencia_{alumno.dni}_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
    response['Content-Disposition'] = f'attachment; filename={filename}'
    
    # Crear el Excel con pandas
    with pd.ExcelWriter(response, engine='openpyxl') as writer:
        # Hoja de detalle de asistencias
        df.to_excel(writer, sheet_name='Detalle Asistencias', index=False)
        
        # Hoja de estadísticas
        stats_data = {
            'Estadística': [
                'Total de registros',
                'Asistencias',
                'Faltas',
                'Porcentaje de Asistencia',
                'Porcentaje de Faltas'
            ],
            'Valor': [
                estadisticas['total'],
                estadisticas['presentes'],
                estadisticas['faltas'],
                f"{estadisticas['porcentaje_asistencia']:.2f}%",
                f"{estadisticas['porcentaje_faltas']:.2f}%"
            ]
        }
        stats_df = pd.DataFrame(stats_data)
        stats_df.to_excel(writer, sheet_name='Estadísticas', index=False)
        
        # Hoja de información del alumno
        info_data = {
            'Campo': ['Nombre', 'DNI', 'CUI', 'Email', 'Semestre Asignado'],
            'Valor': [
                alumno.nombre,
                alumno.dni,
                alumno.cui,
                alumno.email,
                alumno.semestre_asignado or 'No asignado'
            ]
        }
        info_df = pd.DataFrame(info_data)
        info_df.to_excel(writer, sheet_name='Información Alumno', index=False)
    
    return response