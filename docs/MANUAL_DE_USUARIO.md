# Manual de usuario

Sistema de Gestión de Calificaciones, Asistencia e Informes Académicos
Instituto para el Desarrollo de las Inteligencias Múltiples

Este manual explica cómo usar el sistema según el perfil de cada persona. Para instalarlo, vea
[INSTALACION.md](../INSTALACION.md).

## Ingresar y salir

1. Abra el navegador en <http://127.0.0.1:8000> (el sistema debe estar iniciado; ver la guía de
   instalación).
2. Escriba el **usuario** y la **contraseña** que le entregó la institución y pulse **Ingresar**. El
   usuario no distingue mayúsculas de minúsculas.
3. Para salir, pulse **Cerrar sesión**, abajo en el menú lateral. La sesión también se cierra sola
   después de 2 horas.

Si abre un enlace del sistema sin haber ingresado, primero se le pide ingresar y luego llega a la página
que había abierto.

**Cambiar la contraseña:** pulse su nombre, abajo en el menú lateral → **Mi cuenta**. La nueva contraseña
debe tener al menos 8 caracteres y no puede ser demasiado común ni parecida a su usuario.

Si aparece el aviso **"Datos de prueba"**, la información que ve es simulada y no corresponde a
estudiantes reales.

## Perfiles

| Perfil | Qué puede hacer |
|---|---|
| Docente | Registrar calificaciones, asistencia y anotaciones de sus asignaturas; consultar y enviar informes de los estudiantes de sus grados |
| Estudiante | Consultar su propio informe académico (solo lectura) |
| Padre / acudiente | Consultar el informe de sus acudidos y los informes que le envían (solo lectura) |
| Administrador | Todo lo anterior, más gestionar usuarios, estructura académica y copias de seguridad |

---

## Docente

Al ingresar, el **Panel de consulta** muestra sus asignaturas con dos botones: **Calificaciones** y
**Asistencia**.

### Registrar calificaciones

1. Pulse **Calificaciones** en la asignatura y elija el **periodo** arriba a la derecha.
2. En **Nueva actividad evaluativa** escriba el nombre (por ejemplo, *Taller 2*), el porcentaje que vale
   dentro del periodo y la fecha, y pulse **Agregar actividad**.
   - No se pueden repetir nombres de actividad en la misma asignatura y periodo.
   - Si los porcentajes del periodo no suman 100 %, aparece un aviso.
3. En la planilla escriba la nota de cada estudiante, de **1.0 a 5.0** (acepta punto o coma, y se
   redondea a una décima). Deje la casilla vacía si aún no hay nota.
4. Pulse **Guardar notas**. Si alguna nota no es válida, el sistema la ignora, conserva la anterior y lo
   avisa.

La **definitiva** de cada estudiante es el promedio ponderado de las actividades ya calificadas.

Para borrar una actividad pulse **Eliminar** bajo su nombre. Se borran también todas sus notas.

### Registrar asistencia

1. Pulse **Asistencia** en la asignatura.
2. Elija la **fecha** (por defecto, hoy; no se aceptan fechas futuras).
3. Todos aparecen como **Presente**; marque **Ausente** a quien faltó y pulse **Guardar asistencia**.

A la derecha aparecen las fechas ya registradas; pulse una para revisarla o corregirla.

### Anotaciones

En **Anotaciones** (menú lateral) elija el estudiante, la fecha y escriba la anotación. Solo puede anotar
estudiantes de los grados donde dicta clase y solo puede borrar sus propias anotaciones.

### Consultar y enviar informes

- **Estudiantes:** lista de los estudiantes de sus grados; **Ver informe** abre el informe académico.
- El **informe** muestra, para el periodo elegido: promedio, asistencia, ausencias, calificaciones por
  asignatura, historial académico de todos los periodos y anotaciones. **Imprimir informe** permite
  imprimirlo o guardarlo en PDF desde el navegador.
- Al final del informe, **Enviar informe** lo entrega a los acudientes vinculados, con un mensaje
  opcional. Les llega a su sección **Informes recibidos**.
- **Informes enviados:** muestra los informes que usted envió y si el acudiente ya los leyó.
- **Reportes:** tabla de definitivas, promedio y asistencia de todo un grado en un periodo.

---

## Estudiante

Al ingresar se abre directamente **Mi informe académico**: calificaciones, asistencia, ausencias,
historial y anotaciones. Cambie el periodo arriba a la derecha. Solo puede ver su propia información.

## Padre / acudiente

- **Panel de consulta:** sus acudidos y un aviso si tiene informes sin leer.
- **Ver notas y asistencia:** abre el informe académico del acudido, en cualquier periodo.
- **Informes recibidos:** los informes que le enviaron los docentes, con su mensaje. Al pulsar **Abrir
  informe** queda marcado como leído.

Solo puede ver la información de sus propios acudidos.

---

## Administrador

El **Panel de consulta** muestra el indicador del proyecto (usuarios con acceso frente a la meta de 280) y
cuántos usuarios hay por perfil.

### Usuarios

- **Usuarios → Crear usuario:** nombre, documento, correo, usuario, rol y contraseña.
  - Para un **estudiante**, elija su grado.
  - Para un **acudiente**, marque los estudiantes a su cargo.
- **Editar:** permite cambiar los datos, poner una nueva contraseña (el campo vacío la deja igual) o
  desactivar la cuenta. El rol no se cambia después de creado.
- Un usuario **inactivo** no puede ingresar y no aparece en listas ni reportes. Usted no puede
  desactivar su propia cuenta.

### Gestión académica

Primero cree **grados**, **asignaturas** y **periodos** (con fecha de inicio y fin). Luego, en
**Asignación de docentes**, elija grado, asignatura y docente. Si la combinación grado y asignatura ya
existe, se cambia el docente.

No se puede eliminar un grado, asignatura, periodo o asignación que ya tenga estudiantes, notas o
registros asociados.

### Copias de seguridad

**Copias de seguridad → Crear copia de seguridad** guarda una copia completa de la base de datos en la
carpeta `respaldos/`. Cómo restaurarla se explica en [INSTALACION.md](../INSTALACION.md).

Se recomienda crear una copia al menos al cierre de cada semana y antes de actualizar el sistema.
