"""
ISOtools · STARTEC S.A.

Sistema de gestión de calidad ISO 9001:2015 en una sola aplicación:
  · Sistema documental: repositorio, listado maestro, registros y códigos.
  · Gestión: riesgos, indicadores, calendario de revisión y responsabilidades por cargo.
  · Personal habilitado: control de certificados de colaboradores (APO-THU-CER-INS-001).

Ejecutar con:  streamlit run app.py
"""
from pathlib import Path

import streamlit as st

import acceso
import control_documental as cd
import estilos
import paginas as pg

RAIZ = Path(__file__).parent
st.set_page_config(page_title="ISOtools · STARTEC", page_icon=str(RAIZ / "assets" / "icono_startec.png"),
                   layout="wide", initial_sidebar_state="expanded")
st.logo(str(RAIZ / "assets" / "logo_startec.png"), icon_image=str(RAIZ / "assets" / "icono_startec.png"),
        size="large")
st.markdown(estilos.CSS, unsafe_allow_html=True)
st.markdown("""
<style>
.eyebrow { font-family:'IBM Plex Mono',monospace; font-size:11px; letter-spacing:.16em; text-transform:uppercase;
           color:#2F6DAA; margin-bottom:-6px; }
.muted { color:#66717C; font-size:.92em; }
.mono, a.code, span.code-miss { font-family:'IBM Plex Mono',ui-monospace,monospace; font-size:.88em; }
a.code { text-decoration:none; border-bottom:1px solid currentColor; white-space:nowrap; color:#2F6DAA; }
span.code-miss { border-bottom:1px dotted #9AA3AC; color:#77818B; white-space:nowrap; }
.mac { display:inline-block; font-family:'IBM Plex Mono',monospace; font-size:11px; padding:1px 7px; border-radius:3px; border:1px solid; }
.mac.EST { color:#3C3489; background:#EEEDFE; border-color:#AFA9EC; }
.mac.MIS { color:#0F6E56; background:#E1F5EE; border-color:#5DCAA5; }
.mac.APO { color:#993C1D; background:#FAECE7; border-color:#F0997B; }
.tipo { display:inline-block; font-size:10px; font-weight:600; letter-spacing:.06em; text-transform:uppercase;
        color:#66717C; border:1px solid #CED4DA; padding:0 5px; border-radius:2px; background:#FFFFFF; }
.arbol { font-size:13.5px; line-height:2.0; }
.arbol a { color:#25292D; text-decoration:none; } .arbol a:hover { color:#E8820C; }
.raiz { display:block; background:#25292D; border-left:5px solid #E8820C; padding:14px 20px; margin:6px 0 14px; text-decoration:none; }
.raiz span { font-family:'IBM Plex Mono',monospace; font-size:11px; color:#E8820C; letter-spacing:.08em; }
.raiz b { display:block; color:#FFFFFF; font-family:'Archivo',sans-serif; font-size:19px; margin:2px 0; }
.raiz small { color:#C9CED3; }
.caratula { display:grid; grid-template-columns:1fr auto; border:1.5px solid #25292D; background:#FFFFFF; margin:4px 0 12px; }
.caratula .main { padding:14px 18px; border-right:1.5px solid #25292D; min-width:0; }
.caratula .org { font-family:'IBM Plex Mono',monospace; font-size:10.5px; letter-spacing:.14em; text-transform:uppercase; color:#E8820C; }
.caratula h2 { font-family:'Archivo',sans-serif; margin:2px 0 6px; padding:0; font-size:1.65rem; color:#25292D; }
.caratula .sub { font-size:13px; color:#3E4751; display:flex; gap:8px; flex-wrap:wrap; align-items:center; }
.caratula .side div { padding:7px 16px; border-bottom:1px solid #DFE3E8; display:flex; justify-content:space-between; gap:18px; }
.caratula .side div:last-child { border-bottom:0; }
.caratula .side span { font-size:10.5px; letter-spacing:.08em; text-transform:uppercase; color:#77818B; }
.caratula .side b { font-family:'IBM Plex Mono',monospace; font-weight:500; color:#25292D; }
@media (max-width:640px){ .caratula{grid-template-columns:1fr} .caratula .main{border-right:0;border-bottom:1.5px solid #25292D} }
.rel small { color:#77818B; }
table.heat { border-collapse:separate; border-spacing:4px; width:100%; max-width:340px; }
table.heat th { font-family:'IBM Plex Mono',monospace; font-size:11px; color:#66717C; font-weight:500; padding:2px 4px; }
table.heat td.hm { height:58px; text-align:center; font-family:'IBM Plex Mono',monospace; font-size:20px; font-weight:600; }
td.hm.hi { background:#F6D9D6; color:#7C221D; } td.hm.md { background:#F7E9C9; color:#8A4B00; } td.hm.lo { background:#D8ECDF; color:#14523A; }
.bajada { color:#3E4751; font-size:15px; max-width:80ch; margin:0 0 8px; }
ol.guia { margin:0; padding-left:20px; } ol.guia li { margin:4px 0; font-size:14px; color:#3E4751; }
.kpi-ayuda { display:block; font-size:11.5px; color:#77818B; margin-top:6px; line-height:1.35; }
.kpi--neutro { border-left-color:#2F6DAA; } .kpi--neutro .kpi-valor { color:#2F6DAA; }
.salud { background:#FFFFFF; border:1px solid #DFE3E8; padding:12px 16px; margin-bottom:8px; }
.salud-top { display:flex; justify-content:space-between; align-items:baseline; font-size:14px; }
.salud-pct { font-family:'IBM Plex Mono',monospace; font-weight:600; font-size:18px; }
.salud-pct.ok { color:#1D6B4C; } .salud-pct.medio { color:#B4770B; } .salud-pct.bajo { color:#9C2B24; }
.salud-barra { height:8px; background:#E9ECEF; margin:6px 0 5px; }
.salud-barra span { display:block; height:100%; }
.salud-barra span.ok { background:#1D6B4C; } .salud-barra span.medio { background:#E8820C; } .salud-barra span.bajo { background:#9C2B24; }
.salud small { color:#77818B; font-size:12px; }
.pendiente { border-left:4px solid #9AA3AC; padding-left:12px; }
.pendiente b { display:block; font-size:14px; } .pendiente small { color:#66717C; font-size:12.5px; }
.pendiente.critico { border-left-color:#9C2B24; } .pendiente.alerta { border-left-color:#E8820C; } .pendiente.info { border-left-color:#2F6DAA; }
.tarea b { display:block; font-size:14px; line-height:1.3; min-height:2.6em; } .tarea small { color:#66717C; font-size:12.5px; display:block; min-height:2.4em; }
.paso { display:flex; flex-direction:column; gap:4px; font-size:13.5px; color:#3E4751; }
.paso span { width:28px; height:28px; border-radius:50%; background:#E8820C; color:#FFFFFF; display:grid; place-items:center;
             font-family:'Archivo',sans-serif; font-weight:700; }
.paso b { color:#25292D; font-size:15px; }
.resumen { background:#FFFFFF; border:1px solid #DFE3E8; border-left:4px solid #2F6DAA; padding:12px 18px; font-size:15px; color:#25292D; margin:4px 0 12px; }
.resumen span { display:block; font-family:'IBM Plex Mono',monospace; font-size:10.5px; letter-spacing:.14em; text-transform:uppercase; color:#2F6DAA; margin-bottom:3px; }
.flujo-tit { font-family:'IBM Plex Mono',monospace; font-size:10.5px; letter-spacing:.14em; text-transform:uppercase; color:#66717C; margin:6px 0 6px; }
.flujo { display:flex; gap:0; overflow-x:auto; margin-bottom:14px; padding-bottom:4px; }
.flujo-paso { flex:1 0 130px; position:relative; background:#FFFFFF; border:1px solid #DFE3E8; padding:10px 14px 10px 12px; font-size:12.5px;
              line-height:1.35; color:#25292D; margin-right:14px; }
.flujo-paso:not(:last-child)::after { content:"›"; position:absolute; right:-12px; top:50%; transform:translateY(-50%); color:#E8820C; font-size:20px; font-weight:700; }
.flujo-paso span { display:inline-grid; place-items:center; width:20px; height:20px; border-radius:50%; background:#2F6DAA; color:#FFFFFF;
                   font-size:11px; font-weight:600; margin:0 6px 5px 0; }
.ciclo { display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:10px; margin:6px 0 4px; }
@media (max-width:800px){ .ciclo { grid-template-columns:repeat(2,minmax(0,1fr)); } }
.ciclo-fase { background:#FFFFFF; border:1px solid #DFE3E8; border-top:5px solid; padding:12px 14px; }
.ciclo-fase.f1 { border-top-color:#F9BB06; } .ciclo-fase.f2 { border-top-color:#E8820C; } .ciclo-fase.f3 { border-top-color:#4488C8; } .ciclo-fase.f4 { border-top-color:#2F6DAA; }
.ciclo-fase span { font-family:'IBM Plex Mono',monospace; font-size:11px; color:#77818B; }
.ciclo-fase b { display:block; font-family:'Archivo',sans-serif; font-size:19px; color:#25292D; }
.ciclo-fase small { color:#2F6DAA; font-weight:600; } .ciclo-fase p { font-size:13px; color:#3E4751; margin:4px 0 0; }
.termino b { font-size:15px; color:#25292D; } .termino p { margin:4px 0; font-size:13.5px; color:#3E4751; } .termino small { color:#77818B; }
[data-testid="stSidebarHeader"] img { height:44px !important; }
[data-testid="stExpander"] details { background:#FFFFFF; }
</style>""", unsafe_allow_html=True)

# Nada se muestra sin la contraseña (secreto [acceso] clave)
acceso.verificar()

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
    "iso": st.Page(pg.iso9001, title="ISO 9001 en STARTEC", icon=":material/school:", url_path="iso-9001"),
    "glosario": st.Page(pg.glosario, title="Glosario", icon=":material/menu_book:", url_path="glosario"),
    "prueba": st.Page(pg.prueba, title="Ponte a prueba", icon=":material/quiz:", url_path="prueba"),
    "ayuda": st.Page(pg.ayuda, title="Ayuda", icon=":material/help:", url_path="ayuda"),
})

nav = st.navigation({
    "": [P["inicio"]],
    "Sistema documental": [P["documentos"], P["listado"], P["registros"], P["codigos"]],
    "Gestión": [P["riesgos"], P["indicadores"], P["cargo"]],
    "Personal habilitado": [P["hab_control"], P["hab_cargar"], P["hab_equipo"]],
    "Aprende": [P["iso"], P["glosario"], P["prueba"]],
    "Soporte": [P["ayuda"]],
}, expanded=True)

# Búsqueda global: disponible desde cualquier página
with st.sidebar.form("buscar", clear_on_submit=True, border=False):
    texto = st.text_input("Buscar en los documentos", placeholder="Código, título o palabra")
    if st.form_submit_button("Buscar", width="stretch") and texto.strip():
        st.switch_page(P["documentos"], query_params={"q": texto.strip()})

acceso.boton_salir()


SECCIONES = {
    "Personal habilitado": (["hab_control", "hab_cargar", "hab_equipo"],
                            "Gestión de Talento Humano · APO-THU-CER-INS-001", "Personal habilitado",
                            "Certificados y documentos habilitantes de los colaboradores"),
    "Gestión": (["riesgos", "indicadores", "cargo"], "Sistema de Gestión de Calidad · ISO 9001:2015",
                "Gestión del SGC", "Riesgos, indicadores y responsabilidades"),
    "Aprende": (["iso", "glosario", "prueba"], "Formación · ISO 9001:2015", "Aprende el SGC",
                "La norma explicada con los documentos de STARTEC"),
    "Sistema documental": (["documentos", "listado", "registros", "codigos"], "Sistema de Gestión de Calidad · ISO 9001:2015",
                           "Sistema documental", "Políticas, manuales, procedimientos, formatos y registros"),
}
actual = next(((u, t, d) for _, (ks, u, t, d) in SECCIONES.items()
               if any(P[k].url_path == nav.url_path for k in ks)),
              ("Sistema de Gestión de Calidad · ISO 9001:2015", "ISOtools", "STARTEC S.A. · Gestión de calidad"))
st.markdown(estilos.cabecera(None, titulo=actual[1], unidad=actual[0], detalle=actual[2]), unsafe_allow_html=True)

nav.run()
