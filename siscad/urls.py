from django.urls import path
from . import views

urlpatterns = [
    path("", views.inicio, name="inicio"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    # === MENÚS PRINCIPALES ===
    path("admin/menu/", views.inicio_admin, name="inicio_admin"),
    path("secretaria/menu/", views.inicio_secretaria, name="inicio_secretaria"),
    path("profesor/menu/", views.inicio_profesor, name="inicio_profesor"),
    path("alumno/menu/", views.inicio_alumno, name="inicio_alumno"),
    # === SECRETARÍA ===
    path(
        "secretaria/insertar-alumnos/",
        views.insertar_alumnos_excel,
        name="insertar_alumnos_excel",
    ),
    path(
        "secretaria/listar-alumnos-grupo-teoria/",
        views.listar_alumno_grupo_teoria,
        name="listar_alumnos_grupo_teoria",
    ),
    path(
        "secretaria/listar-grupos-laboratorio/",
        views.listar_grupos_laboratorio,
        name="listar_grupos_laboratorio",
    ),
    path(
        "secretaria/listar-alumno-grupo-laboratorio/",
        views.listar_alumno_grupo_laboratorio,
        name="listar_alumnos_grupo_laboratorio",
    ),
    path(
        "secretaria/visualizar-horarios-aulas/",
        views.visualizar_horarios_aulas,
        name="visualizar_horarios_aulas",
    ),
    # === ALUMNO ===
    path(
        "alumno/visualizar-notas/",
        views.visualizar_notas,
        name="visualizar_notas",
    ),
    path(
        "alumno/visualizar-horario-alumno/",
        views.visualizar_horario_alumno,
        name="visualizar_horario_alumno",
    ),
    path(
        "alumno/matricula-laboratorio/",
        views.matricula_laboratorio,
        name="matricula_laboratorio",
    ),
    path(
        "alumno/visualizar-asistencias-alumnos/",
        views.visualizar_asistencias_alumno,
        name="visualizar_asistencias_alumno",
    ),
    # === PROFESOR ===
    path(
        "profesor/visualizar-horario-profesor/",
        views.visualizar_horario_profesor,
        name="visualizar_horario_profesor",
    ),
    path(
        "profesor/visualizar-asitencias-profesor/",
        views.visualizar_asistencias_profesor,
        name="visualizar_asistencias_profesor",
    ),
    path("profesor/reservar-aula/", views.reservar_aula, name="reservar_aula"),
    path(
        "profesor/cancelar-reserva/<int:reserva_id>/",
        views.cancelar_reserva,
        name="cancelar_reserva",
    ),
    path(
        "profesor/ver-cancelar-reservas/",
        views.ver_cancelar_reservas,
        name="ver_cancelar_reservas",
    ),
]
