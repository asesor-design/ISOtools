"""
ISOtools · STARTEC S.A.

Sistema de gestión de calidad ISO 9001:2015 en una sola aplicación:
  · Sistema documental: repositorio, listado maestro, registros y códigos.
  · Gestión: riesgos, indicadores, calendario de revisión y responsabilidades por cargo.
  · Personal habilitado: control de certificados de colaboradores (APO-THU-CER-INS-001).

Ejecutar con:  streamlit run app.py
"""
import streamlit as st

import control_documental as cd
import estilos
import paginas as pg

st.set_page_config(page_title="ISOtools · STARTEC", page_icon="🗂️", layout="wide",
                   initial_sidebar_state="expanded")
st.markdown(estilos.CSS, unsafe_allow_html=True)
st.markdown("""
<style>
.eyebrow { font-family:'IBM Plex Mono',monospace; font-size:11px; letter-spacing:.16em; text-transform:uppercase;
           color:#A8802B; margin-bottom:-6px; }
.muted { color:#5F7784; font-size:.92em; }
.mono, a.code, span.code-miss { font-family:'IBM Plex Mono',ui-monospace,monospace; font-size:.88em; }
a.code { text-decoration:none; border-bottom:1px solid currentColor; white-space:nowrap; color:#274B5C; }
span.code-miss { border-bottom:1px dotted #8DA0AB; color:#6B818D; white-space:nowrap; }
.mac { display:inline-block; font-family:'IBM Plex Mono',monospace; font-size:11px; padding:1px 7px; border-radius:3px; border:1px solid; }
.mac.EST { color:#3C3489; background:#EEEDFE; border-color:#AFA9EC; }
.mac.MIS { color:#0F6E56; background:#E1F5EE; border-color:#5DCAA5; }
.mac.APO { color:#993C1D; background:#FAECE7; border-color:#F0997B; }
.tipo { display:inline-block; font-size:10px; font-weight:600; letter-spacing:.06em; text-transform:uppercase;
        color:#5F7784; border:1px solid #C9D4DB; padding:0 5px; border-radius:2px; background:#FFFFFF; }
.arbol { font-size:13.5px; line-height:2.0; }
.arbol a { color:#0E2733; text-decoration:none; } .arbol a:hover { color:#A8802B; }
.raiz { display:block; background:#0E2733; border-left:5px solid #A8802B; padding:14px 20px; margin:6px 0 14px; text-decoration:none; }
.raiz span { font-family:'IBM Plex Mono',monospace; font-size:11px; color:#A8802B; letter-spacing:.08em; }
.raiz b { display:block; color:#FFFFFF; font-family:'Archivo',sans-serif; font-size:19px; margin:2px 0; }
.raiz small { color:#C7D6DE; }
.caratula { display:grid; grid-template-columns:1fr auto; border:1.5px solid #0E2733; background:#FFFFFF; margin:4px 0 12px; }
.caratula .main { padding:14px 18px; border-right:1.5px solid #0E2733; min-width:0; }
.caratula .org { font-family:'IBM Plex Mono',monospace; font-size:10.5px; letter-spacing:.14em; text-transform:uppercase; color:#A8802B; }
.caratula h2 { font-family:'Archivo',sans-serif; margin:2px 0 6px; padding:0; font-size:1.65rem; color:#0E2733; }
.caratula .sub { font-size:13px; color:#33505F; display:flex; gap:8px; flex-wrap:wrap; align-items:center; }
.caratula .side div { padding:7px 16px; border-bottom:1px solid #DAE1E6; display:flex; justify-content:space-between; gap:18px; }
.caratula .side div:last-child { border-bottom:0; }
.caratula .side span { font-size:10.5px; letter-spacing:.08em; text-transform:uppercase; color:#6B818D; }
.caratula .side b { font-family:'IBM Plex Mono',monospace; font-weight:500; color:#0E2733; }
@media (max-width:640px){ .caratula{grid-template-columns:1fr} .caratula .main{border-right:0;border-bottom:1.5px solid #0E2733} }
.rel small { color:#6B818D; }
table.heat { border-collapse:separate; border-spacing:4px; width:100%; max-width:340px; }
table.heat th { font-family:'IBM Plex Mono',monospace; font-size:11px; color:#5F7784; font-weight:500; padding:2px 4px; }
table.heat td.hm { height:58px; text-align:center; font-family:'IBM Plex Mono',monospace; font-size:20px; font-weight:600; }
td.hm.hi { background:#F6D9D6; color:#7C221D; } td.hm.md { background:#F7E9C9; color:#6F5417; } td.hm.lo { background:#D8ECDF; color:#14523A; }
</style>""", unsafe_allow_html=True)

P = pg.P
P.update({
    "inicio": st.Page(pg.inicio, title="Inicio", icon=":material/home:", default=True),
    "documentos": st.Page(pg.documentos, title="Documentos", icon=":material/description:", url_path="documentos"),
    "listado": st.Page(pg.listado, title="Listado maestro", icon=":material/table_rows:", url_path="listado"),
    "registros": st.Page(pg.registros, title="Registros", icon=":material/inventory_2:", url_path="registros"),
    "codigos": st.Page(pg.codigos, title="Códigos", icon=":material/tag:", url_path="codigos"),
    "riesgos": st.Page(pg.riesgos, title="Riesgos", icon=":material/warning:", url_path="riesgos"),
    "indicadores": st.Page(pg.indicadores, title="Indicadores y revisión", icon=":material/monitoring:", url_path="indicadores"),
    "cargo": st.Page(pg.mi_cargo, title="Mi cargo", icon=":material/badge:", url_path="mi-cargo"),
    "hab_control": st.Page(cd.pagina_control, title="Panel de control", icon=":material/verified_user:", url_path="personal"),
    "hab_cargar": st.Page(cd.pagina_documentos, title="Cargar certificados", icon=":material/upload_file:", url_path="cargar"),
    "hab_equipo": st.Page(cd.pagina_equipo, title="Equipo", icon=":material/groups:", url_path="equipo"),
    "ayuda": st.Page(pg.ayuda, title="Ayuda", icon=":material/help:", url_path="ayuda"),
})

nav = st.navigation({
    "": [P["inicio"]],
    "Sistema documental": [P["documentos"], P["listado"], P["registros"], P["codigos"]],
    "Gestión": [P["riesgos"], P["indicadores"], P["cargo"]],
    "Personal habilitado": [P["hab_control"], P["hab_cargar"], P["hab_equipo"]],
    "Soporte": [P["ayuda"]],
})

# Búsqueda global: disponible desde cualquier página
with st.sidebar.form("buscar", clear_on_submit=True, border=False):
    texto = st.text_input("Buscar en los documentos", placeholder="Código, título o palabra")
    if st.form_submit_button("Buscar", width="stretch") and texto.strip():
        st.switch_page(P["documentos"], query_params={"q": texto.strip()})


@st.cache_data(ttl=3600, show_spinner=False)
def logo():
    if not pg.hay_google():
        return None
    try:
        import nucleo
        return nucleo.logo_incrustado()
    except Exception:
        return None


SECCION = {
    "Personal habilitado": ("Gestión de Talento Humano · APO-THU-CER-INS-001", "Personal habilitado"),
    "Gestión": ("Sistema de Gestión de Calidad · ISO 9001:2015", "Gestión del SGC"),
}
seccion = next((s for s, ps in {"Personal habilitado": ["hab_control", "hab_cargar", "hab_equipo"],
                                 "Gestión": ["riesgos", "indicadores", "cargo"]}.items()
                if any(P[k] is nav or P[k].url_path == nav.url_path for k in ps)), None)
unidad, titulo = SECCION.get(seccion, ("Sistema de Gestión de Calidad · ISO 9001:2015", "ISOtools"))
st.markdown(estilos.cabecera(logo(), titulo=titulo, unidad=unidad), unsafe_allow_html=True)

nav.run()
