from ..comunes.imports import *
import pandas as pd
from django.http import HttpResponse


def visualizar_matriculados_admin(request):
    if "email" not in request.session or request.session.get("rol") != "Administrador":
        return redirect("login")

    cursos = Curso.objects.all()
    turnos = MatriculaCurso.TURNOS
    matriculados_data = []
    curso_seleccionado = None
    turno_seleccionado = None

    if request.method == "POST":
        curso_id = request.POST.get("curso_id")
        turno = request.POST.get("turno")
        descargar_excel = request.POST.get("descargar_excel")

        if curso_id:
            curso_seleccionado = get_object_or_404(Curso, id=curso_id)
            turno_seleccionado = turno

            # Obtener alumnos matriculados
            if turno:
                matriculados = MatriculaCurso.objects.filter(
                    curso=curso_seleccionado, turno=turno
                ).select_related("alumno")
            else:
                matriculados = MatriculaCurso.objects.filter(
                    curso=curso_seleccionado
                ).select_related("alumno")

            # Preparar datos para mostrar
            for matricula in matriculados:
                matriculados_data.append(
                    {
                        "alumno": matricula.alumno,
                        "turno": matricula.turno,
                        "fecha_matricula": matricula.fecha
                        if hasattr(matricula, "fecha")
                        else "N/A",
                    }
                )

            # Descargar Excel si se solicita
            if descargar_excel and matriculados_data:
                return generar_excel_matriculados(
                    matriculados_data, curso_seleccionado, turno_seleccionado
                )

    context = {
        "cursos": cursos,
        "turnos": turnos,
        "matriculados_data": matriculados_data,
        "curso_seleccionado": curso_seleccionado,
        "turno_seleccionado": turno_seleccionado,
    }

    return render(request, "siscad/admin/visualizar_matriculados.html", context)


def generar_excel_matriculados(matriculados_data, curso, turno):
    """Genera un archivo Excel con los alumnos matriculados"""

    # Crear DataFrame
    data = []
    for item in matriculados_data:
        alumno = item["alumno"]
        data.append(
            {
                "DNI": alumno.dni,
                "Nombre": alumno.nombre,
                "Email": alumno.email,
                "CUI": alumno.cui,
                "Semestre": alumno.semestre_asignado,
                "Turno": item["turno"],
                "Fecha Matrícula": item["fecha_matricula"],
            }
        )

    df = pd.DataFrame(data)

    # Crear respuesta HTTP con el Excel
    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    nombre_archivo = f"matriculados_{curso.nombre.replace(' ', '_')}"
    if turno:
        nombre_archivo += f"_turno_{turno}"
    nombre_archivo += ".xlsx"

    response["Content-Disposition"] = f"attachment; filename={nombre_archivo}"

    # Escribir DataFrame a Excel
    with pd.ExcelWriter(response, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="Matriculados", index=False)

        # Ajustar anchos de columna
        worksheet = writer.sheets["Matriculados"]
        worksheet.column_dimensions["A"].width = 15  # DNI
        worksheet.column_dimensions["B"].width = 30  # Nombre
        worksheet.column_dimensions["C"].width = 25  # Email
        worksheet.column_dimensions["D"].width = 15  # CUI
        worksheet.column_dimensions["E"].width = 10  # Semestre
        worksheet.column_dimensions["F"].width = 10  # Turno
        worksheet.column_dimensions["G"].width = 15  # Fecha

    return response
