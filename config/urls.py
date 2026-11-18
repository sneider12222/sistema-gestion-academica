"""Rutas raíz del proyecto."""

from django.conf import settings
from django.contrib import admin
from django.contrib.staticfiles.views import serve as servir_estatico
from django.urls import include, path, re_path

urlpatterns = [
    path("", include("accounts.urls")),
    path("", include("academico.urls")),
    path("", include("calificaciones.urls")),
    path("", include("asistencia.urls")),
    path("", include("reportes.urls")),
    path("admin/", admin.site.urls),
]

if not settings.DEBUG:
    # El sistema corre en localhost sin servidor web aparte (modelo técnico),
    # así que runserver también sirve estilos y scripts con DEBUG=False.
    urlpatterns.append(
        re_path(r"^static/(?P<path>.*)$", servir_estatico, {"insecure": True})
    )

handler403 = "config.errores.prohibido"
handler404 = "config.errores.no_encontrado"
handler400 = "config.errores.solicitud_invalida"
handler500 = "config.errores.error_servidor"
