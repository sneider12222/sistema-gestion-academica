"""Modelos de cuentas.

Porta las tablas ``usuarios``, ``estudiantes`` y ``acudientes_estudiantes`` de
``sga/schema.sql`` al ORM de Django. La tabla ``config`` no se porta: la bandera
``datos_prueba`` vive ahora en ``settings.DATOS_PRUEBA``.
"""

from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import PermissionsMixin
from django.db import models


class Rol(models.TextChoices):
    """Los cuatro roles del sistema; replican el CHECK del esquema original."""

    ADMINISTRADOR = "administrador", "Administrador"
    DOCENTE = "docente", "Docente"
    ESTUDIANTE = "estudiante", "Estudiante"
    ACUDIENTE = "acudiente", "Acudiente"


class UsuarioManager(BaseUserManager):
    """Manager de ``Usuario``.

    El identificador de acceso es la columna ``usuario``, no el ``username`` de
    Django. Sin estos dos métodos ``AbstractBaseUser`` queda inutilizable
    (``createsuperuser`` y ``authenticate`` dependen de ellos).
    """

    use_in_migrations = True

    def create_user(self, usuario, password=None, **extra_fields):
        if not usuario:
            raise ValueError("El usuario requiere un identificador de acceso.")
        if not extra_fields.get("rol"):
            raise ValueError("El usuario requiere un rol.")
        email = extra_fields.pop("email", "") or ""
        user = self.model(
            usuario=usuario.strip(),
            email=self.normalize_email(email),
            **extra_fields,
        )
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, usuario, password=None, **extra_fields):
        # El esquema no tiene "superusuario": el equivalente es un administrador
        # con is_staff, is_superuser e is_active en True.
        extra_fields.setdefault("rol", Rol.ADMINISTRADOR)
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)

        if not extra_fields["is_staff"]:
            raise ValueError("El superusuario debe tener is_staff=True.")
        if not extra_fields["is_superuser"]:
            raise ValueError("El superusuario debe tener is_superuser=True.")
        return self.create_user(usuario, password, **extra_fields)


class Usuario(AbstractBaseUser, PermissionsMixin):
    """Persona que accede al sistema, con uno de los cuatro roles."""

    nombre = models.CharField("nombre", max_length=150)
    documento = models.CharField(
        "documento", max_length=30, unique=True, null=True, blank=True
    )
    email = models.EmailField("correo electrónico", blank=True)
    usuario = models.CharField("usuario", max_length=50, unique=True)
    rol = models.CharField("rol", max_length=20, choices=Rol.choices)
    # `activo` del esquema original pasa a ser `is_active` para que Django lo
    # respete en el backend de autenticación.
    is_active = models.BooleanField("activo", default=True)
    is_staff = models.BooleanField("acceso al admin", default=False)
    creado_en = models.DateTimeField("creado en", auto_now_add=True)

    objects = UsuarioManager()

    USERNAME_FIELD = "usuario"
    REQUIRED_FIELDS = ["nombre", "rol"]

    class Meta:
        verbose_name = "usuario"
        verbose_name_plural = "usuarios"

    def __str__(self):
        return f"{self.nombre} ({self.usuario})"

    @property
    def es_admin(self):
        return self.rol == Rol.ADMINISTRADOR

    @property
    def es_docente(self):
        return self.rol == Rol.DOCENTE

    @property
    def es_estudiante(self):
        return self.rol == Rol.ESTUDIANTE

    @property
    def es_acudiente(self):
        return self.rol == Rol.ACUDIENTE


class Estudiante(models.Model):
    """Ficha de estudiante: la PK es el propio usuario, como en el esquema."""

    usuario = models.OneToOneField(
        Usuario,
        on_delete=models.CASCADE,
        primary_key=True,
        related_name="estudiante",
        verbose_name="usuario",
    )
    grado = models.ForeignKey(
        "academico.Grado",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="estudiantes",
        verbose_name="grado",
    )

    class Meta:
        verbose_name = "estudiante"
        verbose_name_plural = "estudiantes"

    def __str__(self):
        return f"{self.usuario.nombre} — {self.grado or 'sin grado'}"


class AcudienteEstudiante(models.Model):
    """Vínculo acudiente–estudiante (N:M descompuesto, NF4).

    TODO: el esquema original no valida que ``acudiente`` tenga rol
    ``acudiente``. Eso no se puede expresar como CHECK de base de datos contra
    otra tabla, así que se validará en ``clean()`` cuando se construyan los
    formularios.
    """

    acudiente = models.ForeignKey(
        Usuario,
        on_delete=models.PROTECT,
        related_name="acudidos",
        verbose_name="acudiente",
    )
    estudiante = models.ForeignKey(
        Estudiante,
        on_delete=models.CASCADE,
        related_name="acudientes",
        verbose_name="estudiante",
    )

    class Meta:
        verbose_name = "acudiente de estudiante"
        verbose_name_plural = "acudientes de estudiantes"
        constraints = [
            models.UniqueConstraint(
                fields=["acudiente", "estudiante"],
                name="acudiente_estudiante_unico",
            )
        ]

    def __str__(self):
        return f"{self.acudiente.nombre} → {self.estudiante.usuario.nombre}"
