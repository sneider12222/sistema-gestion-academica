from django.urls import path

from . import views

app_name = "asistencia"

urlpatterns = [
    path("asignacion/<int:aid>/asistencia/", views.asistencia, name="asistencia"),
]
