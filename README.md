# Repositorio SGC · STARTEC S.A.

Gestor documental del Sistema de Gestión de Calidad (ISO 9001:2015) de STARTEC S.A., hecho en Streamlit.
Reúne en un solo lugar las políticas, manuales, procedimientos, instructivos, matrices, formatos y registros
del SGC, para que cualquier colaborador encuentre lo que necesita y entienda cómo se relaciona con el resto.

## Qué hace la app

| Sección | Para qué sirve |
|---|---|
| **Inicio** | Accesos por tarea ("ejecutar un servicio", "evaluar un proveedor", "reportar una no conformidad"…), conteo por tipo y códigos citados que aún no tienen archivo. |
| **Buscador** (barra lateral) | Busca por código, título o cualquier palabra dentro de los documentos, sin importar tildes. |
| **Árbol** (barra lateral) | Documentos agrupados por macroproceso (EST, MIS, APO) con su jerarquía padre → hijo. |
| **Ficha de documento** | Carátula (código, versión, fecha), resumen, contenido completo, botón al original en Drive, relaciones y registros que genera. Los códigos dentro del texto son enlaces. |
| **Listado maestro** | Tabla filtrable de todos los documentos con versión, dueño y frecuencia de revisión (EST-SGC-DOC-REG-001). |
| **Registros** | Todos los registros exigidos, quién los archiva y su tiempo de retención (cláusula 7.5.3). |
| **Códigos** | Descifra cualquier código y genera el siguiente código libre para un documento nuevo. |
| **Ayuda** | Cómo usar el repositorio, reglas clave, canal de denuncias y a quién preguntar. |

## Estructura

```
.
├── app.py                 # la aplicación Streamlit (vistas y navegación)
├── sgc.py                 # lectura de documentos, relaciones, registros, búsqueda y códigos
├── documentos/            # un archivo Markdown por documento del SGC
│   ├── EST-SGC-POL-001.md
│   └── …
├── requirements.txt
└── .streamlit/config.toml
```

## Ejecutar en su computador

```bash
pip install -r requirements.txt
streamlit run app.py
```

La app abre en http://localhost:8501.

## Publicar en Streamlit Community Cloud (gratis)

1. Entre a https://share.streamlit.io con su cuenta de GitHub.
2. **Create app** → elija este repositorio, rama `main` y archivo `app.py`.
3. **Deploy**. Cada vez que se haga un cambio en GitHub la app se actualiza sola.

Para que solo el personal de STARTEC la vea, en la configuración de la app (Settings → Sharing) cambie
la visibilidad a privada e invite los correos autorizados.

## Cómo agregar o actualizar un documento

Siga EST-SGC-DOC-PRO-001. En el repositorio, cada documento es un archivo `documentos/CODIGO.md`:

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

Texto en Markdown. Se pueden usar tablas, listas y **negritas**.
```

- **codigo**: use la sección *Códigos* de la app para generar el siguiente número libre.
- **drive**: el ID es la parte de la URL de Drive entre `/d/` y `/view`.
- **padre** y **relacion**: ubican el documento en el árbol (Desarrolla, Deriva, Registro, Documento par…).
- Las tablas cuya primera columna se llama `Código del registro` alimentan automáticamente la sección *Registros*.
- Cualquier código escrito en el texto se convierte en enlace; en ALTO / MEDIO / BAJO dentro de una tabla se colorea el nivel.

Al cambiar de versión: actualice `version` y `fecha`, agregue la fila en la *Bitácora de cambios* del documento
y suba también el archivo original a la carpeta iso de Drive.

## Fuente

El contenido se transcribió de los archivos originales de la carpeta **iso** de Google Drive
(STARTEC S.A., versión vigente al 01/09/2026). Los originales firmados siguen siendo la versión controlada.
