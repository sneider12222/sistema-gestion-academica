"""Rutas raíz del proyecto."""

from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("", include("accounts.urls")),
    path("", include("academico.urls")),
    path("", include("calificaciones.urls")),
    path("", include("asistencia.urls")),
    path("", include("reportes.urls")),
    path("admin/", admin.site.urls),
]

handler403 = "config.errores.prohibido"
handler404 = "config.errores.no_encontrado"
handler400 = "config.errores.solicitud_invalida"
