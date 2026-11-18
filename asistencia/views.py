"""Registro diario de asistencia por asignación."""

from datetime import date

from django.contrib import messages
from django.db import transaction
from django.db.models import Count, Q
from django.shortcuts import redirect, render
from django.urls import reverse

from academico.utils import asignacion_permitida, estudiantes_del_grado, fecha_o_none
from accounts.decorators import rol_requerido
from accounts.models import Rol

from .models import Asistencia


@rol_requerido(Rol.DOCENTE, Rol.ADMINISTRADOR)
def asistencia(request, aid):
    a = asignacion_permitida(request.user, aid)
    hoy = date.today()
    fecha = fecha_o_none(request.POST.get("fecha") or request.GET.get("fecha")) or hoy
    estudiantes = list(estudiantes_del_grado(a.grado_id))

    if request.method == "POST":
        if fecha > hoy:
            messages.error(request, "No se puede registrar asistencia en una fecha futura.")
        else:
            with transaction.atomic():
                for e in estudiantes:
                    estado = request.POST.get(f"estado_{e.pk}", Asistencia.Estado.PRESENTE)
                    if estado not in Asistencia.Estado.values:
                        estado = Asistencia.Estado.PRESENTE
                    Asistencia.objects.update_or_create(
                        asignacion=a, estudiante=e, fecha=fecha, defaults={"estado": estado}
                    )
            messages.success(request, f"Asistencia del {fecha.isoformat()} guardada.")
        return redirect(f"{reverse('asistencia:asistencia', args=[a.pk])}?fecha={fecha.isoformat()}")

    registro = dict(
        Asistencia.objects.filter(asignacion=a, fecha=fecha).values_list("estudiante_id", "estado")
    )
    filas = [
        {"estudiante": e, "estado": registro.get(e.pk, Asistencia.Estado.PRESENTE)} for e in estudiantes
    ]
    historial = (
        Asistencia.objects.filter(asignacion=a)
        .values("fecha")
        .annotate(
            presentes=Count("pk", filter=Q(estado=Asistencia.Estado.PRESENTE)),
            ausentes=Count("pk", filter=Q(estado=Asistencia.Estado.AUSENTE)),
        )
        .order_by("-fecha")[:15]
    )
    return render(request, "asistencia.html", {
        "a": a,
        "fecha": fecha.isoformat(),
        "hoy": hoy.isoformat(),
        "filas": filas,
        "registrado": bool(registro),
        "estados": Asistencia.Estado.choices,
        "historial": historial,
    })
