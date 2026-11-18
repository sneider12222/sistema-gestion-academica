"""Modelos de calificaciones.

Porta las tablas ``actividades`` y ``calificaciones`` de ``sga/schema.sql``.
"""

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class Actividad(models.Model):
    """Actividad evaluativa con su peso dentro del periodo.

    El UNIQUE (asignación, periodo, nombre) no estaba en el SQL original: sin él
    se pueden crear dos «Taller 1» en el mismo periodo y la suma de porcentajes
    se vuelve ambigua.
    """

    asignacion = models.ForeignKey(
        "academico.Asignacion",
        on_delete=models.PROTECT,
        related_name="actividades",
        verbose_name="asignación",
    )
    periodo = models.ForeignKey(
        "academico.Periodo",
        on_delete=models.PROTECT,
        related_name="actividades",
        verbose_name="periodo",
    )
    nombre = models.CharField("nombre", max_length=120)
    porcentaje = models.DecimalField(
        "porcentaje",
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(0.01), MaxValueValidator(100)],
    )
    fecha = models.DateField("fecha")

    class Meta:
        verbose_name = "actividad"
        verbose_name_plural = "actividades"
        constraints = [
            models.UniqueConstraint(
                fields=["asignacion", "periodo", "nombre"],
                name="actividad_unica_por_periodo",
            )
        ]

    def __str__(self):
        return f"{self.nombre} ({self.porcentaje}% — {self.periodo})"


class Calificacion(models.Model):
    """Nota de un estudiante en una actividad, en escala 1.0–5.0."""

    actividad = models.ForeignKey(
        Actividad,
        on_delete=models.CASCADE,
        related_name="calificaciones",
        verbose_name="actividad",
    )
    estudiante = models.ForeignKey(
        "accounts.Estudiante",
        on_delete=models.PROTECT,
        related_name="calificaciones",
        verbose_name="estudiante",
    )
    nota = models.DecimalField(
        "nota",
        max_digits=3,
        decimal_places=1,
        validators=[MinValueValidator(1.0), MaxValueValidator(5.0)],
    )
    registrado_en = models.DateTimeField("registrado en", auto_now_add=True)

    class Meta:
        verbose_name = "calificación"
        verbose_name_plural = "calificaciones"
        constraints = [
            models.UniqueConstraint(
                fields=["actividad", "estudiante"],
                name="calificacion_unica_por_actividad",
            )
        ]

    def __str__(self):
        return f"{self.estudiante} — {self.actividad.nombre}: {self.nota}"
