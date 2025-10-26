from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.contrib import messages
from django.db import transaction
from .forms import UploadExcelForm
import openpyxl
from openpyxl.utils import get_column_letter
from .models import (
    Profesor,
    Alumno,
    Secretaria,
    Administrador,
    Nota,
    Curso,
    MatriculaCurso,
    GrupoTeoria,
    GrupoLaboratorio,
)
import pandas as pd


def inicio(request):
    nombre = request.session.get("nombre")
    rol = request.session.get("rol")

    if not nombre:
        return redirect("login")

    return render(request, "siscad/inicio.html", {"nombre": nombre, "rol": rol})


def login_view(request):
    if request.method == "POST":
        email = request.POST.get("email")
        dni = request.POST.get("dni")

        usuario = None
        rol = None

        if Profesor.objects.filter(email=email, dni=dni).exists():
            usuario = Profesor.objects.get(email=email, dni=dni)
            rol = "Profesor"
        elif Alumno.objects.filter(email=email, dni=dni).exists():
            usuario = Alumno.objects.get(email=email, dni=dni)
            rol = "Alumno"
        elif Secretaria.objects.filter(email=email, dni=dni).exists():
            usuario = Secretaria.objects.get(email=email, dni=dni)
            rol = "Secretaria"
        elif Administrador.objects.filter(email=email, dni=dni).exists():
            usuario = Administrador.objects.get(email=email, dni=dni)
            rol = "Administrador"

        if usuario:
            request.session["usuario_id"] = usuario.id
            request.session["rol"] = rol
            request.session["nombre"] = usuario.nombre
            messages.success(request, f"Bienvenido {rol} {usuario.nombre}")

            if rol == "Administrador":
                return redirect("inicio_admin")
            elif rol == "Secretaria":
                return redirect("inicio_secretaria")
            elif rol == "Profesor":
                return redirect("inicio_profesor")
            elif rol == "Alumno":
                return redirect("inicio_alumno")

        else:
            messages.error(request, "Email o DNI incorrectos")

    return render(request, "siscad/login.html")


def logout_view(request):
    request.session.flush()
    return redirect("login")


# =======================Vista de Secretaria ===============================================
def inicio_secretaria(request):
    return render(request, "siscad/secretaria/menu.html")


def insertar_alumnos_excel(request):
    if request.method == "POST":
        form = UploadExcelForm(request.POST, request.FILES)
        if form.is_valid():
            file = form.cleaned_data["file"]

            try:
                df = pd.read_excel(file)
                df.columns = [str(col).strip().lower() for col in df.columns]

                required_columns = [
                    "apellidop",
                    "apellidom",
                    "nombres",
                    "correo",
                    "dni",
                    "cui",
                ]
                missing = [col for col in required_columns if col not in df.columns]
                if missing:
                    messages.error(
                        request, f"Faltan columnas obligatorias: {', '.join(missing)}"
                    )
                    return redirect("insertar_alumnos_excel")

                created = 0
                updated = 0
                errores = []

                with transaction.atomic():
                    for index, row in df.iterrows():
                        apellidop = (
                            str(row["apellidop"]).strip()
                            if pd.notna(row["apellidop"])
                            else ""
                        )
                        apellidom = (
                            str(row["apellidom"]).strip()
                            if pd.notna(row["apellidom"])
                            else ""
                        )
                        nombres = (
                            str(row["nombres"]).strip()
                            if pd.notna(row["nombres"])
                            else ""
                        )
                        email = (
                            str(row["correo"]).strip().lower()
                            if pd.notna(row["correo"])
                            else ""
                        )
                        dni = str(row["dni"]).strip() if pd.notna(row["dni"]) else ""
                        cui = str(row["cui"]).strip() if pd.notna(row["cui"]) else ""

                        nombre = f"{apellidop} {apellidom} {nombres}".strip()

                        if not email:
                            errores.append(
                                f"Fila {index + 2}: email vacío, no se pudo procesar."
                            )
                            continue

                        alumno, created_flag = Alumno.objects.update_or_create(
                            email=email,
                            defaults={"nombre": nombre, "dni": dni, "cui": cui},
                        )

                        created += 1 if created_flag else updated + 1

                messages.success(
                    request,
                    f"✅ Importación completada: {created} creados, {updated} actualizados.",
                )
                if errores:
                    for err in errores[:10]:
                        messages.warning(request, err)

                return redirect("insertar_alumnos_excel")

            except Exception as e:
                messages.error(request, f"❌ Error leyendo el archivo: {e}")
                return redirect("insertar_alumnos_excel")

    else:
        form = UploadExcelForm()

    alumnos = Alumno.objects.all()

    return render(
        request,
        "siscad/secretaria/insertar_alumnos_excel.html",
        {"form": form, "alumnos": alumnos},
    )


def listar_alumno_grupo_teoria(request):
    alumnos = []
    curso_id = request.POST.get("curso_id", "")
    turno = request.POST.get("turno", "")
    semestre_tipo = request.POST.get("semestre_tipo", "")

    # Filtrar cursos según semestre seleccionado
    todos_cursos = Curso.objects.all()
    if semestre_tipo == "par":
        cursos = [c for c in todos_cursos if c.semestre % 2 == 0]
    elif semestre_tipo == "impar":
        cursos = [c for c in todos_cursos if c.semestre % 2 != 0]
    else:
        cursos = todos_cursos

    # Obtener turnos disponibles y alumnos si se seleccionó curso
    turnos = []
    if request.method == "POST" and curso_id:
        turnos = (
            GrupoTeoria.objects.filter(curso_id=curso_id)
            .values_list("turno", flat=True)
            .distinct()
        )

        if turno:
            matriculas = MatriculaCurso.objects.filter(curso_id=curso_id, turno=turno)
            alumnos = [matricula.alumno for matricula in matriculas]

        # Descargar Excel
        if "descargar_excel" in request.POST and alumnos:
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = "Alumnos"

            # Encabezados
            headers = ["Nombre", "Email", "DNI", "CUI"]
            for col_num, header in enumerate(headers, 1):
                ws[f"{get_column_letter(col_num)}1"] = header

            # Datos de alumnos
            for row_num, alumno in enumerate(alumnos, 2):
                ws[f"A{row_num}"] = alumno.nombre
                ws[f"B{row_num}"] = alumno.email
                ws[f"C{row_num}"] = alumno.dni
                ws[f"D{row_num}"] = alumno.cui

            # Nombre del archivo con curso y turno
            curso_nombre = Curso.objects.get(id=curso_id).nombre
            archivo_nombre = f"Alumnos_{curso_nombre}_Turno_{turno}.xlsx"

            response = HttpResponse(
                content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
            response["Content-Disposition"] = f'attachment; filename="{archivo_nombre}"'
            wb.save(response)
            return response

    return render(
        request,
        "siscad/secretaria/listar_alumnos_grupo_teoria.html",
        {
            "alumnos": alumnos,
            "cursos": cursos,
            "turnos": turnos,
            "curso_id": curso_id,
            "turno": turno,
            "semestre_tipo": semestre_tipo,
        },
    )


def listar_grupos_laboratorio(request):
    laboratorios = GrupoLaboratorio.objects.select_related(
        "grupo_teoria", "grupo_teoria__curso", "profesor"
    ).all()

    if request.method == "POST":
        # Actualizar cupos de un laboratorio
        if "actualizar_cupos" in request.POST:
            lab_id = request.POST.get("lab_id")
            nuevos_cupos = request.POST.get("cupos")

            if lab_id and nuevos_cupos:
                try:
                    lab = GrupoLaboratorio.objects.get(id=lab_id)
                    lab.cupos = int(nuevos_cupos)
                    lab.save()
                    messages.success(request, f"Cupos actualizados para {lab.grupo_teoria.curso.nombre} - Lab {lab.grupo}")
                    return redirect("listar_grupos_laboratorio")
                except GrupoLaboratorio.DoesNotExist:
                    messages.error(request, "Laboratorio no encontrado")
                except ValueError:
                    messages.error(request, "El número de cupos debe ser un entero")

        # Descargar Excel
        elif "descargar_excel" in request.POST:
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = "Laboratorios"

            headers = ["Curso", "Grupo Teoría", "Grupo Laboratorio", "Profesor", "Cupos"]
            for col_num, header in enumerate(headers, 1):
                ws[f"{get_column_letter(col_num)}1"] = header

            for row_num, lab in enumerate(laboratorios, 2):
                ws[f"A{row_num}"] = lab.grupo_teoria.curso.nombre
                ws[f"B{row_num}"] = lab.grupo_teoria.turno
                ws[f"C{row_num}"] = lab.grupo
                ws[f"D{row_num}"] = lab.profesor.nombre if lab.profesor else "Sin asignar"
                ws[f"E{row_num}"] = lab.cupos

            archivo_nombre = "Laboratorios_Disponibles.xlsx"
            response = HttpResponse(
                content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
            response["Content-Disposition"] = f'attachment; filename="{archivo_nombre}"'
            wb.save(response)
            return response

    return render(request, "siscad/secretaria/listar_grupos_laboratorio.html", {"laboratorios": laboratorios})


def listar_alumno_grupo_laboratorio(request):
    if request.method == "POST":
        curso_id = request.POST.get("grupo_id")
        turno = request.POST.get("laboratorio_turno")


# =======================Vista de Alumno====================================================
def inicio_alumno(request):
    return render(request, "siscad/alumno/menu.html")


def notas_alumno_view(request):
    rol = request.session.get("rol")
    email = request.session.get("email")
    if not email or rol != Alumno:
        return redirect("login")

    alumno = Alumno.objects.get(email=email)
    matriculas = MatriculaCurso.objects.filter(alumno=alumno)
    datos = []
    for matricula in matriculas:
        curso = matricula.curso
        notas = Nota.objects.filter(alumno=alumno, curso=curso).order_by(
            "tipo", "periodo"
        )
        datos.append(
            {
                "cursos": curso,
                "notas": notas,
            }
        )
    return render(
        "alumno",
        alumno,
        "datos",
        datos,
    )


# =======================Vista de Profesor====================================================
def inicio_profesor(request):
    return render(request, "siscad/profesor/menu.html")


# =======================Vista de Admin====================================================
def inicio_admin(request):
    return render(request, "siscad/admin/menu.html")
