from django.shortcuts import render, redirect
from django.contrib import messages
from .models import Profesor, Alumno, Secretaria, Administrador

def inicio(request):
    nombre = request.session.get("nombre")
    rol = request.session.get("rol")

    if not nombre:
        return redirect("login")

    return render(request, "usuarios/inicio.html", {
        "nombre": nombre,
        "rol": rol
    })


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
