from ..comunes.imports import *
# LA PUTAMADREEEE, falta verificar silabo subido en registrar asistencia pero easy, la plantilla ya la mando, falta verificar como se procesa un miserable pdf y un excel


# tipo de consulta, busco grupo de teoria con silabo luego reoria con profesor y queda, de ahi saco curso, codigo de curso, y asi guardo el pdf DNI_codigo_de_curso_turno.pdf
# falta corregir como se guarda un examen en memoria y pues marcar progreso y todo el panel de administrador
def subir_silabo(request):
    if "email" not in request.session:
        return redirect("login")
    profesor = get_object_or_404(Profesor, email=request.session["email"])
    cursos = []
    grupos_teoria = GrupoTeoria.objects.filter(profesor=profesor).select_related(
        "curso"
    )
    for grupo in grupos_teoria:
        cursos.append(
            {
                "id": grupo.curso.id,
                "nombre": grupo.curso.nombre,
                "tipo": "Teoría",
                "turno": grupo.turno,
                "grupo_id": grupo.id,
            }
        )
