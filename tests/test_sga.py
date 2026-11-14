"""Pruebas del sistema sobre una base de datos temporal con los datos de prueba.

Ejecutar desde la carpeta del proyecto:  py -m unittest discover tests -v
"""
import re
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sga import create_app  # noqa: E402
from sga.seed import CLAVE_ADMIN, CLAVE_PRUEBA  # noqa: E402
from sga.servicios import definitiva  # noqa: E402


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.app = create_app(instance_path=self.tmp.name)
        self.c = self.app.test_client()

    def tearDown(self):
        self.tmp.cleanup()

    def sql(self, consulta, params=()):
        con = sqlite3.connect(self.app.config["DATABASE"])
        con.row_factory = sqlite3.Row
        filas = con.execute(consulta, params).fetchall()
        con.close()
        return filas

    def token(self, ruta="/login"):
        html = self.c.get(ruta, follow_redirects=True).get_data(as_text=True)
        return re.search(r'name="csrf_token" value="(\w+)"', html).group(1)

    def post(self, ruta, datos, desde=None):
        datos = dict(datos, csrf_token=self.token(desde or ruta))
        return self.c.post(ruta, data=datos, follow_redirects=True)

    def entrar(self, usuario, clave=CLAVE_PRUEBA):
        self.c.post("/logout", data={"csrf_token": self.token("/login")})
        return self.post("/login", {"usuario": usuario, "clave": clave})

    def id_de(self, usuario):
        return self.sql("SELECT id FROM usuarios WHERE usuario = ?", (usuario,))[0]["id"]


class Reglas(unittest.TestCase):
    def test_definitiva_ponderada(self):
        self.assertEqual(definitiva([(4.0, 50), (2.0, 50)]), 3.0)
        self.assertEqual(definitiva([(5.0, 20), (None, 80)]), 5.0)  # solo cuenta lo calificado
        self.assertIsNone(definitiva([(None, 100)]))


class Acceso(Base):
    def test_requiere_sesion(self):
        for ruta in ("/", "/estudiantes", "/admin/usuarios", "/reportes", "/bandeja"):
            self.assertEqual(self.c.get(ruta).status_code, 302, ruta)

    def test_clave_incorrecta(self):
        r = self.entrar("admin", "equivocada")
        self.assertIn("incorrectos", r.get_data(as_text=True))

    def test_post_sin_csrf_rechazado(self):
        self.assertEqual(self.c.post("/login", data={"usuario": "admin", "clave": CLAVE_ADMIN}).status_code, 400)

    def test_todas_las_paginas_por_rol(self):
        est1, est7 = self.id_de("estudiante1"), self.id_de("estudiante7")
        asig = self.sql("SELECT id FROM asignaciones WHERE docente_id = ?", (self.id_de("docente1"),))[0]["id"]
        ajena = self.sql("SELECT id FROM asignaciones WHERE docente_id <> ?", (self.id_de("docente1"),))[0]["id"]
        casos = {
            ("admin", CLAVE_ADMIN): {
                200: ["/", "/admin/usuarios", "/admin/usuarios/nuevo", f"/admin/usuarios/{est1}", "/admin/academico",
                      "/admin/respaldos", "/estudiantes", "/reportes", "/bandeja",
                      "/docente/anotaciones", f"/informe/{est1}", f"/docente/asignacion/{ajena}/calificaciones",
                      f"/docente/asignacion/{ajena}/asistencia", "/perfil"]},
            ("docente1", CLAVE_PRUEBA): {
                200: ["/", "/estudiantes", "/reportes", "/bandeja", "/docente/anotaciones", f"/informe/{est1}",
                      f"/docente/asignacion/{asig}/calificaciones", f"/docente/asignacion/{asig}/asistencia"],
                403: ["/admin/usuarios", "/admin/academico", "/admin/respaldos",
                      f"/docente/asignacion/{ajena}/calificaciones", f"/docente/asignacion/{ajena}/asistencia"]},
            ("estudiante1", CLAVE_PRUEBA): {
                200: [f"/informe/{est1}", "/perfil"],
                403: [f"/informe/{est7}", "/estudiantes", "/reportes", "/bandeja", "/admin/usuarios",
                      "/docente/anotaciones", f"/docente/asignacion/{asig}/calificaciones"]},
            ("acudiente1", CLAVE_PRUEBA): {
                200: ["/", "/estudiantes", "/bandeja", f"/informe/{est1}"],
                403: [f"/informe/{est7}", "/reportes", "/admin/usuarios", "/docente/anotaciones",
                      f"/docente/asignacion/{asig}/asistencia"]},
        }
        for (usuario, clave), esperado in casos.items():
            self.entrar(usuario, clave)
            for codigo, rutas in esperado.items():
                for ruta in rutas:
                    self.assertEqual(self.c.get(ruta).status_code, codigo, f"{usuario} {ruta}")

    def test_solo_lectura_para_estudiante_y_acudiente(self):
        est1 = self.id_de("estudiante1")
        asig = self.sql("SELECT id FROM asignaciones LIMIT 1")[0]["id"]
        for usuario in ("estudiante1", "acudiente1"):
            self.entrar(usuario)
            for ruta in (f"/docente/asignacion/{asig}/calificaciones", f"/docente/asignacion/{asig}/asistencia",
                         "/docente/anotaciones", f"/informe/{est1}/enviar", "/admin/academico"):
                r = self.c.post(ruta, data={"csrf_token": self.token(f"/informe/{est1}")})
                self.assertEqual(r.status_code, 403, f"{usuario} POST {ruta}")


class Flujos(Base):
    def test_docente_registra_notas_asistencia_y_anotacion(self):
        self.entrar("docente1")
        doc, est = self.id_de("docente1"), self.id_de("estudiante1")
        asig = self.sql("""SELECT a.id FROM asignaciones a JOIN estudiantes e ON e.grado_id = a.grado_id
                            WHERE a.docente_id = ? AND e.usuario_id = ?""", (doc, est))[0]["id"]
        ruta = f"/docente/asignacion/{asig}/calificaciones"

        r = self.post(ruta, {"accion": "crear_actividad", "nombre": "Prueba unitaria", "porcentaje": "10", "fecha": "2026-11-10"})
        self.assertIn("Actividad creada", r.get_data(as_text=True))
        act = self.sql("SELECT id FROM actividades WHERE nombre = 'Prueba unitaria'")[0]["id"]

        r = self.post(ruta, {"accion": "guardar_notas", f"nota_{act}_{est}": "4,5"})
        self.assertEqual(self.sql("SELECT nota FROM calificaciones WHERE actividad_id = ? AND estudiante_id = ?",
                                  (act, est))[0]["nota"], 4.5)
        # Fuera de la escala: se rechaza y se conserva la nota anterior
        r = self.post(ruta, {"accion": "guardar_notas", f"nota_{act}_{est}": "7"})
        self.assertIn("no se guardaron", r.get_data(as_text=True))
        self.assertEqual(self.sql("SELECT nota FROM calificaciones WHERE actividad_id = ? AND estudiante_id = ?",
                                  (act, est))[0]["nota"], 4.5)

        ruta = f"/docente/asignacion/{asig}/asistencia"
        self.post(ruta, {"fecha": "2026-11-13", f"estado_{est}": "A"})
        fila = self.sql("SELECT estado FROM asistencias WHERE asignacion_id = ? AND estudiante_id = ? AND fecha = '2026-11-13'",
                        (asig, est))[0]
        self.assertEqual(fila["estado"], "A")

        r = self.post("/docente/anotaciones", {"estudiante_id": est, "descripcion": "Nota de prueba unitaria", "fecha": "2026-11-13"})
        self.assertIn("Anotación registrada", r.get_data(as_text=True))
        # La anotación y la ausencia aparecen en el informe que consulta el estudiante
        self.entrar("estudiante1")
        html = self.c.get(f"/informe/{est}").get_data(as_text=True)
        self.assertIn("Nota de prueba unitaria", html)
        self.assertIn("Historial académico", html)

    def test_envio_y_lectura_de_informe(self):
        est, acu = self.id_de("estudiante1"), self.id_de("acudiente1")
        self.entrar("docente1")
        r = self.post(f"/informe/{est}/enviar", {"mensaje": "Reunión el viernes"}, desde=f"/informe/{est}")
        self.assertIn("Informe enviado", r.get_data(as_text=True))
        envio = self.sql("SELECT * FROM informes_enviados WHERE destinatario_id = ?", (acu,))[0]
        self.assertIsNone(envio["leido_en"])

        self.entrar("acudiente1")
        self.assertIn("Reunión el viernes", self.c.get("/bandeja").get_data(as_text=True))
        self.c.get(f"/informe/{est}?periodo={envio['periodo_id']}&envio={envio['id']}")
        self.assertIsNotNone(self.sql("SELECT leido_en FROM informes_enviados WHERE id = ?", (envio["id"],))[0]["leido_en"])

    def test_admin_crea_usuario_y_respaldo(self):
        self.entrar("admin", CLAVE_ADMIN)
        grado = self.sql("SELECT id FROM grados LIMIT 1")[0]["id"]
        r = self.post("/admin/usuarios/nuevo", {"nombre": "Estudiante Nuevo", "usuario": "nuevo1", "rol": "estudiante",
                                                "clave": "ClaveNueva1*", "grado_id": grado, "activo": "on"})
        self.assertIn("Usuario guardado", r.get_data(as_text=True))
        self.assertEqual(self.sql("SELECT grado_id FROM estudiantes WHERE usuario_id = ?", (self.id_de("nuevo1"),))[0]["grado_id"], grado)
        r = self.post("/admin/usuarios/nuevo", {"nombre": "Repetido", "usuario": "nuevo1", "rol": "docente", "clave": "ClaveNueva1*"})
        self.assertIn("Ya existe otro usuario", r.get_data(as_text=True))
        r = self.post("/admin/usuarios/nuevo", {"nombre": "Corta", "usuario": "corta", "rol": "docente", "clave": "123"})
        self.assertIn("al menos 8", r.get_data(as_text=True))
        # Indicador del proyecto: usuarios registrados frente a la meta de 280
        self.assertIn("de 280", self.c.get("/").get_data(as_text=True))

        self.post("/admin/respaldos", {})
        self.assertEqual(len(list(Path(self.app.config["RESPALDOS"]).glob("sga_*.db"))), 1)

        # No se puede eliminar un grado con estudiantes
        r = self.post("/admin/academico", {"accion": "eliminar", "tabla": "grados", "id": grado})
        self.assertIn("No se puede eliminar", r.get_data(as_text=True))

        self.entrar("nuevo1", "ClaveNueva1*")
        self.assertEqual(self.c.get(f"/informe/{self.id_de('nuevo1')}").status_code, 200)

    def test_usuario_inactivo_no_entra(self):
        self.entrar("admin", CLAVE_ADMIN)
        uid = self.id_de("docente3")
        self.post(f"/admin/usuarios/{uid}", {"nombre": "Carmen", "usuario": "docente3"})  # sin "activo"
        r = self.entrar("docente3")
        self.assertIn("incorrectos", r.get_data(as_text=True))


if __name__ == "__main__":
    unittest.main()
