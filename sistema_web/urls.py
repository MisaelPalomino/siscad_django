from django.contrib import admin
from django.urls import path, include
from django.shortcuts import redirect

def home(request):
    return redirect('/siscad/')


urlpatterns = [
    path('', home),
    path("admin/", admin.site.urls),
    path("siscad/", include("siscad.urls")),  # Enlaza tu aplicación aquí
]
