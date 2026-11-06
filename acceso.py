"""
Acceso con contraseña a ISOtools.

La app puede publicarse como pública en Streamlit Community Cloud y seguir
protegida: nadie ve una página sin escribir la clave. La clave vive en los
secretos de la app, nunca en el código:

    [acceso]
    clave = "una-clave-larga"

Si no hay clave configurada la app no se abre (falla cerrada), para que un
despliegue con los secretos incompletos no quede expuesto por descuido.
"""
import hmac
import time

import streamlit as st

import estilos

INTENTOS_MAX = 5          # intentos fallidos antes de bloquear
BLOQUEO_SEG = 60          # segundos de espera tras agotar los intentos


def _clave_configurada() -> str:
    try:
        return str(st.secrets["acceso"]["clave"]).strip()
    except Exception:
        return ""


def verificar() -> None:
    """Muestra el ingreso y detiene la página hasta que la clave sea correcta."""
    if st.session_state.get("acceso_ok"):
        destino = st.session_state.pop("acceso_destino", None)
        if destino and not st.query_params.to_dict():
            st.query_params.update(destino)
        return
    if st.query_params.to_dict():
        st.session_state["acceso_destino"] = st.query_params.to_dict()

    st.markdown(estilos.cabecera(None, titulo="ISOtools",
                                 unidad="Sistema de Gestión de Calidad · ISO 9001:2015"),
                unsafe_allow_html=True)
    clave = _clave_configurada()
    _, centro, _ = st.columns([1, 1.4, 1])
    with centro:
        if not clave:
            st.markdown(estilos.aviso(
                "error", "Falta configurar la contraseña",
                "Agrega en Settings ▸ Secrets de la app el bloque<br><code>[acceso]</code><br>"
                "<code>clave = \"tu-clave\"</code><br>y vuelve a cargar la página."), unsafe_allow_html=True)
            st.stop()

        espera = st.session_state.get("acceso_bloqueo", 0) - time.time()
        with st.form("ingreso", border=True):
            st.markdown("**Acceso restringido al personal de STARTEC S.A.**")
            escrita = st.text_input("Contraseña", type="password", key="acceso_clave")
            entrar = st.form_submit_button("Entrar", type="primary", width="stretch")

        if entrar:
            if espera > 0:
                st.warning(f"Demasiados intentos. Espera {int(espera) + 1} segundos.")
            elif hmac.compare_digest(escrita.encode(), clave.encode()):
                st.session_state["acceso_ok"] = True
                st.session_state.pop("acceso_fallos", None)
                st.rerun()
            else:
                fallos = st.session_state.get("acceso_fallos", 0) + 1
                st.session_state["acceso_fallos"] = fallos
                if fallos >= INTENTOS_MAX:
                    st.session_state["acceso_bloqueo"] = time.time() + BLOQUEO_SEG
                    st.session_state["acceso_fallos"] = 0
                    st.error(f"Contraseña incorrecta. Ingreso bloqueado {BLOQUEO_SEG} segundos.")
                else:
                    st.error(f"Contraseña incorrecta. Te quedan {INTENTOS_MAX - fallos} intento(s).")
        st.caption("¿No tienes la contraseña? Pídela a Gestión y Control.")
    st.stop()


def boton_salir() -> None:
    """Cierra la sesión desde la barra lateral."""
    if st.sidebar.button("Cerrar sesión", width="stretch"):
        for k in ("acceso_ok", "acceso_fallos", "acceso_bloqueo"):
            st.session_state.pop(k, None)
        st.rerun()
