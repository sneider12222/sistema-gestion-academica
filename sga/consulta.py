"""Consulta y envío de informes académicos (solo lectura para estudiantes y acudientes)."""
from flask import (Blueprint, abort, flash, g, redirect,
                   render_template, request, url_for)

from .auth import login_requerido, rol_requerido
from .db import consulta, ejecutar, get_db, uno
from .servicios import (construir_informe, estudiantes_visibles,
                        grados_visibles, periodo_seleccionado, periodos, puede_ver)

bp = Blueprint("consulta", __name__)


@bp.route("/estudiantes")
@rol_requerido("administrador", "docente", "acudiente")
def estudiantes():
    return render_template("estudiantes.html", estudiantes=estudiantes_visibles(g.usuario))


@bp.route("/informe/<int:estudiante_id>")
@login_requerido
def informe(estudiante_id):
    if not puede_ver(g.usuario, estudiante_id):
        abort(403)
    periodo = periodo_seleccionado(request.args.get("periodo", type=int))
    datos = construir_informe(estudiante_id, periodo)
    if datos is None:
        flash("Aún no hay periodos académicos creados.", "error")
        return render_template("error.html", codigo="", mensaje="No hay información académica para mostrar todavía.")

    # Al abrirlo desde la bandeja, el destinatario lo marca como leído
    envio = request.args.get("envio", type=int)
    if envio:
        ejecutar("""UPDATE informes_enviados SET leido_en = datetime('now', 'localtime')
                     WHERE id = ? AND destinatario_id = ? AND leido_en IS NULL""", (envio, g.usuario["id"]))

    acudientes = consulta(
        """SELECT u.id, u.nombre, u.email FROM acudientes_estudiantes ae
             JOIN usuarios u ON u.id = ae.acudiente_id
            WHERE ae.estudiante_id = ? AND u.activo = 1 ORDER BY u.nombre""", (estudiante_id,))
    return render_template("informe.html", inf=datos, periodos=periodos(), acudientes=acudientes,
                           puede_enviar=g.usuario["rol"] in ("administrador", "docente"))


@bp.route("/informe/<int:estudiante_id>/enviar", methods=["POST"])
@rol_requerido("administrador", "docente")
def enviar(estudiante_id):
    if not puede_ver(g.usuario, estudiante_id):
        abort(403)
    periodo = periodo_seleccionado(request.form.get("periodo", type=int))
    datos = construir_informe(estudiante_id, periodo)
    if datos is None:
        abort(404)
    mensaje = request.form.get("mensaje", "").strip() or None
    acudientes = consulta(
        """SELECT u.id, u.nombre, u.email FROM acudientes_estudiantes ae
             JOIN usuarios u ON u.id = ae.acudiente_id
            WHERE ae.estudiante_id = ? AND u.activo = 1""", (estudiante_id,))
    if not acudientes:
        flash("El estudiante no tiene acudientes vinculados. Pida al administrador que los registre.", "error")
    else:
        db = get_db()
        for ac in acudientes:
            db.execute("""INSERT INTO informes_enviados
                          (estudiante_id, periodo_id, remitente_id, destinatario_id, mensaje)
                          VALUES (?, ?, ?, ?, ?)""",
                       (estudiante_id, periodo["id"], g.usuario["id"], ac["id"], mensaje))
        db.commit()
        nombres = ", ".join(ac["nombre"] for ac in acudientes)
        flash(f"Informe enviado a: {nombres}.", "ok")
    return redirect(url_for("consulta.informe", estudiante_id=estudiante_id, periodo=periodo["id"]))


@bp.route("/bandeja")
@rol_requerido("administrador", "docente", "acudiente")
def bandeja():
    sql = """SELECT i.*, e.nombre estudiante, p.nombre periodo, r.nombre remitente, d.nombre destinatario
               FROM informes_enviados i
               JOIN usuarios e ON e.id = i.estudiante_id
               JOIN periodos p ON p.id = i.periodo_id
               JOIN usuarios r ON r.id = i.remitente_id
               JOIN usuarios d ON d.id = i.destinatario_id {filtro}
              ORDER BY i.enviado_en DESC, i.id DESC LIMIT 300"""
    rol = g.usuario["rol"]
    if rol == "administrador":
        lista = consulta(sql.format(filtro=""))
    elif rol == "docente":
        lista = consulta(sql.format(filtro="WHERE i.remitente_id = ?"), (g.usuario["id"],))
    else:
        lista = consulta(sql.format(filtro="WHERE i.destinatario_id = ?"), (g.usuario["id"],))
    return render_template("bandeja.html", informes=lista, recibidos=(rol == "acudiente"))


@bp.route("/reportes")
@rol_requerido("administrador", "docente")
def reportes():
    grados = grados_visibles(g.usuario)
    periodo = periodo_seleccionado(request.args.get("periodo", type=int))
    grado_id = request.args.get("grado", type=int) or (grados[0]["id"] if grados else None)
    grado = next((x for x in grados if x["id"] == grado_id), None)
    if grado_id and grado is None:
        abort(403)

    filas, asignaturas = [], []
    if grado and periodo:
        asignaturas = [f["nombre"] for f in consulta(
            """SELECT s.nombre FROM asignaciones a JOIN asignaturas s ON s.id = a.asignatura_id
                WHERE a.grado_id = ? ORDER BY s.nombre""", (grado_id,))]
        for e in consulta("""SELECT u.id FROM estudiantes e JOIN usuarios u ON u.id = e.usuario_id
                              WHERE e.grado_id = ? AND u.activo = 1 ORDER BY u.nombre""", (grado_id,)):
            filas.append(construir_informe(e["id"], periodo))

    return render_template("reporte_grado.html", grados=grados, grado=grado, periodo=periodo,
                           periodos=periodos(), asignaturas=asignaturas, filas=filas)
