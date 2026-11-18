from django.urls import path

from . import views

app_name = "reportes"

urlpatterns = [
    path("estudiantes/", views.estudiantes, name="estudiantes"),
    path("informe/<int:estudiante_id>/", views.informe, name="informe"),
    path("informe/<int:estudiante_id>/enviar/", views.enviar, name="enviar"),
    path("informes/", views.bandeja, name="bandeja"),
    path("reportes/", views.reportes, name="reportes"),
    path("anotaciones/", views.anotaciones, name="anotaciones"),
]
