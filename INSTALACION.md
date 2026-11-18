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

1. Detenga el sistema y, si ya había cargado datos de prueba, borre el archivo `db.sqlite3`.
2. Cree la base vacía:

   ```bash
   py manage.py migrate
   ```

3. Cree la cuenta del administrador:

   ```bash
   py manage.py createsuperuser
   ```

   Le pedirá, en este orden: **Usuario** (el que usará para ingresar, en minúsculas), **Nombre**, **Rol**
   (escriba `administrador`) y la **contraseña** dos veces (no se ve mientras la escribe).
4. Inicie el sistema con `py manage.py runserver` e ingrese con esa cuenta.
5. En **Gestión académica** cree los grados, asignaturas y periodos.
6. En **Usuarios** registre docentes, estudiantes y acudientes.
7. En **Gestión académica** asigne cada docente a su asignatura y grado.

El uso diario de cada pantalla está explicado en el [manual de usuario](docs/MANUAL_DE_USUARIO.md).

## 8. Copias de seguridad

### Crear una copia

Ingrese como administrador → **Copias de seguridad** → **Crear copia de seguridad**. La copia queda en
la carpeta `respaldos/` del proyecto, con la fecha y hora en el nombre (por ejemplo
`sga_20261118_093000_123456.sqlite3`). Cree una antes de cada actualización del sistema.

Guarde periódicamente esa carpeta en otro lugar (una memoria USB o una carpeta en la nube de la
institución): si el computador se daña, las copias que solo están en él se pierden con él.

### Restaurar una copia

1. Detenga el sistema (`Ctrl + C` en la ventana donde corre).
2. Por seguridad, cambie el nombre del archivo actual `db.sqlite3` a `db.sqlite3.anterior`.
3. Copie el archivo de respaldo elegido a la carpeta del proyecto y cámbiele el nombre a `db.sqlite3`.
4. Ejecute `py manage.py migrate` (no borra datos; solo aplica cambios de estructura si la copia es de
   una versión anterior) e inicie el sistema.

Si algo sale mal, vuelva a poner el nombre `db.sqlite3` al archivo `db.sqlite3.anterior`.

## 9. Pasar los datos de un computador a otro

Toda la información está en un solo archivo: `db.sqlite3`, en la carpeta del proyecto.

1. En el computador de origen cree una copia de seguridad (sección 8), o detenga el sistema y copie
   `db.sqlite3` directamente.
2. En el computador nuevo, instale el sistema con los pasos 1 a 4.
3. Pegue el archivo en la carpeta del proyecto con el nombre `db.sqlite3`.
4. Ejecute `py manage.py migrate` e inicie el sistema con `py manage.py runserver`.

`db.sqlite3`, `respaldos/` y `.secret_key` no se suben a GitHub porque contienen datos personales de
estudiantes o claves propias de cada instalación.

## 10. Actualizar a una versión nueva

Cuando el equipo publique cambios en GitHub:

1. Cree una copia de seguridad (sección 8) y detenga el sistema.
2. Descargue los cambios. Si instaló con Git, desde la carpeta del proyecto:

   ```bash
   git pull
   ```

   Si lo descargó como ZIP, descargue el ZIP nuevo, descomprímalo en otra carpeta y copie en ella su
   `db.sqlite3`, su `.secret_key` y su carpeta `respaldos/`.
3. Instale las dependencias nuevas, si las hay:

   ```bash
   py -m pip install -r requirements.txt
   ```

4. Aplique los cambios de estructura de la base de datos (conserva todos los datos):

   ```bash
   py manage.py migrate
   ```

5. Inicie el sistema con `py manage.py runserver`.

### Si venía usando la versión Flask

Hasta el 18 de noviembre de 2026 el sistema se iniciaba con `py app.py` en el puerto 5000. Ahora es la
versión Django:

- Se inicia con `py manage.py runserver` y se abre en <http://127.0.0.1:8000>.
- Usa otra base de datos (`db.sqlite3`); la de la versión Flask (`instance/sga.db`) no se modifica ni se
  migra. Como solo contenía datos de prueba, se vuelven a cargar con `py manage.py seed`.
- Los usuarios y contraseñas de prueba son los mismos.

La versión Flask quedó guardada en la etiqueta `v1.0-flask` y en la rama `legacy/flask`. Todavía se
puede iniciar con `py app.py`.

## 11. Configuración opcional

El sistema funciona sin configuración. Si necesita cambiar algo (por ejemplo, usar otro archivo de base
de datos), copie el archivo `.env.example` con el nombre `.env` y siga las indicaciones que trae. Cada
opción está explicada en el propio archivo.

## 12. Comandos disponibles

| Comando | Qué hace |
|---|---|
| `py manage.py runserver` | Inicia el sistema en <http://127.0.0.1:8000> |
| `py manage.py runserver 8001` | Inicia el sistema en otro puerto |
| `py manage.py migrate` | Crea o actualiza las tablas de la base de datos (no borra datos) |
| `py manage.py seed` | Carga los datos de prueba en una base vacía |
| `py manage.py seed --reemplazar` | Borra **todos** los datos y vuelve a cargar los de prueba |
| `py manage.py createsuperuser` | Crea una cuenta de administrador |
| `py manage.py test` | Ejecuta las pruebas automáticas del sistema |
| `py -m unittest discover tests` | Ejecuta las pruebas de la versión Flask anterior |

## 13. Problemas frecuentes

| Problema | Solución |
|---|---|
| `py` no se reconoce como comando | Use `python` en lugar de `py`. Si tampoco funciona, reinstale Python marcando "Add python.exe to PATH". |
| `No module named 'django'` | Falta el paso 4. Ejecute `py -m pip install -r requirements.txt` dentro de la carpeta del proyecto. |
| `can't open file 'manage.py'` | PowerShell no está en la carpeta del proyecto. Entre a ella con `cd` y la ruta de la carpeta. |
| `no such table` al abrir una página | Falta el paso 5. Ejecute `py manage.py migrate`. |
| Después de `git pull` aparece un error en una página | Faltan los pasos 3 y 4 de la sección 10: `pip install -r requirements.txt` y `migrate`. |
| Los estilos no cargan (página sin colores) | Inicie el sistema con `py manage.py runserver` desde la carpeta del proyecto y recargue la página con `Ctrl + F5`. |
| `La base ya tiene usuarios` al ejecutar `seed` | La base ya tiene datos. Para reemplazarlos por los de prueba use `py manage.py seed --reemplazar` (borra todo). |
| La página no carga | Verifique que la ventana donde ejecutó `py manage.py runserver` siga abierta y sin errores. |
| El puerto 8000 está ocupado | Cierre la ventana anterior del sistema, o inícielo en otro puerto con `py manage.py runserver 8001`. |
| Olvidó la contraseña del administrador | Otro administrador puede cambiarla en **Usuarios**. Si no hay otro, ejecute `py manage.py changepassword USUARIO` con el usuario del administrador. |
