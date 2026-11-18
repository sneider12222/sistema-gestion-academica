"""Tests de la capa única de permisos de consulta.

Definen el contrato de ``accounts.permissions``: una función pública por regla,
resuelta en SQL (querysets), nunca cargando todo para filtrar en memoria.

Dataset común (``setUpTestData``):

- Grados: ``Octavo``, ``Septimo``, ``Sexto`` (tres, orden alfabético distinto
  al orden de creación, para que el orden estable se pruebe de verdad).
- Docentes: ``doc_1`` (Sexto y Septimo), ``doc_2`` (Octavo).
- Estudiantes activos: ``Ana Septimo``, ``Beto Septimo``, ``Ana Sexto``,
  ``Carla Octavo``; inactivo: ``Inactivo Sexto`` (en Sexto, ``is_active=False``).
- Acudiente ``acu``: vinculado a ``Ana Sexto`` y ``Ana Septimo``.
"""

from django.test import TestCase

from academico.models import Asignacion, Asignatura, Grado
from accounts.models import AcudienteEstudiante, Estudiante, Rol, Usuario


def _usuario(nombre, rol, activo=True):
    """Usuario sin contraseña usable: estos tests nunca autentican."""
    return Usuario.objects.create(
        usuario=nombre.lower().replace(" ", "."),
        nombre=nombre,
        rol=rol,
        is_active=activo,
    )


class PermisosBase(TestCase):
    """Dataset compartido: se construye una vez por clase."""

    @classmethod
    def setUpTestData(cls):
        cls.octavo = Grado.objects.create(nombre="Octavo")
        cls.septimo = Grado.objects.create(nombre="Septimo")
        cls.sexto = Grado.objects.create(nombre="Sexto")

        cls.doc_1 = _usuario("Docente Uno", Rol.DOCENTE)
        cls.doc_2 = _usuario("Docente Dos", Rol.DOCENTE)

        cls.ana_septimo = _usuario("Ana Septimo", Rol.ESTUDIANTE)
        cls.beto_septimo = _usuario("Beto Septimo", Rol.ESTUDIANTE)
        cls.ana_sexto = _usuario("Ana Sexto", Rol.ESTUDIANTE)
        cls.carla_octavo = _usuario("Carla Octavo", Rol.ESTUDIANTE)
        cls.inactivo = _usuario("Inactivo Sexto", Rol.ESTUDIANTE, activo=False)

        cls.est_ana_septimo = Estudiante.objects.create(
            usuario=cls.ana_septimo, grado=cls.septimo
        )
        cls.est_beto_septimo = Estudiante.objects.create(
            usuario=cls.beto_septimo, grado=cls.septimo
        )
        cls.est_ana_sexto = Estudiante.objects.create(
            usuario=cls.ana_sexto, grado=cls.sexto
        )
        cls.est_carla_octavo = Estudiante.objects.create(
            usuario=cls.carla_octavo, grado=cls.octavo
        )
        cls.est_inactivo = Estudiante.objects.create(
            usuario=cls.inactivo, grado=cls.sexto
        )

        cls.acu = _usuario("Acudiente Uno", Rol.ACUDIENTE)
        AcudienteEstudiante.objects.create(acudiente=cls.acu, estudiante=cls.est_ana_sexto)
        AcudienteEstudiante.objects.create(
            acudiente=cls.acu, estudiante=cls.est_ana_septimo
        )

        cls.admin = _usuario("Admin Uno", Rol.ADMINISTRADOR)
        cls.asignatura = Asignatura.objects.create(nombre="Matematicas")
        cls.asig_sexto = Asignacion.objects.create(
            docente=cls.doc_1, asignatura=cls.asignatura, grado=cls.sexto
        )
        cls.asig_septimo = Asignacion.objects.create(
            docente=cls.doc_1, asignatura=cls.asignatura, grado=cls.septimo
        )
        cls.asig_octavo = Asignacion.objects.create(
            docente=cls.doc_2, asignatura=cls.asignatura, grado=cls.octavo
        )

    @staticmethod
    def _nombres(queryset):
        return list(queryset.values_list("usuario__nombre", flat=True))


class TestEstudiantesVisibles(PermisosBase):
    def test_administrador_ve_todos_los_activos(self):
        from accounts.permissions import estudiantes_visibles

        self.assertCountEqual(
            self._nombres(estudiantes_visibles(self.admin)),
            ["Ana Septimo", "Beto Septimo", "Ana Sexto", "Carla Octavo"],
        )

    def test_administrador_no_ve_estudiantes_inactivos(self):
        from accounts.permissions import estudiantes_visibles

        self.assertNotIn("Inactivo Sexto", self._nombres(estudiantes_visibles(self.admin)))

    def test_docente_ve_los_estudiantes_de_sus_grados(self):
        from accounts.permissions import estudiantes_visibles

        self.assertCountEqual(
            self._nombres(estudiantes_visibles(self.doc_1)),
            ["Ana Septimo", "Beto Septimo", "Ana Sexto"],
        )

    def test_docente_no_ve_el_grado_ajeno(self):
        from accounts.permissions import estudiantes_visibles

        self.assertNotIn("Carla Octavo", self._nombres(estudiantes_visibles(self.doc_1)))

    def test_docente_no_ve_estudiantes_inactivos(self):
        from accounts.permissions import estudiantes_visibles

        self.assertNotIn("Inactivo Sexto", self._nombres(estudiantes_visibles(self.doc_1)))

    def test_acudiente_ve_solo_sus_vinculados(self):
        from accounts.permissions import estudiantes_visibles

        self.assertCountEqual(
            self._nombres(estudiantes_visibles(self.acu)),
            ["Ana Sexto", "Ana Septimo"],
        )

    def test_estudiante_se_ve_solo_a_si_mismo(self):
        from accounts.permissions import estudiantes_visibles

        self.assertEqual(
            self._nombres(estudiantes_visibles(self.ana_sexto)), ["Ana Sexto"]
        )

    def test_orden_estable_por_grado_y_nombre(self):
        from accounts.permissions import estudiantes_visibles

        self.assertEqual(
            self._nombres(estudiantes_visibles(self.doc_1)),
            ["Ana Septimo", "Beto Septimo", "Ana Sexto"],
        )

    def test_rol_desconocido_devuelve_vacio(self):
        from accounts.permissions import estudiantes_visibles

        raro = _usuario("Usuario Raro", "raro")
        self.assertEqual(self._nombres(estudiantes_visibles(raro)), [])

    def test_usuario_none_devuelve_vacio(self):
        from accounts.permissions import estudiantes_visibles

        self.assertEqual(self._nombres(estudiantes_visibles(None)), [])

    def test_docente_se_resuelve_en_una_consulta(self):
        from accounts.permissions import estudiantes_visibles

        with self.assertNumQueries(1):
            list(estudiantes_visibles(self.doc_1))

    def test_puede_ver_se_resuelve_en_una_consulta(self):
        from accounts.permissions import puede_ver

        with self.assertNumQueries(1):
            puede_ver(self.doc_1, self.est_ana_sexto)


class TestGradosVisibles(PermisosBase):
    def test_administrador_ve_todos_los_grados_ordenados(self):
        from accounts.permissions import grados_visibles

        self.assertEqual(
            list(grados_visibles(self.admin).values_list("nombre", flat=True)),
            ["Octavo", "Septimo", "Sexto"],
        )

    def test_docente_ve_solo_sus_grados(self):
        from accounts.permissions import grados_visibles

        self.assertEqual(
            list(grados_visibles(self.doc_1).values_list("nombre", flat=True)),
            ["Septimo", "Sexto"],
        )

    def test_acudiente_no_ve_grados(self):
        from accounts.permissions import grados_visibles

        self.assertFalse(grados_visibles(self.acu).exists())

    def test_estudiante_no_ve_grados(self):
        from accounts.permissions import grados_visibles

        self.assertFalse(grados_visibles(self.ana_sexto).exists())

    def test_rol_desconocido_no_ve_grados(self):
        from accounts.permissions import grados_visibles

        raro = _usuario("Otro Raro", "raro")
        self.assertFalse(grados_visibles(raro).exists())


class TestAsignacionesVisibles(PermisosBase):
    def test_administrador_ve_todas(self):
        from accounts.permissions import asignaciones_visibles

        self.assertCountEqual(
            asignaciones_visibles(self.admin).values_list("pk", flat=True),
            [self.asig_sexto.pk, self.asig_septimo.pk, self.asig_octavo.pk],
        )

    def test_docente_ve_solo_las_suyas(self):
        from accounts.permissions import asignaciones_visibles

        self.assertCountEqual(
            asignaciones_visibles(self.doc_1).values_list("pk", flat=True),
            [self.asig_sexto.pk, self.asig_septimo.pk],
        )

    def test_acudiente_no_ve_asignaciones(self):
        from accounts.permissions import asignaciones_visibles

        self.assertFalse(asignaciones_visibles(self.acu).exists())

    def test_estudiante_no_ve_asignaciones(self):
        from accounts.permissions import asignaciones_visibles

        self.assertFalse(asignaciones_visibles(self.ana_sexto).exists())

    def test_rol_desconocido_no_ve_asignaciones(self):
        from accounts.permissions import asignaciones_visibles

        raro = _usuario("Tercer Raro", "raro")
        self.assertFalse(asignaciones_visibles(raro).exists())


class TestPuedeVer(PermisosBase):
    def test_administrador_ve_cualquiera_activo(self):
        from accounts.permissions import puede_ver

        self.assertTrue(puede_ver(self.admin, self.est_carla_octavo))
        self.assertTrue(puede_ver(self.admin, self.est_ana_sexto))

    def test_administrador_no_ve_inactivo(self):
        from accounts.permissions import puede_ver

        self.assertFalse(puede_ver(self.admin, self.est_inactivo))

    def test_docente_ve_los_de_sus_grados(self):
        from accounts.permissions import puede_ver

        self.assertTrue(puede_ver(self.doc_1, self.est_ana_sexto))
        self.assertTrue(puede_ver(self.doc_1, self.est_ana_septimo))

    def test_docente_no_ve_grado_ajeno(self):
        from accounts.permissions import puede_ver

        self.assertFalse(puede_ver(self.doc_1, self.est_carla_octavo))

    def test_acudiente_ve_sus_vinculados(self):
        from accounts.permissions import puede_ver

        self.assertTrue(puede_ver(self.acu, self.est_ana_sexto))
        self.assertTrue(puede_ver(self.acu, self.est_ana_septimo))

    def test_acudiente_no_ve_nino_no_vinculado(self):
        from accounts.permissions import puede_ver

        self.assertFalse(puede_ver(self.acu, self.est_beto_septimo))

    def test_estudiante_se_ve_solo_a_si_mismo(self):
        from accounts.permissions import puede_ver

        self.assertTrue(puede_ver(self.ana_sexto, self.est_ana_sexto))
        self.assertFalse(puede_ver(self.ana_sexto, self.est_ana_septimo))

    def test_rol_desconocido_no_ve_nada(self):
        from accounts.permissions import puede_ver

        raro = _usuario("Cuarto Raro", "raro")
        self.assertFalse(puede_ver(raro, self.est_ana_sexto))

    def test_usuario_none_no_ve_nada(self):
        from accounts.permissions import puede_ver

        self.assertFalse(puede_ver(None, self.est_ana_sexto))
