"""Acceso a la base de datos SQLite, inicialización y respaldos."""
import sqlite3
from datetime import datetime
from pathlib import Path

from flask import current_app, g


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(current_app.config["DATABASE"])
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


def cerrar_db(_exc=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def consulta(sql, params=()):
    return get_db().execute(sql, params).fetchall()


def uno(sql, params=()):
    return get_db().execute(sql, params).fetchone()


def ejecutar(sql, params=()):
    db = get_db()
    cur = db.execute(sql, params)
    db.commit()
    return cur


def init_db(app, con_datos_prueba=True):
    """Crea la base de datos desde cero (borra la existente)."""
    ruta = Path(app.config["DATABASE"])
    ruta.parent.mkdir(parents=True, exist_ok=True)
    if ruta.exists():
        ruta.unlink()
    con = sqlite3.connect(ruta)
    con.execute("PRAGMA foreign_keys = ON")
    con.executescript((Path(__file__).parent / "schema.sql").read_text(encoding="utf-8"))
    from .seed import cargar_datos_prueba, crear_admin_inicial
    if con_datos_prueba:
        cargar_datos_prueba(con)
    else:
        crear_admin_inicial(con)
    con.commit()
    con.close()


def respaldar(app):
    """Copia segura de la base de datos en la carpeta de respaldos."""
    carpeta = Path(app.config["RESPALDOS"])
    carpeta.mkdir(parents=True, exist_ok=True)
    destino = carpeta / f"sga_{datetime.now():%Y%m%d_%H%M%S}.db"
    origen = sqlite3.connect(app.config["DATABASE"])
    copia = sqlite3.connect(destino)
    with copia:
        origen.backup(copia)
    copia.close()
    origen.close()
    return destino
