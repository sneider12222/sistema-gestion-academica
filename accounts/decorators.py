"""Control de acceso por rol para las vistas."""

from functools import wraps

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied


def rol_requerido(*roles):
    """Exige sesión iniciada y que el rol del usuario esté en ``roles``.

    Sin sesión redirige al ingreso; con sesión y otro rol responde 403.
    """

    def decorador(vista):
        @wraps(vista)
        @login_required
        def envoltura(request, *args, **kwargs):
            if request.user.rol not in roles:
                raise PermissionDenied
            return vista(request, *args, **kwargs)

        return envoltura

    return decorador
