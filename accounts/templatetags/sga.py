"""Filtros de presentación compartidos por las plantillas."""

from django import template

register = template.Library()


@register.filter
def nota(valor):
    """Nota o promedio con un decimal; guion si todavía no hay nota."""
    if valor is None or valor == "":
        return "—"
    return f"{float(valor):.1f}"


@register.filter
def entero(valor):
    """Porcentaje sin decimales (20.00 → 20)."""
    if valor is None:
        return ""
    return f"{float(valor):.0f}"


@register.filter
def porcentaje(valor):
    """Porcentaje de asistencia; guion si no hay clases registradas."""
    return "—" if valor is None else f"{valor}%"


@register.filter
def obtener(diccionario, clave):
    """``diccionario[clave]`` en plantillas; ``None`` si no existe."""
    return diccionario.get(clave) if diccionario else None
