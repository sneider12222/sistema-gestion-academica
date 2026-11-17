"""Estructura académica (grados, asignaturas, periodos, asignaciones) y copias de seguridad."""

import sqlite3
from datetime import date, datetime

from django.conf import settings
from django.contrib import messages
from django.db import IntegrityError, connection, transaction
from django.db.models import Count, ProtectedError
from django.shortcuts import redirect, render

from accounts.decorators import rol_requerido
from accounts.models import Rol, Usuario

from .models import Asignacion, Asignatura, Grado, Periodo

MODELOS_BORRABLES = {
    "grados": Grado,
    "asignaturas": Asignatura,
    "periodos": Periodo,
    "asignaciones": Asignacion,
}


def _fecha(texto):
    try:
        return date.fromisoformat(texto or "")
    except ValueError:
        return None


@rol_requerido(Rol.ADMINISTRADOR)
def academico(request):
    if request.method == "POST":
        f = request.POST
        accion = f.get("accion")
        try:
            with transaction.atomic():
                if accion in ("grado", "asignatura"):
                    nombre = f.get("nombre", "").strip()
                    if not nombre:
                        messages.error(request, "Escriba un nombre.")
                    else:
                        (Grado if accion == "grado" else Asignatura).objects.create(nombre=nombre)
                        messages.success(request, "Registro creado.")
                elif accion == "periodo":
                    nombre = f.get("nombre", "").strip()
                    ini, fin = _fecha(f.get("fecha_inicio")), _fecha(f.get("fecha_fin"))
                    if not (nombre and ini and fin) or ini > fin:
                        messages.error(request, "Complete el nombre y un rango de fechas válido.")
                    else:
                        Periodo.objects.create(nombre=nombre, fecha_inicio=ini, fecha_fin=fin)
                        messages.success(request, "Periodo creado.")
                elif accion == "asignacion":
                    docente = Usuario.objects.filter(
                        pk=f.get("docente_id") or 0, rol=Rol.DOCENTE
                    ).first()
                    asignatura = Asignatura.objects.filter(pk=f.get("asignatura_id") or 0).first()
                    grado = Grado.objects.filter(pk=f.get("grado_id") or 0).first()
                    if not (docente and asignatura and grado):
                        messages.error(request, "Seleccione docente, asignatura y grado.")
                    else:
                        # Guardar una combinación existente cambia el docente
                        Asignacion.objects.update_or_create(
                            asignatura=asignatura, grado=grado, defaults={"docente": docente}
                        )
                        messages.success(request, "Asignación guardada.")
                elif accion == "eliminar" and f.get("tabla") in MODELOS_BORRABLES:
                    MODELOS_BORRABLES[f["tabla"]].objects.filter(pk=f.get("id") or 0).delete()
                    messages.success(request, "Registro eliminado.")
        except ProtectedError:
            messages.error(request, "No se puede eliminar: tiene registros académicos asociados.")
        except IntegrityError:
            messages.error(request, "Ya existe un registro con ese nombre.")
        return redirect("academico:academico")

    return render(request, "academico.html", {
        "grados": Grado.objects.annotate(n_estudiantes=Count("estudiantes")).order_by("nombre"),
        "asignaturas": Asignatura.objects.order_by("nombre"),
        "periodos": Periodo.objects.order_by("fecha_inicio"),
        "docentes": Usuario.objects.filter(rol=Rol.DOCENTE, is_active=True).order_by("nombre"),
        "asignaciones": Asignacion.objects.select_related("asignatura", "grado", "docente").order_by(
            "grado__nombre", "asignatura__nombre"
        ),
    })


# ------------------------------------------------------- copias de seguridad


def _es_sqlite():
    return settings.DATABASES["default"]["ENGINE"] == "django.db.backends.sqlite3"


def crear_respaldo():
    """Copia en caliente de la base SQLite a la carpeta de respaldos.

    Usa la conexión activa de Django (la misma base que está usando el sistema)
    y la API ``backup`` de SQLite, que copia de forma consistente aunque haya
    escrituras en curso.
    """
    carpeta = settings.RESPALDOS_DIR
    carpeta.mkdir(parents=True, exist_ok=True)
    destino = carpeta / f"sga_{datetime.now():%Y%m%d_%H%M%S_%f}.sqlite3"
    connection.ensure_connection()
    copia = sqlite3.connect(destino)
    try:
        connection.connection.backup(copia)
    finally:
        copia.close()
    return destino


@rol_requerido(Rol.ADMINISTRADOR)
def respaldos(request):
    if request.method == "POST":
        if not _es_sqlite():
            messages.error(request, "Las copias desde el sistema solo están disponibles con SQLite.")
        else:
            archivo = crear_respaldo()
            messages.success(request, f"Copia de seguridad creada: {archivo.name}")
        return redirect("academico:respaldos")
    carpeta = settings.RESPALDOS_DIR
    archivos = [
        {
            "nombre": p.name,
            "kb": round(p.stat().st_size / 1024),
            "fecha": datetime.fromtimestamp(p.stat().st_mtime),
        }
        for p in sorted(carpeta.glob("sga_*.sqlite3"), reverse=True)
    ] if carpeta.exists() else []
    return render(request, "respaldos.html", {
        "archivos": archivos, "carpeta": carpeta, "base": settings.DATABASES["default"]["NAME"],
        "es_sqlite": _es_sqlite(),
    })
