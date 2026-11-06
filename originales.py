"""
Entrega de los archivos originales (Word, Excel) de la carpeta iso de Google Drive.

Los originales viven en Drive y no se comparten con cada colaborador. La app los
descarga con su cuenta de servicio (la misma de Personal habilitado) y se los
entrega a quien ya pasó la contraseña de ISOtools. Para eso basta compartir la
carpeta iso UNA vez con el correo de la cuenta de servicio, como Lector.
"""
from __future__ import annotations

import io

import streamlit as st

from sgc import DRIVE_FOLDER

CARPETA_ISO = DRIVE_FOLDER.rstrip("/").split("/")[-1]

MIME = {
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "pdf": "application/pdf",
    "html": "text/html",
}


def cuenta_servicio() -> str:
    """Correo de la cuenta de servicio configurada, o cadena vacía si no hay."""
    try:
        return str(st.secrets["gcp_service_account"]["client_email"])
    except Exception:
        return ""


def _drive():
    import nucleo
    return nucleo.conexiones()[1]


@st.cache_data(ttl=600, show_spinner=False)
def estado() -> dict:
    """
    ¿Puede la app leer la carpeta iso?
    Devuelve {"ok": bool, "motivo": "sin_google" | "sin_permiso" | "error" | "", "detalle": str}.
    """
    if not cuenta_servicio():
        return {"ok": False, "motivo": "sin_google", "detalle": ""}
    try:
        import nucleo
        nucleo.reintentar(lambda: _drive().files().get(
            fileId=CARPETA_ISO, fields="id", supportsAllDrives=True).execute())
        return {"ok": True, "motivo": "", "detalle": ""}
    except Exception as e:  # 404/403: la carpeta no está compartida con la cuenta
        texto = str(e)
        motivo = "sin_permiso" if any(c in texto for c in ("404", "403", "notFound", "insufficient")) else "error"
        return {"ok": False, "motivo": motivo, "detalle": texto[:300]}


@st.cache_data(ttl=1800, show_spinner=False, max_entries=60)
def contenido(file_id: str) -> bytes:
    """Bytes del archivo original, descargados por la cuenta de servicio."""
    import nucleo
    from googleapiclient.http import MediaIoBaseDownload

    def bajar():
        buf = io.BytesIO()
        pedido = _drive().files().get_media(fileId=file_id, supportsAllDrives=True)
        descarga = MediaIoBaseDownload(buf, pedido)
        listo = False
        while not listo:
            _, listo = descarga.next_chunk()
        return buf.getvalue()
    return nucleo.reintentar(bajar)


def instrucciones_permiso() -> str:
    correo = cuenta_servicio()
    return (
        "La app todavía no puede leer la carpeta **iso** de Google Drive. Para que cualquiera con la "
        "contraseña de ISOtools pueda descargar los originales, el dueño de la carpeta "
        "(asesor@startec.com.ec) debe compartirla **una sola vez**:\n\n"
        f"1. Abra la [carpeta iso]({DRIVE_FOLDER}) ▸ **Compartir**.\n"
        f"2. Agregue el correo `{correo}` con permiso **Lector** y desmarque «Notificar».\n"
        "3. Vuelva aquí y recargue la página (puede tardar hasta 10 minutos en reflejarse).\n\n"
        "No hace falta compartir nada con los colaboradores: la app les entrega el archivo."
    )
