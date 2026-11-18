"""Utilidades compartidas por las vistas de registro docente."""

from datetime import date

from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404

from accounts.models import Estudiante
from accounts.permissions import asignaciones_visibles

from .models import Asignacion


def asignacion_permitida(usuario, aid):
    """La asignación pedida, solo si el usuario puede gestionarla (404 si no existe, 403 si es ajena)."""
    asignacion = get_object_or_404(
        Asignacion.objects.select_related("asignatura", "grado", "docente"), pk=aid
    )
    if not asignaciones_visibles(usuario).filter(pk=asignacion.pk).exists():
        raise PermissionDenied
    return asignacion


def estudiantes_del_grado(grado_id):
    return (
        Estudiante.objects.filter(grado_id=grado_id, usuario__is_active=True)
        .select_related("usuario")
        .order_by("usuario__nombre")
    )


def fecha_o_none(texto):
    try:
        return date.fromisoformat(texto or "")
    except ValueError:
        return None
