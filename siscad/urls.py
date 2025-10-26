from django.urls import path
from . import views

urlpatterns = [
    path("", views.inicio, name="inicio"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path('admin/menu/', views.inicio_admin, name='inicio_admin'),
    path('secretaria/menu/', views.inicio_secretaria, name='inicio_secretaria'),
    path('profesor/menu/', views.inicio_profesor, name='inicio_profesor'),
    path('alumno/menu/', views.inicio_alumno, name='inicio_alumno'),
    path(
        "secretaria/insertar-alumnos/", views.insertar_alumnos_excel, name="insertar_alumnos_excel"
    ),
    path(
        "secretaria/listar-alumnos-grupo-teoria/",
        views.listar_alumno_grupo_teoria,
        name="listar_alumnos_grupo_teoria",
    ),
]
