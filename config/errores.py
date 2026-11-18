"""Páginas de error con la identidad del sistema."""

from django.shortcuts import render


def _error(request, codigo, mensaje):
    return render(request, "error.html", {"codigo": codigo, "mensaje": mensaje}, status=codigo)


def solicitud_invalida(request, exception=None):
    return _error(request, 400, "La solicitud no es válida.")


def prohibido(request, exception=None):
    return _error(request, 403, "No tiene permiso para acceder a esta sección.")


def no_encontrado(request, exception=None):
    return _error(request, 404, "La página solicitada no existe.")


def error_servidor(request):
    return _error(request, 500, "Ocurrió un error inesperado. Intente de nuevo; si persiste, avise al administrador.")


def csrf_fallido(request, reason=""):
    return _error(request, 403, "Token de seguridad inválido. Recargue la página e intente de nuevo.")
