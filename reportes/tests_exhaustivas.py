"""Pruebas exhaustivas: seguridad entre roles, validación de datos y casos límite."""

import sqlite3
import tempfile
from datetime import date, timedelta
from decimal import Decimal
from io import StringIO
from pathlib import Path

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, TransactionTestCase, override_settings

from academico.models import Asignacion, Asignatura, Grado, Periodo
from accounts.management.commands.seed import CLAVE_ADMIN, CLAVE_PRUEBA, cargar_datos_prueba
from accounts.models import AcudienteEstudiante, Estudiante, Rol, Usuario
from asistencia.models import Asistencia
from calificaciones.models import Actividad, Calificacion
from reportes.models import Anotacion, InformeEnviado

HASH_RAPIDO = ["django.contrib.auth.hashers.MD5PasswordHasher"]
HOY = date(2026, 11, 14)


@override_settings(PASSWORD_HASHERS=HASH_RAPIDO)
class Base(TestCase):
    @classmethod
    def setUpTestData(cls):
        cargar_datos_prueba(hoy=HOY)
        cls.periodo4 = Periodo.objects.get(nombre="Periodo 4")

    def entrar(self, usuario, clave=CLAVE_PRUEBA):
        self.client.logout()
        return self.client.post("/entrar/", {"usuario": usuario, "clave": clave}, follow=True)

    def est(self, usuario):
        return Estudiante.objects.get(usuario__usuario=usuario)

    def asig(self, docente, grado="6°A"):
        return Asignacion.objects.filter(docente__usuario=docente, grado__nombre=grado).first()


class Autenticacion(Base):
    def test_usuario_sin_distinguir_mayusculas(self):
        r = self.entrar("DOCENTE1")
        self.assertEqual(r.resolver_match.view_name, "accounts:inicio")

    def test_redirige_a_la_pagina_pedida_tras_ingresar(self):
        destino = f"/informe/{self.est('estudiante1').pk}/"
        r = self.client.get(destino)
        self.assertRedirects(r, f"/entrar/?next={destino}", fetch_redirect_response=False)
        r = self.client.post(f"/entrar/?next={destino}", {"usuario": "docente1", "clave": CLAVE_PRUEBA})
        self.assertRedirects(r, destino, fetch_redirect_response=False)

    def test_next_externo_ignorado(self):
        r = self.client.post("/entrar/?next=https://sitio-malicioso.example/",
                             {"usuario": "docente1", "clave": CLAVE_PRUEBA})
        self.assertRedirects(r, "/", fetch_redirect_response=False)

    def test_cerrar_sesion_solo_por_post(self):
        self.entrar("docente1")
        self.assertEqual(self.client.get("/salir/").status_code, 405)
        self.client.post("/salir/")
        self.assertEqual(self.client.get("/").status_code, 302)

    def test_cambio_de_contrasena(self):
        self.entrar("docente2")
        r = self.client.post("/perfil/", {"actual": "mala", "nueva": "OtraClave99*", "confirmar": "OtraClave99*"}, follow=True)
        self.assertContains(r, "actual no es correcta")
        r = self.client.post("/perfil/", {"actual": CLAVE_PRUEBA, "nueva": "OtraClave99*", "confirmar": "Distinta99*"}, follow=True)
        self.assertContains(r, "no coincide")
        r = self.client.post("/perfil/", {"actual": CLAVE_PRUEBA, "nueva": "123", "confirmar": "123"}, follow=True)
        self.assertContains(r, "demasiado corta")
        r = self.client.post("/perfil/", {"actual": CLAVE_PRUEBA, "nueva": "OtraClave99*", "confirmar": "OtraClave99*"}, follow=True)
        self.assertContains(r, "Contraseña actualizada")
        # La sesión sigue abierta tras el cambio y la clave nueva funciona
        self.assertEqual(self.client.get("/").status_code, 200)
        self.assertContains(self.entrar("docente2", "OtraClave99*"), "Mis asignaturas")
        self.assertContains(self.entrar("docente2", CLAVE_PRUEBA), "incorrectos")

    def test_admin_no_puede_desactivarse_a_si_mismo(self):
        self.entrar("admin", CLAVE_ADMIN)
        admin = Usuario.objects.get(usuario="admin")
        self.client.post(f"/administracion/usuarios/{admin.pk}/", {"nombre": "Admin", "usuario": "admin"})
        admin.refresh_from_db()
        self.assertTrue(admin.is_active)


class SeguridadEntreRoles(Base):
    def test_docente_no_puede_calificar_asignacion_ajena(self):
        self.entrar("docente1")
        ajena = Asignacion.objects.exclude(docente__usuario="docente1").first()
        act = Actividad.objects.filter(asignacion=ajena, periodo=self.periodo4).first()
        est = Estudiante.objects.filter(grado=ajena.grado).first()
        antes = Calificacion.objects.get(actividad=act, estudiante=est).nota
        r = self.client.post(f"/asignacion/{ajena.pk}/calificaciones/",
                             {"accion": "guardar_notas", f"nota_{act.pk}_{est.pk}": "1.0"})
        self.assertEqual(r.status_code, 403)
        self.assertEqual(Calificacion.objects.get(actividad=act, estudiante=est).nota, antes)

    def test_no_se_inyectan_notas_de_otra_asignacion_en_la_propia(self):
        self.entrar("docente1")
        propia = self.asig("docente1")
        ajena = Asignacion.objects.exclude(docente__usuario="docente1").filter(grado=propia.grado).first()
        act_ajena = Actividad.objects.filter(asignacion=ajena, periodo=self.periodo4).first()
        est = Estudiante.objects.filter(grado=propia.grado).first()
        antes = Calificacion.objects.get(actividad=act_ajena, estudiante=est).nota
        self.client.post(f"/asignacion/{propia.pk}/calificaciones/?periodo={self.periodo4.pk}",
                         {"accion": "guardar_notas", "periodo": self.periodo4.pk,
                          f"nota_{act_ajena.pk}_{est.pk}": "1.0"})
        self.assertEqual(Calificacion.objects.get(actividad=act_ajena, estudiante=est).nota, antes)

    def test_docente_no_elimina_actividad_ajena(self):
        self.entrar("docente1")
        propia = self.asig("docente1")
        act_ajena = Actividad.objects.exclude(asignacion__docente__usuario="docente1").first()
        self.client.post(f"/asignacion/{propia.pk}/calificaciones/",
                         {"accion": "eliminar_actividad", "actividad_id": act_ajena.pk})
        self.assertTrue(Actividad.objects.filter(pk=act_ajena.pk).exists())

    def test_docente_sin_grados_no_ve_ni_anota_estudiantes(self):
        Usuario.objects.create_user("nuevo.docente", "ClaveSegura1*", nombre="Docente Nuevo", rol=Rol.DOCENTE)
        self.client.logout()
        self.client.post("/entrar/", {"usuario": "nuevo.docente", "clave": "ClaveSegura1*"})
        est = self.est("estudiante1")
        self.assertEqual(self.client.get(f"/informe/{est.pk}/").status_code, 403)
        r = self.client.post("/anotaciones/", {"estudiante_id": est.pk, "descripcion": "x"}, follow=True)
        self.assertContains(r, "Seleccione un estudiante de sus grados")
        self.assertFalse(Anotacion.objects.filter(descripcion="x").exists())
        self.assertEqual(self.client.get("/reportes/?grado=1").status_code, 403)

    def test_docente_no_borra_anotacion_de_otro(self):
        ajena = Anotacion.objects.exclude(autor__usuario="docente1").first()
        self.entrar("docente1")
        self.client.post("/anotaciones/", {"accion": "eliminar", "id": ajena.pk})
        self.assertTrue(Anotacion.objects.filter(pk=ajena.pk).exists())

    def test_acudiente_con_dos_acudidos(self):
        # acudiente3 tiene a Camila Ipuana (6°A) y Laura Pushaina (7°A)
        self.entrar("acudiente3")
        r = self.client.get("/estudiantes/")
        self.assertContains(r, "Camila Ipuana")
        self.assertContains(r, "Laura Pushaina")
        self.assertNotContains(r, "Andrés Pinto")

    def test_bandejas_separadas(self):
        est1 = self.est("estudiante1")
        self.entrar("docente1")
        self.client.post(f"/informe/{est1.pk}/enviar/", {"mensaje": "De docente uno"})
        self.entrar("docente2")
        self.assertNotContains(self.client.get("/informes/"), "De docente uno")
        self.entrar("acudiente2")
        self.assertNotContains(self.client.get("/informes/"), "De docente uno")
        self.entrar("admin", CLAVE_ADMIN)
        self.assertContains(self.client.get("/informes/"), "De docente uno")

    def test_acudiente_no_marca_leido_un_envio_ajeno(self):
        est1 = self.est("estudiante1")
        self.entrar("docente1")
        self.client.post(f"/informe/{est1.pk}/enviar/", {})
        envio = InformeEnviado.objects.get()
        self.entrar("admin", CLAVE_ADMIN)
        self.client.get(f"/informe/{est1.pk}/?envio={envio.pk}")
        envio.refresh_from_db()
        self.assertIsNone(envio.leido_en)

    def test_reportes_de_grado_ajeno_prohibido(self):
        Usuario.objects.create_user("doc.sexto", "ClaveSegura1*", nombre="Doc Sexto", rol=Rol.DOCENTE)
        doc = Usuario.objects.get(usuario="doc.sexto")
        sexto, septimo = Grado.objects.get(nombre="6°A"), Grado.objects.get(nombre="7°A")
        asignatura = Asignatura.objects.create(nombre="Artes")
        Asignacion.objects.create(docente=doc, asignatura=asignatura, grado=sexto)
        self.client.post("/entrar/", {"usuario": "doc.sexto", "clave": "ClaveSegura1*"})
        self.assertEqual(self.client.get(f"/reportes/?grado={sexto.pk}").status_code, 200)
        self.assertEqual(self.client.get(f"/reportes/?grado={septimo.pk}").status_code, 403)
        otro = Estudiante.objects.filter(grado=septimo).first()
        self.assertEqual(self.client.get(f"/informe/{otro.pk}/").status_code, 403)

    def test_estudiante_inexistente_404(self):
        self.entrar("admin", CLAVE_ADMIN)
        self.assertEqual(self.client.get("/informe/99999/").status_code, 404)
        self.assertEqual(self.client.get("/asignacion/99999/calificaciones/").status_code, 404)


class ValidacionDeDatos(Base):
    def setUp(self):
        self.entrar("docente1")
        self.a = self.asig("docente1")
        self.ruta = f"/asignacion/{self.a.pk}/calificaciones/"
        self.act = Actividad.objects.filter(asignacion=self.a, periodo=self.periodo4).first()
        self.e = Estudiante.objects.filter(grado=self.a.grado).first()

    def guardar(self, texto):
        return self.client.post(self.ruta, {"accion": "guardar_notas", "periodo": self.periodo4.pk,
                                            f"nota_{self.act.pk}_{self.e.pk}": texto}, follow=True)

    def nota(self):
        c = Calificacion.objects.filter(actividad=self.act, estudiante=self.e).first()
        return c.nota if c else None

    def test_limites_de_la_escala(self):
        for texto, esperado in [("1", Decimal("1.0")), ("5.0", Decimal("5.0")), ("3,25", Decimal("3.2")),
                                ("4.35", Decimal("4.4"))]:
            self.guardar(texto)
            self.assertEqual(self.nota(), esperado, texto)
        for invalido in ("0.9", "5.1", "-3", "abc", "1e3", "NaN"):
            self.assertContains(self.guardar(invalido), "no se guardaron", msg_prefix=invalido)
            self.assertEqual(self.nota(), Decimal("4.4"), invalido)

    def test_casilla_vacia_borra_la_nota(self):
        self.guardar("")
        self.assertIsNone(self.nota())

    def test_porcentaje_de_actividad(self):
        for pct in ("0", "101", "-5", "abc", ""):
            r = self.client.post(self.ruta, {"accion": "crear_actividad", "nombre": f"A{pct}", "porcentaje": pct,
                                             "fecha": "2026-11-10", "periodo": self.periodo4.pk}, follow=True)
            self.assertContains(r, "porcentaje entre 1 y 100", msg_prefix=pct)
        self.assertFalse(Actividad.objects.filter(nombre__startswith="A").exists())

    def test_aviso_si_porcentajes_no_suman_100(self):
        self.client.post(self.ruta, {"accion": "crear_actividad", "nombre": "Extra", "porcentaje": "10",
                                     "fecha": "2026-11-10", "periodo": self.periodo4.pk})
        r = self.client.get(f"{self.ruta}?periodo={self.periodo4.pk}")
        self.assertContains(r, "suman 110%")

    def test_eliminar_actividad_borra_sus_notas(self):
        self.client.post(self.ruta, {"accion": "eliminar_actividad", "actividad_id": self.act.pk,
                                     "periodo": self.periodo4.pk})
        self.assertFalse(Calificacion.objects.filter(actividad_id=self.act.pk).exists())

    def test_estado_de_asistencia_invalido_queda_presente(self):
        ayer = (date.today() - timedelta(days=1)).isoformat()
        self.client.post(f"/asignacion/{self.a.pk}/asistencia/", {"fecha": ayer, f"estado_{self.e.pk}": "X"})
        self.assertEqual(Asistencia.objects.get(asignacion=self.a, estudiante=self.e, fecha=ayer).estado, "P")

    def test_asistencia_se_actualiza_sin_duplicar(self):
        ayer = (date.today() - timedelta(days=1)).isoformat()
        ruta = f"/asignacion/{self.a.pk}/asistencia/"
        self.client.post(ruta, {"fecha": ayer, f"estado_{self.e.pk}": "A"})
        self.client.post(ruta, {"fecha": ayer, f"estado_{self.e.pk}": "P"})
        registros = Asistencia.objects.filter(asignacion=self.a, estudiante=self.e, fecha=ayer)
        self.assertEqual([r.estado for r in registros], ["P"])

    def test_parametros_basura_no_rompen(self):
        for ruta in (f"{self.ruta}?periodo=abc", f"/asignacion/{self.a.pk}/asistencia/?fecha=31-31-2026",
                     f"/informe/{self.e.pk}/?periodo=xyz&envio=abc", "/reportes/?grado=abc&periodo=-1"):
            self.assertEqual(self.client.get(ruta).status_code, 200, ruta)

    def test_anotacion_vacia_o_futura(self):
        manana = (date.today() + timedelta(days=1)).isoformat()
        r = self.client.post("/anotaciones/", {"estudiante_id": self.e.pk, "descripcion": "   "}, follow=True)
        self.assertContains(r, "Escriba la anotación")
        r = self.client.post("/anotaciones/", {"estudiante_id": self.e.pk, "descripcion": "Futura",
                                               "fecha": manana}, follow=True)
        self.assertContains(r, "no puede ser futura")

    def test_texto_con_html_se_escapa(self):
        self.client.post("/anotaciones/", {"estudiante_id": self.e.pk,
                                           "descripcion": "<script>alert(1)</script>"})
        r = self.client.get("/anotaciones/")
        self.assertNotContains(r, "<script>alert(1)</script>")
        self.assertContains(r, "&lt;script&gt;alert(1)&lt;/script&gt;")


class Administracion(Base):
    def setUp(self):
        self.entrar("admin", CLAVE_ADMIN)

    def post(self, datos):
        return self.client.post("/administracion/academico/", datos, follow=True)

    def test_periodo_con_fechas_invertidas(self):
        r = self.post({"accion": "periodo", "nombre": "Malo", "fecha_inicio": "2027-05-01", "fecha_fin": "2027-01-01"})
        self.assertContains(r, "rango de fechas válido")
        self.assertFalse(Periodo.objects.filter(nombre="Malo").exists())

    def test_nombres_duplicados(self):
        self.assertContains(self.post({"accion": "grado", "nombre": "6°A"}), "Ya existe")
        self.assertContains(self.post({"accion": "asignatura", "nombre": "Inglés"}), "Ya existe")

    def test_reasignar_docente(self):
        a = Asignacion.objects.get(grado__nombre="6°A", asignatura__nombre="Inglés")
        nuevo = Usuario.objects.get(usuario="docente3")
        self.post({"accion": "asignacion", "grado_id": a.grado_id, "asignatura_id": a.asignatura_id,
                   "docente_id": nuevo.pk})
        a.refresh_from_db()
        self.assertEqual(a.docente, nuevo)
        self.assertEqual(Asignacion.objects.filter(grado_id=a.grado_id, asignatura_id=a.asignatura_id).count(), 1)

    def test_no_asigna_a_quien_no_es_docente(self):
        estudiante = Usuario.objects.get(usuario="estudiante1")
        r = self.post({"accion": "asignacion", "grado_id": 1, "asignatura_id": 1, "docente_id": estudiante.pk})
        self.assertContains(r, "Seleccione docente")

    def test_borrados_protegidos(self):
        for tabla, obj in [("asignaturas", Asignatura.objects.first()), ("periodos", self.periodo4),
                           ("asignaciones", Asignacion.objects.first())]:
            r = self.post({"accion": "eliminar", "tabla": tabla, "id": obj.pk})
            self.assertContains(r, "No se puede eliminar", msg_prefix=tabla)
        # Una tabla que no está en la lista blanca no se toca
        self.post({"accion": "eliminar", "tabla": "usuarios", "id": 1})
        self.assertTrue(Usuario.objects.filter(pk=1).exists())

    def test_borrado_permitido_sin_dependencias(self):
        self.post({"accion": "grado", "nombre": "11°B"})
        g = Grado.objects.get(nombre="11°B")
        self.assertContains(self.post({"accion": "eliminar", "tabla": "grados", "id": g.pk}), "Registro eliminado")

    def test_crear_acudiente_con_acudidos(self):
        e1, e2 = self.est("estudiante1"), self.est("estudiante8")
        self.client.post("/administracion/usuarios/nuevo/", {
            "nombre": "Acudiente Nuevo", "usuario": "acu.nuevo", "rol": "acudiente", "clave": "ClaveNueva1*",
            "activo": "on", "acudidos": [e1.pk, e2.pk]})
        acu = Usuario.objects.get(usuario="acu.nuevo")
        self.assertEqual(set(AcudienteEstudiante.objects.filter(acudiente=acu).values_list("estudiante_id", flat=True)),
                         {e1.pk, e2.pk})
        # Al editar se reemplazan los vínculos
        self.client.post(f"/administracion/usuarios/{acu.pk}/", {
            "nombre": "Acudiente Nuevo", "usuario": "acu.nuevo", "activo": "on", "acudidos": [e2.pk]})
        self.assertEqual(list(AcudienteEstudiante.objects.filter(acudiente=acu).values_list("estudiante_id", flat=True)),
                         [e2.pk])

    def test_el_rol_no_cambia_al_editar(self):
        u = Usuario.objects.get(usuario="docente1")
        self.client.post(f"/administracion/usuarios/{u.pk}/", {"nombre": u.nombre, "usuario": "docente1",
                                                                "rol": "administrador", "activo": "on"})
        u.refresh_from_db()
        self.assertEqual(u.rol, Rol.DOCENTE)

    def test_filtros_de_usuarios(self):
        r = self.client.get("/administracion/usuarios/?rol=docente")
        self.assertContains(r, "3 usuario(s)")
        r = self.client.get("/administracion/usuarios/?q=Pushaina")
        self.assertContains(r, "1 usuario(s)")

@override_settings(PASSWORD_HASHERS=HASH_RAPIDO)
class ComandoSeed(TestCase):
    def test_carga_rechaza_base_con_datos_y_reemplaza(self):
        call_command("seed", stdout=StringIO())
        self.assertEqual(Usuario.objects.count(), 26)
        with self.assertRaises(CommandError):
            call_command("seed", stdout=StringIO())
        Usuario.objects.create_user("extra", "ClaveSegura1*", nombre="Extra", rol=Rol.DOCENTE)
        call_command("seed", "--reemplazar", stdout=StringIO())
        self.assertEqual(Usuario.objects.count(), 26)
        self.assertFalse(Usuario.objects.filter(usuario="extra").exists())

    def test_datos_coherentes(self):
        cargar_datos_prueba(hoy=HOY)
        # Cada actividad con notas tiene una nota por estudiante del grado
        for act in Actividad.objects.filter(calificaciones__isnull=False).distinct():
            alumnos = Estudiante.objects.filter(grado=act.asignacion.grado).count()
            self.assertEqual(act.calificaciones.count(), alumnos)
        # Ninguna actividad futura tiene notas y todas las notas están en escala
        self.assertFalse(Calificacion.objects.filter(actividad__fecha__gt=HOY).exists())
        self.assertFalse(Calificacion.objects.exclude(nota__gte=1, nota__lte=5).exists())
        # Los porcentajes de cada asignación suman 100 en cada periodo
        for a in Asignacion.objects.all():
            for p in Periodo.objects.filter(fecha_inicio__lte=HOY):
                total = sum(x.porcentaje for x in Actividad.objects.filter(asignacion=a, periodo=p))
                self.assertEqual(total, 100)


@override_settings(PASSWORD_HASHERS=HASH_RAPIDO)
class CopiaDeSeguridad(TransactionTestCase):
    """Sin transacción envolvente, como en una petición real (la copia lee la base en uso)."""

    def test_copia_de_seguridad_valida(self):
        cargar_datos_prueba(hoy=HOY)
        self.client.post("/entrar/", {"usuario": "admin", "clave": CLAVE_ADMIN})
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            with override_settings(RESPALDOS_DIR=Path(tmp)):
                r = self.client.post("/administracion/respaldos/", follow=True)
                self.assertContains(r, "Copia de seguridad creada")
                copias = list(Path(tmp).glob("sga_*.sqlite3"))
                self.assertEqual(len(copias), 1)
                con = sqlite3.connect(copias[0])
                usuarios = con.execute("SELECT COUNT(*) FROM accounts_usuario").fetchone()[0]
                notas = con.execute("SELECT COUNT(*) FROM calificaciones_calificacion").fetchone()[0]
                con.close()
                self.assertEqual(usuarios, Usuario.objects.count())
                self.assertEqual(notas, Calificacion.objects.count())
