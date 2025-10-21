from django.shortcuts import render, redirect
from django.contrib import messages
from django.db import transaction
from .forms import UploadExcelForm
from . import utils
from .models import (
    Profesor,
    Alumno,
    Secretaria,
    Administrador,
    Nota,
    Curso,
    MatriculaCurso,
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
            return redirect("inicio")
        else:
            messages.error(request, "Email o DNI incorrectos")

    return render(request, "siscad/login.html")


def logout_view(request):
    request.session.flush()
    return redirect("login")


# =======================Vista de Secretaria ===============================================
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
        "siscad/insertar_alumnos_excel.html",
        {"form": form, "alumnos": alumnos},
    )


def listar_alumno_grupo_teoria(request):
    alumnos = []
    cursos = (
        Curso.objects.all()
    )  

    if request.method == "POST":
        curso_id = request.POST.get("curso_nombre")
        turno = request.POST.get("curso_turno")

        curso = utils.ObtenerCursoId(curso_id)  
        matriculas = MatriculaCurso.objects.filter(curso=curso, turno=turno)

        for matricula in matriculas:
            alumnos.append(matricula.alumno)

    return render(
        request,
        "siscad/listar_alumnos_grupo_teoria.html",
        {"alumnos": alumnos, "cursos": cursos},
    )


def listar_grupos_laboratorio(request):
    pass


def listar_alumno_grupo_laboratorio(request):
    if request.method == "POST":
        curso_id = request.POST.get("grupo_id")
        turno = request.POST.get("laboratorio_turno")


# =======================Vista de Alumno====================================================


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
