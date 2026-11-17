"""Tests de la capa de servicios de calificaciones.

Cobertura mínima TDD para funciones puras portadas desde sga/servicios.py.
"""
from django.test import TestCase


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

    def test_definitiva_redondeo_mitad_sube(self):
        from calificaciones.services import definitiva
        # (4.0+5.0)/2 = 4.5 exacto. Este test NO prueba el epsilon: da 4.5 con
        # y sin él. Prueba que dos notas con el mismo peso dan su media simple.
        self.assertEqual(definitiva([(4.0, 0.5), (5.0, 0.5)]), 4.5)

    def test_definitiva_epsilon_medio_punto(self):
        from calificaciones.services import definitiva
        # (1.0*25 + 2.4*75) / 100 = 2.05, pero en binario da 2.049999999...:
        # round() a secas cae a 2.0 y hunde la nota una décima injustamente.
        # Con el epsilon redondea a 2.1 (mitad hacia arriba, como el legacy).
        self.assertEqual(definitiva([(1.0, 25), (2.4, 75)]), 2.1)

    def test_definitiva_epsilon_otro_medio_punto(self):
        from calificaciones.services import definitiva
        # (1.1+1.2)/2 = 1.15 → 1.1 sin epsilon, 1.2 con epsilon. Es el caso
        # gemelo del anterior con otra fracción: el epsilon no es un parche
        # de un solo valor.
        self.assertEqual(definitiva([(1.1, 50), (1.2, 50)]), 1.2)

    def test_definitiva_sin_calificados(self):
        from calificaciones.services import definitiva
        # Si todas las notas son None, peso 0 → None
        self.assertIsNone(definitiva([(None, 0.3), (None, 0.7)]))