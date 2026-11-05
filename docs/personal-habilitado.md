# Personal habilitado · historial de versiones

Notas de diseño heredadas de la app gestion-de-datos, hoy integrada en ISOtools como la sección Personal habilitado.


---

## Versión 2 · Colaboradores, vigencias y avisos

### Vigencias automáticas

La fecha de caducidad ya no se escribe: se calcula desde el tipo y la fecha de emisión.

| Documento | Vigencia |
|---|---|
| Certificado Médico | 1 año |
| Antecedentes Penales | 3 meses |
| Fiscalía | 3 meses |
| Riesgos de Trabajo (los cuatro) | 4 años |
| Afiliación IESS | 1 mes |
| Otros | manual |

El cálculo es por meses calendario, no por días: emisión 11-02-2026 → caducidad 11-02-2027. Cuando el día no existe en el mes destino (31 de enero + 1 mes) cae al último día de ese mes.

### Registro de colaboradores

Pestaña `Colaboradores` en la hoja. Cada persona tiene una ficha única por cédula con rol, supervisor, etiqueta y estado. Los documentos solo la referencian, así que cambiar de supervisor es una edición, no cientos.

**Activo / inactivo.** Un inactivo conserva su expediente pero sale de los indicadores y deja de generar avisos. Al cumplir un año inactivo aparece en la lista de depuración; el sistema **nunca borra por su cuenta**.

### Etiqueta Diebold

Pasó de ser una propiedad del documento a serlo **del colaborador**. Los certificados de riesgos de trabajo duran 4 años por ley, pero para las personas etiquetadas se guarda además una **fecha de revisión** al año. El semáforo usa la más próxima de las dos, y aparece un estado propio: 🟠 Renovar por etiqueta, que distingue "el cliente exige renovarlo" de "está vencido".

### Documento compartido

Para la planilla del IESS y otros documentos colectivos. El archivo se sube **una vez** a `Documentos compartidos` y genera una fila por colaborador cubierto, todas apuntando al mismo archivo. Cada persona lo tiene en su expediente sin duplicar el PDF, y el semáforo funciona igual. Al renovarse, el registro anterior se marca como reemplazado pero el archivo no se mueve a Histórico: es uno solo y lo comparten varios.

### Recordatorios por correo

`notificar.py` corre desde GitHub Actions (`.github/workflows/recordatorios.yml`), cada día laborable a las 07:00 de Ecuador. **No puede vivir dentro de la aplicación**: Streamlit solo ejecuta código cuando alguien abre la página.

Cada supervisor recibe únicamente los vencimientos de su equipo; el administrador recibe el consolidado más los inactivos pendientes de depurar. Solo se avisa de colaboradores activos.

Secretos en GitHub (Settings ▸ Secrets and variables ▸ Actions):

| Secreto | Valor |
|---|---|
| `GCP_SERVICE_ACCOUNT` | el JSON completo de la cuenta de servicio, en una línea |
| `SMTP_USER` | correo desde el que se envía |
| `SMTP_PASSWORD` | **contraseña de aplicación**, no la del correo |
| `CORREO_ADMIN` | destinatario del consolidado |

Con Workspace, la contraseña de aplicación se genera en la cuenta de Google (requiere verificación en dos pasos activa). Si el administrador de Grupostar bloquea las contraseñas de aplicación, la alternativa es un servicio transaccional como Resend, que cambia solo la función `enviar()`.

Prueba local sin enviar nada: `python notificar.py --prueba`

### Estructura

```
control_documental.py  Interfaz: páginas de Personal habilitado
nucleo.py           Google, Drive, escritura y tabla de control
personas.py         Colaboradores y supervisores
reglas.py           Fechas, vigencias y semáforo (sin dependencias)
notificar.py        Recordatorios por correo (GitHub Actions)
ajustes.py          Identificadores, catálogos y reglas  ← lo que se edita
estilos.py          Identidad visual
```

`reglas.py` no importa Streamlit ni Google a propósito: es la capa que comparten la app y el notificador, de modo que ambos apliquen exactamente el mismo criterio de vencimiento.


---

## Versión 3 · Cumplimiento y presentación

### Análisis de cobertura: qué falta, no solo qué vence

La mejora de fondo de esta versión. Hasta aquí el sistema solo conocía los documentos que **existen**, así que un colaborador sin certificado médico no aparecía en ninguna alerta —no hay nada que venza— pese a ser el incumplimiento más grave.

Ahora cada colaborador declara **sus propios** documentos exigibles y el panel de **Cumplimiento** cruza lo exigible contra lo cargado. Una persona sin ningún documento deja de ser invisible.

**Los requisitos son de la persona, no del cargo.** Los certificados de riesgos dependen de la tarea que ejecuta cada quien: dos guardias del mismo puesto pueden necesitar uno alturas y el otro nada. En `ajustes.py` solo se fija el mínimo común:

```python
REQUERIDOS_BASE = ["Certificado Médico", "Antecedentes Penales", "Afiliación IESS"]
SUGERIDOS_POR_ROL = {"Guardia de Seguridad": ["Fiscalía"], ...}   # solo propone
```

Lo demás se marca en la ficha de cada persona, y se edita en bloque desde **Equipo ▸ Etiquetas y equipos ▸ Documentos exigibles**, con tres operaciones: agregar, quitar o reemplazar. Cuando una cuadrilla empieza a trabajar en alturas se marcan todos de una vez sin pisar lo que cada quien ya tenía.

Una ficha con la celda `Requeridos` vacía cae a la sugerencia de su cargo, para no romper las creadas antes de esta versión. La marca `NINGUNO` significa, explícitamente, que solo se le exigen los básicos.

El indicador de cumplimiento cuenta personas con expediente completo, que es más exigente y más honesto que contar documentos vigentes.

### Expediente individual

Responde la pregunta más natural del día a día —«¿cómo está fulano?»— que antes obligaba a filtrar el listado. Muestra una tarjeta por documento exigible, incluidas las casillas vacías, con los días restantes en grande, más el historial de renovaciones plegado.

### Navegación de tres paneles

Antes eran cinco pestañas de primer nivel que mezclaban tareas de distinta naturaleza.

| Panel | Contiene |
|---|---|
| **Panel de control** | Vencimientos · Cumplimiento · Expediente |
| **Documentos** | Un selector de modo: individual, masivo o compartido |
| **Equipo** | Colaboradores · Etiquetas y equipos · Supervisores |

El panel de control va primero porque responde la pregunta de todos los días. Las tres formas de cargar se unificaron en una sola tarea con un selector, porque cargar un documento es una sola cosa: el modo es un detalle, no una decisión previa.

### Detalles de presentación

Un **titular de riesgo** bajo la cabecera resume lo que requiere gestión hoy, visible desde cualquier panel. Los rótulos de sección perdieron la numeración arbitraria y ganaron una línea de contexto. Los estados vacíos explican qué falta y qué hacer en lugar de dejar la pantalla en blanco. Y la lista de vigencias pasó a un desplegable en la barra lateral, que estaba saturada.


---

## Versión 4 · Auditoría y consistencia

### Cédulas: el error silencioso

Google Sheets interpreta `0104567890` como un número y le quita el cero inicial. Si la ficha se guardó como texto y el documento como número, el cruce falla y **el expediente entero aparece como no cargado** aunque los archivos estén ahí. Era la causa del cumplimiento en cero.

Todas las comparaciones de cédula pasan ahora por `reglas.clave_cedula()`, que compara solo los dígitos significativos. La pantalla sigue mostrando la cédula con sus ceros. Afecta al cruce de cobertura, al expediente individual, a la reconciliación de versiones y a la asignación en bloque.

### Supervisores: lista única

La hoja puede contener el mismo nombre escrito de varias formas, por la importación del historial o por cargas repetidas. Los selectores colapsan esas variantes en una sola entrada, ignorando tildes, mayúsculas y espacios sobrantes; se conserva el correo de la variante que lo tenga y se muestra la escritura mejor formateada. Un alta con un nombre equivalente actualiza la entrada existente en vez de duplicarla.

### Perfil de administrador

La hoja `Supervisores` tiene ahora una columna `Rol`:

| Perfil | Qué recibe |
|---|---|
| Supervisor | Los vencimientos de los colaboradores a su cargo |
| Administrador | El consolidado de toda la plantilla, incluidos los que no tienen supervisor |

Puede haber varios administradores y se gestionan desde la aplicación, sin tocar los secretos de GitHub. La variable `CORREO_ADMIN` queda como respaldo por si nadie está marcado.

### Bitácora de auditoría

Pestaña `Bitácora` en la hoja: un registro **de solo anexado** que la aplicación nunca edita ni borra. Anota cargas individuales, masivas y compartidas, reemplazos de versión, altas y ediciones de ficha, cambios de estado, de etiqueta, de requisitos y asignaciones de supervisor.

Escribe en silencio: si la bitácora falla, la operación del usuario continúa. Un registro de auditoría no debe poder bloquear el trabajo que documenta.

### Control de consistencia

En **Panel de control ▸ Auditoría**, junto a la bitácora, el sistema se revisa a sí mismo y reporta lo que una auditoría encontraría: documentos de personas sin ficha, colaboradores activos sin supervisor, supervisores sin correo, ausencia de administrador, documentos sin fecha de caducidad e inactivos que superaron el plazo de retención.

Es la vista que conviene tener abierta antes de una revisión externa.
