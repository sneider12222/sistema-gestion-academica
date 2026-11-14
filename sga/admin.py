"""Administración: usuarios, estructura académica y respaldos."""
import sqlite3
from datetime import date, datetime
from pathlib import Path

from flask import (Blueprint, abort, current_app, flash, g, redirect,
                   render_template, request, url_for)
from werkzeug.security import generate_password_hash

from .auth import CLAVE_MINIMA, rol_requerido
from .db import consulta, ejecutar, get_db, respaldar, uno

bp = Blueprint("admin", __name__, url_prefix="/admin")

ROLES = ["administrador", "docente", "estudiante", "acudiente"]


# ---------------------------------------------------------------- usuarios

@bp.route("/usuarios")
@rol_requerido("administrador")
def usuarios():
    rol = request.args.get("rol", "")
    buscar = request.args.get("q", "").strip()
    sql = """SELECT u.*, gr.nombre grado FROM usuarios u
               LEFT JOIN estudiantes e ON e.usuario_id = u.id
               LEFT JOIN grados gr ON gr.id = e.grado_id WHERE 1 = 1"""
    params = []
    if rol in ROLES:
        sql += " AND u.rol = ?"
        params.append(rol)
    if buscar:
        sql += " AND (u.nombre LIKE ? OR u.usuario LIKE ? OR u.documento LIKE ?)"
        params += [f"%{buscar}%"] * 3
    return render_template("usuarios.html", usuarios=consulta(sql + " ORDER BY u.rol, u.nombre", params),
                           roles=ROLES, rol=rol, buscar=buscar)


@bp.route("/usuarios/nuevo", methods=["GET", "POST"])
@bp.route("/usuarios/<int:uid>", methods=["GET", "POST"])
@rol_requerido("administrador")
def usuario_form(uid=None):
    u = None
    if uid is not None:
        u = uno("""SELECT u.*, e.grado_id FROM usuarios u
                     LEFT JOIN estudiantes e ON e.usuario_id = u.id WHERE u.id = ?""", (uid,))
        if u is None:
            abort(404)
    acudidos = {f["estudiante_id"] for f in consulta(
        "SELECT estudiante_id FROM acudientes_estudiantes WHERE acudiente_id = ?", (uid,))} if uid else set()

    if request.method == "POST":
        f = request.form
        nombre = f.get("nombre", "").strip()
        usuario = f.get("usuario", "").strip().lower()
        documento = f.get("documento", "").strip() or None
        email = f.get("email", "").strip() or None
        rol = u["rol"] if u else f.get("rol", "")  # el rol no cambia después de creado
        clave = f.get("clave", "")
        activo = 1 if (f.get("activo") or (u and u["id"] == g.usuario["id"])) else 0
        errores = []
        if not nombre or not usuario:
            errores.append("El nombre y el usuario son obligatorios.")
        if rol not in ROLES:
            errores.append("Seleccione un rol válido.")
        if (u is None or clave) and len(clave) < CLAVE_MINIMA:
            errores.append(f"La contraseña debe tener al menos {CLAVE_MINIMA} caracteres.")
        if errores:
            for e in errores:
                flash(e, "error")
        else:
            db = get_db()
            try:
                if u is None:
                    uid = db.execute(
                        """INSERT INTO usuarios (nombre, documento, email, usuario, clave_hash, rol, activo)
                           VALUES (?, ?, ?, ?, ?, ?, ?)""",
                        (nombre, documento, email, usuario, generate_password_hash(clave), rol, activo)).lastrowid
                else:
                    db.execute("UPDATE usuarios SET nombre = ?, documento = ?, email = ?, usuario = ?, activo = ? WHERE id = ?",
                               (nombre, documento, email, usuario, activo, uid))
                    if clave:
                        db.execute("UPDATE usuarios SET clave_hash = ? WHERE id = ?",
                                   (generate_password_hash(clave), uid))
                if rol == "estudiante":
                    grado = f.get("grado_id", type=int)
                    db.execute("""INSERT INTO estudiantes (usuario_id, grado_id) VALUES (?, ?)
                                  ON CONFLICT (usuario_id) DO UPDATE SET grado_id = excluded.grado_id""",
                               (uid, grado))
                if rol == "acudiente":
                    db.execute("DELETE FROM acudientes_estudiantes WHERE acudiente_id = ?", (uid,))
                    db.executemany("INSERT INTO acudientes_estudiantes VALUES (?, ?)",
                                   [(uid, e) for e in f.getlist("acudidos", type=int)])
                db.commit()
                flash("Usuario guardado.", "ok")
                return redirect(url_for("admin.usuarios", rol=rol))
            except sqlite3.IntegrityError:
                db.rollback()
                flash("Ya existe otro usuario con ese nombre de usuario o documento.", "error")

    return render_template(
        "usuario_form.html", u=u, roles=ROLES, acudidos=acudidos, form=request.form,
        grados=consulta("SELECT * FROM grados ORDER BY nombre"),
        estudiantes=consulta("""SELECT u.id, u.nombre, gr.nombre grado FROM estudiantes e
                                  JOIN usuarios u ON u.id = e.usuario_id
                                  LEFT JOIN grados gr ON gr.id = e.grado_id
                                 ORDER BY gr.nombre, u.nombre"""))


# ------------------------------------------------------ estructura académica

_TABLAS_BORRABLES = {"grados", "asignaturas", "periodos", "asignaciones"}


def _fecha(texto):
    try:
        return date.fromisoformat(texto or "").isoformat()
    except ValueError:
        return None


@bp.route("/academico", methods=["GET", "POST"])
@rol_requerido("administrador")
def academico():
    if request.method == "POST":
        f = request.form
        accion = f.get("accion")
        try:
            if accion in ("grado", "asignatura"):
                nombre = f.get("nombre", "").strip()
                if not nombre:
                    flash("Escriba un nombre.", "error")
                else:
                    ejecutar(f"INSERT INTO {accion}s (nombre) VALUES (?)", (nombre,))
                    flash("Registro creado.", "ok")
            elif accion == "periodo":
                nombre, ini, fin = f.get("nombre", "").strip(), _fecha(f.get("fecha_inicio")), _fecha(f.get("fecha_fin"))
                if not (nombre and ini and fin) or ini > fin:
                    flash("Complete el nombre y un rango de fechas válido.", "error")
                else:
                    ejecutar("INSERT INTO periodos (nombre, fecha_inicio, fecha_fin) VALUES (?, ?, ?)", (nombre, ini, fin))
                    flash("Periodo creado.", "ok")
            elif accion == "asignacion":
                docente = uno("SELECT id FROM usuarios WHERE id = ? AND rol = 'docente'", (f.get("docente_id", type=int),))
                asignatura, grado = f.get("asignatura_id", type=int), f.get("grado_id", type=int)
                if not (docente and asignatura and grado):
                    flash("Seleccione docente, asignatura y grado.", "error")
                else:
                    ejecutar("""INSERT INTO asignaciones (docente_id, asignatura_id, grado_id) VALUES (?, ?, ?)
                                ON CONFLICT (asignatura_id, grado_id) DO UPDATE SET docente_id = excluded.docente_id""",
                             (docente["id"], asignatura, grado))
                    flash("Asignación guardada.", "ok")
            elif accion == "eliminar" and f.get("tabla") in _TABLAS_BORRABLES:
                ejecutar(f"DELETE FROM {f['tabla']} WHERE id = ?", (f.get("id", type=int),))
                flash("Registro eliminado.", "ok")
        except sqlite3.IntegrityError:
            get_db().rollback()
            if accion == "eliminar":
                flash("No se puede eliminar: tiene registros académicos asociados.", "error")
            else:
                flash("Ya existe un registro con ese nombre.", "error")
        return redirect(url_for("admin.academico"))

    return render_template(
        "academico.html",
        grados=consulta("""SELECT gr.*, (SELECT COUNT(*) FROM estudiantes e WHERE e.grado_id = gr.id) estudiantes
                             FROM grados gr ORDER BY nombre"""),
        asignaturas=consulta("SELECT * FROM asignaturas ORDER BY nombre"),
        periodos=consulta("SELECT * FROM periodos ORDER BY fecha_inicio"),
        docentes=consulta("SELECT id, nombre FROM usuarios WHERE rol = 'docente' AND activo = 1 ORDER BY nombre"),
        asignaciones=consulta("""SELECT a.id, s.nombre asignatura, gr.nombre grado, u.nombre docente
                                   FROM asignaciones a
                                   JOIN asignaturas s ON s.id = a.asignatura_id
                                   JOIN grados gr ON gr.id = a.grado_id
                                   JOIN usuarios u ON u.id = a.docente_id
                                  ORDER BY gr.nombre, s.nombre"""))


# --------------------------------------------------------------- respaldos

@bp.route("/respaldos", methods=["GET", "POST"])
@rol_requerido("administrador")
def respaldos():
    if request.method == "POST":
        archivo = respaldar(current_app)
        flash(f"Respaldo creado: {archivo.name}", "ok")
        return redirect(url_for("admin.respaldos"))
    carpeta = Path(current_app.config["RESPALDOS"])
    archivos = [{"nombre": p.name, "kb": round(p.stat().st_size / 1024),
                 "fecha": datetime.fromtimestamp(p.stat().st_mtime).strftime("%Y-%m-%d %H:%M")}
                for p in sorted(carpeta.glob("sga_*.db"), reverse=True)] if carpeta.exists() else []
    return render_template("respaldos.html", archivos=archivos, carpeta=carpeta)
