"""Pruebas funcionales de las vistas Django sobre los datos del comando ``seed``.

Portan las pruebas de ``tests/test_sga.py`` (versión Flask): acceso por rol,
solo lectura para estudiante y acudiente, y los flujos de registro y envío.
"""

from datetime import date, timedelta
from decimal import Decimal

from django.conf import settings
from django.test import TestCase, override_settings

from academico.models import Asignacion, Grado
from accounts.management.commands.seed import CLAVE_ADMIN, CLAVE_PRUEBA, cargar_datos_prueba
from accounts.models import Estudiante, Usuario
from asistencia.models import Asistencia
from calificaciones.models import Actividad, Calificacion
from reportes.models import InformeEnviado

HASH_RAPIDO = ["django.contrib.auth.hashers.MD5PasswordHasher"]


@override_settings(PASSWORD_HASHERS=HASH_RAPIDO)
class Base(TestCase):
    @classmethod
    def setUpTestData(cls):
        cargar_datos_prueba(hoy=date(2026, 11, 14))

    def entrar(self, usuario, clave=CLAVE_PRUEBA):
        self.client.logout()
        return self.client.post("/entrar/", {"usuario": usuario, "clave": clave}, follow=True)

    def pk(self, usuario):
        return Usuario.objects.get(usuario=usuario).pk


class Acceso(Base):
    def test_requiere_sesion(self):
        for ruta in ("/", "/estudiantes/", "/administracion/usuarios/", "/reportes/", "/informes/"):
            r = self.client.get(ruta)
            self.assertEqual(r.status_code, 302, ruta)
            self.assertIn("/entrar/", r["Location"])

    def test_clave_incorrecta(self):
        self.assertContains(self.entrar("admin", "equivocada"), "incorrectos")

    def test_post_sin_csrf_rechazado(self):
        cliente = self.client_class(enforce_csrf_checks=True)
        r = cliente.post("/entrar/", {"usuario": "admin", "clave": CLAVE_ADMIN})
        self.assertEqual(r.status_code, 403)

    def test_paginas_por_rol(self):
        est1, est7 = self.pk("estudiante1"), self.pk("estudiante7")
        doc1 = self.pk("docente1")
        propia = Asignacion.objects.filter(docente_id=doc1).first().pk
        ajena = Asignacion.objects.exclude(docente_id=doc1).first().pk
        casos = {
            ("admin", CLAVE_ADMIN): {
                200: ["/", "/administracion/usuarios/", "/administracion/usuarios/nuevo/",
                      f"/administracion/usuarios/{est1}/", "/administracion/academico/",
                      "/administracion/respaldos/", "/estudiantes/", "/reportes/", "/informes/",
                      "/anotaciones/", f"/informe/{est1}/", f"/asignacion/{ajena}/calificaciones/",
                      f"/asignacion/{ajena}/asistencia/", "/perfil/"]},
            ("docente1", CLAVE_PRUEBA): {
                200: ["/", "/estudiantes/", "/reportes/", "/informes/", "/anotaciones/", f"/informe/{est1}/",
                      f"/asignacion/{propia}/calificaciones/", f"/asignacion/{propia}/asistencia/"],
                403: ["/administracion/usuarios/", "/administracion/academico/", "/administracion/respaldos/",
                      f"/asignacion/{ajena}/calificaciones/", f"/asignacion/{ajena}/asistencia/"]},
            ("estudiante1", CLAVE_PRUEBA): {
                200: [f"/informe/{est1}/", "/perfil/"],
                403: [f"/informe/{est7}/", "/estudiantes/", "/reportes/", "/informes/",
                      "/administracion/usuarios/", "/anotaciones/", f"/asignacion/{propia}/calificaciones/"]},
            ("acudiente1", CLAVE_PRUEBA): {
                200: ["/", "/estudiantes/", "/informes/", f"/informe/{est1}/"],
                403: [f"/informe/{est7}/", "/reportes/", "/administracion/usuarios/", "/anotaciones/",
                      f"/asignacion/{propia}/asistencia/"]},
        }
        for (usuario, clave), esperado in casos.items():
            self.entrar(usuario, clave)
            for codigo, rutas in esperado.items():
                for ruta in rutas:
                    self.assertEqual(self.client.get(ruta).status_code, codigo, f"{usuario} {ruta}")

    def test_estudiante_entra_directo_a_su_informe(self):
        self.entrar("estudiante1")
        r = self.client.get("/")
        self.assertRedirects(r, f"/informe/{self.pk('estudiante1')}/")

    def test_solo_lectura_para_estudiante_y_acudiente(self):
        est1 = self.pk("estudiante1")
        asig = Asignacion.objects.first().pk
        for usuario in ("estudiante1", "acudiente1"):
            self.entrar(usuario)
            for ruta in (f"/asignacion/{asig}/calificaciones/", f"/asignacion/{asig}/asistencia/",
                         "/anotaciones/", f"/informe/{est1}/enviar/", "/administracion/academico/"):
                self.assertEqual(self.client.post(ruta, {}).status_code, 403, f"{usuario} POST {ruta}")

    def test_pagina_404_propia_sin_detalles_tecnicos(self):
        self.entrar("docente1")
        r = self.client.get("/no-existe/")
        self.assertEqual(r.status_code, 404)
        self.assertContains(r, "La página solicitada no existe.", status_code=404)
        self.assertNotContains(r, "URLconf", status_code=404)

    def test_estilos_disponibles_sin_debug(self):
        r = self.client.get("/static/estilos.css")
        self.assertEqual(r.status_code, 200)

    def test_aviso_de_datos_de_prueba(self):
        self.entrar("admin", CLAVE_ADMIN)
        self.assertContains(self.client.get("/"), "Datos de prueba.")


class Flujos(Base):
    def test_docente_registra_notas_asistencia_y_anotacion(self):
        self.entrar("docente1")
        est = Estudiante.objects.get(usuario__usuario="estudiante1")
        asig = Asignacion.objects.get(docente__usuario="docente1", grado=est.grado)
        ruta = f"/asignacion/{asig.pk}/calificaciones/"

        r = self.client.post(ruta, {"accion": "crear_actividad", "nombre": "Prueba unitaria",
                                    "porcentaje": "10", "fecha": "2026-11-10"}, follow=True)
        self.assertContains(r, "Actividad creada")
        act = Actividad.objects.get(nombre="Prueba unitaria")
        periodo = act.periodo_id

        # ADR 0003: no se repite el nombre de la actividad en el periodo
        r = self.client.post(ruta, {"accion": "crear_actividad", "nombre": "Prueba unitaria", "periodo": periodo,
                                    "porcentaje": "10", "fecha": "2026-11-10"}, follow=True)
        self.assertContains(r, "Ya existe una actividad")

        self.client.post(ruta, {"accion": "guardar_notas", "periodo": periodo, f"nota_{act.pk}_{est.pk}": "4,5"})
        self.assertEqual(Calificacion.objects.get(actividad=act, estudiante=est).nota, Decimal("4.5"))
        # Fuera de la escala: se rechaza y se conserva la nota anterior
        r = self.client.post(ruta, {"accion": "guardar_notas", "periodo": periodo,
                                    f"nota_{act.pk}_{est.pk}": "7"}, follow=True)
        self.assertContains(r, "no se guardaron")
        self.assertEqual(Calificacion.objects.get(actividad=act, estudiante=est).nota, Decimal("4.5"))

        ayer = (date.today() - timedelta(days=1)).isoformat()
        self.client.post(f"/asignacion/{asig.pk}/asistencia/", {"fecha": ayer, f"estado_{est.pk}": "A"})
        self.assertEqual(Asistencia.objects.get(asignacion=asig, estudiante=est, fecha=ayer).estado, "A")

        r = self.client.post("/anotaciones/", {"estudiante_id": est.pk, "descripcion": "Nota de prueba unitaria",
                                               "fecha": ayer}, follow=True)
        self.assertContains(r, "Anotación registrada")

        # La anotación y el historial aparecen en el informe que consulta el estudiante
        self.entrar("estudiante1")
        r = self.client.get(f"/informe/{est.pk}/?periodo={periodo}")
        self.assertContains(r, "Historial académico")

    def test_asistencia_futura_rechazada(self):
        self.entrar("docente1")
        asig = Asignacion.objects.filter(docente__usuario="docente1").first()
        manana = (date.today() + timedelta(days=1)).isoformat()
        r = self.client.post(f"/asignacion/{asig.pk}/asistencia/", {"fecha": manana}, follow=True)
        self.assertContains(r, "fecha futura")

    def test_envio_y_lectura_de_informe(self):
        est, acu = self.pk("estudiante1"), self.pk("acudiente1")
        self.entrar("docente1")
        r = self.client.post(f"/informe/{est}/enviar/", {"mensaje": "Reunión el viernes"}, follow=True)
        self.assertContains(r, "Informe enviado")
        envio = InformeEnviado.objects.get(destinatario_id=acu)
        self.assertIsNone(envio.leido_en)

        self.entrar("acudiente1")
        self.assertContains(self.client.get("/informes/"), "Reunión el viernes")
        self.client.get(f"/informe/{est}/?periodo={envio.periodo_id}&envio={envio.pk}")
        envio.refresh_from_db()
        self.assertIsNotNone(envio.leido_en)

    def test_admin_crea_usuario_valida_y_hace_respaldo(self):
        self.entrar("admin", CLAVE_ADMIN)
        grado = Grado.objects.first()
        r = self.client.post("/administracion/usuarios/nuevo/", {
            "nombre": "Estudiante Nuevo", "usuario": "nuevo1", "rol": "estudiante",
            "clave": "ClaveNueva1*", "grado_id": grado.pk, "activo": "on"}, follow=True)
        self.assertContains(r, "Usuario guardado")
        self.assertEqual(Estudiante.objects.get(usuario__usuario="nuevo1").grado, grado)

        r = self.client.post("/administracion/usuarios/nuevo/", {
            "nombre": "Repetido", "usuario": "nuevo1", "rol": "docente", "clave": "ClaveNueva1*"}, follow=True)
        self.assertContains(r, "Ya existe otro usuario")
        r = self.client.post("/administracion/usuarios/nuevo/", {
            "nombre": "Corta", "usuario": "corta", "rol": "docente", "clave": "123"}, follow=True)
        self.assertContains(r, "demasiado corta")

        # Indicador del proyecto: usuarios registrados frente a la meta de 280
        self.assertContains(self.client.get("/"), "de 280")

        # No se puede eliminar un grado con estudiantes
        r = self.client.post("/administracion/academico/", {"accion": "eliminar", "tabla": "grados",
                                                            "id": grado.pk}, follow=True)
        self.assertContains(r, "No se puede eliminar")

        self.entrar("nuevo1", "ClaveNueva1*")
        self.assertEqual(self.client.get(f"/informe/{self.pk('nuevo1')}/").status_code, 200)

    def test_usuario_inactivo_no_entra_ni_aparece(self):
        self.entrar("admin", CLAVE_ADMIN)
        uid = self.pk("estudiante2")
        self.client.post(f"/administracion/usuarios/{uid}/", {"nombre": "Andrés Pinto", "usuario": "estudiante2"})
        self.assertFalse(Usuario.objects.get(pk=uid).is_active)
        self.assertNotContains(self.client.get("/estudiantes/"), "Andrés Pinto")
        self.assertContains(self.entrar("estudiante2"), "incorrectos")

    def test_respaldo_de_la_base(self):
        # La base de pruebas de SQLite vive en memoria; se comprueba la vista y el mensaje
        self.entrar("admin", CLAVE_ADMIN)
        self.assertEqual(settings.DATABASES["default"]["ENGINE"], "django.db.backends.sqlite3")
        self.assertContains(self.client.get("/administracion/respaldos/"), "Copias de seguridad")
