"""Punto de entrada del Sistema de Gestión Académica (entorno local).

Uso:
    py app.py                  Inicia el servidor en http://127.0.0.1:5000
    py app.py --reiniciar      Borra la base de datos y la recrea con datos de prueba
    py app.py --vacio          Borra la base de datos y la recrea solo con el administrador
"""
import sys

from sga import create_app
from sga.db import init_db

app = create_app()

if __name__ == "__main__":
    if "--reiniciar" in sys.argv or "--vacio" in sys.argv:
        init_db(app, con_datos_prueba="--vacio" not in sys.argv)
        print("Base de datos recreada.")
        sys.exit(0)
    app.run(host="127.0.0.1", port=5000, debug=False)
