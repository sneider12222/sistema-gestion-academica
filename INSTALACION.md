# Guía de instalación en otro computador

Sistema de Gestión de Calificaciones, Asistencia e Informes Académicos
Instituto para el Desarrollo de las Inteligencias Múltiples

El sistema funciona en entorno local: se instala en un computador y se abre desde el navegador de ese
mismo equipo. No necesita internet para funcionar, solo para descargarlo e instalarlo.

## 1. Requisitos

| Requisito | Detalle |
|---|---|
| Sistema operativo | Windows 10 u 11 (también funciona en macOS y Linux) |
| Python | Versión 3.10 o superior |
| Navegador | Chrome, Edge o Firefox |
| Git | Opcional; solo si va a descargar el proyecto con `git clone` |

## 2. Instalar Python

1. Entre a <https://www.python.org/downloads/> y descargue el instalador de Python para Windows.
2. Ejecute el instalador y **marque la casilla "Add python.exe to PATH"** antes de pulsar *Install Now*.
3. Compruebe la instalación: abra **PowerShell** (menú Inicio → escriba `PowerShell`) y ejecute:

```bash
py --version
```

Debe aparecer algo como `Python 3.13.x`. Si el comando `py` no existe, use `python` en su lugar en todos
los pasos de esta guía.

## 3. Descargar el proyecto

**Opción A, con Git:**

```bash
git clone https://github.com/sneider12222/sistema-gestion-academica.git
```

Esto crea la carpeta `sistema-gestion-academica`.

**Opción B, sin Git:** entre a <https://github.com/sneider12222/sistema-gestion-academica>, pulse **Code → Download ZIP**, y descomprima
el archivo en una carpeta, por ejemplo en `Documentos`.

## 4. Instalar las dependencias

Abra PowerShell **dentro de la carpeta del proyecto** (la que contiene `manage.py`). En el Explorador de
archivos puede hacerlo con clic derecho sobre la carpeta → *Abrir en Terminal*. Luego ejecute:

```bash
py -m pip install -r requirements.txt
```

Este paso se hace una sola vez por computador.

## 5. Crear la base de datos

```bash
py manage.py migrate
```

Esto crea el archivo `db.sqlite3` con todas las tablas. Para probar el sistema con **datos de prueba**
(ficticios), cárguelos con:

```bash
py manage.py seed
```

Los usuarios y contraseñas de prueba de cada rol están en el archivo [README.md](README.md).

## 6. Iniciar el sistema

```bash
py manage.py runserver
```

Deje esa ventana abierta mientras usa el sistema y entre desde el navegador a:

<http://127.0.0.1:8000>

Para detener el sistema, vuelva a la ventana de PowerShell y pulse `Ctrl + C`.

## 7. Preparar el sistema para datos reales

Los datos de prueba no deben mezclarse con información real. Para empezar con el sistema limpio:

1. Detenga el sistema y borre el archivo `db.sqlite3` (si ya lo había creado con datos de prueba).
2. Cree la base vacía con `py manage.py migrate`.
3. Cree la cuenta del administrador con `py manage.py createsuperuser`. Le pedirá usuario, nombre,
   rol (escriba `administrador`) y contraseña.
4. Inicie el sistema con `py manage.py runserver` e ingrese con esa cuenta.
5. En **Gestión académica** cree los grados, asignaturas y periodos.
6. En **Usuarios** registre docentes, estudiantes y acudientes.
7. En **Gestión académica** asigne cada docente a su asignatura y grado.

## 8. Pasar los datos de un computador a otro

Toda la información está en un solo archivo: `db.sqlite3`, en la carpeta del proyecto.

1. En el computador de origen, ingrese como administrador y cree una copia en **Copias de seguridad**
   (queda en la carpeta `respaldos/`), o detenga el sistema y copie `db.sqlite3` directamente.
2. En el computador nuevo, instale el sistema con los pasos 1 a 4.
3. Pegue el archivo en la carpeta del proyecto con el nombre `db.sqlite3`.
4. Ejecute `py manage.py migrate` (no borra datos; solo aplica cambios de estructura pendientes) e
   inicie el sistema con `py manage.py runserver`.

`db.sqlite3` y `respaldos/` no se suben a GitHub porque contienen datos personales de estudiantes.

## 9. Comandos disponibles

| Comando | Qué hace |
|---|---|
| `py manage.py runserver` | Inicia el sistema |
| `py manage.py migrate` | Crea o actualiza las tablas de la base de datos |
| `py manage.py seed` | Carga los datos de prueba en una base vacía |
| `py manage.py seed --reemplazar` | Borra **todos** los datos y vuelve a cargar los de prueba |
| `py manage.py createsuperuser` | Crea una cuenta de administrador |
| `py manage.py test` | Ejecuta las pruebas automáticas |

La versión Flask anterior se conserva como referencia y todavía se puede iniciar con `py app.py`
(en <http://127.0.0.1:5000>); usa su propia base en `instance/sga.db`.

## 10. Problemas frecuentes

| Problema | Solución |
|---|---|
| `py` no se reconoce como comando | Use `python` en lugar de `py`. Si tampoco funciona, reinstale Python marcando "Add python.exe to PATH". |
| `No module named 'django'` | Falta el paso 4. Ejecute `py -m pip install -r requirements.txt` dentro de la carpeta del proyecto. |
| `can't open file 'manage.py'` | PowerShell no está en la carpeta del proyecto. Entre a ella con `cd` y la ruta de la carpeta. |
| `no such table` al abrir una página | Falta el paso 5. Ejecute `py manage.py migrate`. |
| `La base ya tiene usuarios` al ejecutar `seed` | La base ya tiene datos. Para reemplazarlos por los de prueba use `py manage.py seed --reemplazar` (borra todo). |
| La página no carga | Verifique que la ventana donde ejecutó `py manage.py runserver` siga abierta y sin errores. |
| El puerto 8000 está ocupado | Cierre la ventana anterior del sistema, o inícielo en otro puerto con `py manage.py runserver 8001`. |
| Olvidó la contraseña de `admin` | Otro administrador puede cambiarla en **Usuarios**. Si no hay otro, restaure una copia de seguridad. |
