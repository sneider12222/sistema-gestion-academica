# ADR 0004 — Los usuarios inactivos no aparecen en ninguna lista

- **Estado:** aceptada
- **Fecha:** 2026-11-16
- **Contexto del proyecto:** migración Flask → Django (ADR 0001)

## Contexto

El esquema original tiene `usuarios.activo` desde el primer día, pero el código del Flask lo usaba
casi solo como puerta de entrada: el login rechazaba a un usuario inactivo y poco más. La regla de
visibilidad (`sga/servicios.py:49-60`) filtraba **por rol**, sin mirar el estado, y esa regla estaba
duplicada en cuatro sitios con cuatro criterios ligeramente distintos: el listado del docente
(`sga/docente.py:33`) sí añadía `AND u.activo = 1`, mientras que `estudiantes_visibles` —la que
alimenta las vistas de consulta y de administración— no lo hacía en ninguna de sus cuatro ramas.

El efecto observable: un estudiante retirado —con la cuenta desactivada— aparecía en el listado de
estudiantes y en el reporte del grado de cualquier administrador, con sus notas y su porcentaje de
asistencia, y desaparecía del listado del docente. Dos pantallas del mismo sistema daban respuestas
distintas sobre la misma persona.

Al unificar la regla en `accounts/permissions.py` (commit `73432e0`) había que decidir
qué hacer con ese caso, porque la tabla de estrategias por rol obliga a definirlo una sola vez.

## Decisión

**Un estudiante con `usuario.is_active = False` no aparece en ninguna lista, para ningún rol.**

La exclusión se implementa en una sola función (`_estudiantes_activos()`,
`accounts/permissions.py:28-29`) que alimenta las cuatro ramas de `estudiantes_visibles()`, y como
`puede_ver()` se construye sobre el mismo queryset, hereda la regla sin código adicional. Un
administrador tampoco lo ve: la desactivación es la forma de decir «esto ya no está en el sistema».

## Alternativas consideradas

**(a) Mantener el comportamiento del legacy: filtrar por rol y no por estado.**
Descartada. Reproduce el defecto que motivó la revisión. Además, al unificar la regla, «no
filtrar» también habría que escribirlo explícitamente, así que el argumento de «no cambiar nada»
no ahorra código ni riesgo.

**(b) Excluirlos de los listados pero permitir verlos por URL directa.**
Descartada. Es la variante más peligrosa: la lista miente sobre lo que el sistema permite. Si el
usuario puede abrir el detalle, entonces el detalle debe listarse; si no puede, `puede_ver` debe
decir que no. Lista y detalle se resuelven con el mismo queryset o se desincronizan.

**(c) Mostrarlos marcados como «inactivo» en el listado del administrador.**
Razonable a futuro, pero es una decisión de producto (UI) y esta fase no tiene vistas. Queda como
candidato para cuando exista el listado de usuarios del administrador, no como excepción dentro de
la capa de permisos.

## Consecuencias

### Positivas

- Lo que el sistema muestra coincide con lo que la institución considera vigente.
- La regla vive en un solo lugar: desactivar a alguien lo saca de listados y detalles a la vez,
  sin tocar cuatro sitios.
- Elimina la posibilidad de que un usuario desactivado siga leyendo información académica por una
  ruta que no pasó por el login actualizado.

### Negativas

- **Se pierde el histórico.** Un estudiante retirado desaparece de los reportes de periodos
  anteriores, aunque sus notas sigan en la base. Para una entrega académica sin requisito de
  archivo histórico es aceptable; para una institución real no lo sería. La solución correcta es
  separar «retirado» (estado académico, mantiene histórico) de «cuenta desactivada» (estado de
  acceso). Eso exige un campo nuevo en `Estudiante`, fuera del alcance de esta fase.
- **Desvía del legacy de forma intencional.** No es un port: es un cambio de comportamiento. Quien
  compare el Flask con el Django encontrará esta diferencia; este ADR es la explicación.

### Sobre el trabajo previo

No se modifica `legacy/flask`. La columna `activo` sigue existiendo y sigue siendo la misma; lo
que cambia es que ahora se respeta en lectura, no solo en el login. Contradice el
comportamiento del código congelado, que se documenta aquí.

## Cómo revertir

1. En `accounts/permissions.py`, cambiar `_estudiantes_activos()` para que devuelva
   `Estudiante.objects.all()` en vez de filtrar por `usuario__is_active=True`.
2. Correr `.venv/bin/python manage.py test accounts`: deben pasar a rojo **seis** tests —
   `test_administrador_no_ve_estudiantes_inactivos`,
   `test_docente_no_ve_estudiantes_inactivos`, `test_administrador_no_ve_inactivo`,
   `test_administrador_ve_todos_los_activos`, `test_docente_ve_los_estudiantes_de_sus_grados`
   y `test_orden_estable_por_grado_y_nombre`. Si pasan verdes, la reversión no se aplicó; si
   fallan menos de seis, se cambió algo más en el camino. (Conteo medido el 2026-11-16: la
   primera versión de este ADR decía cinco y listaba tres.)
3. Decidir y documentar qué pasa con `puede_ver`: al heredar el queryset, se revierte sola.
