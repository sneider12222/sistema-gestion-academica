"""Registro de calificaciones por asignación y periodo."""

from datetime import date
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.db import IntegrityError, transaction
from django.shortcuts import redirect, render
from django.urls import reverse

from academico.models import Periodo
from academico.utils import asignacion_permitida, estudiantes_del_grado, fecha_o_none
from accounts.decorators import rol_requerido
from accounts.models import Rol
from reportes.services import periodo_seleccionado

from .models import Actividad, Calificacion
from .services import definitiva

NOTA_MIN, NOTA_MAX = Decimal("1.0"), Decimal("5.0")


def _leer_nota(texto):
    """Devuelve la nota redondeada a una décima, o ``None`` si no es válida."""
    try:
        nota = Decimal(texto.replace(",", "."))
        if not nota.is_finite():  # "NaN" o "Infinity" son Decimal válidos pero no notas
            return None
        nota = nota.quantize(Decimal("0.1"))
    except InvalidOperation:
        return None
    return nota if NOTA_MIN <= nota <= NOTA_MAX else None


@rol_requerido(Rol.DOCENTE, Rol.ADMINISTRADOR)
def calificaciones(request, aid):
    a = asignacion_permitida(request.user, aid)
    periodo = periodo_seleccionado(request.POST.get("periodo") or request.GET.get("periodo"))
    if periodo is None:
        messages.error(request, "Aún no hay periodos académicos creados.")
        return redirect("accounts:inicio")
    estudiantes = list(estudiantes_del_grado(a.grado_id))
    aqui = f"{reverse('calificaciones:calificaciones', args=[a.pk])}?periodo={periodo.pk}"
    actividades = Actividad.objects.filter(asignacion=a, periodo=periodo).order_by("fecha", "id")

    if request.method == "POST":
        f = request.POST
        accion = f.get("accion")
        if accion == "crear_actividad":
            nombre, fecha = f.get("nombre", "").strip(), fecha_o_none(f.get("fecha"))
            try:
                pct = Decimal(f.get("porcentaje", ""))
                if not pct.is_finite():
                    pct = None
            except InvalidOperation:
                pct = None
            if not nombre or not fecha or pct is None or not 0 < pct <= 100:
                messages.error(request, "Complete nombre, fecha y un porcentaje entre 1 y 100.")
            else:
                try:
                    with transaction.atomic():
                        Actividad.objects.create(
                            asignacion=a, periodo=periodo, nombre=nombre, porcentaje=pct, fecha=fecha
                        )
                    messages.success(request, "Actividad creada.")
                except IntegrityError:
                    # ADR 0003: no se repite el nombre de actividad en el periodo
                    messages.error(request, "Ya existe una actividad con ese nombre en este periodo.")
        elif accion == "eliminar_actividad":
            actividades.filter(pk=f.get("actividad_id") or 0).delete()
            messages.success(request, "Actividad eliminada junto con sus notas.")
        elif accion == "guardar_notas":
            guardadas = invalidas = 0
            with transaction.atomic():
                for act in actividades:
                    for e in estudiantes:
                        texto = f.get(f"nota_{act.pk}_{e.pk}", "").strip()
                        if not texto:
                            Calificacion.objects.filter(actividad=act, estudiante=e).delete()
                            continue
                        nota = _leer_nota(texto)
                        if nota is None:
                            invalidas += 1
                            continue
                        existente = Calificacion.objects.filter(actividad=act, estudiante=e).first()
                        if existente is None:
                            Calificacion.objects.create(actividad=act, estudiante=e, nota=nota)
                        elif existente.nota != nota:
                            existente.nota = nota
                            existente.save(update_fields=["nota"])
                        guardadas += 1
            messages.success(request, f"Notas guardadas ({guardadas}).")
            if invalidas:
                messages.error(
                    request,
                    f"{invalidas} valor(es) no se guardaron: la nota debe estar entre "
                    f"{NOTA_MIN} y {NOTA_MAX}.",
                )
        return redirect(aqui)

    actividades = list(actividades)
    notas = {
        (c.actividad_id, c.estudiante_id): c.nota
        for c in Calificacion.objects.filter(actividad__in=actividades)
    }
    filas = []
    for e in estudiantes:
        celdas = [{"actividad": x, "nota": notas.get((x.pk, e.pk))} for x in actividades]
        filas.append({
            "estudiante": e,
            "celdas": celdas,
            "definitiva": definitiva((c["nota"], c["actividad"].porcentaje) for c in celdas),
        })
    suma = sum((x.porcentaje for x in actividades), Decimal(0))
    return render(request, "calificaciones.html", {
        "a": a,
        "periodo": periodo,
        "periodos": Periodo.objects.order_by("fecha_inicio"),
        "actividades": actividades,
        "filas": filas,
        "suma_pct": suma,
        "aviso_pct": bool(actividades) and suma != 100,
        "hoy": date.today().isoformat(),
    })
