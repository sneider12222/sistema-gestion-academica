"""Rutas raíz del proyecto.

Solo se registra el admin: las vistas por rol se agregan en la fase de vistas.
"""

from django.contrib import admin
from django.urls import path

urlpatterns = [
    path("admin/", admin.site.urls),
]
