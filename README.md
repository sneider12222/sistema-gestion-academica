# Sistema de Gestión de Calificaciones, Asistencia e Informes Académicos

Aplicativo web para el **Instituto para el Desarrollo de las Inteligencias Múltiples** (Riohacha, La Guajira),
construido según el modelo técnico del proyecto. Hecho en **Python (Flask) + SQLite**; se ejecuta en entorno
local (localhost), como lo define el documento.

## Cómo ejecutarlo

Requiere Python 3.10 o superior.

```bash
py -m pip install -r requirements.txt
```

```bash
py app.py
```

Abra <http://127.0.0.1:5000> en el navegador. La primera vez se crea la base de datos con datos de prueba.

| Comando | Qué hace |
|---|---|
| `py app.py` | Inicia el sistema |
| `py app.py --reiniciar` | Borra la base de datos y la recrea con los datos de prueba |
| `py app.py --vacio` | Borra la base de datos y deja solo la cuenta `admin` (para cargar datos reales) |
| `py -m unittest discover tests -v` | Ejecuta las pruebas automáticas |

## Usuarios de prueba

Todos los datos de prueba son **ficticios** (documentos `PRUEBA-…`, correos `@prueba.local`) y el sistema lo
indica con un aviso en pantalla.

| Rol | Usuario | Contraseña |
|---|---|---|
| Administrador | `admin` | `Admin2026*` |
| Docente | `docente1`, `docente2`, `docente3` | `Prueba2026*` |
| Estudiante | `estudiante1` … `estudiante12` | `Prueba2026*` |
| Acudiente | `acudiente1` … `acudiente10` | `Prueba2026*` |

Antes de usar el sistema con datos reales, ejecute `py app.py --vacio` y cambie la contraseña del
administrador desde **Mi cuenta** (clic en el nombre, arriba a la derecha).

## Módulos (según los objetivos específicos del modelo técnico)

1. **Autenticación y gestión de usuarios**
   - Inicio de sesión y control de acceso diferenciado por rol: docente, estudiante, padre/acudiente y
     administrador. Cada ruta valida el acceso según el perfil.
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

El documento no detalla el modelo de datos, así que la estructura mínima para poder registrar una nota
(grados, asignaturas, periodos, actividades evaluativas con porcentaje y notas de 1.0 a 5.0) es una
decisión de implementación; ajústela al diagrama de base de datos del proyecto si difiere.

## Estructura

```
app.py                 Punto de entrada
requirements.txt
sga/
  __init__.py          Configuración de la aplicación y protección CSRF
  schema.sql           Modelo de la base de datos
  db.py                Conexión, inicialización y respaldos
  auth.py              Inicio de sesión y control de acceso por rol
  admin.py             Usuarios, estructura académica y respaldos
  docente.py           Calificaciones, asistencia y anotaciones
  consulta.py          Informes, reportes y envío a acudientes
  servicios.py         Reglas académicas (definitivas, desempeño, permisos)
  seed.py              Datos de prueba
  templates/, static/  Pantallas y estilos
tests/test_sga.py      Pruebas automáticas
instance/              Base de datos (sga.db), clave de sesión y respaldos (se crea sola)
```

## Protección de datos

El sistema maneja datos personales de menores (Ley 1581 de 2012 y Ley 1098 de 2006): las contraseñas se
guardan cifradas, cada consulta verifica el permiso del usuario sobre el estudiante, los formularios están
protegidos contra CSRF y la carpeta `instance/` no debe compartirse ni subirse a repositorios públicos.
