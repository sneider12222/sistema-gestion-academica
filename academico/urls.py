from django.urls import path

from . import views

app_name = "academico"

urlpatterns = [
    path("administracion/academico/", views.academico, name="academico"),
    path("administracion/respaldos/", views.respaldos, name="respaldos"),
]
