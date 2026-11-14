"""Registro docente: calificaciones, asistencia y anotaciones."""
from datetime import date

from flask import (Blueprint, abort, flash, g, redirect, render_template,
                   request, url_for)

from .auth import rol_requerido
from .db import consulta, ejecutar, get_db, uno
from .servicios import (ESTADOS, NOTA_MAX, NOTA_MIN, definitiva,
                        estudiantes_visibles, periodo_seleccionado,
                        periodos, puede_ver)

bp = Blueprint("docente", __name__, url_prefix="/docente")


def _asignacion(aid):
    """La asignación pedida, solo si pertenece al docente (el administrador ve todas)."""
    a = uno("""SELECT a.*, s.nombre asignatura, gr.nombre grado, u.nombre docente
                 FROM asignaciones a
                 JOIN asignaturas s ON s.id = a.asignatura_id
                 JOIN grados gr ON gr.id = a.grado_id
                 JOIN usuarios u ON u.id = a.docente_id
                WHERE a.id = ?""", (aid,))
    if a is None:
        abort(404)
    if g.usuario["rol"] == "docente" and a["docente_id"] != g.usuario["id"]:
        abort(403)
    return a


def _estudiantes(grado_id):
    return consulta("""SELECT u.id, u.nombre FROM estudiantes e JOIN usuarios u ON u.id = e.usuario_id
                        WHERE e.grado_id = ? AND u.activo = 1 ORDER BY u.nombre""", (grado_id,))


def _fecha(texto):
    try:
        return date.fromisoformat(texto or "").isoformat()
    except ValueError:
        return None


# ------------------------------------------------------------ calificaciones

@bp.route("/asignacion/<int:aid>/calificaciones", methods=["GET", "POST"])
@rol_requerido("docente", "administrador")
def calificaciones(aid):
    a = _asignacion(aid)
    periodo = periodo_seleccionado(request.values.get("periodo", type=int))
    if periodo is None:
        flash("Aún no hay periodos académicos creados.", "error")
        return redirect(url_for("auth.inicio"))
    estudiantes = _estudiantes(a["grado_id"])
    aqui = url_for("docente.calificaciones", aid=aid, periodo=periodo["id"])

    def actividades():
        return consulta("SELECT * FROM actividades WHERE asignacion_id = ? AND periodo_id = ? ORDER BY fecha, id",
                        (aid, periodo["id"]))

    if request.method == "POST":
        f = request.form
        accion = f.get("accion")
        if accion == "crear_actividad":
            nombre, fecha = f.get("nombre", "").strip(), _fecha(f.get("fecha"))
            pct = f.get("porcentaje", type=float)
            if not nombre or not fecha or pct is None or not 0 < pct <= 100:
                flash("Complete nombre, fecha y un porcentaje entre 1 y 100.", "error")
            else:
                ejecutar("INSERT INTO actividades (asignacion_id, periodo_id, nombre, porcentaje, fecha) VALUES (?, ?, ?, ?, ?)",
                         (aid, periodo["id"], nombre, pct, fecha))
                flash("Actividad creada.", "ok")
        elif accion == "eliminar_actividad":
            ejecutar("DELETE FROM actividades WHERE id = ? AND asignacion_id = ?", (f.get("actividad_id", type=int), aid))
            flash("Actividad eliminada junto con sus notas.", "ok")
        elif accion == "guardar_notas":
            db = get_db()
            guardadas, invalidas = 0, 0
            for act in actividades():
                for e in estudiantes:
                    texto = f.get(f"nota_{act['id']}_{e['id']}", "").strip().replace(",", ".")
                    if not texto:
                        db.execute("DELETE FROM calificaciones WHERE actividad_id = ? AND estudiante_id = ?", (act["id"], e["id"]))
                        continue
                    try:
                        nota = round(float(texto), 1)
                    except ValueError:
                        nota = None
                    if nota is None or not NOTA_MIN <= nota <= NOTA_MAX:
                        invalidas += 1
                        continue
                    db.execute("""INSERT INTO calificaciones (actividad_id, estudiante_id, nota) VALUES (?, ?, ?)
                                  ON CONFLICT (actividad_id, estudiante_id)
                                  DO UPDATE SET nota = excluded.nota, registrado_en = CURRENT_TIMESTAMP
                                  WHERE calificaciones.nota <> excluded.nota""", (act["id"], e["id"], nota))
                    guardadas += 1
            db.commit()
            flash(f"Notas guardadas ({guardadas}).", "ok")
            if invalidas:
                flash(f"{invalidas} valor(es) no se guardaron: la nota debe estar entre {NOTA_MIN:.1f} y {NOTA_MAX:.1f}.", "error")
        return redirect(aqui)

    acts = actividades()
    notas = {(n["actividad_id"], n["estudiante_id"]): n["nota"] for n in consulta(
        """SELECT c.* FROM calificaciones c JOIN actividades act ON act.id = c.actividad_id
            WHERE act.asignacion_id = ? AND act.periodo_id = ?""", (aid, periodo["id"]))}
    definitivas = {e["id"]: definitiva([(notas.get((x["id"], e["id"])), x["porcentaje"]) for x in acts])
                   for e in estudiantes}
    return render_template("calificaciones.html", a=a, periodo=periodo, periodos=periodos(),
                           estudiantes=estudiantes, actividades=acts, notas=notas, definitivas=definitivas,
                           suma_pct=sum(x["porcentaje"] for x in acts), hoy=date.today().isoformat())


# ---------------------------------------------------------------- asistencia

@bp.route("/asignacion/<int:aid>/asistencia", methods=["GET", "POST"])
@rol_requerido("docente", "administrador")
def asistencia(aid):
    a = _asignacion(aid)
    hoy = date.today().isoformat()
    fecha = _fecha(request.values.get("fecha")) or hoy
    estudiantes = _estudiantes(a["grado_id"])

    if request.method == "POST":
        if fecha > hoy:
            flash("No se puede registrar asistencia en una fecha futura.", "error")
        else:
            db = get_db()
            for e in estudiantes:
                estado = request.form.get(f"estado_{e['id']}", "P")
                if estado not in ESTADOS:
                    estado = "P"
                db.execute("""INSERT INTO asistencias (asignacion_id, estudiante_id, fecha, estado)
                              VALUES (?, ?, ?, ?)
                              ON CONFLICT (asignacion_id, estudiante_id, fecha)
                              DO UPDATE SET estado = excluded.estado""",
                           (aid, e["id"], fecha, estado))
            db.commit()
            flash(f"Asistencia del {fecha} guardada.", "ok")
        return redirect(url_for("docente.asistencia", aid=aid, fecha=fecha))

    registro = {r["estudiante_id"]: r for r in consulta(
        "SELECT * FROM asistencias WHERE asignacion_id = ? AND fecha = ?", (aid, fecha))}
    historial = consulta(
        """SELECT fecha, SUM(estado = 'P') p, SUM(estado = 'A') a
             FROM asistencias WHERE asignacion_id = ? GROUP BY fecha ORDER BY fecha DESC LIMIT 15""", (aid,))
    return render_template("asistencia.html", a=a, fecha=fecha, hoy=hoy, estudiantes=estudiantes,
                           registro=registro, historial=historial)


# --------------------------------------------------------------- anotaciones

@bp.route("/anotaciones", methods=["GET", "POST"])
@rol_requerido("docente", "administrador")
def anotaciones():
    hoy = date.today().isoformat()
    if request.method == "POST":
        f = request.form
        if f.get("accion") == "eliminar":
            nid = f.get("id", type=int)
            if g.usuario["rol"] == "administrador":
                ejecutar("DELETE FROM anotaciones WHERE id = ?", (nid,))
            else:
                ejecutar("DELETE FROM anotaciones WHERE id = ? AND autor_id = ?", (nid, g.usuario["id"]))
            flash("Anotación eliminada.", "ok")
        else:
            est = f.get("estudiante_id", type=int)
            texto = f.get("descripcion", "").strip()
            fecha = _fecha(f.get("fecha")) or hoy
            if est is None or not puede_ver(g.usuario, est):
                flash("Seleccione un estudiante de sus grados.", "error")
            elif not texto:
                flash("Escriba la anotación.", "error")
            elif fecha > hoy:
                flash("La fecha no puede ser futura.", "error")
            else:
                ejecutar("INSERT INTO anotaciones (estudiante_id, autor_id, descripcion, fecha) VALUES (?, ?, ?, ?)",
                         (est, g.usuario["id"], texto, fecha))
                flash("Anotación registrada.", "ok")
        return redirect(url_for("docente.anotaciones"))

    sql = """SELECT n.*, e.nombre estudiante, gr.nombre grado, u.nombre autor
               FROM anotaciones n
               JOIN usuarios e ON e.id = n.estudiante_id
               JOIN estudiantes es ON es.usuario_id = n.estudiante_id
               LEFT JOIN grados gr ON gr.id = es.grado_id
               JOIN usuarios u ON u.id = n.autor_id {filtro}
              ORDER BY n.fecha DESC, n.id DESC LIMIT 200"""
    if g.usuario["rol"] == "administrador":
        lista = consulta(sql.format(filtro=""))
    else:
        lista = consulta(sql.format(filtro="WHERE n.autor_id = ?"), (g.usuario["id"],))
    return render_template("anotaciones.html", anotaciones=lista, hoy=hoy,
                           estudiantes=estudiantes_visibles(g.usuario))
