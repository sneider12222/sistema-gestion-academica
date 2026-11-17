"""Regla única de visibilidad por rol.

En el Flask la misma regla estaba escrita cuatro veces —``estudiantes_visibles``,
``docente._asignacion``, ``consulta.bandeja`` y ``docente.anotaciones``— con
cuatro oportunidades distintas de desviarse. Aquí hay una función pública por
regla y una estrategia por rol: agregar o corregir un rol es tocar una sola
entrada de la tabla, no cuatro ``if``.

Todo se resuelve como queryset, es decir en SQL. Nada de listar y filtrar en
memoria: ``estudiantes_visibles`` de un docente cuesta una consulta aunque
tenga veinte grados.
"""

from academico.models import Asignacion, Grado

from .models import Estudiante, Rol

# Orden estable de las listas que se muestran al usuario.
ORDEN_ESTUDIANTES = ("grado__nombre", "usuario__nombre")
ORDEN_GRADOS = ("nombre",)
ORDEN_ASIGNACIONES = ("grado__nombre", "asignatura__nombre")


# --------------------------------------------------------------- estudiantes
# Un usuario desactivado no aparece en ninguna lista, para ningún rol.


def _estudiantes_activos():
    return Estudiante.objects.filter(usuario__is_active=True)


def _estudiantes_admin(usuario):
    return _estudiantes_activos()


def _estudiantes_docente(usuario):
    grados_del_docente = Asignacion.objects.filter(docente=usuario).values("grado_id")
    return _estudiantes_activos().filter(grado_id__in=grados_del_docente)


def _estudiantes_acudiente(usuario):
    return _estudiantes_activos().filter(acudientes__acudiente=usuario)


def _estudiantes_estudiante(usuario):
    return _estudiantes_activos().filter(usuario=usuario)


_ESTUDIANTES_POR_ROL = {
    Rol.ADMINISTRADOR: _estudiantes_admin,
    Rol.DOCENTE: _estudiantes_docente,
    Rol.ACUDIENTE: _estudiantes_acudiente,
    Rol.ESTUDIANTE: _estudiantes_estudiante,
}


# -------------------------------------------------------------------- grados


def _grados_admin(usuario):
    return Grado.objects.all()


def _grados_docente(usuario):
    # distinct(): un docente puede dictar varias asignaturas en el mismo grado
    # y el JOIN devolvería el grado repetido.
    return Grado.objects.filter(asignaciones__docente=usuario).distinct()


def _grados_vacio(usuario):
    return Grado.objects.none()


_GRADOS_POR_ROL = {
    Rol.ADMINISTRADOR: _grados_admin,
    Rol.DOCENTE: _grados_docente,
    Rol.ACUDIENTE: _grados_vacio,
    Rol.ESTUDIANTE: _grados_vacio,
}


# -------------------------------------------------------------- asignaciones


def _asignaciones_admin(usuario):
    return Asignacion.objects.all()


def _asignaciones_docente(usuario):
    return Asignacion.objects.filter(docente=usuario)


def _asignaciones_vacio(usuario):
    return Asignacion.objects.none()


_ASIGNACIONES_POR_ROL = {
    Rol.ADMINISTRADOR: _asignaciones_admin,
    Rol.DOCENTE: _asignaciones_docente,
    Rol.ACUDIENTE: _asignaciones_vacio,
    Rol.ESTUDIANTE: _asignaciones_vacio,
}


def _estrategia(tabla, usuario):
    """La estrategia del rol, o ``None`` si el rol falta o no existe.

    ``getattr`` en vez de ``usuario.rol`` porque estas funciones también reciben
    ``None`` y ``AnonymousUser``; un rol desconocido nunca significa "ver todo".
    """
    return tabla.get(getattr(usuario, "rol", None))


# ------------------------------------------------------------------- API


def estudiantes_visibles(usuario):
    """Estudiantes activos que el usuario puede consultar, orden grado y nombre."""
    estrategia = _estrategia(_ESTUDIANTES_POR_ROL, usuario)
    if estrategia is None:
        return Estudiante.objects.none()
    return estrategia(usuario).order_by(*ORDEN_ESTUDIANTES)


def grados_visibles(usuario):
    """Grados que el usuario puede consultar; acudiente y estudiante, ninguno."""
    estrategia = _estrategia(_GRADOS_POR_ROL, usuario)
    if estrategia is None:
        return Grado.objects.none()
    return estrategia(usuario).order_by(*ORDEN_GRADOS)


def asignaciones_visibles(usuario):
    """Asignaciones que el usuario puede consultar; acudiente y estudiante, ninguna."""
    estrategia = _estrategia(_ASIGNACIONES_POR_ROL, usuario)
    if estrategia is None:
        return Asignacion.objects.none()
    return estrategia(usuario).order_by(*ORDEN_ASIGNACIONES)


def puede_ver(usuario, estudiante):
    """¿El usuario puede ver a ese estudiante?

    Acepta la instancia o su ``pk``. Filtra con el criterio del rol y pregunta
    al motor con ``exists()``: una sola consulta, sin traer la lista completa.
    Pensada para ``get_object_or_404(estudiantes_visibles(usuario), pk=...)`` en
    vistas de detalle.
    """
    pk = getattr(estudiante, "pk", estudiante)
    if pk is None:
        return False
    return estudiantes_visibles(usuario).filter(pk=pk).exists()
