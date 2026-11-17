"""Consulta y envío de informes académicos, reportes por grado y anotaciones docentes.

Estudiantes y acudientes solo tienen acceso de lectura a su propia información:
toda consulta pasa por ``accounts.permissions``.
"""

from datetime import date

from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from academico.models import Asignacion, Periodo
from academico.utils import fecha_o_none
from accounts.decorators import rol_requerido
from accounts.models import Estudiante, Rol, Usuario
from accounts.permissions import estudiantes_visibles, grados_visibles, puede_ver

from .models import Anotacion, InformeEnviado
from .services import construir_informe, historial, periodo_seleccionado


def _estudiante_visible(usuario, estudiante_id):
    estudiante = get_object_or_404(Estudiante.objects.select_related("usuario", "grado"), pk=estudiante_id)
    if not puede_ver(usuario, estudiante):
        raise PermissionDenied
    return estudiante


def _acudientes_de(estudiante):
    return Usuario.objects.filter(
        acudidos__estudiante=estudiante, is_active=True
    ).order_by("nombre")


@rol_requerido(Rol.ADMINISTRADOR, Rol.DOCENTE, Rol.ACUDIENTE)
def estudiantes(request):
    return render(request, "estudiantes.html", {
        "estudiantes": estudiantes_visibles(request.user).select_related("usuario", "grado"),
    })


def informe(request, estudiante_id):
    if not request.user.is_authenticated:
        return redirect(f"{reverse('accounts:login')}?next={request.path}")
    estudiante = _estudiante_visible(request.user, estudiante_id)
    periodo = periodo_seleccionado(request.GET.get("periodo"))
    if periodo is None:
        return render(request, "error.html", {
            "codigo": "", "mensaje": "No hay información académica para mostrar todavía."
        })

    # Al abrirlo desde la bandeja, el destinatario lo marca como leído
    envio = request.GET.get("envio", "")
    if envio.isdigit():
        InformeEnviado.objects.filter(
            pk=envio, destinatario=request.user, leido_en__isnull=True
        ).update(leido_en=timezone.now())

    periodos = list(Periodo.objects.order_by("fecha_inicio"))
    return render(request, "informe.html", {
        "inf": construir_informe(estudiante, periodo),
        "historial": historial(estudiante, periodos),
        "periodos": periodos,
        "acudientes": _acudientes_de(estudiante),
        "puede_enviar": request.user.rol in (Rol.ADMINISTRADOR, Rol.DOCENTE),
    })


@require_POST
@rol_requerido(Rol.ADMINISTRADOR, Rol.DOCENTE)
def enviar(request, estudiante_id):
    estudiante = _estudiante_visible(request.user, estudiante_id)
    periodo = periodo_seleccionado(request.POST.get("periodo"))
    if periodo is None:
        messages.error(request, "Aún no hay periodos académicos creados.")
        return redirect("reportes:informe", estudiante_id=estudiante.pk)
    acudientes = list(_acudientes_de(estudiante))
    if not acudientes:
        messages.error(
            request,
            "El estudiante no tiene acudientes vinculados. Pida al administrador que los registre.",
        )
    else:
        mensaje = request.POST.get("mensaje", "").strip()
        InformeEnviado.objects.bulk_create(
            InformeEnviado(
                estudiante=estudiante, periodo=periodo, remitente=request.user,
                destinatario=ac, mensaje=mensaje,
            )
            for ac in acudientes
        )
        messages.success(request, f"Informe enviado a: {', '.join(ac.nombre for ac in acudientes)}.")
    return redirect(f"{reverse('reportes:informe', args=[estudiante.pk])}?periodo={periodo.pk}")


@rol_requerido(Rol.ADMINISTRADOR, Rol.DOCENTE, Rol.ACUDIENTE)
def bandeja(request):
    lista = InformeEnviado.objects.select_related(
        "estudiante__usuario", "periodo", "remitente", "destinatario"
    ).order_by("-enviado_en", "-id")
    rol = request.user.rol
    if rol == Rol.DOCENTE:
        lista = lista.filter(remitente=request.user)
    elif rol == Rol.ACUDIENTE:
        lista = lista.filter(destinatario=request.user)
    return render(request, "bandeja.html", {"informes": lista[:300], "recibidos": rol == Rol.ACUDIENTE})


@rol_requerido(Rol.ADMINISTRADOR, Rol.DOCENTE)
def reportes(request):
    grados = list(grados_visibles(request.user))
    periodo = periodo_seleccionado(request.GET.get("periodo"))
    pedido = request.GET.get("grado", "")
    grado = grados[0] if grados else None
    if pedido.isdigit():
        grado = next((x for x in grados if x.pk == int(pedido)), None)
        if grado is None:
            raise PermissionDenied

    filas, asignaturas = [], []
    if grado and periodo:
        asignaturas = list(
            Asignacion.objects.filter(grado=grado)
            .order_by("asignatura__nombre")
            .values_list("asignatura__nombre", flat=True)
        )
        alumnos = Estudiante.objects.filter(grado=grado, usuario__is_active=True).select_related(
            "usuario", "grado"
        ).order_by("usuario__nombre")
        filas = [construir_informe(e, periodo) for e in alumnos]

    con_nota = [f["promedio"] for f in filas if f["promedio"] is not None]
    return render(request, "reporte_grado.html", {
        "grados": grados,
        "grado": grado,
        "periodo": periodo,
        "periodos": Periodo.objects.order_by("fecha_inicio"),
        "asignaturas": asignaturas,
        "filas": filas,
        "promedio_grado": round(sum(con_nota) / len(con_nota) + 1e-9, 1) if con_nota else None,
        "ausencias_grado": sum(f["ausentes"] for f in filas),
    })


@rol_requerido(Rol.DOCENTE, Rol.ADMINISTRADOR)
def anotaciones(request):
    hoy = date.today()
    if request.method == "POST":
        f = request.POST
        if f.get("accion") == "eliminar":
            propias = Anotacion.objects.filter(pk=f.get("id") or 0)
            if request.user.rol != Rol.ADMINISTRADOR:
                propias = propias.filter(autor=request.user)
            propias.delete()
            messages.success(request, "Anotación eliminada.")
        else:
            texto = f.get("descripcion", "").strip()
            fecha = fecha_o_none(f.get("fecha")) or hoy
            est_id = f.get("estudiante_id", "")
            if not est_id.isdigit() or not puede_ver(request.user, int(est_id)):
                messages.error(request, "Seleccione un estudiante de sus grados.")
            elif not texto:
                messages.error(request, "Escriba la anotación.")
            elif fecha > hoy:
                messages.error(request, "La fecha no puede ser futura.")
            else:
                Anotacion.objects.create(
                    estudiante_id=int(est_id), autor=request.user, descripcion=texto, fecha=fecha
                )
                messages.success(request, "Anotación registrada.")
        return redirect("reportes:anotaciones")

    lista = Anotacion.objects.select_related("estudiante__usuario", "estudiante__grado", "autor").order_by(
        "-fecha", "-id"
    )
    if request.user.rol != Rol.ADMINISTRADOR:
        lista = lista.filter(autor=request.user)
    return render(request, "anotaciones.html", {
        "anotaciones": lista[:200],
        "hoy": hoy.isoformat(),
        "estudiantes": estudiantes_visibles(request.user).select_related("usuario", "grado"),
    })
