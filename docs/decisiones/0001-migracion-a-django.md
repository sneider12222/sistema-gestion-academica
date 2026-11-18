# ADR 0001 — Migración del sistema de Flask a Django

- **Estado:** aceptada
- **Fecha:** 2026-11-14
- **Decisores:** Piloto del proyecto (decisión), equipo de desarrollo (ejecución)
- **Rama de trabajo:** `django-migration`
- **Documentos relacionados:** ADR 0002 (motor de base de datos), Feature Doc de la migración

## Contexto

El Acta de Constitución y el Modelo Técnico declaran **Django** como framework y
**MySQL/MariaDB** como motor de base de datos. El repositorio, en cambio, está implementado en
**Flask** sobre **SQLite**: `app.py` como punto de entrada, un paquete `sga/` con la lógica de
negocio y los templates, y un `schema.sql` que define la base.

Ambas cosas existen y funcionan: el sistema Flask opera, y los documentos firmados describen
otro stack. Lo que hay es una **inconsistencia entre la documentación y el código**. No es un
defecto funcional ni el resultado de una decisión equivocada de una persona; la documentación y
la implementación avanzaron por caminos separados y hoy describen sistemas distintos.

La entrega de la asignatura es el **2026-11-30**. El sistema entregado debe corresponder con lo
que el Acta y el Modelo Técnico comprometen. Eso obliga a cerrar la brecha, y hacerlo sin
desperdiciar el trabajo ya construido.

## Decisión

Migrar el sistema a **Django 5.x**, conservando el trabajo previo, con estas condiciones:

1. **Rama de trabajo:** la migración vive en `django-migration`. `main` conserva el Flask
   desplegable y no se toca hasta que el merge esté verificado.
2. **Snapshot congelado:** se crea la rama `legacy/flask` desde `main`. Contiene el Flask
   actual más estos ADRs y **no se modifica** durante la migración. Es la referencia inmutable
   y el respaldo funcional.
3. **Estrategia mixta (A+B):**
   - **A — se porta la lógica de negocio:** `schema.sql` → `models.py`, `servicios.py` →
     `services.py`, y el mapa de roles y permisos (docente, estudiante, acudiente,
     administrador). Las reglas ya probadas se conservan.
   - **B — se rehacen los templates** con Django templates, usando los de Flask como
     **referencia visual**, no como copia 1:1. La presentación se adapta al nuevo framework.
4. **Nada se descarta:** el Flask queda como referencia y respaldo; la lógica se porta; los
   datos de estructura (grados, asignaturas, periodos, usuarios de prueba) se migran como
   fixtures de Django.

## Alternativas consideradas

| Alternativa | Por qué no se eligió |
| :--- | :--- |
| **(a) Mantener Flask y corregir la documentación** | El stack declarado es parte del compromiso firmado con el docente, no un detalle editable. Cambiarlo exige un trámite que no cabe en el plazo, y deja el entregable por fuera de lo pactado. |
| **(b) Migrar sin congelar el Flask** | Sin snapshot se pierde la referencia para comparar y el respaldo si la migración falla. Congelar cuesta una rama y protege la reversión y la verificación. |
| **(c) Reescritura total desde cero** | Descarta lógica de negocio ya escrita y probada —reglas de calificaciones, asistencia y permisos— y multiplica el riesgo en una ventana de dos semanas. Se prefiere conservar lo que funciona y reescribir solo la capa que el framework cambia. |

## Consecuencias

### Positivas

- El sistema entregado coincide con el stack que declara la documentación firmada.
- El trabajo previo no se pierde: se porta la lógica y el Flask queda como referencia.
- Django aporta ORM, migraciones y admin, lo que reduce el código artesanal de autenticación y
  CRUD.
- `main` sigue desplegable durante toda la migración: si algo se complica, hay sistema que
  mostrar.

### Negativas

- Los templates se rehacen; es esfuerzo que no se recupera del Flask.
- Conviven dos bases de código hasta el merge, y el equipo debe tener claro en qué rama trabaja.
- Existe riesgo de divergencia si alguien modifica `legacy/flask` por error.

### Sobre el trabajo previo

- **No se descarta nada.** La lógica de negocio se porta; el Flask queda congelado en
  `legacy/flask`. **Corrección 2026-11-16:** no existe base SQLite dentro del repositorio
  (`instance/` está en `.gitignore` y el árbol no trae el archivo), así que no hay datos que
  migrar. La estructura (grados, asignaturas, periodos, usuarios de prueba) se reconstruye desde
  `sga/seed.py`, que es determinista (`random.Random(2026)`), y se porta como management command
  `seed`. Notas y asistencia se regeneran con el mismo comando.
- `legacy/flask` es también el archivo de estos ADRs: la decisión queda junto al código que
  reemplaza.

## Cómo revertir

La reversión es barata porque `main` no se modifica:

1. **Revertir = no mergear.** Mientras `django-migration` no se integre, `main` sigue siendo el
   Flask desplegable.
2. **Volver al estado anterior:** `git checkout main`. Es el mismo código que el snapshot de
   `legacy/flask`, salvo los ADRs.
3. Si el merge ya ocurrió y hay que deshacerlo, `main` conserva el historial: se revierte el
   merge con `git revert -m 1 <commit>` y el Flask vuelve a ser el estado desplegable.
