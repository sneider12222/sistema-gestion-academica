"""Ejecutor de pruebas limitado a las apps Django del proyecto.

Sin etiquetas, el ejecutor por defecto de Django recorre todo el repositorio e
importa también el paquete ``sga`` (la versión Flask conservada como
referencia). Eso mezcla las dos suites y, sin Flask instalado, rompe la
ejecución. Con este ejecutor ``manage.py test`` solo descubre pruebas dentro de
las apps Django; la suite Flask se sigue ejecutando con
``python -m unittest discover tests``.
"""

from django.test.runner import DiscoverRunner

APPS_DEL_PROYECTO = ["accounts", "academico", "calificaciones", "asistencia", "reportes"]


class AppsDelProyectoRunner(DiscoverRunner):
    def build_suite(self, test_labels=None, *args, **kwargs):
        return super().build_suite(test_labels or APPS_DEL_PROYECTO, *args, **kwargs)
