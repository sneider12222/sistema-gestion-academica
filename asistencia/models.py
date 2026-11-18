"""Modelos de asistencia.

Porta la tabla ``asistencias`` de ``sga/schema.sql``. La PK compuesta original
(asignación, estudiante, fecha) se expresa como UNIQUE sobre los tres campos.
"""

from django.db import models


class Asistencia(models.Model):
    """Registro diario de presencia de un estudiante en una asignación."""

    class Estado(models.TextChoices):
        PRESENTE = "P", "Presente"
        AUSENTE = "A", "Ausente"

    asignacion = models.ForeignKey(
        "academico.Asignacion",
        on_delete=models.PROTECT,
        related_name="asistencias",
        verbose_name="asignación",
    )
    estudiante = models.ForeignKey(
        "accounts.Estudiante",
        on_delete=models.PROTECT,
        related_name="asistencias",
        verbose_name="estudiante",
    )
    fecha = models.DateField("fecha")
    estado = models.CharField("estado", max_length=1, choices=Estado.choices)

    class Meta:
        verbose_name = "asistencia"
        verbose_name_plural = "asistencias"
        constraints = [
            # Un estudiante no puede tener dos registros el mismo día para la
            # misma asignación.
            models.UniqueConstraint(
                fields=["asignacion", "estudiante", "fecha"],
                name="asistencia_unica_por_dia",
            )
        ]
        indexes = [
            models.Index(
                fields=["estudiante", "fecha"],
                name="asistencia_est_fecha_idx",
            )
        ]

    def __str__(self):
        return f"{self.estudiante} — {self.fecha}: {self.get_estado_display()}"
