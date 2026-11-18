"""Configuración del proyecto Django del Sistema de Gestión Académica."""

import secrets
from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parent.parent

# Lectura opcional de .env: si el archivo no existe, todo cae a los valores por
# defecto de desarrollo local.
env = environ.Env()
environ.Env.read_env(BASE_DIR / ".env")



def _clave_local():
    """Clave aleatoria propia de cada instalación, guardada fuera del repositorio.

    Evita una SECRET_KEY fija y conocida en el código. Se crea la primera vez
    que arranca el sistema; si se define SECRET_KEY en el entorno, tiene
    prioridad.
    """
    ruta = BASE_DIR / ".secret_key"
    if not ruta.exists():
        ruta.write_text(secrets.token_urlsafe(50), encoding="utf-8")
    return ruta.read_text(encoding="utf-8").strip()


SECRET_KEY = env("SECRET_KEY", default=None) or _clave_local()

# DEBUG queda desactivado por defecto: con DEBUG=True Django muestra páginas
# técnicas de error que revelan rutas y configuración. Para desarrollar se
# activa con DEBUG=True en el entorno o en .env.
DEBUG = env.bool("DEBUG", default=False)
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=["127.0.0.1", "localhost"])

# ADR 0002: el motor es configuración, no código. SQLite por defecto; para un
# motor servidor se leen USER, PASSWORD, HOST y PORT del entorno.
DB_ENGINE = env("DB_ENGINE", default="django.db.backends.sqlite3")
if DB_ENGINE == "django.db.backends.sqlite3":
    DATABASES = {
        "default": {
            "ENGINE": DB_ENGINE,
            "NAME": env("DB_NAME", default=str(BASE_DIR / "db.sqlite3")),
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": DB_ENGINE,
            "NAME": env("DB_NAME"),
            "USER": env("DB_USER", default=""),
            "PASSWORD": env("DB_PASSWORD", default=""),
            "HOST": env("DB_HOST", default=""),
            "PORT": env("DB_PORT", default=""),
        }
    }

# Crítico: el usuario personalizado debe declararse ANTES de la primera
# migración, o Django crea auth.User y el cambio ya no es posible sin cirugía.
AUTH_USER_MODEL = "accounts.Usuario"

# Reemplaza la tabla `config` del esquema Flask (era un EAV para una bandera).
DATOS_PRUEBA = env.bool("DATOS_PRUEBA", default=False)

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Apps del proyecto
    "accounts",
    "academico",
    "calificaciones",
    "asistencia",
    "reportes",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"
TEST_RUNNER = "config.test_runner.AppsDelProyectoRunner"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "accounts.context_processors.institucion",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

LANGUAGE_CODE = "es-co"
TIME_ZONE = "America/Bogota"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
# La carpeta puede no existir todavía; Django no falla si se omite.
STATICFILES_DIRS = [BASE_DIR / "static"] if (BASE_DIR / "static").exists() else []

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

LOGIN_URL = "accounts:login"
LOGIN_REDIRECT_URL = "accounts:inicio"
LOGOUT_REDIRECT_URL = "accounts:login"

# Sesiones y cookies (mismos criterios que la versión Flask)
SESSION_COOKIE_AGE = 2 * 60 * 60
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_HTTPONLY = True
X_FRAME_OPTIONS = "DENY"
CSRF_FAILURE_VIEW = "config.errores.csrf_fallido"

# En localhost se usa HTTP. Si algún día se publica detrás de HTTPS, HTTPS=True
# activa cookies seguras, redirección y HSTS (lo que pide `check --deploy`).
if env.bool("HTTPS", default=False):
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_SSL_REDIRECT = True
    SECURE_HSTS_SECONDS = env.int("SECURE_HSTS_SECONDS", default=3600)

# Copias de seguridad de la base SQLite (riesgo 5 del modelo técnico)
RESPALDOS_DIR = BASE_DIR / "respaldos"

MESSAGE_TAGS = {
    40: "error",  # messages.ERROR
    25: "ok",  # messages.SUCCESS
    30: "aviso",  # messages.WARNING
}
