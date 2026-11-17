from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    path("", views.inicio, name="inicio"),
    path("entrar/", views.entrar, name="login"),
    path("salir/", views.salir, name="logout"),
    path("perfil/", views.perfil, name="perfil"),
    path("administracion/usuarios/", views.usuarios, name="usuarios"),
    path("administracion/usuarios/nuevo/", views.usuario_form, name="usuario_nuevo"),
    path("administracion/usuarios/<int:uid>/", views.usuario_form, name="usuario_editar"),
]
