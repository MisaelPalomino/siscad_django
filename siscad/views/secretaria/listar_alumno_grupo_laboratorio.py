from ..comunes.imports import *

def listar_alumno_grupo_laboratorio(request):
    cursos = Curso.objects.all()
    laboratorios = []
    alumnos = []
    curso_id = None
    lab_id = None

    if request.method == "POST":
        curso_id = request.POST.get("curso_id")
        lab_id = request.POST.get("lab_id")

        # Filtrar laboratorios por curso seleccionado
        if curso_id:
            laboratorios = GrupoLaboratorio.objects.filter(
                grupo_teoria__curso_id=curso_id
            )

        # Buscar alumnos
        if lab_id and "buscar_alumnos" in request.POST:
            matriculas = MatriculaLaboratorio.objects.filter(
                grupo_laboratorio_id=lab_id
            )
            alumnos = [m.alumno for m in matriculas]

        # Descargar Excel
        if lab_id and "descargar_excel" in request.POST:
            matriculas = MatriculaLaboratorio.objects.filter(
                grupo_laboratorio_id=lab_id
            )
            alumnos = [m.alumno for m in matriculas]

            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = "Alumnos Laboratorio"

            headers = ["Nombre", "Email", "DNI", "CUI"]
            for col_num, header in enumerate(headers, 1):
                ws[f"{get_column_letter(col_num)}1"] = header

            for row_num, alumno in enumerate(alumnos, 2):
                ws[f"A{row_num}"] = alumno.nombre
                ws[f"B{row_num}"] = alumno.email
                ws[f"C{row_num}"] = alumno.dni
                ws[f"D{row_num}"] = alumno.cui

            response = HttpResponse(
                content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
            response["Content-Disposition"] = (
                'attachment; filename="Alumnos_Laboratorio.xlsx"'
            )
            wb.save(response)
            return response

    return render(
        request,
        "siscad/secretaria/listar_alumno_grupo_laboratorio.html",
        {
            "cursos": cursos,
            "laboratorios": laboratorios,
            "alumnos": alumnos,
            "curso_id": curso_id,
            "lab_id": lab_id,
        },
    )