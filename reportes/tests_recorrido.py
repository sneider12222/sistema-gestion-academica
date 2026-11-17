"""Recorre todas las páginas con cada rol y detecta variables de plantilla inexistentes.

Con ``string_if_invalid`` cualquier ``{{ variable }}`` mal escrita aparece en el
HTML como ``#VARIABLE_INVALIDA#`` y la prueba lo detecta.
"""

import copy
import re
from datetime import date

from django.conf import settings
from django.test import TestCase, override_settings

from academico.models import Asignacion, Periodo
from accounts.management.commands.seed import CLAVE_ADMIN, CLAVE_PRUEBA, cargar_datos_prueba
from accounts.models import Estudiante, Usuario
from reportes.models import InformeEnviado

MARCA = "#VARIABLE_INVALIDA#"
TEMPLATES_ESTRICTAS = copy.deepcopy(settings.TEMPLATES)
TEMPLATES_ESTRICTAS[0]["OPTIONS"]["string_if_invalid"] = MARCA


@override_settings(
    TEMPLATES=TEMPLATES_ESTRICTAS,
    PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"],
)
class RecorridoCompleto(TestCase):
    @classmethod
    def setUpTestData(cls):
        cargar_datos_prueba(hoy=date(2026, 11, 14))

    def revisar(self, ruta):
        r = self.client.get(ruta)
        self.assertEqual(r.status_code, 200, ruta)
        html = r.content.decode()
        self.assertNotIn(MARCA, html, f"Variable inválida en {ruta}")
        # Las plantillas Django no deben dejar llaves sin procesar
        self.assertIsNone(re.search(r"\{\{|\{%", html), f"Etiqueta sin procesar en {ruta}")
        return html

    def entrar(self, usuario, clave=CLAVE_PRUEBA):
        self.client.logout()
        self.client.post("/entrar/", {"usuario": usuario, "clave": clave})

    def test_todas_las_paginas_de_todos_los_roles(self):
        self.revisar("/entrar/")
        periodos = list(Periodo.objects.all())
        estudiantes = list(Estudiante.objects.all())
        asignaciones = list(Asignacion.objects.all())

        # Un informe enviado para que las bandejas tengan contenido
        self.entrar("docente1")
        self.client.post(f"/informe/{estudiantes[0].pk}/enviar/", {"mensaje": "Prueba de recorrido"})

        self.entrar("admin", CLAVE_ADMIN)
        rutas = ["/", "/perfil/", "/administracion/usuarios/", "/administracion/usuarios/nuevo/",
                 "/administracion/academico/", "/administracion/respaldos/", "/estudiantes/",
                 "/informes/", "/anotaciones/", "/reportes/"]
        rutas += [f"/administracion/usuarios/{u.pk}/" for u in Usuario.objects.all()]
        rutas += [f"/informe/{e.pk}/?periodo={p.pk}" for e in estudiantes for p in periodos]
        rutas += [f"/reportes/?grado={a.grado_id}&periodo={p.pk}" for a in asignaciones for p in periodos]
        rutas += [f"/asignacion/{a.pk}/calificaciones/?periodo={p.pk}" for a in asignaciones for p in periodos]
        rutas += [f"/asignacion/{a.pk}/asistencia/" for a in asignaciones]
        for ruta in rutas:
            self.revisar(ruta)

        self.entrar("docente1")
        for ruta in ["/", "/perfil/", "/estudiantes/", "/informes/", "/anotaciones/", "/reportes/"]:
            self.revisar(ruta)

        for e in estudiantes:
            self.entrar(e.usuario.usuario)
            for p in periodos:
                self.revisar(f"/informe/{e.pk}/?periodo={p.pk}")

        envio = InformeEnviado.objects.first()
        for acudiente in Usuario.objects.filter(rol="acudiente"):
            self.entrar(acudiente.usuario)
            self.revisar("/")
            self.revisar("/estudiantes/")
            html = self.revisar("/informes/")
            if acudiente.pk == envio.destinatario_id:
                self.assertIn("Prueba de recorrido", html)
                self.revisar(f"/informe/{envio.estudiante_id}/?periodo={envio.periodo_id}&envio={envio.pk}")
