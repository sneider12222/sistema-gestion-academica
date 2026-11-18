# Sistema de Gestión de Calificaciones, Asistencia e Informes Académicos

Aplicativo web para el **Instituto para el Desarrollo de las Inteligencias Múltiples** (Riohacha, La Guajira),
construido según el modelo técnico del proyecto. Hecho en **Python con Django y SQLite**; se ejecuta en
entorno local (localhost), como lo define el documento.

La primera versión se construyó en Flask (`app.py` y `sga/`). Se conserva como referencia mientras dura la
migración, descrita en [docs/decisiones](docs/decisiones). La versión principal es la de Django.

## Cómo ejecutarlo

Requiere Python 3.10 o superior. La guía paso a paso para otro computador está en [INSTALACION.md](INSTALACION.md).

```bash
py -m pip install -r requirements.txt
```

```bash
py manage.py migrate
```

```bash
py manage.py seed
```

```bash
py manage.py runserver
```

Abra <http://127.0.0.1:8000> en el navegador.

| Comando | Qué hace |
|---|---|
| `py manage.py runserver` | Inicia el sistema |
| `py manage.py migrate` | Crea o actualiza las tablas de la base de datos (`db.sqlite3`) |
| `py manage.py seed` | Carga los datos de prueba en una base vacía |
| `py manage.py seed --reemplazar` | Borra **todos** los datos y vuelve a cargar los de prueba |
| `py manage.py createsuperuser` | Crea una cuenta de administrador (para empezar con datos reales) |
| `py manage.py test` | Ejecuta las pruebas automáticas del sistema Django |
| `py -m unittest discover tests` | Ejecuta las pruebas de la versión Flask |

## Usuarios de prueba

Todos los datos de prueba son **ficticios** (documentos `PRUEBA-…`, correos `@prueba.local`) y el sistema lo
indica con un aviso en pantalla.

| Rol | Usuario | Contraseña |
|---|---|---|
| Administrador | `admin` | `Admin2026*` |
| Docente | `docente1`, `docente2`, `docente3` | `Prueba2026*` |
| Estudiante | `estudiante1` … `estudiante12` | `Prueba2026*` |
| Acudiente | `acudiente1` … `acudiente10` | `Prueba2026*` |

Para usar el sistema con datos reales, parta de una base sin datos de prueba (ver [INSTALACION.md](INSTALACION.md)).

## Módulos (según los objetivos específicos del modelo técnico)

1. **Autenticación y gestión de usuarios**
   - Inicio de sesión y control de acceso diferenciado por rol: docente, estudiante, padre/acudiente y
     administrador. Cada vista valida el acceso según el perfil (`accounts/permissions.py`).
   - El administrador registra los usuarios; el panel muestra el indicador del proyecto
     (usuarios con acceso al sistema frente a la meta de 280 usuarios potenciales).
2. **Calificaciones y asistencia**
   - Formularios de registro de calificaciones y de asistencia, con validación de datos.
   - Anotaciones realizadas por los docentes.
3. **Reportes e informes académicos**
   - Paneles y vistas de consulta por rol, con el historial académico del estudiante por periodo.
   - Reportes de calificaciones y asistencia por grado.
   - Envío del informe académico a los acudientes dentro del sistema.
   - Estudiantes y acudientes tienen permisos de solo lectura sobre su propia información.

Mitigación de riesgos del modelo técnico: los datos de prueba están claramente identificados y el
administrador puede crear copias de seguridad de la base de datos.

## Estructura

```
manage.py                  Punto de entrada de Django
config/                    Configuración (settings, rutas, páginas de error, ejecutor de pruebas)
accounts/                  Usuarios, roles, inicio de sesión, permisos y comando seed
academico/                 Grados, asignaturas, periodos, asignaciones y copias de seguridad
calificaciones/            Actividades evaluativas, notas y cálculo de la definitiva
asistencia/                Registro diario de asistencia
reportes/                  Informes, reportes por grado, anotaciones y envío a acudientes
templates/, static/        Pantallas y estilos
docs/decisiones/           Registro de decisiones de arquitectura (ADR)

app.py, sga/, tests/       Versión Flask anterior (referencia)
```

Archivos que crea el sistema y que no se suben al repositorio: `db.sqlite3` (base de datos),
`.secret_key` (clave de sesión propia de cada instalación) y `respaldos/` (copias de seguridad).

## Protección de datos

El sistema maneja datos personales de menores (Ley 1581 de 2012 y Ley 1098 de 2006): las contraseñas se
guardan cifradas, cada consulta verifica el permiso del usuario sobre el estudiante y los formularios están
protegidos contra CSRF. `db.sqlite3` y `respaldos/` no deben compartirse ni subirse a repositorios públicos.
