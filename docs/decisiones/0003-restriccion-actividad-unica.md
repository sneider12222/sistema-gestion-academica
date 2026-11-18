# ADR 0003 — Restricción de unicidad en actividades evaluativas

- **Estado:** aceptada
- **Fecha:** 2026-11-16
- **Contexto del proyecto:** migración Flask → Django (ADR 0001), base de datos SQLite (ADR 0002)

## Contexto

El esquema original (`sga/schema.sql`, tabla `actividades`) no restringía la combinación
(asignación, periodo, nombre). En la práctica eso permite dos actividades con el mismo nombre en
el mismo periodo de la misma asignatura —dos «Taller 1», por ejemplo— y ninguna forma de
distinguirlas al calificar.

El problema no es cosmético. La definitiva de una materia en un periodo es un promedio ponderado
por el `porcentaje` de cada actividad (`sga/servicios.py:16-21`). Con nombres repetidos, el
docente que revisa el listado de notas ve dos filas idénticas con porcentajes distintos y no
tiene manera de saber cuál corresponde a qué evidencia. Tampoco hay forma de auditar después qué
actividad se calificó.

Durante el port a `models.py` se agregó, sin ADR previo:

```python
constraints = [
    models.UniqueConstraint(
        fields=["asignacion", "periodo", "nombre"],
        name="actividad_unica_por_periodo",
    )
]
```

Ese cambio de esquema se hizo en la misma tarea que el andamiaje, así que quedó registrado en
código pero no en la documentación de decisiones. Este ADR lo formaliza.

## Decisión

**Se mantiene la restricción.** Una asignación no puede tener dos actividades con el mismo nombre
dentro del mismo periodo.

La restricción vive en la base de datos (`UniqueConstraint`), no solo en un formulario, porque el
formulario es una de las puertas de entrada y no la única: el management command `seed`, una
eventual importación de datos y el admin de Django escriben por caminos distintos. Una validación
de aplicación que se olvide en uno de esos caminos deja pasar el duplicado.

## Alternativas consideradas

**(a) Revertir la restricción y quedar igual que el esquema original.**
Descartada. Reproduce el defecto: el sistema permitiría datos que el propio informe no puede
explicar. «El esquema lo permitía» no es una razón para conservar una ambigüedad que ya se
identificó como problema.

**(b) Validar solo en el formulario (`ModelForm.clean`).** Descartada por lo anterior: deja
desprotegidos el `seed`, el admin y cualquier carga masiva. Es exactamente el tipo de validación
que el Explore marcó como riesgo (lógica en las vistas, permisos duplicados, cuatro puertas).

**(c) Cambiar la restricción por (asignación, periodo, fecha).** Descartada. Dos actividades
pueden legítimamente compartir fecha —un quiz y un taller del mismo día—, así que la restricción
bloquearía casos válidos sin resolver el problema real, que es el nombre.

**(d) Agregar `orden` o un identificador visible a la actividad.** Es una mejora real, pero
implica columna nueva, migración y cambios en templates y vistas. No entra en esta fase; queda
como candidato para el trabajo futuro de normalización del modelo académico.

## Consecuencias

### Positivas

- El listado de notas de una materia en un periodo no puede contener dos filas indistinguibles.
- El `seed` falla ruidosamente si genera duplicados, en vez de crear datos ambiguos en silencio.
- La regla queda escrita en la base y en un ADR, no en la memoria de quien escribió el modelo.

### Negativas

- **Restringe de más en un caso legítimo:** dos actividades con el mismo nombre y distinto
  porcentaje en el mismo periodo (p. ej. «Recuperación» con dos cortes). El docente tendrá que
  nombrarlas distinto («Recuperación 1», «Recuperación 2»).
- Toda vista o formulario que cree actividades debe manejar `IntegrityError` con un mensaje
  entendible; si no, el usuario ve un error 500 en vez de «ya existe una actividad con ese nombre».
- El esquema Django deja de ser un calco exacto de `schema.sql`. Es una diferencia **deliberada**
  y ahora está documentada, que era el punto.

### Sobre el trabajo previo

El Flask congelado en `legacy/flask` conserva el esquema sin la restricción. No se modifica:
`legacy/flask` es la referencia de lo que existía, no de lo que debería existir. La diferencia
entre ambos esquemas queda explicada aquí, que es donde se puede encontrar.

## Cómo revertir

1. Quitar el bloque `constraints` de `Actividad.Meta` en `calificaciones/models.py`.
2. `python manage.py makemigrations calificaciones` y `python manage.py migrate`.
   En SQLite, retirar un `UniqueConstraint` reconstruye la tabla; conviene correr
   `python manage.py makemigrations --check` después para confirmar que no quedó deriva.
3. Si el sistema ya está en uso, revisar antes qué datos se habrían duplicado: la reversión es de
   esquema, no de datos, y no borra nada.
