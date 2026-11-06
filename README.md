# ISOtools · STARTEC S.A.

Sistema de Gestión de Calidad ISO 9001:2015 de STARTEC S.A. en una sola aplicación de Streamlit.
Une dos herramientas que antes estaban separadas:

- el **sistema documental** del SGC (políticas, manuales, procedimientos, formatos y registros), y
- el **control de certificados del personal** (antes la app `gestion-de-datos`), que implementa
  APO-THU-CER-INS-001.

## Qué hay en la app

| Sección | Página | Para qué sirve |
|---|---|---|
| | **Inicio** | Tareas frecuentes, estado del sistema hoy (documentos, riesgos ALTO, revisiones por vencer, % del personal en regla) y mapa del sistema. |
| Sistema documental | **Documentos** | Árbol por macroproceso, buscador y ficha de cada documento: carátula, resumen, contenido completo, enlace al original en Drive, relaciones, registros y próxima revisión. |
| | **Listado maestro** | Todos los documentos con versión, dueño y próxima revisión (EST-SGC-DOC-REG-001), más los códigos citados que no existen. |
| | **Registros** | Cada registro exigido, quién lo archiva y su retención (7.5.3). |
| | **Códigos** | Descifra cualquier código y propone el siguiente libre para un documento nuevo. |
| Gestión | **No conformidades** | Registro EST-SGC-NCF-REG-001: cualquiera reporta; cada caso avanza paso a paso (5 porqués, acción correctiva, aprobación, implementación, verificación de eficacia a los 30-90 días, cierre o reapertura) con control de plazos. Calcula solos los indicadores de cierre y eficacia. |
| | **Riesgos** | Matriz unificada + riesgos de cada procedimiento, con mapa de calor P × I y filtros por proceso, nivel y ejecutor. |
| | **Indicadores y revisión** | Los 18 indicadores de los procedimientos con su meta; los que el sistema puede medir muestran su valor. Calendario de revisión documental. |
| | **Mi cargo** | Para cada cargo: rol en el SGC, políticas, tareas, registros, riesgos que controla y certificados que necesita. Todo leído de los documentos. |
| Aprende | **ISO 9001 en STARTEC** | El ciclo Planificar-Hacer-Verificar-Actuar y, por cada capítulo de la norma, qué pide en lenguaje simple y qué documentos de STARTEC lo cumplen. Útil para preparar auditorías. |
| | **Glosario** | Términos de los manuales de STARTEC y básicos de ISO 9001, con buscador. |
| | **Ponte a prueba** | 8 situaciones reales con su explicación y el documento donde está la regla. Para inducción y repaso. |
| Personal habilitado | **Panel de control** | Vencimientos, cumplimiento por persona, expediente individual y auditoría. |
| | **Cargar certificados** | Carga individual, por lotes o compartida (planilla IESS) a Drive, con vigencia calculada. |
| | **Equipo** | Colaboradores, etiquetas, documentos exigibles y supervisores. |
| Soporte | **Ayuda** | Cómo usar la app, reglas clave, canal de denuncias y a quién preguntar. |

Además:

- **Inicio ejecutivo**: indicadores clave, barras de salud del sistema y una lista de pendientes ordenada por urgencia, cada uno con su botón «Resolver».
- **Didáctica en cada página**: un desplegable «¿Cómo se usa esta página?», el resumen «En pocas palabras» de cada documento y «Los pasos en un vistazo» de cada procedimiento.
- **Exportaciones**: listado maestro en Excel, paquete completo para la revisión por la dirección (listado, calendario, indicadores, riesgos, registros y personal habilitado), ficha de responsabilidades por cargo y copia de consulta de cada documento.
- **Identidad STARTEC**: logo en la cabecera y la barra lateral, y paleta tomada del logo (grafito, azul, naranja y amarillo). El logo está en `assets/`; para cambiarlo basta reemplazar esos archivos.

Las páginas del sistema documental funcionan sin ninguna configuración. Personal habilitado necesita la
cuenta de servicio de Google (ver abajo); sin ella, esas tres páginas lo indican y el resto sigue funcionando.

## Estructura

```
app.py                  Entrada: navegación, cabecera y búsqueda global
paginas.py              Páginas del sistema documental y de gestión
sgc.py                  Lectura de documentos, relaciones, riesgos, indicadores y cargos
documentos/             Un archivo Markdown por documento del SGC  ← contenido editable
control_documental.py   Páginas de Personal habilitado
nucleo.py               Google Drive y Sheets, tabla de control y cobertura
personas.py             Colaboradores, supervisores y bitácora
reglas.py               Fechas, vigencias y semáforo (compartido con notificar.py)
ajustes.py              Identificadores, vigencias, catálogos y requisitos  ← configuración
estilos.py              Identidad visual
notificar.py            Recordatorios por correo (GitHub Actions)
.github/workflows/      Ejecución diaria de los recordatorios
acceso.py               Contraseña de ingreso
mejora.py               No conformidades: flujo, plazos e indicadores (pestaña «No conformidades» del Sheet)
pagina_mejora.py        Página de No conformidades
originales.py           Descarga de los originales de Drive con la cuenta de servicio
assets/                 Logo e icono de STARTEC
docs/                   Notas de diseño de Personal habilitado
```

## Contraseña de acceso

ISOtools se publica como app **pública** de Streamlit (así no ocupa el único espacio privado de la cuenta),
pero nadie ve ninguna página sin escribir la contraseña. Se configura en los secretos de la app:

```toml
[acceso]
clave = "una-clave-larga-y-dificil"
```

- Sin ese bloque la app **no abre** (falla cerrada), para que un despliegue incompleto no quede expuesto.
- Tras 5 intentos fallidos el ingreso se bloquea 60 segundos.
- Para cambiar la clave basta con editar el secreto; todos deberán volver a ingresar.
- Cámbiala cuando alguien con acceso deje la empresa.

## Archivos originales de Drive

Los Word y Excel originales viven en la carpeta **iso** de Google Drive, que no se comparte con cada
colaborador. La app los descarga con su cuenta de servicio y los entrega a quien entró con la contraseña
(botón **Descargar original** en la ficha de cada documento). Para activarlo, una sola vez:

1. Copie el `client_email` del bloque `[gcp_service_account]` de los secretos.
2. Abra la carpeta iso en Drive ▸ **Compartir** ▸ agregue ese correo como **Lector** (sin notificar).

La página **Ayuda ▸ Archivos originales** muestra si la conexión funciona. Mientras no esté activa,
el botón abre Drive y solo sirve a quien tenga acceso a la carpeta.

## Publicar en Streamlit Community Cloud

1. En https://share.streamlit.io ▸ **Create app** ▸ repositorio `asesor-design/ISOtools`, rama `main`,
   archivo **`app.py`**.
2. **Advanced settings** ▸ Python **3.13** y en *Secrets* pega:
   - el bloque `[acceso]` con la contraseña, y
   - el bloque `[gcp_service_account]` (el mismo que usa la app de certificados) para activar Personal habilitado.
3. **Deploy**. Luego en **Settings ▸ Sharing** deja la app como **pública**: la contraseña la protege.

**Si al elegir el repositorio aparece «You can only have one private app per workspace»:** las apps que
salen de un repositorio privado nacen privadas, y ese espacio ya lo usa otra app. Para desplegar:
cambia por un momento esa otra app a pública (Settings ▸ Sharing), despliega ISOtools, pásala a pública
y devuelve la otra app a privada. Son un par de minutos.

### Recordatorios por correo

`notificar.py` corre desde GitHub Actions cada día laborable a las 07:00 de Ecuador. Como ahora vive en
este repositorio, hay que cargar sus secretos aquí: **Settings ▸ Secrets and variables ▸ Actions** de
`ISOtools`, con los mismos valores que tenía `gestion-de-datos`:

| Secreto | Valor |
|---|---|
| `GCP_SERVICE_ACCOUNT` | el JSON completo de la cuenta de servicio, en una línea |
| `SMTP_USER` | correo desde el que se envía |
| `SMTP_PASSWORD` | contraseña de aplicación |
| `CORREO_ADMIN` | destinatario del consolidado (respaldo) |

Mientras la app `gestion-de-datos` siga en uso, deja el workflow activo **solo en uno** de los dos
repositorios (Actions ▸ Recordatorio de certificados ▸ Disable en el otro) para que no lleguen correos duplicados. Prueba local sin enviar nada: `python notificar.py --prueba`.

## Ejecutar en su computador

```bash
pip install -r requirements.txt
streamlit run app.py
```

Para Personal habilitado copia `secrets.toml.example` como `.streamlit/secrets.toml` y complétalo.

## Agregar o actualizar un documento del SGC

Siga EST-SGC-DOC-PRO-001. Cada documento es un archivo `documentos/CODIGO.md`:

```markdown
---
codigo: APO-THU-IND-FOR-001
titulo: Acta de inducción
version: 1.0
fecha: 15/11/2026
drive: ID_DEL_ARCHIVO_EN_DRIVE
formato: docx
dueno: Gestión y Control
padre: APO-THU-SEL-PRO-001
relacion: Registro
revision: Cada 2 años
resumen: Una o dos frases que expliquen para qué sirve el documento.
---

# Acta de inducción

## Objetivo

Texto en Markdown: tablas, listas y **negritas**.
```

- **codigo**: use la página *Códigos* para obtener el siguiente número libre.
- **drive**: el ID es la parte de la URL de Drive entre `/d/` y `/view`.
- **fecha**: con ella se calcula la próxima revisión en *Indicadores y revisión*.
- **padre** y **relacion** ubican el documento en el árbol.
- Convenciones que la app lee automáticamente:
  - tablas cuya primera columna es `Código del registro` → página *Registros*;
  - sección `## Indicadores de gestión` con viñetas `- **Nombre:** cálculo. Meta: X.` → *Indicadores*;
  - sección `## Matriz de riesgos y controles asociados` → *Riesgos*;
  - tablas con columna `Responsable` y `Política`, y viñetas `- **Cargo:** tarea` bajo `## Responsables` → *Mi cargo*.

Al cambiar de versión: actualice `version` y `fecha`, agregue la fila en la *Bitácora de cambios* y suba
también el original a la carpeta iso de Drive, que sigue siendo la versión controlada.
