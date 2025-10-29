from django.urls import path
from . import views

urlpatterns = [
    path("", views.inicio, name="inicio"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("admin/menu/", views.inicio_admin, name="inicio_admin"),
    path("secretaria/menu/", views.inicio_secretaria, name="inicio_secretaria"),
    path("profesor/menu/", views.inicio_profesor, name="inicio_profesor"),
    path("alumno/menu/", views.inicio_alumno, name="inicio_alumno"),
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
    path(
        "profesor/visualizar-horario-profesor/",
        views.visualizar_horario_profesor,
        name="visualizar_horario_profesor",
    ),
]
