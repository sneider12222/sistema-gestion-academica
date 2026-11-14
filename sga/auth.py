"""Autenticación y control de acceso por rol."""
from functools import wraps

from flask import (Blueprint, abort, flash, g, redirect, render_template,
                   request, session, url_for)
from werkzeug.security import check_password_hash, generate_password_hash

from .db import consulta, ejecutar, uno

bp = Blueprint("auth", __name__)

CLAVE_MINIMA = 8


@bp.before_app_request
def cargar_usuario():
    g.usuario = None
    uid = session.get("uid")
    if uid is not None:
        g.usuario = uno("SELECT * FROM usuarios WHERE id = ? AND activo = 1", (uid,))
        if g.usuario is None:
            session.clear()


def login_requerido(vista):
    @wraps(vista)
    def envoltura(*args, **kwargs):
        if g.usuario is None:
            return redirect(url_for("auth.login"))
        return vista(*args, **kwargs)
    return envoltura


def rol_requerido(*roles):
    def decorador(vista):
        @wraps(vista)
        def envoltura(*args, **kwargs):
            if g.usuario is None:
                return redirect(url_for("auth.login"))
            if g.usuario["rol"] not in roles:
                abort(403)
            return vista(*args, **kwargs)
        return envoltura
    return decorador


@bp.route("/login", methods=["GET", "POST"])
def login():
    if g.usuario:
        return redirect(url_for("auth.inicio"))
    if request.method == "POST":
        nombre = request.form.get("usuario", "").strip().lower()
        fila = uno("SELECT * FROM usuarios WHERE usuario = ?", (nombre,))
        if fila and fila["activo"] and check_password_hash(fila["clave_hash"], request.form.get("clave", "")):
            session.clear()
            session.permanent = True
            session["uid"] = fila["id"]
            return redirect(url_for("auth.inicio"))
        flash("Usuario o contraseña incorrectos.", "error")
    return render_template("login.html")


@bp.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return redirect(url_for("auth.login"))


@bp.route("/")
@login_requerido
def inicio():
    from .servicios import META_USUARIOS, estudiantes_visibles
    u = g.usuario
    datos = {}
    if u["rol"] == "estudiante":
        return redirect(url_for("consulta.informe", estudiante_id=u["id"]))
    if u["rol"] == "administrador":
        datos["por_rol"] = {f["rol"]: f["n"] for f in consulta(
            "SELECT rol, COUNT(*) n FROM usuarios WHERE activo = 1 GROUP BY rol")}
        datos["total"] = sum(datos["por_rol"].values())
        datos["meta"] = META_USUARIOS
        datos["grados"] = uno("SELECT COUNT(*) n FROM grados")["n"]
        datos["asignaturas"] = uno("SELECT COUNT(*) n FROM asignaturas")["n"]
        datos["enviados"] = uno("SELECT COUNT(*) n FROM informes_enviados")["n"]
    elif u["rol"] == "docente":
        datos["asignaciones"] = consulta(
            """SELECT a.id, s.nombre asignatura, gr.nombre grado,
                      (SELECT COUNT(*) FROM estudiantes e JOIN usuarios us ON us.id = e.usuario_id
                        WHERE e.grado_id = a.grado_id AND us.activo = 1) estudiantes
                 FROM asignaciones a
                 JOIN asignaturas s ON s.id = a.asignatura_id
                 JOIN grados gr ON gr.id = a.grado_id
                WHERE a.docente_id = ? ORDER BY gr.nombre, s.nombre""", (u["id"],))
    elif u["rol"] == "acudiente":
        datos["acudidos"] = estudiantes_visibles(u)
        datos["sin_leer"] = uno(
            "SELECT COUNT(*) n FROM informes_enviados WHERE destinatario_id = ? AND leido_en IS NULL",
            (u["id"],))["n"]
    return render_template("inicio.html", **datos)


@bp.route("/perfil", methods=["GET", "POST"])
@login_requerido
def perfil():
    if request.method == "POST":
        actual = request.form.get("actual", "")
        nueva = request.form.get("nueva", "")
        if not check_password_hash(g.usuario["clave_hash"], actual):
            flash("La contraseña actual no es correcta.", "error")
        elif len(nueva) < CLAVE_MINIMA:
            flash(f"La nueva contraseña debe tener al menos {CLAVE_MINIMA} caracteres.", "error")
        elif nueva != request.form.get("confirmar", ""):
            flash("La confirmación no coincide con la nueva contraseña.", "error")
        else:
            ejecutar("UPDATE usuarios SET clave_hash = ? WHERE id = ?",
                     (generate_password_hash(nueva), g.usuario["id"]))
            flash("Contraseña actualizada.", "ok")
            return redirect(url_for("auth.perfil"))
    return render_template("perfil.html")
