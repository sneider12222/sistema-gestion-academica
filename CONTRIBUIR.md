# Guía para el equipo de desarrollo

Cómo trabajar en el código del sistema sin romper lo que ya funciona. Para instalarlo, vea
[INSTALACION.md](INSTALACION.md).

## Preparar el entorno

```bash
git clone https://github.com/sneider12222/sistema-gestion-academica.git
```

```bash
py -m venv .venv
```

```bash
.venv\Scripts\activate
```

```bash
py -m pip install -r requirements.txt
```

```bash
py manage.py migrate
```

```bash
py manage.py seed
```

Para ver los errores con detalle mientras programa, cree un archivo `.env` con `DEBUG=True` (ver
`.env.example`). No lo active en un equipo con datos reales.

## Ramas

| Rama | Para qué |
|---|---|
| `main` | Versión estable. Siempre debe instalar, migrar y pasar todas las pruebas. No se trabaja directamente en ella. |
| `django-migration` | Rama de integración de la migración a Django (ADR 0001). |
| `legacy/flask` y etiqueta `v1.0-flask` | Versión Flask congelada como referencia y respaldo. **No se modifican.** |

Cada cambio se hace en una rama propia creada desde `main` actualizado:

```bash
git switch main
```

```bash
git pull
```

```bash
git switch -c tipo/descripcion-corta
```

Ejemplos de nombre: `feat/reporte-por-docente`, `fix/nota-con-coma`, `docs/manual-acudiente`.

## Commits

- Un commit por cambio coherente, con mensaje en español: `tipo: qué cambia`. Tipos: `feat`
  (funcionalidad), `fix` (corrección), `docs`, `test`, `refactor`, `chore`.
- En el cuerpo, explique **por qué** cuando no sea evidente.
- Nunca suba `db.sqlite3`, `.env`, `.secret_key`, `respaldos/` ni `instance/` (ya están en
  `.gitignore`). Contienen datos personales de menores o claves propias de cada instalación.

## Antes de abrir un Pull Request

Todo debe pasar en su rama:

```bash
py manage.py check
```

```bash
py manage.py makemigrations --check --dry-run
```

```bash
py manage.py test
```

```bash
py -m unittest discover tests
```

- `makemigrations --check` debe decir *No changes detected*. Si cambió un modelo, genere la migración
  con `py manage.py makemigrations` y súbala en el mismo PR.
- Revise también a mano, en el navegador, las pantallas que tocó, con cada rol afectado.
- Si agrega una funcionalidad, agregue sus pruebas en la app correspondiente (archivos `tests_*.py`).

## Pull Requests e integración

1. Suba su rama (`git push -u origin NOMBRE-DE-LA-RAMA`) y abra el Pull Request hacia `main` en GitHub.
2. Describa qué cambia, cómo lo probó y cómo deshacerlo.
3. Pida revisión a otro integrante del equipo. No integre su propio PR sin revisión, salvo acuerdo
   explícito del equipo.
4. Integre con **Create a merge commit** (equivale a `git merge --no-ff`). Así el historial conserva
   cada commit y el cambio completo se puede revertir de una vez.
5. Nunca use `git push --force` sobre `main` ni sobre ramas de otra persona.

## Deshacer una integración

Si un merge en `main` causó un problema, se revierte sin borrar historial:

```bash
git switch main
```

```bash
git pull
```

```bash
git log --oneline --merges -5
```

Copie el identificador del merge que quiere deshacer y ejecute:

```bash
git revert -m 1 IDENTIFICADOR
```

```bash
git push
```

Si el merge incluía una migración de base de datos, avise al equipo antes: en cada instalación puede
hacer falta restaurar la copia de seguridad previa (ver INSTALACION.md, sección 8).

## Decisiones de arquitectura

Las decisiones importantes se registran en `docs/decisiones/` como ADR (*Architecture Decision Record*),
numerados en orden: contexto, decisión, alternativas, consecuencias y cómo revertir. Si su cambio
contradice o modifica un ADR existente, actualícelo o escriba uno nuevo en el mismo PR.

## Reglas del proyecto que el código debe respetar

- **Permisos:** toda consulta de estudiantes, grados o asignaciones pasa por `accounts/permissions.py`.
  No filtre por rol en las vistas por su cuenta.
- **Base de datos:** solo el ORM de Django, sin SQL propio de SQLite (ADR 0002).
- **Acceso:** toda vista nueva lleva `@rol_requerido(...)` o `@login_required`.
- **Datos de prueba:** los usuarios ficticios llevan documento `PRUEBA-…` para que el sistema muestre
  el aviso de datos de prueba (riesgo 4 del modelo técnico).
- **Alcance:** las funcionalidades deben corresponder al modelo técnico del proyecto; lo que no esté en
  él se discute con el equipo antes de agregarlo.
