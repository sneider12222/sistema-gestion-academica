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

Abra PowerShell **dentro de la carpeta del proyecto** (la que contiene `app.py`). En el Explorador de
archivos puede hacerlo con clic derecho sobre la carpeta → *Abrir en Terminal*. Luego ejecute:

```bash
py -m pip install -r requirements.txt
```

Este paso se hace una sola vez por computador.

## 5. Iniciar el sistema

```bash
py app.py
```

Deje esa ventana abierta mientras usa el sistema y entre desde el navegador a:

<http://127.0.0.1:5000>

La primera vez que se inicia, el sistema crea solo la base de datos con **datos de prueba** (ficticios).
Los usuarios y contraseñas de prueba de cada rol están en el archivo [README.md](README.md).

Para detener el sistema, vuelva a la ventana de PowerShell y pulse `Ctrl + C`.

## 6. Preparar el sistema para datos reales

Los datos de prueba no deben mezclarse con información real. Para empezar con el sistema limpio:

```bash
py app.py --vacio
```

Esto borra la base de datos y deja únicamente la cuenta `admin` (su contraseña inicial está en el
README). Después:

1. Inicie el sistema con `py app.py` e ingrese como `admin`.
2. Cambie la contraseña desde **Mi cuenta** (clic en su nombre, abajo a la izquierda).
3. En **Gestión académica** cree los grados, asignaturas y periodos.
4. En **Usuarios** registre docentes, estudiantes y acudientes.
5. En **Gestión académica** asigne cada docente a su asignatura y grado.

## 7. Pasar los datos de un computador a otro

Toda la información está en un solo archivo: `instance/sga.db`.

1. En el computador de origen, ingrese como administrador y cree una copia en **Copias de seguridad**
   (queda en `instance/respaldos/`), o detenga el sistema y copie `instance/sga.db` directamente.
2. En el computador nuevo, instale el sistema con los pasos 1 a 4.
3. Cree la carpeta `instance` dentro del proyecto si no existe, y pegue allí el archivo con el nombre
   `sga.db`.
4. Inicie el sistema con `py app.py`.

La carpeta `instance` no se sube a GitHub porque contiene datos personales de estudiantes.

## 8. Comandos disponibles

| Comando | Qué hace |
|---|---|
| `py app.py` | Inicia el sistema |
| `py app.py --reiniciar` | Borra la base de datos y la recrea con los datos de prueba |
| `py app.py --vacio` | Borra la base de datos y deja solo la cuenta `admin` |
| `py -m unittest discover tests -v` | Ejecuta las pruebas automáticas |

## 9. Problemas frecuentes

| Problema | Solución |
|---|---|
| `py` no se reconoce como comando | Use `python` en lugar de `py`. Si tampoco funciona, reinstale Python marcando "Add python.exe to PATH". |
| `No module named 'flask'` | Falta el paso 4. Ejecute `py -m pip install -r requirements.txt` dentro de la carpeta del proyecto. |
| `can't open file 'app.py'` | PowerShell no está en la carpeta del proyecto. Entre a ella con `cd` y la ruta de la carpeta. |
| La página no carga | Verifique que la ventana donde ejecutó `py app.py` siga abierta y sin errores. |
| El puerto 5000 está ocupado | Cierre el otro programa que lo usa, o cierre una ventana anterior del sistema que haya quedado abierta. |
| Olvidó la contraseña de `admin` | Otro administrador puede cambiarla en **Usuarios**. Si no hay otro, restaure una copia de seguridad. |
