from datetime import date, datetime, timedelta
from django.utils import timezone
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse
from django.contrib import messages
from django.db import transaction
from django.db.models import Q, Count
from ...forms import UploadExcelForm
from django.db.models import Avg, Max, Min, Count, Q
import io
import statistics


import openpyxl
from openpyxl.utils import get_column_letter
from ...models import (
    Profesor,
    Alumno,
    Secretaria,
    Administrador,
    Nota,
    Curso,
    MatriculaCurso,
    GrupoTeoria,
    GrupoLaboratorio,
    MatriculaLaboratorio,
    Hora,
    AsistenciaAlumno,
    GrupoPractica,
    AsistenciaProfesor,
    Reserva,
    Aula,
    Examen,
    Silabo,
    Tema,
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

            registrar_asistencia_profesor(usuario)

            marcar_temas_como_hechos(usuario)

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
            request.session["email"] = email
            messages.success(request, f"Bienvenido {rol} {usuario.nombre}")

            return redirect(f"inicio_{rol.lower()}")

        else:
            messages.error(request, "Email o DNI incorrectos")

    return render(request, "siscad/login.html")


def registrar_asistencia_profesor(profesor):
    ahora = timezone.now()
    fecha_actual = ahora.date()
    hora_actual = ahora.time()
    dia_actual = obtener_dia_actual()

    # CORREGIDO: Buscar en Hora donde el profesor está asignado
    horas_activas = Hora.objects.filter(
        Q(grupo_teoria__profesor=profesor)
        | Q(grupo_practica__profesor=profesor)
        | Q(grupo_laboratorio__profesor=profesor),
        dia=dia_actual,
        hora_inicio__lte=hora_actual,
        hora_fin__gte=hora_actual,
    )

    for hora in horas_activas:
        if not AsistenciaProfesor.objects.filter(
            profesor=profesor, fecha=fecha_actual, hora=hora
        ).exists():
            AsistenciaProfesor.objects.create(
                profesor=profesor, fecha=fecha_actual, estado="P", hora=hora
            )


def marcar_temas_como_hechos(profesor):
    ahora = timezone.now()
    fecha_actual = ahora.date()
    hora_actual = ahora.time()
    dia_actual = obtener_dia_actual()

    horas_teoria_activas = Hora.objects.filter(
        grupo_teoria__profesor=profesor,
        dia=dia_actual,
        hora_inicio__lte=hora_actual,
        hora_fin__gte=hora_actual,
        tipo="T",  # Teoría
    )

    for hora in horas_teoria_activas:
        temas_hoy = Tema.objects.filter(
            Q(grupo_teoria=hora.grupo_teoria)
            | Q(silabo__grupo_teoria=hora.grupo_teoria),
            fecha=fecha_actual,
            estado="N",  # No hecho
        )

        temas_hoy.update(estado="H")  # Hecho


def obtener_dia_actual():
    dias = {
        0: "L",  # Lunes
        1: "M",  # Martes
        2: "X",  # Miércoles
        3: "J",  # Jueves
        4: "V",  # Viernes
    }
    return dias.get(timezone.now().weekday(), "L")


def logout_view(request):
    request.session.flush()
    return redirect("login")


def inicio_admin(request):
    rol = request.session.get("rol")

    if rol != "Administrador":
        request.session["rol"] = "Ninguno"
        return redirect("login")

    nombre = request.session.get("nombre")
    return render(
        request, "siscad/admin/menu.html", {"nombre": nombre, "rol": rol}
    )


def inicio_secretaria(request):
    rol = request.session.get("rol")

    if rol != "Secretaria":
        request.session["rol"] = "Ninguno"
        return redirect("login")

    nombre = request.session.get("nombre")
    return render(
        request, "siscad/secretaria/menu.html", {"nombre": nombre, "rol": rol}
    )


def inicio_alumno(request):
    rol = request.session.get("rol")

    if rol != "Alumno":
        request.session["rol"] = "Ninguno"
        return redirect("login")

    nombre = request.session.get("nombre")
    return render(request, "siscad/alumno/menu.html", {"nombre": nombre, "rol": rol})


def inicio_profesor(request):
    rol = request.session.get("rol")

    if rol != "Profesor":
        request.session["rol"] = "Ninguno"
        return redirect("login")

    nombre = request.session.get("nombre")
    return render(request, "siscad/profesor/menu.html", {"nombre": nombre, "rol": rol})
