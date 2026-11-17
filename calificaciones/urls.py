from django.urls import path

from . import views

app_name = "calificaciones"

urlpatterns = [
    path("asignacion/<int:aid>/calificaciones/", views.calificaciones, name="calificaciones"),
]
