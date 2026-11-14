"""Datos de prueba (ficticios). Ninguna persona o nota aquí corresponde a datos reales."""
import random
from datetime import date, timedelta

from werkzeug.security import generate_password_hash

# Credenciales del entorno de prueba (documentadas en el README)
CLAVE_ADMIN = "Admin2026*"
CLAVE_PRUEBA = "Prueba2026*"

DOCENTES = ["Marta Pérez Iguarán", "Luis Brito Mendoza", "Carmen Epieyú Gómez"]
ASIGNATURAS = ["Ciencias Naturales", "Inglés", "Lenguaje", "Matemáticas"]
# (asignatura, índice del docente) por cada grado
CARGA = {"6°A": [(3, 0), (2, 1), (0, 2), (1, 1)], "7°A": [(3, 0), (2, 1), (0, 2), (1, 2)]}
ESTUDIANTES = {
    "6°A": ["Ana Sofía Cotes", "Andrés Pinto", "Camila Ipuana", "Daniel Redondo", "Isabella Mejía", "Juan David Deluque"],
    "7°A": ["Laura Pushaina", "Mateo Vanegas", "Nicolás Romero", "Sara Fonseca", "Sebastián Uriana", "Valentina Daza"],
}
# Cada acudiente con los índices (global) de sus acudidos
ACUDIENTES = [("Rosa Cotes", [0]), ("Pedro Pinto", [1]), ("Yolanda Ipuana", [2, 6]), ("Jorge Redondo", [3]),
              ("Elena Mejía", [4]), ("Óscar Deluque", [5]), ("Marina Vanegas", [7]), ("Hernán Romero", [8, 9]),
              ("Luz Uriana", [10]), ("Diana Daza", [11])]
PERIODOS = [("Periodo 1", "02-02", "04-10"), ("Periodo 2", "04-13", "06-19"),
            ("Periodo 3", "07-13", "09-18"), ("Periodo 4", "09-21", "11-27")]
ACTIVIDADES = [("Taller", 20), ("Quiz", 20), ("Exposición", 25), ("Examen final", 35)]


def crear_admin_inicial(con):
    con.execute("""INSERT INTO usuarios (nombre, usuario, clave_hash, rol)
                   VALUES ('Administrador', 'admin', ?, 'administrador')""",
                (generate_password_hash(CLAVE_ADMIN),))


def cargar_datos_prueba(con):
    rnd = random.Random(2026)
    hoy = date.today()
    anio = hoy.year
    clave = generate_password_hash(CLAVE_PRUEBA)

    def usuario(nombre, login, rol, doc, clave_hash=clave):
        return con.execute(
            "INSERT INTO usuarios (nombre, documento, email, usuario, clave_hash, rol) VALUES (?, ?, ?, ?, ?, ?)",
            (nombre, doc, f"{login}@prueba.local", login, clave_hash, rol)).lastrowid

    con.execute("INSERT INTO config VALUES ('datos_prueba', '1')")
    usuario("Administrador (prueba)", "admin", "administrador", "PRUEBA-0001", generate_password_hash(CLAVE_ADMIN))
    docentes = [usuario(n, f"docente{i}", "docente", f"PRUEBA-1{i:03d}") for i, n in enumerate(DOCENTES, 1)]
    asignaturas = [con.execute("INSERT INTO asignaturas (nombre) VALUES (?)", (n,)).lastrowid for n in ASIGNATURAS]
    periodos = [(con.execute("INSERT INTO periodos (nombre, fecha_inicio, fecha_fin) VALUES (?, ?, ?)",
                             (n, f"{anio}-{i}", f"{anio}-{f}")).lastrowid,
                 date.fromisoformat(f"{anio}-{i}"), date.fromisoformat(f"{anio}-{f}")) for n, i, f in PERIODOS]

    alumnos, n_est = [], 0
    for grado, nombres in ESTUDIANTES.items():
        gid = con.execute("INSERT INTO grados (nombre) VALUES (?)", (grado,)).lastrowid
        del_grado = []
        for nombre in nombres:
            n_est += 1
            uid = usuario(nombre, f"estudiante{n_est}", "estudiante", f"PRUEBA-2{n_est:03d}")
            con.execute("INSERT INTO estudiantes VALUES (?, ?)", (uid, gid))
            del_grado.append(uid)
            alumnos.append(uid)

        for asig, doc in CARGA[grado]:
            aid = con.execute("INSERT INTO asignaciones (docente_id, asignatura_id, grado_id) VALUES (?, ?, ?)",
                              (docentes[doc], asignaturas[asig], gid)).lastrowid
            nivel = {e: rnd.uniform(2.6, 4.7) for e in del_grado}  # rendimiento base por estudiante

            for pid, ini, fin in periodos:
                if ini > hoy:
                    continue
                dias = (fin - ini).days
                for k, (nombre, pct) in enumerate(ACTIVIDADES):
                    fecha = ini + timedelta(days=int(dias * (k + 1) / (len(ACTIVIDADES) + 0.3)))
                    act = con.execute(
                        "INSERT INTO actividades (asignacion_id, periodo_id, nombre, porcentaje, fecha) VALUES (?, ?, ?, ?, ?)",
                        (aid, pid, nombre, pct, fecha.isoformat())).lastrowid
                    if fecha > hoy:
                        continue  # actividad programada, aún sin notas
                    for e in del_grado:
                        nota = min(5.0, max(1.0, round(nivel[e] + rnd.uniform(-0.8, 0.8), 1)))
                        con.execute("INSERT INTO calificaciones (actividad_id, estudiante_id, nota) VALUES (?, ?, ?)",
                                    (act, e, nota))

            # Asistencia de las últimas tres semanas (días hábiles)
            for atras in range(1, 22):
                dia = hoy - timedelta(days=atras)
                if dia.weekday() >= 5:
                    continue
                for e in del_grado:
                    estado = rnd.choices("PA", weights=[92, 8])[0]
                    con.execute("INSERT INTO asistencias VALUES (?, ?, ?, ?)", (aid, e, dia.isoformat(), estado))

    for i, (nombre, acudidos) in enumerate(ACUDIENTES, 1):
        uid = usuario(nombre, f"acudiente{i}", "acudiente", f"PRUEBA-3{i:03d}")
        con.executemany("INSERT INTO acudientes_estudiantes VALUES (?, ?)", [(uid, alumnos[k]) for k in acudidos])

    notas = [(0, 0, "Excelente participación en la feria de ciencias.", 3),
             (1, 1, "No entregó el taller de comprensión lectora.", 5),
             (3, 0, "Interrumpió la clase en repetidas ocasiones.", 8),
             (6, 2, "Apoya a sus compañeros en las actividades de laboratorio.", 4),
             (8, 1, "Debe reforzar la lectura en casa.", 10)]
    for est, doc, texto, atras in notas:
        con.execute("INSERT INTO anotaciones (estudiante_id, autor_id, descripcion, fecha) VALUES (?, ?, ?, ?)",
                    (alumnos[est], docentes[doc], texto, (hoy - timedelta(days=atras)).isoformat()))
