"""Variables disponibles en todas las plantillas."""

from django.conf import settings

from .models import Usuario

INSTITUCION = "Instituto para el Desarrollo de las Inteligencias Múltiples"
DIRECCION = "Calle 17 # 7a, Riohacha, La Guajira"

# Los usuarios que crea el comando ``seed`` llevan este prefijo en el documento.
PREFIJO_DOCUMENTO_PRUEBA = "PRUEBA-"


def hay_datos_prueba():
    """Riesgo 4 del modelo técnico: los datos simulados deben estar identificados.

    El aviso aparece si se fuerza con ``DATOS_PRUEBA`` o si la base contiene los
    usuarios ficticios del comando ``seed``.
    """
    return settings.DATOS_PRUEBA or Usuario.objects.filter(
        documento__startswith=PREFIJO_DOCUMENTO_PRUEBA
    ).exists()


def institucion(request):
    datos = {"INSTITUCION": INSTITUCION, "DIRECCION": DIRECCION}
    if getattr(request, "user", None) is not None and request.user.is_authenticated:
        datos["datos_prueba"] = hay_datos_prueba()
    return datos
