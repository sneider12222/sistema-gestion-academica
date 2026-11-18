"""Carga los datos de prueba del sistema (todos ficticios).

Porta ``sga/seed.py``: mismos usuarios, grados, asignaturas, periodos y la
misma semilla aleatoria (``random.Random(2026)``), así que los datos son
deterministas para una misma fecha. Las fechas de periodos, actividades y
asistencia se calculan respecto al día en que se ejecuta.

Uso:
    python manage.py seed                Carga los datos en una base vacía
    python manage.py seed --reemplazar   Borra TODOS los datos y los vuelve a cargar
"""

import random
from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth.hashers import make_password
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from academico.models import Asignacion, Asignatura, Grado, Periodo
from accounts.context_processors import PREFIJO_DOCUMENTO_PRUEBA
from accounts.models import AcudienteEstudiante, Estudiante, Rol, Usuario
from asistencia.models import Asistencia
from calificaciones.models import Actividad, Calificacion
from reportes.models import Anotacion

# Credenciales del entorno de prueba (documentadas en el README)
CLAVE_ADMIN = "Admin2026*"
CLAVE_PRUEBA = "Prueba2026*"

DOCENTES = ["Marta Pérez Iguarán", "Luis Brito Mendoza", "Carmen Epieyú Gómez"]
ASIGNATURAS = ["Ciencias Naturales", "Inglés", "Lenguaje", "Matemáticas"]
# (índice de asignatura, índice de docente) por cada grado
CARGA = {"6°A": [(3, 0), (2, 1), (0, 2), (1, 1)], "7°A": [(3, 0), (2, 1), (0, 2), (1, 2)]}
ESTUDIANTES = {
    "6°A": ["Ana Sofía Cotes", "Andrés Pinto", "Camila Ipuana", "Daniel Redondo", "Isabella Mejía", "Juan David Deluque"],
    "7°A": ["Laura Pushaina", "Mateo Vanegas", "Nicolás Romero", "Sara Fonseca", "Sebastián Uriana", "Valentina Daza"],
}
# Cada acudiente con los índices (globales) de sus acudidos
ACUDIENTES = [("Rosa Cotes", [0]), ("Pedro Pinto", [1]), ("Yolanda Ipuana", [2, 6]), ("Jorge Redondo", [3]),
              ("Elena Mejía", [4]), ("Óscar Deluque", [5]), ("Marina Vanegas", [7]), ("Hernán Romero", [8, 9]),
              ("Luz Uriana", [10]), ("Diana Daza", [11])]
PERIODOS = [("Periodo 1", "02-02", "04-10"), ("Periodo 2", "04-13", "06-19"),
            ("Periodo 3", "07-13", "09-18"), ("Periodo 4", "09-21", "11-27")]
ACTIVIDADES = [("Taller", 20), ("Quiz", 20), ("Exposición", 25), ("Examen final", 35)]
ANOTACIONES = [(0, 0, "Excelente participación en la feria de ciencias.", 3),
               (1, 1, "No entregó el taller de comprensión lectora.", 5),
               (3, 0, "Interrumpió la clase en repetidas ocasiones.", 8),
               (6, 2, "Apoya a sus compañeros en las actividades de laboratorio.", 4),
               (8, 1, "Debe reforzar la lectura en casa.", 10)]


class Command(BaseCommand):
    help = "Carga los datos de prueba ficticios del sistema de gestión académica."

    def add_arguments(self, parser):
        parser.add_argument(
            "--reemplazar",
            action="store_true",
            help="Borra todos los datos de la base antes de cargar los de prueba.",
        )

    def handle(self, *args, reemplazar=False, **opciones):
        if Usuario.objects.exists():
            if not reemplazar:
                raise CommandError(
                    "La base ya tiene usuarios. Use --reemplazar para borrar todos los datos "
                    "y cargar los de prueba (no lo haga sobre una base con información real)."
                )
            call_command("flush", interactive=False, verbosity=0)
        with transaction.atomic():
            totales = cargar_datos_prueba()
        self.stdout.write(self.style.SUCCESS(
            "Datos de prueba cargados: " + ", ".join(f"{n} {k}" for k, n in totales.items())
        ))


def cargar_datos_prueba(hoy=None):
    rnd = random.Random(2026)
    hoy = hoy or date.today()
    anio = hoy.year
    # Un solo hash por contraseña: hashear 32 veces haría el comando muy lento
    hash_prueba = make_password(CLAVE_PRUEBA)
    contador = {"doc": 0}

    def usuario(nombre, login, rol, clave_hash=hash_prueba):
        contador["doc"] += 1
        return Usuario.objects.create(
            nombre=nombre, usuario=login, rol=rol, password=clave_hash,
            documento=f"{PREFIJO_DOCUMENTO_PRUEBA}{contador['doc']:04d}",
            email=f"{login}@prueba.local",
            is_staff=(rol == Rol.ADMINISTRADOR), is_superuser=(rol == Rol.ADMINISTRADOR),
        )

    usuario("Administrador (prueba)", "admin", Rol.ADMINISTRADOR, make_password(CLAVE_ADMIN))
    docentes = [usuario(n, f"docente{i}", Rol.DOCENTE) for i, n in enumerate(DOCENTES, 1)]
    asignaturas = [Asignatura.objects.create(nombre=n) for n in ASIGNATURAS]
    periodos = [
        Periodo.objects.create(
            nombre=n,
            fecha_inicio=date.fromisoformat(f"{anio}-{i}"),
            fecha_fin=date.fromisoformat(f"{anio}-{f}"),
        )
        for n, i, f in PERIODOS
    ]

    alumnos, n_est = [], 0
    calificaciones, asistencias = [], []
    for nombre_grado, nombres in ESTUDIANTES.items():
        grado = Grado.objects.create(nombre=nombre_grado)
        del_grado = []
        for nombre in nombres:
            n_est += 1
            u = usuario(nombre, f"estudiante{n_est}", Rol.ESTUDIANTE)
            e = Estudiante.objects.create(usuario=u, grado=grado)
            del_grado.append(e)
            alumnos.append(e)

        for i_asig, i_doc in CARGA[nombre_grado]:
            asignacion = Asignacion.objects.create(
                docente=docentes[i_doc], asignatura=asignaturas[i_asig], grado=grado
            )
            nivel = {e.pk: rnd.uniform(2.6, 4.7) for e in del_grado}  # rendimiento base

            for periodo in periodos:
                if periodo.fecha_inicio > hoy:
                    continue
                dias = (periodo.fecha_fin - periodo.fecha_inicio).days
                for k, (nombre_act, pct) in enumerate(ACTIVIDADES):
                    fecha = periodo.fecha_inicio + timedelta(days=int(dias * (k + 1) / (len(ACTIVIDADES) + 0.3)))
                    act = Actividad.objects.create(
                        asignacion=asignacion, periodo=periodo, nombre=nombre_act,
                        porcentaje=Decimal(pct), fecha=fecha,
                    )
                    if fecha > hoy:
                        continue  # actividad programada, aún sin notas
                    for e in del_grado:
                        nota = min(5.0, max(1.0, round(nivel[e.pk] + rnd.uniform(-0.8, 0.8), 1)))
                        calificaciones.append(
                            Calificacion(actividad=act, estudiante=e, nota=Decimal(str(nota)))
                        )

            # Asistencia de las últimas tres semanas (días hábiles)
            for atras in range(1, 22):
                dia = hoy - timedelta(days=atras)
                if dia.weekday() >= 5:
                    continue
                for e in del_grado:
                    estado = rnd.choices("PA", weights=[92, 8])[0]
                    asistencias.append(Asistencia(asignacion=asignacion, estudiante=e, fecha=dia, estado=estado))

    Calificacion.objects.bulk_create(calificaciones)
    Asistencia.objects.bulk_create(asistencias)

    for i, (nombre, acudidos) in enumerate(ACUDIENTES, 1):
        u = usuario(nombre, f"acudiente{i}", Rol.ACUDIENTE)
        AcudienteEstudiante.objects.bulk_create(
            AcudienteEstudiante(acudiente=u, estudiante=alumnos[k]) for k in acudidos
        )

    for est, doc, texto, atras in ANOTACIONES:
        Anotacion.objects.create(
            estudiante=alumnos[est], autor=docentes[doc], descripcion=texto, fecha=hoy - timedelta(days=atras)
        )

    return {
        "usuarios": Usuario.objects.count(),
        "calificaciones": len(calificaciones),
        "registros de asistencia": len(asistencias),
    }
