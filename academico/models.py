"""Modelos de estructura académica.

Porta las tablas ``grados``, ``asignaturas``, ``periodos`` y ``asignaciones`` de
``sga/schema.sql``. ``asignaciones`` mantiene el UNIQUE (asignatura, grado):
es lo que convierte la relación multivaluada docente–asignatura–grado en una
dependencia funcional (NF4).
"""

from django.core.exceptions import ValidationError
from django.db import models


class Grado(models.Model):
    """Curso o nivel escolar (p. ej. «Sexto»)."""

    nombre = models.CharField("nombre", max_length=100, unique=True)

    class Meta:
        verbose_name = "grado"
        verbose_name_plural = "grados"

    def __str__(self):
        return self.nombre


class Asignatura(models.Model):
    """Materia dictada dentro de un grado."""

    nombre = models.CharField("nombre", max_length=100, unique=True)

    class Meta:
        verbose_name = "asignatura"
        verbose_name_plural = "asignaturas"

    def __str__(self):
        return self.nombre


class Periodo(models.Model):
    """Periodo académico con rango de fechas."""

    nombre = models.CharField("nombre", max_length=100, unique=True)
    fecha_inicio = models.DateField("fecha de inicio")
    fecha_fin = models.DateField("fecha de fin")

    class Meta:
        verbose_name = "periodo"
        verbose_name_plural = "periodos"

    def __str__(self):
        return self.nombre

    def clean(self):
        """Un periodo no puede terminar antes de empezar."""
        super().clean()
        if self.fecha_inicio and self.fecha_fin and self.fecha_inicio > self.fecha_fin:
            raise ValidationError(
                {"fecha_fin": "La fecha de fin no puede ser anterior a la de inicio."}
            )


class Asignacion(models.Model):
    """Un docente dicta una asignatura en un grado.

    ``unique_together`` evita que la misma materia y grado tengan dos docentes;
    es la restricción que sostiene la NF4 del esquema.
    """

    docente = models.ForeignKey(
        "accounts.Usuario",
        on_delete=models.PROTECT,
        limit_choices_to={"rol": "docente"},
        related_name="asignaciones",
        verbose_name="docente",
    )
    asignatura = models.ForeignKey(
        Asignatura,
        on_delete=models.PROTECT,
        related_name="asignaciones",
        verbose_name="asignatura",
    )
    grado = models.ForeignKey(
        Grado,
        on_delete=models.PROTECT,
        related_name="asignaciones",
        verbose_name="grado",
    )

    class Meta:
        verbose_name = "asignación"
        verbose_name_plural = "asignaciones"
        constraints = [
            models.UniqueConstraint(
                fields=["asignatura", "grado"],
                name="asignatura_grado_unica",
            )
        ]

    def __str__(self):
        return f"{self.asignatura} — {self.grado} ({self.docente.nombre})"
