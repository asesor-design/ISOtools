"""
Núcleo: conexiones con Google, esquema de la hoja, operaciones en Drive y
composición de la tabla de control.

Este módulo no importa `personas` para evitar una dependencia circular; los
datos de colaboradores entran como parámetro donde hacen falta.
"""

import io
import os
import ssl
import time
import base64
import uuid
import socket
from datetime import datetime

import gspread
import pandas as pd
import streamlit as st
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

import ajustes as cfg
import reglas as r

ALCANCES = ["https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"]


# ==========================================================================================
# CONEXIONES
# ==========================================================================================
@st.cache_resource(show_spinner=False)
def conexiones():
    """Cliente de Sheets y servicio de Drive con la cuenta de servicio."""
    if "gcp_service_account" not in st.secrets:
        raise RuntimeError("Falta el bloque [gcp_service_account] en los secretos.")
    credenciales = Credentials.from_service_account_info(
        dict(st.secrets["gcp_service_account"]), scopes=ALCANCES)
    return gspread.authorize(credenciales), build(
        "drive", "v3", credentials=credenciales, cache_discovery=False)


#  Fallos de red, no de configuración: un corte de TLS, un socket caído o un
#  error 5xx de Google. Son pasajeros, pero la conexión queda cacheada y rota,
#  así que hay que descartarla y reconstruirla en lugar de propagar el error.
TRANSITORIOS = (ssl.SSLError, socket.timeout, socket.gaierror,
                ConnectionError, TimeoutError, BrokenPipeError, OSError)

MARCAS_TRANSITORIAS = ("ssl", "record_layer", "timed out", "timeout", "connection",
                       "broken pipe", "eof occurred", "transport", "503", "500", "502")


def es_transitorio(error):
    """Distingue un problema de red de uno de permisos o de datos."""
    if isinstance(error, TRANSITORIOS):
        return True
    texto = str(error).lower()
    return any(m in texto for m in MARCAS_TRANSITORIAS)


def reintentar(operacion, intentos=3):
    """
    Ejecuta la operación reconstruyendo la conexión si falla por red.

    Sin esto, un corte momentáneo de TLS deja el cliente cacheado inservible y
    la aplicación caída hasta que alguien la reinicie a mano.
    """
    ultimo = None
    for intento in range(intentos):
        try:
            return operacion()
        except Exception as e:
            if not es_transitorio(e) or intento == intentos - 1:
                raise
            ultimo = e
            conexiones.clear()          # descarta credenciales y sockets muertos
            pestana.clear()             # el handle de la hoja cuelga del cliente viejo
            time.sleep(0.8 * (intento + 1))
    raise ultimo


def ident(clave, defecto):
    """Permite sobrescribir un identificador desde los secretos."""
    try:
        return st.secrets.get(clave, defecto)
    except Exception:
        return defecto


def ensanchar(hoja, columnas_necesarias):
    """
    Amplía la cuadrícula si el esquema del código tiene más columnas que la hoja.

    Google Sheets no crea columnas al escribir fuera del rango: devuelve
    «exceeds grid limits». Al agregar campos nuevos en una versión posterior hay
    que pedir el espacio primero.
    """
    try:
        actuales = hoja.col_count
    except Exception:
        return
    if actuales < columnas_necesarias:
        hoja.add_cols(columnas_necesarias - actuales)


def sincronizar_esquema(hoja):
    """Adapta la hoja al esquema del código sin perder nada de lo registrado."""
    encabezados = hoja.row_values(1)
    if not encabezados:
        hoja.append_row(cfg.COLUMNAS_SHEET, value_input_option="USER_ENTERED")
        return list(cfg.COLUMNAS_SHEET)

    for viejo, nuevo in cfg.RENOMBRES_COLUMNA.items():
        if viejo in encabezados and nuevo not in encabezados:
            indice = encabezados.index(viejo) + 1
            hoja.update_cell(1, indice, nuevo)
            encabezados[indice - 1] = nuevo

    faltantes = [c for c in cfg.COLUMNAS_SHEET if c not in encabezados]
    if faltantes:
        ultima = len(hoja.col_values(1))
        ensanchar(hoja, len(encabezados) + len(faltantes))
        for columna in faltantes:
            encabezados.append(columna)
            indice = len(encabezados)
            hoja.update_cell(1, indice, columna)
            defecto = cfg.VALORES_DEFECTO.get(columna, "")
            if ultima > 1 and defecto:
                rango = (gspread.utils.rowcol_to_a1(2, indice) + ":" +
                         gspread.utils.rowcol_to_a1(ultima, indice))
                hoja.update(rango, [[defecto] for _ in range(ultima - 1)],
                            value_input_option="USER_ENTERED")
    return encabezados


@st.cache_resource(show_spinner=False)
def pestana():
    """Pestaña de documentos y sus encabezados reales."""
    cliente, _ = conexiones()
    libro = cliente.open_by_key(ident("sheet_id", cfg.SHEET_ID))
    hoja = None
    gid = ident("sheet_gid", cfg.SHEET_GID)
    if gid is not None:
        try:
            hoja = libro.get_worksheet_by_id(int(gid))
        except Exception:
            hoja = None
    if hoja is None:
        try:
            hoja = libro.worksheet(cfg.NOMBRE_HOJA)
        except gspread.WorksheetNotFound:
            hoja = libro.add_worksheet(title=cfg.NOMBRE_HOJA, rows=2000,
                                       cols=len(cfg.COLUMNAS_SHEET) + 4)
    return hoja, sincronizar_esquema(hoja)


@st.cache_data(ttl=cfg.TTL_CACHE, show_spinner=False)
def leer_hoja():
    """
    Contenido de la hoja de documentos. Se descartan las filas totalmente
    vacías, pero NO se reindexa: la reconciliación traduce el índice del
    DataFrame a número de fila real del Sheet (índice + 2).
    """
    hoja, encabezados = pestana()
    valores = reintentar(hoja.get_all_values)
    if len(valores) < 2:
        return pd.DataFrame(columns=encabezados or cfg.COLUMNAS_SHEET)
    cabecera = valores[0]
    ancho = len(cabecera)
    cuerpo = [(f + [""] * ancho)[:ancho] for f in valores[1:]]
    df = pd.DataFrame(cuerpo, columns=cabecera)
    df = df[df.apply(lambda f: any(str(v).strip() for v in f), axis=1)]

    #  Se garantizan las columnas del esquema aunque la hoja sea anterior, para
    #  que ninguna consulta tenga que preguntar si el campo existe.
    for columna in cfg.COLUMNAS_SHEET:
        if columna not in df.columns:
            df[columna] = ""
    return df


def invalidar_cache():
    leer_hoja.clear()


def diagnostico():
    """Comprueba los accesos y resume el estado para la barra lateral."""
    res = {"drive": None, "hoja": None, "registros": 0, "error": None,
           "transitorio": False}

    def consultar_drive():
        _, servicio = conexiones()
        return servicio.files().get(
            fileId=ident("carpeta_raiz_id", cfg.CARPETA_RAIZ_ID),
            fields="id,name", supportsAllDrives=True).execute()

    try:
        res["drive"] = reintentar(consultar_drive).get("name")
    except Exception as e:
        res["error"] = f"Drive: {e}"
        res["transitorio"] = es_transitorio(e)
        return res

    try:
        hoja, _ = pestana()
        res["hoja"] = hoja.title
        res["registros"] = len(leer_hoja())
    except Exception as e:
        res["error"] = f"Sheets: {e}"
        res["transitorio"] = es_transitorio(e)
    return res


# ==========================================================================================
# CARPETAS Y ARCHIVOS EN DRIVE
# ==========================================================================================
def _buscar_carpeta(padre, nombre=None, empieza_por=None):
    _, servicio = conexiones()
    consulta = (f"'{padre}' in parents and trashed = false "
                f"and mimeType = 'application/vnd.google-apps.folder'")
    if nombre:
        consulta += f" and name = '{nombre}'"
    elif empieza_por:
        consulta += f" and name contains '{empieza_por}'"
    hallados = servicio.files().list(
        q=consulta, fields="files(id,name)", pageSize=10,
        supportsAllDrives=True, includeItemsFromAllDrives=True).execute().get("files", [])
    if empieza_por:
        hallados = [h for h in hallados if h["name"].startswith(empieza_por)]
    return hallados[0] if hallados else None


def _crear_carpeta(nombre, padre):
    _, servicio = conexiones()
    return servicio.files().create(
        body={"name": nombre, "parents": [padre],
              "mimeType": "application/vnd.google-apps.folder"},
        fields="id,name", supportsAllDrives=True).execute()


@st.cache_data(ttl=cfg.TTL_CACHE, show_spinner=False)
def carpeta_colaborador(cedula, nombre, rol):
    """
    Subcarpeta del colaborador. La CÉDULA es la llave: si el nombre se escribe
    distinto en otra carga, el archivo cae igual en la carpeta correcta.
    """
    raiz = ident("carpeta_raiz_id", cfg.CARPETA_RAIZ_ID)
    cedula = str(cedula).strip()
    hallada = _buscar_carpeta(raiz, empieza_por=cedula)
    if hallada:
        return hallada["id"], hallada["name"]

    nombre_carpeta = f"{cedula} - {str(nombre).strip().upper()}"
    if rol:
        nombre_carpeta += f" ({str(rol).strip()})"
    nueva = _crear_carpeta(nombre_carpeta, raiz)
    return nueva["id"], nueva["name"]


@st.cache_data(ttl=cfg.TTL_CACHE, show_spinner=False)
def carpeta_compartidos():
    """Carpeta única donde vive un documento que cubre a varios colaboradores."""
    raiz = ident("carpeta_raiz_id", cfg.CARPETA_RAIZ_ID)
    hallada = _buscar_carpeta(raiz, nombre=cfg.NOMBRE_COMPARTIDOS)
    if hallada:
        return hallada["id"], hallada["name"]
    nueva = _crear_carpeta(cfg.NOMBRE_COMPARTIDOS, raiz)
    return nueva["id"], nueva["name"]


def carpeta_historico(carpeta_id):
    """Subcarpeta Histórico. Si la recibida ya ES el histórico, la devuelve igual."""
    _, servicio = conexiones()
    info = servicio.files().get(fileId=carpeta_id, fields="name",
                                supportsAllDrives=True).execute()
    if info.get("name") == cfg.NOMBRE_HISTORICO:
        return carpeta_id
    hallada = _buscar_carpeta(carpeta_id, nombre=cfg.NOMBRE_HISTORICO)
    return hallada["id"] if hallada else _crear_carpeta(
        cfg.NOMBRE_HISTORICO, carpeta_id)["id"]


def mover_a_historico(archivo_id):
    """Archiva el documento reemplazado. Su enlace sigue sirviendo: el id no cambia."""
    try:
        _, servicio = conexiones()
        padres = servicio.files().get(fileId=archivo_id, fields="parents",
                                      supportsAllDrives=True).execute().get("parents", [])
        if not padres:
            return False
        destino = carpeta_historico(padres[0])
        if destino == padres[0]:
            return False
        servicio.files().update(fileId=archivo_id, addParents=destino,
                                removeParents=padres[0], fields="id",
                                supportsAllDrives=True).execute()
        return True
    except Exception:
        return False


def subir_archivo(contenido, nombre_destino, mime, carpeta_id):
    """Sube los bytes y devuelve (id, enlace de visualización)."""
    _, servicio = conexiones()
    medio = MediaIoBaseUpload(io.BytesIO(contenido),
                              mimetype=mime or "application/octet-stream", resumable=False)
    archivo = reintentar(lambda: servicio.files().create(
        body={"name": nombre_destino, "parents": [carpeta_id]},
        media_body=medio, fields="id,webViewLink", supportsAllDrives=True).execute())
    return archivo["id"], (archivo.get("webViewLink")
                           or f"https://drive.google.com/file/d/{archivo['id']}/view")


@st.cache_data(ttl=cfg.TTL_LOGO, show_spinner=False)
def logo_incrustado():
    """Primera imagen de la carpeta del logo, como data URI. None si no hay."""
    try:
        _, servicio = conexiones()
        consulta = (f"'{ident('carpeta_logo_id', cfg.CARPETA_LOGO_ID)}' in parents "
                    f"and trashed = false and mimeType contains 'image/'")
        archivos = servicio.files().list(
            q=consulta, fields="files(id,name,mimeType)", pageSize=5, orderBy="name",
            supportsAllDrives=True, includeItemsFromAllDrives=True
        ).execute().get("files", [])
        if not archivos:
            return None
        datos = servicio.files().get_media(fileId=archivos[0]["id"],
                                           supportsAllDrives=True).execute()
        return f"data:{archivos[0]['mimeType']};base64,{base64.b64encode(datos).decode()}"
    except Exception:
        return None


# ==========================================================================================
# ESCRITURA DE DOCUMENTOS
# ==========================================================================================
def _nombre_archivo(tipo, cedula, rol, emision, extension):
    sufijo = cfg.ABREVIATURAS_TIPO.get(tipo, r.limpiar_texto(tipo, 24))
    return (f"{sufijo}_{r.limpiar_texto(cedula, 15)}_{r.limpiar_texto(rol, 20)}_"
            f"{emision.strftime('%Y%m%d')}_{r.ahora().strftime('%H%M%S%f')[:12]}"
            f"{extension}")


def _fila(cedula, nombre, rol, etiquetado, tipo, emision, caducidad, revision,
          nombre_archivo, carpeta, enlace, archivo_id, grupo, observaciones):
    return {
        "Marca_Temporal": r.sello(),
        "Nombre": str(nombre).strip().title(),
        "Cedula": str(cedula).strip(),
        "Rol": str(rol or "").strip(),
        "Diebold": "SÍ" if etiquetado else "NO",
        "Tipo_Documento": tipo,
        "Fecha_Emision": emision.strftime(cfg.FORMATO_FECHA),
        "Fecha_Caducidad": caducidad.strftime(cfg.FORMATO_FECHA) if caducidad else "",
        "Fecha_Revision": revision.strftime(cfg.FORMATO_FECHA) if revision else "",
        "Nombre_Archivo": nombre_archivo,
        "Carpeta_Colaborador": carpeta,
        "Enlace_Drive": enlace,
        "ID_Archivo": archivo_id,
        "Grupo_Documento": grupo or "",
        "Observaciones": str(observaciones or "").strip(),
        "Vigencia_Registro": "ACTUAL",
    }


def cargar_documento(cedula, nombre, rol, etiquetado, tipo, contenido, nombre_original,
                     mime, emision, caducidad, observaciones=""):
    """Sube un documento individual. Devuelve (fila, nombre de la carpeta)."""
    carpeta_id, carpeta_nombre = carpeta_colaborador(cedula, nombre, rol)
    extension = os.path.splitext(nombre_original)[1].lower() or ".pdf"
    archivo = _nombre_archivo(tipo, cedula, rol, emision, extension)
    archivo_id, enlace = subir_archivo(contenido, archivo, mime, carpeta_id)
    revision = r.fecha_revision(tipo, emision, etiquetado)
    return _fila(cedula, nombre, rol, etiquetado, tipo, emision, caducidad, revision,
                 archivo, carpeta_nombre, enlace, archivo_id, "", observaciones), carpeta_nombre


def cargar_compartido(personas, tipo, contenido, nombre_original, mime,
                      emision, caducidad, observaciones=""):
    """
    Documento único que cubre a varios colaboradores, como la planilla del IESS.

    El archivo se sube UNA sola vez a la carpeta de compartidos y se generan
    tantas filas como colaboradores cubiertos, todas apuntando al mismo archivo.
    Así cada persona lo tiene en su expediente sin duplicar el PDF, y el
    semáforo funciona igual que con cualquier otro documento.

    `personas` es una lista de diccionarios con cedula, nombre, rol y etiquetado.
    """
    carpeta_id, carpeta_nombre = carpeta_compartidos()
    extension = os.path.splitext(nombre_original)[1].lower() or ".pdf"
    sufijo = cfg.ABREVIATURAS_TIPO.get(tipo, r.limpiar_texto(tipo, 24))
    archivo = (f"{sufijo}_COMPARTIDO_{emision.strftime('%Y%m%d')}_"
               f"{len(personas)}PERSONAS_{r.ahora().strftime('%H%M%S')}{extension}")

    archivo_id, enlace = subir_archivo(contenido, archivo, mime, carpeta_id)
    grupo = uuid.uuid4().hex[:12]

    filas = []
    for p in personas:
        revision = r.fecha_revision(tipo, emision, p.get("etiquetado"))
        filas.append(_fila(p["cedula"], p["nombre"], p.get("rol"), p.get("etiquetado"),
                           tipo, emision, caducidad, revision, archivo, carpeta_nombre,
                           enlace, archivo_id, grupo, observaciones))
    return filas, archivo, grupo


def escribir_filas(filas):
    """Agrega las filas en una sola operación, guiándose por los encabezados reales."""
    if not filas:
        return
    hoja, encabezados = pestana()
    reintentar(lambda: hoja.append_rows(
        [[f.get(c, "") for c in encabezados] for f in filas],
        value_input_option="USER_ENTERED"))
    invalidar_cache()


def reconciliar(pares):
    """
    Para cada (cédula, tipo) deja UN registro ACTUAL: el de caducidad más lejana.
    Los demás pasan a REEMPLAZADO y su archivo se mueve a Histórico.

    Los documentos compartidos no se archivan en Drive: el archivo es uno solo y
    lo comparten varias personas, así que moverlo afectaría a todas. Solo se
    marca el registro.
    """
    hoja, encabezados = pestana()
    df = leer_hoja()
    if df.empty or "Vigencia_Registro" not in df.columns:
        return 0

    columna = encabezados.index("Vigencia_Registro") + 1
    cambios, archivar = [], []

    for cedula, tipo in {(str(c).strip(), t) for c, t in pares}:
        clave = r.clave_cedula(cedula)
        grupo = df[(df["Cedula"].map(r.clave_cedula) == clave) &
                   (df["Tipo_Documento"] == tipo)]
        if grupo.empty:
            continue

        def prioridad(indice):
            reg = df.loc[indice]
            cad = r.parsear_fecha(reg.get("Fecha_Caducidad")) or datetime.min
            carga = r.parsear_fecha(str(reg.get("Marca_Temporal", "")).split(" ")[0]) \
                or datetime.min
            return (cad, carga)

        vigente = max(grupo.index, key=prioridad)
        for indice in grupo.index:
            nuevo = "ACTUAL" if indice == vigente else "REEMPLAZADO"
            if str(df.at[indice, "Vigencia_Registro"]).strip().upper() != nuevo:
                cambios.append({
                    "range": gspread.utils.rowcol_to_a1(indice + 2, columna),
                    "values": [[nuevo]]})
                compartido = str(df.at[indice, "Grupo_Documento"] or "").strip()
                archivo_id = str(df.at[indice, "ID_Archivo"] or "").strip()
                if nuevo == "REEMPLAZADO" and archivo_id and not compartido:
                    archivar.append(archivo_id)

    if cambios:
        hoja.batch_update(cambios, value_input_option="USER_ENTERED")
        invalidar_cache()
    return sum(mover_a_historico(a) for a in archivar)


# ==========================================================================================
# TABLA DE CONTROL
# ==========================================================================================
COLUMNAS_TABLA = ["Colaborador", "Cédula", "Rol", "Supervisor", "Etiqueta", "Persona",
                  "Tipo de Documento", "Emisión", "Caducidad", "Revisión",
                  "Días Restantes", "Estado", "Registro", "Documento"]


def tabla_control(fichas=None):
    """
    Vista del dashboard. `fichas` es el DataFrame de colaboradores; cuando se
    entrega, cada documento hereda el estado, la etiqueta y el supervisor
    vigentes de la persona, no los que tenía al momento de la carga.
    """
    df = leer_hoja()
    if df.empty:
        return pd.DataFrame(columns=COLUMNAS_TABLA)

    indice = {}
    if fichas is not None and not fichas.empty:
        indice = {str(f["Cedula"]).strip(): f for _, f in fichas.iterrows()}

    filas = []
    for _, reg in df.iterrows():
        def campo(clave):
            return str(reg.get(clave, "") or "")

        cedula = campo("Cedula").strip()
        ficha = indice.get(cedula, {})
        etiqueta = str(ficha.get("Etiqueta", "")).strip()
        estado_persona = str(ficha.get("Estado", cfg.ACTIVO)).strip().upper() or cfg.ACTIVO

        #  Los documentos cargados antes de esta versión no tienen fecha de
        #  revisión. Si la persona lleva la etiqueta, se deduce al vuelo desde la
        #  emisión, así el historial también respeta la renovación anual.
        revision = campo("Fecha_Revision")
        if not revision and etiqueta:
            calculada = r.fecha_revision(campo("Tipo_Documento"),
                                         campo("Fecha_Emision"), True)
            revision = calculada.strftime(cfg.FORMATO_FECHA) if calculada else ""

        dias, estado = r.calcular_estado(campo("Fecha_Caducidad"), revision)
        vigencia = campo("Vigencia_Registro").strip().upper() or "ACTUAL"

        filas.append({
            "Colaborador": ficha.get("Nombre", campo("Nombre")),
            "Cédula": r.cedula_visible(cedula),
            "Rol": ficha.get("Rol", campo("Rol")),
            "Supervisor": str(ficha.get("Supervisor", "")),
            "Etiqueta": etiqueta,
            "Persona": estado_persona.capitalize(),
            "Tipo de Documento": campo("Tipo_Documento"),
            "Emisión": campo("Fecha_Emision"),
            "Caducidad": campo("Fecha_Caducidad"),
            "Revisión": revision,
            "Días Restantes": None if dias is None else int(dias),
            "Estado": estado,
            "Registro": "Histórico" if vigencia == "REEMPLAZADO" else "Actual",
            "Documento": campo("Enlace_Drive"),
        })

    tabla = pd.DataFrame(filas, columns=COLUMNAS_TABLA)
    tabla = tabla.sort_values("Días Restantes", na_position="last").reset_index(drop=True)

    # Tipos explícitos: sin columnas de objetos mixtos, la conversión a Arrow no
    # tiene que inferir nada. Es la fuente habitual de caídas nativas.
    tabla["Días Restantes"] = pd.array(
        [None if pd.isna(v) else int(v) for v in tabla["Días Restantes"]], dtype="Int64")
    for columna in COLUMNAS_TABLA:
        if columna != "Días Restantes":
            tabla[columna] = tabla[columna].fillna("").astype("string")
    return tabla


COLUMNAS_COBERTURA = ["Colaborador", "Cédula", "Rol", "Supervisor",
                      "Tipo de Documento", "Caducidad", "Días Restantes", "Estado"]


def cobertura(tabla, fichas):
    """
    Cruza lo exigible con lo cargado y devuelve el expediente completo de cada
    colaborador activo, incluidas las casillas vacías.

    Es la vista que responde «¿quién no está en regla?», que no es lo mismo que
    «¿a quién le vence algo?». Un colaborador sin certificado médico nunca
    aparece en las alertas de vencimiento, porque no hay nada que venza; aquí sí.
    """
    if fichas is None or fichas.empty:
        return pd.DataFrame(columns=COLUMNAS_COBERTURA)

    vigentes = tabla[(tabla["Registro"] == "Actual") &
                     (tabla["Persona"].str.upper() != cfg.INACTIVO)] if len(tabla) \
        else tabla
    cargados = {}
    for _, doc in vigentes.iterrows():
        cargados[(r.clave_cedula(doc["Cédula"]), doc["Tipo de Documento"])] = doc

    filas = []
    for _, f in fichas.iterrows():
        if str(f.get("Estado", cfg.ACTIVO)).strip().upper() == cfg.INACTIVO:
            continue
        cedula = str(f["Cedula"]).strip()
        clave = r.clave_cedula(cedula)
        for tipo in cfg.requeridos_de(f):
            doc = cargados.get((clave, tipo))
            filas.append({
                "Colaborador": f.get("Nombre", ""),
                "Cédula": cedula,
                "Rol": str(f.get("Rol", "")),
                "Supervisor": str(f.get("Supervisor", "")),
                "Tipo de Documento": tipo,
                "Caducidad": doc["Caducidad"] if doc is not None else "",
                "Días Restantes": (doc["Días Restantes"] if doc is not None else None),
                "Estado": doc["Estado"] if doc is not None else cfg.ESTADO_FALTANTE,
            })

    df = pd.DataFrame(filas, columns=COLUMNAS_COBERTURA)
    if df.empty:
        return df
    df["Días Restantes"] = pd.array(
        [None if pd.isna(v) else int(v) for v in df["Días Restantes"]], dtype="Int64")
    for c in COLUMNAS_COBERTURA:
        if c != "Días Restantes":
            df[c] = df[c].fillna("").astype("string")
    orden = {cfg.ESTADO_FALTANTE: 0, cfg.ESTADO_VENCIDO: 1, cfg.ESTADO_REVISION: 2,
             cfg.ESTADO_POR_RENOVAR: 3, cfg.ESTADO_VIGENTE: 4}
    df["_o"] = df["Estado"].map(lambda e: orden.get(e, 5))
    return df.sort_values(["_o", "Colaborador"]).drop(columns="_o").reset_index(drop=True)


def resumen_cobertura(cob):
    """Métricas de cumplimiento: cuántas casillas y cuántas personas en regla."""
    if cob.empty:
        return {"casillas": 0, "faltantes": 0, "vencidos": 0, "en_regla": 0,
                "personas": 0, "personas_ok": 0, "porcentaje": 0}
    incumple = cob["Estado"].isin(cfg.ESTADOS_INCUMPLE)
    personas = cob["Cédula"].nunique()
    con_problema = cob[incumple]["Cédula"].nunique()
    en_regla = int((~incumple).sum())
    return {
        "casillas": len(cob),
        "faltantes": int((cob["Estado"] == cfg.ESTADO_FALTANTE).sum()),
        "vencidos": int((cob["Estado"] == cfg.ESTADO_VENCIDO).sum()),
        "en_regla": en_regla,
        "personas": personas,
        "personas_ok": personas - con_problema,
        "porcentaje": round((personas - con_problema) / personas * 100) if personas else 0,
    }


def cumplimiento_por_persona(cob):
    """
    Una fila por colaborador con su avance: cuántos documentos exigibles tiene en
    regla, cuántos le faltan y cuántos están vencidos.

    Es la lectura que pide un jefe: no «hay 14 casillas rojas» sino «estas cuatro
    personas no están en regla y esto es lo que les falta».
    """
    if cob.empty:
        return pd.DataFrame(columns=["Colaborador", "Cédula", "Rol", "Supervisor",
                                     "Exigibles", "En regla", "Sin cargar", "Vencidos",
                                     "Avance", "Situación"])
    filas = []
    for cedula, grupo in cob.groupby("Cédula", sort=False):
        exigibles = len(grupo)
        faltan = int((grupo["Estado"] == cfg.ESTADO_FALTANTE).sum())
        vencidos = int((grupo["Estado"] == cfg.ESTADO_VENCIDO).sum())
        en_regla = exigibles - faltan - vencidos
        primero = grupo.iloc[0]
        filas.append({
            "Colaborador": primero["Colaborador"],
            "Cédula": cedula,
            "Rol": primero["Rol"],
            "Supervisor": primero["Supervisor"],
            "Exigibles": exigibles,
            "En regla": en_regla,
            "Sin cargar": faltan,
            "Vencidos": vencidos,
            "Avance": round(en_regla / exigibles * 100) if exigibles else 0,
            "Situación": ("✅ Completo" if en_regla == exigibles
                          else ("🔴 Vencidos" if vencidos else "⬛ Incompleto")),
        })
    df = pd.DataFrame(filas)
    return df.sort_values(["Avance", "Colaborador"]).reset_index(drop=True)


def expediente(tabla, cedula):
    """Todos los documentos de una persona, vigentes e históricos."""
    if tabla.empty:
        return tabla
    clave = r.clave_cedula(cedula)
    return tabla[tabla["Cédula"].map(r.clave_cedula) == clave]


def aplicar_filtros(tabla, estado, tipo, busqueda, ver_historico,
                    supervisor="Todos", etiqueta="Todos", incluir_inactivos=False):
    """Filtra la vista. Todo ocurre en memoria: ningún filtro consulta la API."""
    df = tabla.copy()
    if df.empty:
        return df

    if not ver_historico:
        df = df[df["Registro"] == "Actual"]
    if not incluir_inactivos:
        df = df[df["Persona"].str.upper() != cfg.INACTIVO]

    mapa = {"🔴 Vencidos": [cfg.ESTADO_VENCIDO],
            "🟠 Renovar por etiqueta": [cfg.ESTADO_REVISION],
            "🟡 Por renovar": [cfg.ESTADO_POR_RENOVAR],
            "🟢 Vigentes": [cfg.ESTADO_VIGENTE],
            "⚠️ Requieren acción": cfg.ESTADOS_CRITICOS}
    if estado in mapa:
        df = df[df["Estado"].isin(mapa[estado])]

    if tipo and tipo != "Todos":
        df = df[df["Tipo de Documento"] == tipo]
    if supervisor and supervisor != "Todos":
        df = df[df["Supervisor"] == supervisor]
    if etiqueta and etiqueta != "Todos":
        df = (df[df["Etiqueta"] != ""] if etiqueta == cfg.ETIQUETA_ESPECIAL
              else df[df["Etiqueta"] == ""])

    termino = (busqueda or "").strip().lower()
    if termino:
        df = df[df.apply(
            lambda f: termino in " ".join(str(v).lower() for v in f.values), axis=1)]
    return df


def indicadores(tabla):
    """Métricas sobre los registros actuales de colaboradores activos."""
    historicos = int((tabla["Registro"] == "Histórico").sum()) if len(tabla) else 0
    df = tabla[(tabla["Registro"] == "Actual") &
               (tabla["Persona"].str.upper() != cfg.INACTIVO)] if len(tabla) else tabla
    total = len(df)
    vigentes = int((df["Estado"] == cfg.ESTADO_VIGENTE).sum()) if total else 0
    return {
        "colaboradores": int(df["Cédula"].replace("", pd.NA).dropna().nunique()) if total else 0,
        "documentos": total,
        "vencidos": int((df["Estado"] == cfg.ESTADO_VENCIDO).sum()) if total else 0,
        "revision": int((df["Estado"] == cfg.ESTADO_REVISION).sum()) if total else 0,
        "renovar": int((df["Estado"] == cfg.ESTADO_POR_RENOVAR).sum()) if total else 0,
        "vigentes": vigentes,
        "historicos": historicos,
        "cumplimiento": round(vigentes / total * 100) if total else 0,
    }
