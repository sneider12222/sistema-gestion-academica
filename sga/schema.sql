-- Sistema de Gestión de Calificaciones, Asistencia e Informes Académicos
-- Instituto para el Desarrollo de las Inteligencias Múltiples

CREATE TABLE usuarios (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre      TEXT NOT NULL,
    documento   TEXT UNIQUE,
    email       TEXT,
    usuario     TEXT NOT NULL UNIQUE,
    clave_hash  TEXT NOT NULL,
    rol         TEXT NOT NULL CHECK (rol IN ('administrador', 'docente', 'estudiante', 'acudiente')),
    activo      INTEGER NOT NULL DEFAULT 1,
    creado_en   TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE grados (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre  TEXT NOT NULL UNIQUE
);

CREATE TABLE estudiantes (
    usuario_id  INTEGER PRIMARY KEY REFERENCES usuarios(id),
    grado_id    INTEGER REFERENCES grados(id)
);

CREATE TABLE acudientes_estudiantes (
    acudiente_id   INTEGER NOT NULL REFERENCES usuarios(id),
    estudiante_id  INTEGER NOT NULL REFERENCES estudiantes(usuario_id),
    PRIMARY KEY (acudiente_id, estudiante_id)
);

CREATE TABLE asignaturas (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre  TEXT NOT NULL UNIQUE
);

CREATE TABLE periodos (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre        TEXT NOT NULL UNIQUE,
    fecha_inicio  TEXT NOT NULL,
    fecha_fin     TEXT NOT NULL
);

-- Un docente dicta una asignatura en un grado
CREATE TABLE asignaciones (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    docente_id     INTEGER NOT NULL REFERENCES usuarios(id),
    asignatura_id  INTEGER NOT NULL REFERENCES asignaturas(id),
    grado_id       INTEGER NOT NULL REFERENCES grados(id),
    UNIQUE (asignatura_id, grado_id)
);

-- Actividades evaluativas (taller, examen, etc.) con su peso en el periodo
CREATE TABLE actividades (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    asignacion_id  INTEGER NOT NULL REFERENCES asignaciones(id),
    periodo_id     INTEGER NOT NULL REFERENCES periodos(id),
    nombre         TEXT NOT NULL,
    porcentaje     REAL NOT NULL CHECK (porcentaje > 0 AND porcentaje <= 100),
    fecha          TEXT NOT NULL
);

CREATE TABLE calificaciones (
    actividad_id   INTEGER NOT NULL REFERENCES actividades(id) ON DELETE CASCADE,
    estudiante_id  INTEGER NOT NULL REFERENCES estudiantes(usuario_id),
    nota           REAL NOT NULL CHECK (nota >= 1.0 AND nota <= 5.0),
    registrado_en  TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (actividad_id, estudiante_id)
);

-- P = presente, A = ausente
CREATE TABLE asistencias (
    asignacion_id  INTEGER NOT NULL REFERENCES asignaciones(id),
    estudiante_id  INTEGER NOT NULL REFERENCES estudiantes(usuario_id),
    fecha          TEXT NOT NULL,
    estado         TEXT NOT NULL CHECK (estado IN ('P', 'A')),
    PRIMARY KEY (asignacion_id, estudiante_id, fecha)
);

CREATE TABLE anotaciones (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    estudiante_id  INTEGER NOT NULL REFERENCES estudiantes(usuario_id),
    autor_id       INTEGER NOT NULL REFERENCES usuarios(id),
    descripcion    TEXT NOT NULL,
    fecha          TEXT NOT NULL
);

CREATE TABLE informes_enviados (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    estudiante_id    INTEGER NOT NULL REFERENCES estudiantes(usuario_id),
    periodo_id       INTEGER NOT NULL REFERENCES periodos(id),
    remitente_id     INTEGER NOT NULL REFERENCES usuarios(id),
    destinatario_id  INTEGER NOT NULL REFERENCES usuarios(id),
    mensaje          TEXT,
    enviado_en       TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    leido_en         TEXT
);

CREATE TABLE config (
    clave  TEXT PRIMARY KEY,
    valor  TEXT
);

CREATE INDEX idx_asistencias_est ON asistencias (estudiante_id, fecha);
CREATE INDEX idx_anotaciones_est ON anotaciones (estudiante_id, fecha);
CREATE INDEX idx_informes_dest ON informes_enviados (destinatario_id);
