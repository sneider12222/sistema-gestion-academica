"""Modelos de reportes.

Porta las tablas ``anotaciones`` e ``informes_enviados`` de ``sga/schema.sql``.
"""

from datetime import date

from django.db import models


class Anotacion(models.Model):
    """Observación de un docente (u otro autor) sobre un estudiante."""

    estudiante = models.ForeignKey(
        "accounts.Estudiante",
        on_delete=models.PROTECT,
        related_name="anotaciones",
        verbose_name="estudiante",
    )
    autor = models.ForeignKey(
        "accounts.Usuario",
        on_delete=models.PROTECT,
        related_name="anotaciones_escritas",
        verbose_name="autor",
    )
    descripcion = models.TextField("descripción")
    fecha = models.DateField("fecha", default=date.today)

    class Meta:
        verbose_name = "anotación"
        verbose_name_plural = "anotaciones"
        indexes = [
            models.Index(
                fields=["estudiante", "fecha"],
                name="anotacion_est_fecha_idx",
            )
        ]

    def __str__(self):
        return f"{self.estudiante} — {self.fecha}: {self.descripcion[:40]}"


class InformeEnviado(models.Model):
    """Informe académico enviado de un remitente a un destinatario."""

    estudiante = models.ForeignKey(
        "accounts.Estudiante",
        on_delete=models.PROTECT,
        related_name="informes",
        verbose_name="estudiante",
    )
    periodo = models.ForeignKey(
        "academico.Periodo",
        on_delete=models.PROTECT,
        related_name="informes",
        verbose_name="periodo",
    )
    remitente = models.ForeignKey(
        "accounts.Usuario",
        on_delete=models.PROTECT,
        related_name="informes_enviados",
        verbose_name="remitente",
    )
    destinatario = models.ForeignKey(
        "accounts.Usuario",
        on_delete=models.PROTECT,
        related_name="informes_recibidos",
        verbose_name="destinatario",
    )
    mensaje = models.TextField("mensaje", blank=True)
    enviado_en = models.DateTimeField("enviado en", auto_now_add=True)
    leido_en = models.DateTimeField("leído en", null=True, blank=True)

    class Meta:
        verbose_name = "informe enviado"
        verbose_name_plural = "informes enviados"
        indexes = [
            models.Index(
                fields=["destinatario"],
                name="informe_destinatario_idx",
            )
        ]

    def __str__(self):
        return (
            f"Informe de {self.estudiante} ({self.periodo}) "
            f"para {self.destinatario.nombre}"
        )
