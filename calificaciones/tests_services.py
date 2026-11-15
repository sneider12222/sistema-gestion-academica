"""Tests de la capa de servicios de calificaciones.

Cobertura mínima TDD para funciones puras que se portarán desde sga/servicios.py.
"""
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone


class TestDefinitiva(TestCase):
    """Promedio ponderado SOLO sobre lo calificado."""

    def test_definitiva_lista_vacia(self):
        from calificaciones.services import definitiva
        self.assertIsNone(definitiva([]))

    def test_definitiva_todos_none(self):
        from calificaciones.services import definitiva
        self.assertIsNone(definitiva([(None, 30), (None, 70)]))

    def test_definitiva_un_par(self):
        from calificaciones.services import definitiva
        # 10 * 0.4 = 4.0 / 0.4 = 10.0, pero redondeo a 1 decimal con 1e-9
        self.assertEqual(definitiva([(10.0, 0.4)]), 10.0)

    def test_definitiva_dos_pares(self):
        from calificaciones.services import definitiva
        # (10*0.4 + 8*0.6) / (0.4+0.6) = (4+4.8)/1.0 = 8.8 → round(8.8+1e-9, 1) = 8.8
        self.assertEqual(definitiva([(10.0, 0.4), (8.0, 0.6)]), 8.8)

    def test_definitiva_mixto_con_none(self):
        from calificaciones.services import definitiva
        # Solo la nota 7 cuenta, la None se ignora en el peso y el numerador
        # (7*0.5) / 0.5 = 7.0, round(7.0+1e-9, 1) = 7.0
        self.assertEqual(definitiva([(7.0, 0.5), (None, 0.5)]), 7.0)

    def test_definitiva_redondeo_tres_cuarte(self):
        from calificaciones.services import definitiva
        # 4.95 → round(4.95+1e-9, 1) → 5.0 por el epsilon
        # 4.44 → 4.4; 4.45 → 4.5
        self.assertEqual(definitiva([(4.0, 0.5), (5.0, 0.5)]), 4.5)

    def test_definitiva_sin_calificados(self):
        from calificaciones.services import definitiva
        # Si todas las notas son None, peso 0 → None
        self.assertIsNone(definitiva([(None, 0.3), (None, 0.7)]))