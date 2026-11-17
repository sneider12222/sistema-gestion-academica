"""Construcción de informes académicos con el ORM (sin SQL propio del motor, ADR 0002).

Porta ``construir_informe``, ``historial`` y ``periodo_seleccionado`` de
``sga/servicios.py``.
"""

from datetime import date

from django.db.models import Count, Q

from academico.models import Asignacion, Periodo
from asistencia.models import Asistencia
from calificaciones.models import Actividad, Calificacion
from calificaciones.services import definitiva

from .models import Anotacion

# Indicador del modelo técnico: usuarios con acceso al sistema de gestión académica
META_USUARIOS = 280


def periodo_seleccionado(periodo_id=None):
    """El periodo pedido; si no, el que contiene hoy; si no, el último iniciado."""
    try:
        periodo_id = int(periodo_id)
    except (TypeError, ValueError):
        periodo_id = None
    if periodo_id:
        periodo = Periodo.objects.filter(pk=periodo_id).first()
        if periodo:
            return periodo
    hoy = date.today()
    return (
        Periodo.objects.filter(fecha_inicio__lte=hoy, fecha_fin__gte=hoy).first()
        or Periodo.objects.filter(fecha_inicio__lte=hoy).order_by("-fecha_inicio").first()
        or Periodo.objects.order_by("fecha_inicio").first()
    )


def _notas_de(estudiante, actividades):
    return dict(
        Calificacion.objects.filter(estudiante=estudiante, actividad__in=actividades)
        .values_list("actividad_id", "nota")
    )


def historial(estudiante, periodos):
    """Definitiva de cada asignatura del grado del estudiante en cada periodo."""
    asignaciones = (
        Asignacion.objects.filter(grado_id=estudiante.grado_id)
        .select_related("asignatura")
        .order_by("asignatura__nombre")
    )
    actividades = list(Actividad.objects.filter(asignacion__in=asignaciones))
    notas = _notas_de(estudiante, actividades)
    filas = []
    for asignacion in asignaciones:
        celdas = []
        for periodo in periodos:
            pares = [
                (notas.get(a.id), a.porcentaje)
                for a in actividades
                if a.asignacion_id == asignacion.id and a.periodo_id == periodo.id
            ]
            celdas.append({"periodo": periodo, "nota": definitiva(pares)})
        filas.append({"asignatura": asignacion.asignatura.nombre, "celdas": celdas})
    return filas


def construir_informe(estudiante, periodo):
    """Notas, asistencia y anotaciones de un estudiante en un periodo."""
    rango = (periodo.fecha_inicio, periodo.fecha_fin)
    asignaciones = list(
        Asignacion.objects.filter(grado_id=estudiante.grado_id)
        .select_related("asignatura", "docente")
        .order_by("asignatura__nombre")
    )
    actividades = list(
        Actividad.objects.filter(asignacion__in=asignaciones, periodo=periodo).order_by("fecha", "id")
    )
    notas = _notas_de(estudiante, actividades)
    conteo = {
        fila["asignacion_id"]: fila
        for fila in Asistencia.objects.filter(estudiante=estudiante, fecha__range=rango)
        .values("asignacion_id")
        .annotate(
            presentes=Count("pk", filter=Q(estado=Asistencia.Estado.PRESENTE)),
            ausentes=Count("pk", filter=Q(estado=Asistencia.Estado.AUSENTE)),
        )
    }

    materias = []
    for asignacion in asignaciones:
        propias = [
            {"nombre": a.nombre, "porcentaje": a.porcentaje, "fecha": a.fecha, "nota": notas.get(a.id)}
            for a in actividades
            if a.asignacion_id == asignacion.id
        ]
        asis = conteo.get(asignacion.id, {})
        materias.append({
            "asignatura": asignacion.asignatura.nombre,
            "docente": asignacion.docente.nombre,
            "actividades": propias,
            "definitiva": definitiva((x["nota"], x["porcentaje"]) for x in propias),
            "presentes": asis.get("presentes", 0),
            "ausentes": asis.get("ausentes", 0),
        })

    con_nota = [m["definitiva"] for m in materias if m["definitiva"] is not None]
    presentes = sum(m["presentes"] for m in materias)
    ausentes = sum(m["ausentes"] for m in materias)
    clases = presentes + ausentes

    return {
        "estudiante": estudiante,
        "periodo": periodo,
        "materias": materias,
        "promedio": round(sum(con_nota) / len(con_nota) + 1e-9, 1) if con_nota else None,
        "presentes": presentes,
        "ausentes": ausentes,
        "clases": clases,
        "pct_asistencia": round(100 * presentes / clases) if clases else None,
        "lista_ausencias": Asistencia.objects.filter(
            estudiante=estudiante, estado=Asistencia.Estado.AUSENTE, fecha__range=rango
        )
        .select_related("asignacion__asignatura")
        .order_by("-fecha", "asignacion__asignatura__nombre"),
        "anotaciones": Anotacion.objects.filter(estudiante=estudiante, fecha__range=rango)
        .select_related("autor")
        .order_by("-fecha", "-id"),
    }
