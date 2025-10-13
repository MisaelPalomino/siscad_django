from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path("admin/", admin.site.urls),
    path("siscad/", include("siscad.urls")),  # Enlaza tu aplicación aquí
]
