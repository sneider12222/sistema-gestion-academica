"""Sistema de Gestión de Calificaciones, Asistencia e Informes Académicos."""
import secrets
from datetime import timedelta
from pathlib import Path

from flask import Flask, abort, render_template, request, session

from . import db as base


def create_app(instance_path=None):
    app = Flask(__name__, instance_path=instance_path)
    instancia = Path(app.instance_path)
    instancia.mkdir(parents=True, exist_ok=True)

    # La clave de sesión se genera una sola vez y se guarda fuera del código
    ruta_clave = instancia / "secret_key"
    if not ruta_clave.exists():
        ruta_clave.write_text(secrets.token_hex(32))

    app.config.update(
        SECRET_KEY=ruta_clave.read_text().strip(),
        DATABASE=str(instancia / "sga.db"),
        RESPALDOS=str(instancia / "respaldos"),
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        PERMANENT_SESSION_LIFETIME=timedelta(hours=2),
    )

    if not Path(app.config["DATABASE"]).exists():
        base.init_db(app, con_datos_prueba=True)

    app.teardown_appcontext(base.cerrar_db)

    from . import admin, auth, consulta, docente, servicios
    app.register_blueprint(auth.bp)
    app.register_blueprint(admin.bp)
    app.register_blueprint(docente.bp)
    app.register_blueprint(consulta.bp)

    @app.before_request
    def proteger_csrf():
        if request.method == "POST":
            token = session.get("csrf")
            if not token or not secrets.compare_digest(token, request.form.get("csrf_token", "")):
                abort(400, "Token de seguridad inválido. Recargue la página e intente de nuevo.")

    def csrf_token():
        if "csrf" not in session:
            session["csrf"] = secrets.token_hex(16)
        return session["csrf"]

    @app.context_processor
    def variables_globales():
        prueba = base.uno("SELECT valor FROM config WHERE clave = 'datos_prueba'")
        return {
            "csrf_token": csrf_token,
            "datos_prueba": bool(prueba and prueba["valor"] == "1"),
            "ESTADOS": servicios.ESTADOS,
            "INSTITUCION": servicios.INSTITUCION,
            "DIRECCION": servicios.DIRECCION,
        }

    @app.template_filter("nota")
    def filtro_nota(valor):
        return "—" if valor is None else f"{valor:.1f}"

    @app.errorhandler(400)
    @app.errorhandler(403)
    @app.errorhandler(404)
    def error(e):
        mensajes = {
            400: "La solicitud no es válida.",
            403: "No tiene permiso para acceder a esta sección.",
            404: "La página solicitada no existe.",
        }
        detalle = e.description if e.code == 400 and e.description else mensajes[e.code]
        return render_template("error.html", codigo=e.code, mensaje=detalle), e.code

    return app
