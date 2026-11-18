"""Reglas puras de calificaciones: sin ORM, sin estado, testeables de a una.

Porta ``definitiva`` de ``sga/servicios.py``. En esta fase solo esa función:
``porcentaje_total`` y ``validar_porcentaje`` llegarán con sus propios tests.
"""


def definitiva(pares):
    """Promedio ponderado de ``(nota, porcentaje)`` sobre lo ya calificado.

    ``nota`` puede ser ``None`` (actividad sin calificar) y puede venir como
    ``float``, ``int`` o ``Decimal``; la salida es ``float`` o ``None``.
    El peso se acumula solo de los pares calificados, así que una actividad
    pendiente no hunde el promedio. Si nada está calificado —o el peso total es
    cero— devuelve ``None``: nunca divide por cero.

    Una sola pasada: acepta cualquier iterable, generadores incluidos.
    """
    peso = 0.0
    acumulado = 0.0
    for nota, porcentaje in pares:
        if nota is None:
            continue
        # float() normaliza Decimal e int: Decimal * float y Decimal + float
        # revientan en Python, y las notas del modelo son Decimal.
        p = float(porcentaje)
        peso += p
        acumulado += float(nota) * p
    if not peso:
        return None
    # El epsilon corrige la representación binaria: sin él hay promedios que
    # caen una décima por debajo del valor decimal esperado.
    return round(acumulado / peso + 1e-9, 1)
