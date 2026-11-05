"""Repositorio SGC · STARTEC S.A.

Gestor documental del Sistema de Gestión de Calidad (ISO 9001:2015).
Ejecutar con:  streamlit run app.py
"""
from __future__ import annotations

import html
import re

import pandas as pd
import streamlit as st

from sgc import (CODE_RE, DRIVE_FOLDER, MACROS, MACRO_ORDER, PROC_MACRO, PROCS, SUBS,
                 TYPE_ORDER, TYPES, Repositorio, descifrar)

st.set_page_config(page_title="Repositorio SGC · STARTEC", page_icon="📁", layout="wide")


@st.cache_resource
def cargar() -> Repositorio:
    return Repositorio()


repo = cargar()

# ---------------------------------------------------------------- estilo
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=IBM+Plex+Sans+Condensed:wght@600;700&display=swap');
h1, h2, h3, .caratula h2 {font-family:"IBM Plex Sans Condensed","Arial Narrow",sans-serif !important; letter-spacing:.005em}
.mono, a.code, span.code-miss {font-family:"IBM Plex Mono",ui-monospace,monospace; font-size:.88em}
a.code {text-decoration:none; border-bottom:1px solid currentColor; white-space:nowrap}
span.code-miss {border-bottom:1px dotted; opacity:.7; white-space:nowrap}
.mac {display:inline-block; font-family:"IBM Plex Mono",monospace; font-size:11px; padding:2px 7px; border-radius:5px; border:1px solid}
.mac.EST {color:#3C3489; background:#EEEDFE; border-color:#AFA9EC}
.mac.MIS {color:#0F6E56; background:#E1F5EE; border-color:#5DCAA5}
.mac.APO {color:#993C1D; background:#FAECE7; border-color:#F0997B}
.caratula {display:grid; grid-template-columns:1fr auto; border:1.5px solid rgba(128,128,128,.7); border-radius:4px; overflow:hidden; margin-bottom:12px}
.caratula .main {padding:14px 18px; border-right:1.5px solid rgba(128,128,128,.7); min-width:0}
.caratula .org {font-size:11px; letter-spacing:.1em; text-transform:uppercase; opacity:.65; font-weight:600}
.caratula h2 {margin:2px 0 6px; padding:0; font-size:1.7rem}
.caratula .sub {font-size:13px; opacity:.8; display:flex; gap:8px; flex-wrap:wrap; align-items:center}
.caratula .side div {padding:7px 16px; border-bottom:1px solid rgba(128,128,128,.3); display:flex; justify-content:space-between; gap:18px}
.caratula .side div:last-child {border-bottom:0}
.caratula .side span {font-size:11px; letter-spacing:.07em; text-transform:uppercase; opacity:.65}
.caratula .side b {font-family:"IBM Plex Mono",monospace; font-weight:500}
@media (max-width:640px){.caratula{grid-template-columns:1fr}.caratula .main{border-right:0;border-bottom:1.5px solid rgba(128,128,128,.7)}}
.ficha small {opacity:.7}
</style>
""", unsafe_allow_html=True)

LEVEL = {"ALTO": "red", "MEDIO": "orange", "BAJO": "green", "ROJO": "red", "AMARILLO": "orange", "VERDE": "green"}


# ---------------------------------------------------------------- navegación
def ir(vista: str = "inicio", doc: str | None = None) -> None:
    st.query_params.clear()
    st.query_params["v"] = vista
    if doc:
        st.query_params["doc"] = doc
    st.session_state["q"] = ""


def link(code: str) -> str:
    """Código como enlace a su ficha (o marcado si no tiene archivo)."""
    if code in repo.docs:
        t = html.escape(repo.docs[code].titulo)
        return f'<a class="code" href="?v=doc&doc={code}" target="_self" title="{t}">{code}</a>'
    return f'<span class="code-miss" title="Citado en el sistema, sin archivo en el repositorio">{code}</span>'


def enlazar(texto: str) -> str:
    """Prepara el Markdown de un documento: enlaza códigos y colorea niveles de riesgo."""
    texto = CODE_RE.sub(lambda m: link(m.group()), texto)

    def nivel(m: re.Match) -> str:
        palabra, resto = m.group(1), m.group(2) or ""
        return f"| :{LEVEL[palabra]}-background[**{palabra}{resto}**] |"
    texto = re.sub(r"\| (ALTO|MEDIO|BAJO)( \(\d+\))? \|", nivel, texto)
    texto = re.sub(r"\| (ALTO|MEDIO|BAJO)( \(\d+\))? \|", nivel, texto)  # celdas contiguas
    texto = re.sub(r"\| (VERDE|AMARILLO|ROJO) · ([^|]+) \|",
                   lambda m: f"| :{LEVEL[m.group(1)]}-background[**{m.group(2).strip()}**] |", texto)
    return texto


# ---------------------------------------------------------------- barra lateral
with st.sidebar:
    st.markdown("**STARTEC S.A.** · ISO 9001:2015")
    st.title("Repositorio SGC")
    st.text_input("Buscar", key="q", placeholder="Código, título o palabra",
                  help="Ejemplos: checklist, proveedor, alturas, APO-THU")
    for vista, nombre in [("inicio", "Inicio"), ("listado", "Listado maestro"), ("registros", "Registros"),
                          ("codigos", "Códigos"), ("ayuda", "Ayuda")]:
        st.button(nombre, key=f"nav-{vista}", on_click=ir, args=(vista,), width="stretch",
                  type="primary" if st.query_params.get("v", "inicio") == vista else "secondary")
    st.divider()
    st.caption("Documentos por macroproceso")
    pol = repo.docs.get("EST-SGC-POL-001")
    if pol:
        st.button(f"⬤ {pol.titulo}", key="tree-pol", on_click=ir, args=("doc", pol.codigo), type="tertiary")

    def rama(code: str, nivel: int) -> None:
        d = repo.docs[code]
        sangria = " " * nivel + ("└ " if nivel else "")
        st.button(f"{sangria}{d.tipo} · {d.titulo}", key=f"tree-{code}", on_click=ir, args=("doc", code),
                  type="tertiary", help=code)
        for h in d.hijos:
            rama(h, nivel + 1)

    for m in MACRO_ORDER:
        with st.expander(f"{m} · {MACROS[m]}", expanded=st.query_params.get("doc", "")[:3] == m):
            for d in repo.raices(m):
                rama(d.codigo, 0)
    st.divider()
    st.link_button("Carpeta iso en Google Drive", DRIVE_FOLDER, width="stretch")


# ---------------------------------------------------------------- vistas
TAREAS = [
    ("Ejecutar un servicio en campo", "De la orden de trabajo a la firma del cliente.", "MIS-OPS-EJE-PRO-001"),
    ("Llenar el checklist antes de salir", "Personal, herramientas, EPP y sitio.", "MIS-OPS-CHK-FOR-001"),
    ("Evaluar o aprobar un proveedor", "Criterios, puntajes y quién aprueba.", "APO-COM-EVP-PRO-001"),
    ("Reportar algo que no se cumplió", "No conformidad: se reporta en 3 días hábiles.", "EST-SGC-NCF-PRO-001"),
    ("Verificar certificados del personal", "Semáforo de vigencia en Streamlit.", "APO-THU-CER-INS-001"),
    ("Saber qué certificados pide un cargo", "Médico, alturas, eléctrico, HSE e inducción.", "APO-THU-GDR-MAT-001"),
    ("Contratar a una persona", "Vacante, entrevistas, contrato e inducción.", "APO-THU-SEL-PRO-001"),
    ("Planificar capacitaciones", "Diagnóstico, plan anual y eficacia.", "APO-THU-CAP-PRO-001"),
    ("Preparar una auditoría interna", "Programa anual y regla de independencia.", "EST-SGC-AUD-PRO-001"),
    ("Crear o cambiar un documento", "Codificación, aprobación y versiones.", "EST-SGC-DOC-PRO-001"),
    ("Consultar los riesgos de un proceso", "33 riesgos con control y responsable.", "EST-SGC-RIE-MAT-001"),
    ("Preparar la revisión por la dirección", "Acta anual con entradas y salidas 9.3.", "EST-DIR-PLA-REG-001"),
]


def vista_busqueda(texto: str) -> None:
    st.header(f"Resultados para «{texto}»")
    hits = repo.buscar(texto)
    if not hits:
        st.info("Ningún documento contiene esa palabra. Pruebe con otra o con parte del código.")
        return
    for d, snip in hits:
        with st.container(border=True):
            c1, c2 = st.columns([5, 1], vertical_alignment="center")
            c1.markdown(f'<span class="mac {d.macro}">{d.codigo}</span> **{html.escape(d.titulo)}**', unsafe_allow_html=True)
            c1.caption(snip)
            c2.button("Abrir", key=f"hit-{d.codigo}", on_click=ir, args=("doc", d.codigo), width="stretch")


def vista_inicio() -> None:
    st.caption("SISTEMA DE GESTIÓN DE CALIDAD")
    st.header("¿Qué necesita hacer hoy?")
    st.write("Elija una tarea y llegará directo al documento que la explica. Si busca algo puntual, "
             "escríbalo en el buscador de la izquierda: encuentra códigos, títulos y cualquier palabra dentro de los documentos.")
    cols = st.columns(3)
    for i, (titulo, sub, code) in enumerate(TAREAS):
        with cols[i % 3].container(border=True):
            st.markdown(f"**{titulo}**  \n{sub}")
            st.button(code, key=f"task-{code}", on_click=ir, args=("doc", code), type="tertiary")

    st.subheader("Lo que contiene el repositorio")
    cols = st.columns(len(TYPE_ORDER) + 1)
    cols[0].metric("Documentos", len(repo.docs))
    for c, t in zip(cols[1:], TYPE_ORDER):
        c.metric(TYPES[t][0], sum(d.tipo == t for d in repo.docs.values()))
    st.caption(f"Además, los documentos ordenan llevar {len(repo.registros)} registros. Vea la sección Registros.")

    faltan = repo.sin_archivo()
    if faltan:
        st.subheader("Códigos citados que aún no tienen archivo")
        st.write("Los documentos los mencionan, pero no existe un archivo con ese código ni aparecen en ninguna tabla de registros. "
                 "Revíselos al actualizar el listado maestro.")
        filas = "".join(f"| {link(c)} | {', '.join(link(o) for o in repo.citas[c])} |\n" for c in faltan)
        st.markdown("| Código | Citado en |\n|---|---|\n" + filas, unsafe_allow_html=True)


def vista_listado() -> None:
    st.caption("EST-SGC-DOC-REG-001")
    st.header("Listado maestro de documentos")
    st.write("Versión vigente, dueño y frecuencia de revisión de cada documento. Seleccione una fila para abrirlo.")
    c1, c2 = st.columns(2)
    macros = c1.pills("Macroproceso", MACRO_ORDER, format_func=lambda m: f"{m} · {MACROS[m]}", selection_mode="multi")
    tipos = c2.pills("Tipo", [t for t in TYPE_ORDER if any(d.tipo == t for d in repo.docs.values())],
                     format_func=lambda t: TYPES[t][0], selection_mode="multi")
    docs = [d for d in repo.ordenados() if (not macros or d.macro in macros) and (not tipos or d.tipo in tipos)]
    df = pd.DataFrame([{"Código": d.codigo, "Documento": d.titulo, "Tipo": d.tipo_nombre, "Versión": d.version,
                        "Dueño": d.dueno, "Revisión": d.revision, "Archivo": d.formato} for d in docs])
    ev = st.dataframe(df, hide_index=True, width="stretch", on_select="rerun", selection_mode="single-row",
                      height=min(38 * (len(df) + 1) + 4, 760))
    st.caption(f"{len(docs)} de {len(repo.docs)} documentos")
    if ev.selection.rows:
        st.query_params.clear()
        st.query_params.update(v="doc", doc=docs[ev.selection.rows[0]].codigo)
        st.rerun()


def vista_registros() -> None:
    st.caption("CLÁUSULA 7.5.3 · RETENCIÓN")
    st.header("Registros y tiempos de retención")
    st.write("Cada registro que los documentos ordenan llevar, quién lo archiva y cuánto tiempo se conserva. "
             "Los códigos subrayados tienen plantilla en el repositorio; los punteados se generan en el día a día "
             "(órdenes de trabajo, facturas, actas) o aún no tienen plantilla.")
    filas = "".join(
        f"| {link(r.codigo)} | {html.escape(r.nombre)} | {html.escape(r.responsable)} | {r.retencion} | {'<br>'.join(link(o) for o in r.origen)} |\n"
        for r in sorted(repo.registros.values(), key=lambda r: r.codigo))
    st.markdown("| Código | Registro | Responsable del archivo | Retención | Lo exige |\n|---|---|---|---|---|\n" + filas,
                unsafe_allow_html=True)


def vista_codigos() -> None:
    st.caption("EST-SGC-DOC-PRO-001 · SECCIÓN 5.1")
    st.header("Cómo se leen los códigos")
    st.write("Todo documento se identifica con la estructura **MACROPROCESO-PROCESO-(SUBPROCESO)-TIPO-SECUENCIAL**. "
             "Escriba un código para descifrarlo, o arme uno nuevo con el generador.")
    code = st.text_input("Descifrar un código", value="MIS-OPS-CHK-FOR-001")
    segs, veredicto = descifrar(code, repo)
    if segs:
        cols = st.columns(len(segs))
        for c, s in zip(cols, segs):
            with c.container(border=True):
                st.caption(s["parte"].upper())
                st.markdown(f"### `{s['valor']}` {'✓' if s['ok'] else '✗'}")
                st.write(s["significado"])
    (st.success if "Existe" in veredicto or "disponible" in veredicto else st.warning)(veredicto)

    st.subheader("Generar el código de un documento nuevo")
    st.write("Elija dónde vive el documento y de qué tipo es. El generador propone el siguiente número libre, "
             "revisando todos los códigos que ya existen o están citados.")
    c1, c2, c3 = st.columns(3)
    proc = c1.selectbox("Proceso", list(PROCS), format_func=lambda p: f"{PROC_MACRO[p]}-{p} · {PROCS[p]}")
    sub = c2.selectbox("Subproceso (opcional)", [""] + list(SUBS), format_func=lambda s: f"{s} · {SUBS[s]}" if s else "— Ninguno —")
    tipo = c3.selectbox("Tipo", TYPE_ORDER, format_func=lambda t: f"{t} · {TYPES[t][0]}")
    nuevo, usados = repo.siguiente_codigo(proc, sub, tipo)
    st.code(nuevo, language=None)
    st.caption(f"Ya existen {usados} con este prefijo." if usados else "Primer documento con este prefijo.")

    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Tipos de documento")
        st.dataframe(pd.DataFrame([{"Sigla": t, "Tipo": n, "Para qué sirve": d} for t, (n, d) in TYPES.items()]),
                     hide_index=True, width="stretch")
    with c2:
        st.subheader("Macroprocesos y procesos")
        st.dataframe(pd.DataFrame([{"Macro": PROC_MACRO[p], "Proceso": p, "Nombre": n} for p, n in PROCS.items()]),
                     hide_index=True, width="stretch")


def vista_ayuda() -> None:
    st.caption("GUÍA DE USO")
    st.header("Cómo usar el repositorio")
    st.write("Este repositorio reúne en un solo lugar los documentos del Sistema de Gestión de Calidad. "
             "Aquí se consultan; los archivos originales (Word y Excel) viven en la carpeta iso de Google Drive.")
    pasos = [
        ("Busque o navegue", "Escriba en el buscador un código, un cargo o una palabra (arnés, proveedor, facturación). También puede partir de las tareas de Inicio, del árbol de la izquierda o del Listado maestro."),
        ("Lea la ficha del documento", "Arriba está la carátula con código, versión y tipo; debajo, un resumen y el contenido completo. Los códigos dentro del texto son enlaces: tóquelos para ir al documento citado."),
        ("Revise sus relaciones", "La ficha de la derecha muestra de qué documento deriva, cuáles lo desarrollan, quién lo cita y qué registros debe generar."),
        ("Abra el original para llenar o firmar", "El botón «Abrir original en Drive» lleva al archivo controlado. Ahí se llenan formatos y registros."),
    ]
    for i, (t, d) in enumerate(pasos, 1):
        st.markdown(f"**{i}. {t}**  \n{d}")

    st.subheader("Reglas que todos debemos recordar")
    reglas = [
        ("Solo vale la versión digital vigente", "Toda copia impresa es «no controlada». Antes de usar un formato, confirme aquí su versión."),
        ("Sin checklist firmado, no se trabaja", "El Supervisor de campo firma el checklist previo antes de cada intervención (MIS-OPS-EJE-PRO-001, 5.3)."),
        ("Certificado en rojo, persona en pausa", "Nadie ejecuta tareas de riesgo con un certificado vencido o ausente (APO-THU-MAN-001, política 9)."),
        ("Solo proveedores aprobados", "Toda contratación usa la lista aprobada; las excepciones las autoriza por escrito la Gerencia General."),
        ("Una falla se reporta en 3 días hábiles", "Cualquier incumplimiento va a Gestión y Control, que lo registra y da seguimiento (EST-SGC-NCF-PRO-001)."),
        ("Todo cambio pasa por la bitácora", "Ningún documento se modifica sin anotar versión, sección, descripción y fecha antes de publicarlo."),
    ]
    cols = st.columns(3)
    for i, (t, d) in enumerate(reglas):
        with cols[i % 3].container(border=True):
            st.markdown(f"**{t}**")
            st.markdown(enlazar(d), unsafe_allow_html=True)

    st.subheader("Canal de denuncias y sugerencias")
    st.write("Anónimo y protegido contra represalias (EST-DIR-GOB-POL-001 y EST-DIR-RSE-POL-001).")
    st.code("Ec. Fernando Zapatier · fzapatier@startec.com.ec · 0969424471", language=None)

    st.subheader("¿A quién le pregunto?")
    st.markdown("""
| Si su duda es sobre… | Pregunte a |
|---|---|
| Códigos, versiones, dónde está un documento, auditorías, no conformidades, proveedores, talento humano | **Gestión y Control** |
| Cómo se ejecuta un servicio, checklist, entregas al cliente | **Jefa de Operaciones** |
| Facturación, pagos, soportes contables | **Contabilidad** |
| Aprobación de presupuestos, proveedores nuevos, recursos | **Gerencia General** |
""")


def vista_doc(code: str) -> None:
    d = repo.docs.get(code)
    if not d:
        st.header(code)
        st.warning("Este código no tiene archivo en el repositorio.")
        if code in repo.citas:
            st.markdown("Está citado en: " + ", ".join(link(c) for c in repo.citas[code]), unsafe_allow_html=True)
        if code in repo.registros:
            st.info("Es un registro que se genera al aplicar el documento que lo exige. Vea la sección Registros.")
        st.button("Volver al inicio", on_click=ir)
        return

    ruta = " › ".join(x for x in (MACROS[d.macro], PROCS.get(d.proc, d.proc), SUBS.get(d.sub, d.sub)) if x)
    st.caption(ruta)
    st.markdown(f"""
<div class="caratula">
  <div class="main">
    <div class="org">STARTEC S.A. · Sistema de Gestión de Calidad</div>
    <h2>{html.escape(d.titulo)}</h2>
    <div class="sub"><span class="mac {d.macro}">{d.macro} · {MACROS[d.macro]}</span>
      <span>{d.tipo_nombre} ({d.tipo})</span><span>· Dueño: {html.escape(d.dueno)}</span></div>
  </div>
  <div class="side">
    <div><span>Código</span><b>{d.codigo}</b></div>
    <div><span>Versión</span><b>{d.version}</b></div>
    <div><span>Fecha</span><b>{d.fecha or "—"}</b></div>
  </div>
</div>""", unsafe_allow_html=True)
    st.info(d.resumen)
    b1, b2, _ = st.columns([1.4, 1.2, 3])
    b1.link_button(f"Abrir original en Drive (.{d.formato})", d.drive_url, type="primary", width="stretch")
    if d.padre in repo.docs:
        b2.button("Ir al documento superior", on_click=ir, args=("doc", d.padre), width="stretch")

    izq, der = st.columns([3, 1.15], gap="large")
    with izq:
        st.markdown(enlazar(d.body), unsafe_allow_html=True)
    with der:
        with st.container(border=True):
            st.caption("FICHA")
            st.markdown(f"**Tipo:** {d.tipo_nombre}  \n**Proceso:** {PROCS.get(d.proc, d.proc)}  \n"
                        f"**Revisión:** {d.revision}  \n**Archivo:** .{d.formato} en Drive")
        if d.tipo in ("POL", "MAN"):
            with st.container(border=True):
                st.caption("AUTORIZACIONES")
                st.markdown("**Elaboró:** Gestión y Control  \n**Revisó:** Gerente General  \n**Aprobó:** Representante Legal")
        with st.container(border=True):
            st.caption("RELACIONES")
            partes = []
            if d.padre:
                partes.append(f"<small>{html.escape(d.relacion)} de</small><br>{link(d.padre)}")
            else:
                partes.append(f"<small>{html.escape(d.relacion)}</small>")
            if d.hijos:
                partes.append("<small>Lo desarrollan</small><br>" + "<br>".join(link(h) for h in d.hijos))
            otros = [c for c in repo.citas.get(code, []) if c != d.padre and c not in d.hijos]
            if otros:
                partes.append("<small>También lo citan</small><br>" + "<br>".join(link(c) for c in otros))
            st.markdown('<div class="ficha">' + "<br><br>".join(partes) + "</div>", unsafe_allow_html=True)
        regs = [r for r in repo.registros.values() if code in r.origen]
        if regs:
            with st.container(border=True):
                st.caption("REGISTROS QUE GENERA")
                st.markdown('<div class="ficha">' + "<br>".join(
                    f"{link(r.codigo)}<br><small>{html.escape(r.nombre)} · {r.retencion}</small>" for r in regs) + "</div>",
                    unsafe_allow_html=True)


# ---------------------------------------------------------------- enrutado
texto = st.session_state.get("q", "").strip()
vista = st.query_params.get("v", "inicio")
if len(texto) >= 2:
    vista_busqueda(texto)
elif vista == "doc":
    vista_doc(st.query_params.get("doc", ""))
else:
    {"listado": vista_listado, "registros": vista_registros, "codigos": vista_codigos,
     "ayuda": vista_ayuda}.get(vista, vista_inicio)()
