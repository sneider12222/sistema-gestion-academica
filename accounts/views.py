"""Autenticación, panel de inicio, cuenta propia y gestión de usuarios."""

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from academico.models import Grado
from reportes.models import InformeEnviado
from reportes.services import META_USUARIOS

from .decorators import rol_requerido
from .models import AcudienteEstudiante, Estudiante, Rol, Usuario
from .permissions import asignaciones_visibles, estudiantes_visibles

# ------------------------------------------------------------------ sesión


def entrar(request):
    if request.user.is_authenticated:
        return redirect("accounts:inicio")
    if request.method == "POST":
        usuario = authenticate(
            request,
            usuario=request.POST.get("usuario", "").strip().lower(),
            password=request.POST.get("clave", ""),
        )
        if usuario is not None:
            login(request, usuario)
            return redirect("accounts:inicio")
        messages.error(request, "Usuario o contraseña incorrectos.")
    return render(request, "login.html")


@require_POST
def salir(request):
    logout(request)
    return redirect("accounts:login")


# ------------------------------------------------------------------ inicio


@login_required
def inicio(request):
    u = request.user
    if u.es_estudiante:
        return redirect("reportes:informe", estudiante_id=u.pk)
    datos = {}
    if u.es_admin:
        por_rol = dict(
            Usuario.objects.filter(is_active=True).values_list("rol").annotate(n=Count("pk"))
        )
        total = sum(por_rol.values())
        datos.update(
            total=total,
            meta=META_USUARIOS,
            avance=min(100, round(100 * total / META_USUARIOS)),
            perfiles=[
                (Rol.DOCENTE, "Docentes", por_rol.get(Rol.DOCENTE, 0)),
                (Rol.ESTUDIANTE, "Estudiantes", por_rol.get(Rol.ESTUDIANTE, 0)),
                (Rol.ACUDIENTE, "Padres / acudientes", por_rol.get(Rol.ACUDIENTE, 0)),
                (Rol.ADMINISTRADOR, "Administradores", por_rol.get(Rol.ADMINISTRADOR, 0)),
            ],
            enviados=InformeEnviado.objects.count(),
        )
    elif u.es_docente:
        datos["asignaciones"] = asignaciones_visibles(u).select_related("asignatura", "grado").annotate(
            n_estudiantes=Count("grado__estudiantes", distinct=True)
        )
    elif u.es_acudiente:
        datos["acudidos"] = estudiantes_visibles(u).select_related("usuario", "grado")
        datos["sin_leer"] = InformeEnviado.objects.filter(destinatario=u, leido_en__isnull=True).count()
    return render(request, "inicio.html", datos)


@login_required
def perfil(request):
    if request.method == "POST":
        actual = request.POST.get("actual", "")
        nueva = request.POST.get("nueva", "")
        if not request.user.check_password(actual):
            messages.error(request, "La contraseña actual no es correcta.")
        elif nueva != request.POST.get("confirmar", ""):
            messages.error(request, "La confirmación no coincide con la nueva contraseña.")
        else:
            try:
                validate_password(nueva, request.user)
            except ValidationError as e:
                for m in e.messages:
                    messages.error(request, m)
            else:
                request.user.set_password(nueva)
                request.user.save(update_fields=["password"])
                update_session_auth_hash(request, request.user)
                messages.success(request, "Contraseña actualizada.")
                return redirect("accounts:perfil")
    return render(request, "perfil.html")


# ---------------------------------------------------------------- usuarios


@rol_requerido(Rol.ADMINISTRADOR)
def usuarios(request):
    rol = request.GET.get("rol", "")
    buscar = request.GET.get("q", "").strip()
    lista = Usuario.objects.select_related("estudiante__grado").order_by("rol", "nombre")
    if rol in Rol.values:
        lista = lista.filter(rol=rol)
    if buscar:
        lista = lista.filter(
            Q(nombre__icontains=buscar) | Q(usuario__icontains=buscar) | Q(documento__icontains=buscar)
        )
    return render(request, "usuarios.html", {
        "usuarios": lista, "roles": Rol.choices, "rol": rol, "buscar": buscar,
    })


def _grado_de(u):
    try:
        return u.estudiante.grado_id
    except Estudiante.DoesNotExist:
        return None


@rol_requerido(Rol.ADMINISTRADOR)
def usuario_form(request, uid=None):
    u = get_object_or_404(Usuario, pk=uid) if uid is not None else None
    acudidos = set(
        AcudienteEstudiante.objects.filter(acudiente=u).values_list("estudiante_id", flat=True)
    ) if u else set()
    valores = {
        "nombre": u.nombre if u else "",
        "documento": (u.documento or "") if u else "",
        "email": u.email if u else "",
        "usuario": u.usuario if u else "",
        "rol": u.rol if u else Rol.ESTUDIANTE,
        "grado_id": _grado_de(u) if u else None,
        "activo": u.is_active if u else True,
    }

    if request.method == "POST":
        f = request.POST
        valores.update(
            nombre=f.get("nombre", "").strip(),
            documento=f.get("documento", "").strip(),
            email=f.get("email", "").strip(),
            usuario=f.get("usuario", "").strip().lower(),
            rol=u.rol if u else f.get("rol", ""),  # el rol no cambia después de creado
            grado_id=int(f["grado_id"]) if f.get("grado_id", "").isdigit() else None,
            activo=bool(f.get("activo")) or (u is not None and u.pk == request.user.pk),
        )
        acudidos = {int(x) for x in f.getlist("acudidos") if x.isdigit()}
        clave = f.get("clave", "")
        errores = []
        if not valores["nombre"] or not valores["usuario"]:
            errores.append("El nombre y el usuario son obligatorios.")
        if valores["rol"] not in Rol.values:
            errores.append("Seleccione un rol válido.")
        if u is None or clave:
            try:
                validate_password(clave, u)
            except ValidationError as e:
                errores.extend(e.messages)
        if errores:
            for e in errores:
                messages.error(request, e)
        else:
            try:
                with transaction.atomic():
                    if u is None:
                        u = Usuario(rol=valores["rol"])
                    u.nombre = valores["nombre"]
                    u.documento = valores["documento"] or None
                    u.email = valores["email"]
                    u.usuario = valores["usuario"]
                    u.is_active = valores["activo"]
                    if clave:
                        u.set_password(clave)
                    u.save()
                    if u.es_estudiante:
                        Estudiante.objects.update_or_create(
                            usuario=u, defaults={"grado_id": valores["grado_id"]}
                        )
                    if u.es_acudiente:
                        AcudienteEstudiante.objects.filter(acudiente=u).delete()
                        AcudienteEstudiante.objects.bulk_create(
                            AcudienteEstudiante(acudiente=u, estudiante_id=e) for e in acudidos
                        )
                messages.success(request, "Usuario guardado.")
                return redirect(f"{reverse('accounts:usuarios')}?rol={u.rol}")
            except IntegrityError:
                if uid is None:
                    u = None
                messages.error(request, "Ya existe otro usuario con ese nombre de usuario o documento.")

    return render(request, "usuario_form.html", {
        "u": u,
        "v": valores,
        "roles": Rol.choices,
        "acudidos": acudidos,
        "grados": Grado.objects.order_by("nombre"),
        "estudiantes": Estudiante.objects.select_related("usuario", "grado").order_by(
            "grado__nombre", "usuario__nombre"
        ),
        "es_propio": u is not None and u.pk == request.user.pk,
    })
