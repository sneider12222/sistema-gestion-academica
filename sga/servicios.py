"""Reglas académicas compartidas: permisos de consulta, definitivas e informes."""
from datetime import date

from .db import consulta, uno

ESTADOS = {"P": "Presente", "A": "Ausente"}
NOTA_MIN, NOTA_MAX = 1.0, 5.0

# Indicador del modelo técnico: usuarios con acceso al sistema de gestión académica
META_USUARIOS = 280

INSTITUCION = "Instituto para el Desarrollo de las Inteligencias Múltiples"
DIRECCION = "Calle 17 # 7a, Riohacha, La Guajira"


def definitiva(pares):
    """Promedio ponderado de [(nota, porcentaje)] sobre las actividades ya calificadas."""
    peso = sum(p for n, p in pares if n is not None)
    if not peso:
        return None
    return round(sum(n * p for n, p in pares if n is not None) / peso + 1e-9, 1)


def periodos():
    return consulta("SELECT * FROM periodos ORDER BY fecha_inicio")


def periodo_seleccionado(periodo_id=None):
    """El periodo pedido; si no, el que contiene la fecha de hoy; si no, el último iniciado."""
    if periodo_id:
        p = uno("SELECT * FROM periodos WHERE id = ?", (periodo_id,))
        if p:
            return p
    hoy = date.today().isoformat()
    return (uno("SELECT * FROM periodos WHERE ? BETWEEN fecha_inicio AND fecha_fin", (hoy,))
            or uno("SELECT * FROM periodos WHERE fecha_inicio <= ? ORDER BY fecha_inicio DESC", (hoy,))
            or uno("SELECT * FROM periodos ORDER BY fecha_inicio"))


_SQL_ESTUDIANTES = """
    SELECT u.id, u.nombre, u.documento, e.grado_id, gr.nombre grado
      FROM estudiantes e
      JOIN usuarios u ON u.id = e.usuario_id
      LEFT JOIN grados gr ON gr.id = e.grado_id
     WHERE u.activo = 1 {filtro}
     ORDER BY gr.nombre, u.nombre"""


def estudiantes_visibles(usuario):
    """Estudiantes que el usuario está autorizado a consultar según su rol."""
    rol, uid = usuario["rol"], usuario["id"]
    if rol == "administrador":
        return consulta(_SQL_ESTUDIANTES.format(filtro=""))
    if rol == "docente":
        return consulta(_SQL_ESTUDIANTES.format(
            filtro="AND e.grado_id IN (SELECT grado_id FROM asignaciones WHERE docente_id = ?)"), (uid,))
    if rol == "acudiente":
        return consulta(_SQL_ESTUDIANTES.format(
            filtro="AND u.id IN (SELECT estudiante_id FROM acudientes_estudiantes WHERE acudiente_id = ?)"), (uid,))
    return consulta(_SQL_ESTUDIANTES.format(filtro="AND u.id = ?"), (uid,))


def puede_ver(usuario, estudiante_id):
    return any(e["id"] == estudiante_id for e in estudiantes_visibles(usuario))


def grados_visibles(usuario):
    if usuario["rol"] == "administrador":
        return consulta("SELECT * FROM grados ORDER BY nombre")
    return consulta(
        """SELECT * FROM grados WHERE id IN (SELECT grado_id FROM asignaciones WHERE docente_id = ?)
            ORDER BY nombre""", (usuario["id"],))


def historial(estudiante):
    """Historial académico: definitiva de cada asignatura en cada periodo."""
    filas = consulta(
        """SELECT s.nombre asignatura, act.periodo_id, act.porcentaje, c.nota
             FROM asignaciones a
             JOIN asignaturas s ON s.id = a.asignatura_id
             LEFT JOIN actividades act ON act.asignacion_id = a.id
             LEFT JOIN calificaciones c ON c.actividad_id = act.id AND c.estudiante_id = ?
            WHERE a.grado_id = ? ORDER BY s.nombre""", (estudiante["id"], estudiante["grado_id"]))
    pares = {}
    for f in filas:
        por_periodo = pares.setdefault(f["asignatura"], {})
        if f["periodo_id"] is not None:
            por_periodo.setdefault(f["periodo_id"], []).append((f["nota"], f["porcentaje"]))
    return [{"asignatura": nombre, "notas": {p: definitiva(v) for p, v in por_periodo.items()}}
            for nombre, por_periodo in pares.items()]


def construir_informe(estudiante_id, periodo):
    """Informe académico de un estudiante en un periodo: notas, asistencia y anotaciones."""
    est = uno(_SQL_ESTUDIANTES.format(filtro="AND u.id = ?"), (estudiante_id,))
    if est is None or periodo is None:
        return None
    rango = (periodo["fecha_inicio"], periodo["fecha_fin"])

    filas = consulta(
        """SELECT a.id asignacion_id, s.nombre asignatura, d.nombre docente,
                  act.id actividad_id, act.nombre actividad, act.porcentaje, act.fecha, c.nota
             FROM asignaciones a
             JOIN asignaturas s ON s.id = a.asignatura_id
             JOIN usuarios d ON d.id = a.docente_id
             LEFT JOIN actividades act ON act.asignacion_id = a.id AND act.periodo_id = ?
             LEFT JOIN calificaciones c ON c.actividad_id = act.id AND c.estudiante_id = ?
            WHERE a.grado_id = ?
            ORDER BY s.nombre, act.fecha, act.id""",
        (periodo["id"], estudiante_id, est["grado_id"]))

    asistencia = {}
    for f in consulta(
            """SELECT asignacion_id, estado, COUNT(*) n FROM asistencias
                WHERE estudiante_id = ? AND fecha BETWEEN ? AND ?
                GROUP BY asignacion_id, estado""", (estudiante_id, *rango)):
        asistencia.setdefault(f["asignacion_id"], dict.fromkeys(ESTADOS, 0))[f["estado"]] = f["n"]

    materias = {}
    for f in filas:
        m = materias.setdefault(f["asignacion_id"], {
            "asignatura": f["asignatura"], "docente": f["docente"], "actividades": [],
            "asistencia": asistencia.get(f["asignacion_id"], dict.fromkeys(ESTADOS, 0))})
        if f["actividad_id"] is not None:
            m["actividades"].append(f)
    materias = list(materias.values())
    for m in materias:
        m["definitiva"] = definitiva([(a["nota"], a["porcentaje"]) for a in m["actividades"]])

    con_nota = [m["definitiva"] for m in materias if m["definitiva"] is not None]
    total = dict.fromkeys(ESTADOS, 0)
    for m in materias:
        for k, n in m["asistencia"].items():
            total[k] += n
    clases = sum(total.values())

    return {
        "estudiante": est,
        "periodo": periodo,
        "materias": materias,
        "promedio": round(sum(con_nota) / len(con_nota) + 1e-9, 1) if con_nota else None,
        "asistencia": total,
        "clases": clases,
        "pct_asistencia": round(100 * total["P"] / clases) if clases else None,
        "ausencias": consulta(
            """SELECT x.fecha, s.nombre asignatura
                 FROM asistencias x
                 JOIN asignaciones a ON a.id = x.asignacion_id
                 JOIN asignaturas s ON s.id = a.asignatura_id
                WHERE x.estudiante_id = ? AND x.estado = 'A' AND x.fecha BETWEEN ? AND ?
                ORDER BY x.fecha DESC, s.nombre""", (estudiante_id, *rango)),
        "anotaciones": consulta(
            """SELECT n.*, u.nombre autor FROM anotaciones n JOIN usuarios u ON u.id = n.autor_id
                WHERE n.estudiante_id = ? AND n.fecha BETWEEN ? AND ?
                ORDER BY n.fecha DESC, n.id DESC""", (estudiante_id, *rango)),
        "historial": historial(est),
    }
