from django.urls import path
from . import views

urlpatterns = [
    path("", views.inicio, name="inicio"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path(
        "insertar-alumnos/", views.insertar_alumnos_excel, name="insertar_alumnos_excel"
    ),
]
