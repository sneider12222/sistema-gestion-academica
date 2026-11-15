# ADR 0002 — SQLite como motor de base de datos

- **Estado:** aceptada (con trabajo futuro declarado)
- **Fecha:** 2026-11-14
- **Decisores:** Piloto del proyecto (decisión), equipo de desarrollo (ejecución)
- **Documentos relacionados:** ADR 0001 (migración a Django)

## Contexto

El Modelo Técnico declara **MySQL/MariaDB** como motor de base de datos. El sistema migrado,
sin embargo, se despliega en **local** (`localhost`): un solo proceso, una sola persona
operándolo durante la demostración, sin servidor de base de datos remoto ni concurrencia real.

El propio Modelo Técnico deja abierta la puerta al **"entorno local"**, y el alcance de la
entrega no exige un servidor compartido. La pregunta es qué motor conviene para ese escenario y
para una entrega el **2026-11-30**.

## Decisión

Usar **SQLite** como motor del sistema migrado.

Justificación:

- El despliegue es local y mono-usuario: no hay concurrencia real que exija un servidor.
- No requiere instalar, configurar ni mantener un servicio de base de datos en cada equipo.
- Es suficiente para demostrar calificaciones, asistencia e informes con datos de `seed`.

Además, `DATABASES` en `settings.py` queda **parametrizado por variable de entorno**, con SQLite
como valor por defecto:

```python
DATABASES = {
    "default": {
        "ENGINE": env("DB_ENGINE", default="django.db.backends.sqlite3"),
        "NAME": env("DB_NAME", default=BASE_DIR / "db.sqlite3"),
        # USER, PASSWORD, HOST, PORT y OPTIONS se leen solo si se define un motor servidor.
    }
}
```

El objetivo de la parametrización es que el código **no quede atado al motor**: cambiar de
SQLite a MySQL/MariaDB debe ser un cambio de configuración, no de modelo ni de lógica.

Criterio de diseño asociado: no se usa SQL específico de SQLite en la lógica de negocio. Todo
pasa por el ORM de Django, para que el cambio de motor no obligue a reescribir consultas.

## Alternativas consideradas

| Alternativa | Por qué no ahora |
| :--- | :--- |
| **MySQL/MariaDB** | Es el motor declarado en el Modelo Técnico, pero exige instalar y administrar un servidor, credenciales y configuración en cada equipo. Para un despliegue local y mono-usuario añade superficie de fallo y tiempo de montaje sin beneficio para la demostración. **No se descarta: queda como trabajo futuro.** |
| **PostgreSQL** | Más robusto en concurrencia y tipos, pero igual exige servidor y no está en la documentación firmada. Introduce trabajo de configuración y migración que el alcance y el plazo no justifican. |

## Consecuencias

### Positivas

- Cero configuración de servidor: el archivo de base viaja con el proyecto y arranca con él.
- El equipo no depende de un servicio externo para levantar el sistema en la sustentación.
- La configuración por variable de entorno deja el cambio de motor como una tarea acotada.

### Negativas

- SQLite **limita la concurrencia de escritura**: bloquea la base entera mientras escribe. Para
  un usuario y una demo es irrelevante; para uso simultáneo real, no.
- **No reproduce exactamente el motor documentado** (MySQL/MariaDB). Hay diferencias de tipos,
  funciones y comportamiento transaccional que solo se verían al migrar.
- Se acepta conscientemente por el alcance y el plazo de la entrega (2026-11-30).

### Sobre el trabajo previo y trabajo futuro

- La estructura de datos se migra igual; el motor es configuración, no modelo.
- **MySQL/MariaDB queda declarado como trabajo futuro.** Cuando se aborde, la migración de motor
  no debe exigir cambios de modelo ni de lógica: solo cambiar `DATABASES`, instalar el driver y
  correr las migraciones contra el nuevo motor.

## Cómo revertir

Cambiar el motor es una operación de configuración:

1. Definir la variable de entorno (o el valor por defecto en `settings.py`) con el motor destino,
   la base, el usuario, la contraseña y el host.
2. Instalar el driver correspondiente (`mysqlclient` o `psycopg`).
3. Correr `python manage.py migrate` contra el nuevo motor.
4. Volver a ejecutar el management command `seed` para poblar la base nueva.

No se modifican modelos ni lógica de negocio. Para volver a SQLite basta con quitar la variable
de entorno y apuntar de nuevo a `db.sqlite3`.
