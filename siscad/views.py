from django.shortcuts import render, redirect
from django.contrib import messages
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


def inicio(request):
    nombre = request.session.get("nombre")
    rol = request.session.get("rol")

    if not nombre:
        return redirect("login")

    return render(request, "usuarios/inicio.html", {"nombre": nombre, "rol": rol})


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

    return render(request, "usuarios/login.html")


def logout_view(request):
    request.session.flush()
    return redirect("login")


# =======================Vista de Secretaria ===============================================


def listar_alumno_grupo_teoria(request):
    if request.method == "POST":
        curso_id = request.POST.get("curso_nombre")
        turno = request.POST.get("curso_turno")
    curso = utils.ObtenerCursoId(curso_id)
    matriculas = MatriculaCurso.objects.filter(curso=curso, turno = turno)
    datos = []
    for matricula in matriculas:
        alumno = matricula.alumno
        datos.append({"alumnos": alumno})
    return render(
        "datos",
        datos,
    )

def listar_alumno_grupo_laboratorio(request):
    if request.method == "POST":
        curso_id = request.POST.get("grupo_id")


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
