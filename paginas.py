"""
Páginas del sistema documental de ISOtools.

Cada función pública es una página que app.py registra en la navegación.
Las páginas de Personal habilitado viven en control_documental.py.
"""
from __future__ import annotations

import html
import re
from datetime import date

import pandas as pd
import streamlit as st

import sgc
from sgc import (CODE_RE, DRIVE_FOLDER, MACROS, MACRO_ORDER, PROC_MACRO, PROCS, SUBS,
                 TYPE_ORDER, TYPES, Repositorio, descifrar)

LEVEL = {"ALTO": "red", "MEDIO": "orange", "BAJO": "green", "ROJO": "red", "AMARILLO": "orange", "VERDE": "green"}

# app.py rellena este diccionario con los objetos de página para poder enlazarlos
P: dict = {}


@st.cache_resource
def repo() -> Repositorio:
    return Repositorio()


def hoy() -> date:
    """Fecha de hoy en la zona de Ecuador (la misma que usa Personal habilitado)."""
    try:
        import reglas
        return reglas.hoy()
    except Exception:
        return date.today()


# ------------------------------------------------------------------------------ utilidades
def link(code: str) -> str:
    """Código como enlace a su ficha, o marcado si no tiene archivo."""
    r = repo()
    if code in r.docs:
        t = html.escape(r.docs[code].titulo)
        return f'<a class="code" href="documentos?doc={code}" target="_self" title="{t}">{code}</a>'
    return f'<span class="code-miss" title="Citado en el sistema, sin archivo en el repositorio">{code}</span>'


def enlazar(texto: str) -> str:
    """Markdown listo para mostrar: códigos enlazados y niveles de riesgo en color."""
    texto = CODE_RE.sub(lambda m: link(m.group()), texto)

    def nivel(m: re.Match) -> str:
        return f"| :{LEVEL[m.group(1)]}-background[**{m.group(1)}{m.group(2) or ''}**] |"
    for _ in range(2):  # celdas contiguas comparten el separador
        texto = re.sub(r"\| (ALTO|MEDIO|BAJO)( \(\d+\))? \|", nivel, texto)
    texto = re.sub(r"\| (VERDE|AMARILLO|ROJO) · ([^|]+) \|",
                   lambda m: f"| :{LEVEL[m.group(1)]}-background[**{m.group(2).strip()}**] |", texto)
    return texto


def encabezado(eyebrow: str, titulo: str, texto: str = "") -> None:
    st.markdown(f'<div class="eyebrow">{eyebrow}</div>', unsafe_allow_html=True)
    st.header(titulo, anchor=False)
    if texto:
        st.markdown(enlazar(texto), unsafe_allow_html=True)


def ir_doc(code: str, label: str | None = None, **kw) -> None:
    st.page_link(P["documentos"], label=label or code, query_params={"doc": code}, **kw)


def hay_google() -> bool:
    """True si la app tiene configurada la cuenta de servicio de Google."""
    try:
        return "gcp_service_account" in st.secrets
    except Exception:
        return False


def personal_habilitado() -> dict | None:
    """Indicadores de Personal habilitado si hay conexión con Google; None si no."""
    if not hay_google():
        return None
    try:
        import nucleo as nu
        import personas as pe
        fichas = pe.colaboradores()
        tabla = nu.tabla_control(fichas)
        m = nu.indicadores(tabla)
        m["cobertura"] = nu.resumen_cobertura(nu.cobertura(tabla, fichas))
        return m
    except Exception:
        return None


# ------------------------------------------------------------------------------ INICIO
TAREAS = [
    ("Ejecutar un servicio en campo", "De la orden de trabajo a la firma del cliente.", "doc", "MIS-OPS-EJE-PRO-001"),
    ("Llenar el checklist antes de salir", "Personal, herramientas, EPP y sitio.", "doc", "MIS-OPS-CHK-FOR-001"),
    ("Cargar un certificado de un colaborador", "Médico, alturas, eléctrico, IESS…", "hab_cargar", None),
    ("¿Cómo está el expediente de alguien?", "Vencimientos y lo que le falta.", "hab_control", None),
    ("Saber qué me toca según mi cargo", "Políticas, tareas, registros y riesgos.", "cargo", None),
    ("Evaluar o aprobar un proveedor", "Criterios, puntajes y quién aprueba.", "doc", "APO-COM-EVP-PRO-001"),
    ("Reportar algo que no se cumplió", "No conformidad: se reporta en 3 días hábiles.", "doc", "EST-SGC-NCF-PRO-001"),
    ("Contratar a una persona", "Vacante, entrevistas, contrato e inducción.", "doc", "APO-THU-SEL-PRO-001"),
    ("Consultar los riesgos de un proceso", "Mapa de calor y controles por etapa.", "riesgos", None),
    ("Preparar una auditoría interna", "Programa anual y regla de independencia.", "doc", "EST-SGC-AUD-PRO-001"),
    ("Preparar la revisión por la dirección", "Indicadores y calendario de revisión.", "indicadores", None),
    ("Crear o cambiar un documento", "Codificación, aprobación y versiones.", "codigos", None),
]


def inicio() -> None:
    r = repo()
    encabezado("ISOtools · STARTEC S.A.", "¿Qué necesita hacer hoy?",
               "Elija una tarea y llegará directo a donde se resuelve. Para algo puntual use el "
               "buscador de la barra lateral: encuentra códigos, títulos y cualquier palabra dentro de los documentos.")
    cols = st.columns(3)
    for i, (titulo, sub, destino, code) in enumerate(TAREAS):
        with cols[i % 3].container(border=True):
            st.markdown(f"**{titulo}**  \n<span class='muted'>{sub}</span>", unsafe_allow_html=True)
            if destino == "doc":
                ir_doc(code, label=f"Abrir {code}")
            else:
                st.page_link(P[destino], label=f"Ir a {P[destino].title}")

    st.subheader("Estado del sistema hoy", anchor=False)
    cal = sgc.calendario_revision(r, hoy())
    altos = [x for x in sgc.riesgos(r) if x["Nivel"] == "ALTO"]
    vencer = [c for c in cal if c["Estado"] in ("Vencida", "Próxima (≤ 60 días)")]
    sin_fecha = [c for c in cal if c["Estado"] == "Sin fecha de aprobación"]
    m = personal_habilitado()

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Documentos controlados", len(r.docs), help="Archivos del SGC en el repositorio")
    c2.metric("Riesgos en nivel ALTO", len(altos), help="Matriz unificada y matrices de cada procedimiento")
    c3.metric("Revisiones por vencer", len(vencer), help="Vencidas o en los próximos 60 días")
    if m:
        c4.metric("Personal en regla", f'{m["cobertura"]["porcentaje"]}%',
                  help="Colaboradores activos con todo su expediente vigente (APO-THU-CER-INS-001)")
    else:
        c4.metric("Personal en regla", "—", help="Requiere la conexión con Google de Personal habilitado")

    avisos = []
    if m and (m["vencidos"] or m["revision"] or m["renovar"]):
        avisos.append(("error" if m["vencidos"] else "warning",
                       f'Personal habilitado: {m["vencidos"]} certificado(s) vencido(s), '
                       f'{m["renovar"]} por renovar en 30 días.', "hab_control"))
    if sin_fecha:
        avisos.append(("warning", f"{len(sin_fecha)} documento(s) sin fecha de aprobación: no se puede calcular "
                                  "su próxima revisión (EST-SGC-DOC-PRO-001, 5.6).", "indicadores"))
    faltan = r.sin_archivo()
    if faltan:
        avisos.append(("warning", f"{len(faltan)} código(s) citados que no existen: "
                                  + ", ".join(faltan) + ".", "listado"))
    for tipo, texto, destino in avisos:
        with st.container(border=True):
            a, b = st.columns([5, 1], vertical_alignment="center")
            (a.error if tipo == "error" else a.warning)(texto)
            b.page_link(P[destino], label="Revisar")
    if not m:
        st.caption("La sección Personal habilitado se activa al configurar la cuenta de servicio de Google "
                   "en los secretos de la app. El resto de ISOtools funciona sin ella.")

    st.subheader("Mapa del sistema", anchor=False)
    st.write("Todo nace de la Política de Calidad; cada manual deriva de ella y se desarrolla en procedimientos, "
             "instructivos, formatos y registros.")
    cols = st.columns(3)
    for col, mac in zip(cols, MACRO_ORDER):
        with col.container(border=True):
            st.markdown(f'<span class="mac {mac}">{mac}</span> **{MACROS[mac]}**', unsafe_allow_html=True)
            lineas = []

            def rama(code, nivel):
                d = r.docs[code]
                pre = "&emsp;" * nivel + ("└ " if nivel else "")
                lineas.append(f'{pre}<span class="tipo">{d.tipo}</span> '
                              f'<a href="documentos?doc={code}" target="_self">{html.escape(d.titulo)}</a>')
                for h in d.hijos:
                    rama(h, nivel + 1)
            for d in r.raices(mac):
                rama(d.codigo, 0)
            st.markdown('<div class="arbol">' + "<br>".join(lineas) + "</div>", unsafe_allow_html=True)


# ------------------------------------------------------------------------------ DOCUMENTOS
def documentos() -> None:
    r = repo()
    q = st.query_params.get("q", "").strip()
    code = st.query_params.get("doc", "").strip()
    if code:
        ficha(code)
        return
    encabezado("Sistema documental", "Documentos del SGC",
               "Busque por código, título o palabra, o recorra el árbol por macroproceso.")
    nuevo = st.text_input("Buscar", value=q, placeholder="Ej.: checklist, arnés, proveedor, APO-THU",
                          label_visibility="collapsed")
    if nuevo.strip() != q:
        st.query_params["q"] = nuevo.strip()
        st.rerun()
    if len(q) >= 2:
        hits = r.buscar(q)
        st.caption(f"{len(hits)} resultado(s) para «{q}»")
        if not hits:
            st.info("Ningún documento contiene esa palabra. Pruebe con otra o con parte del código.")
        for d, snip in hits:
            with st.container(border=True):
                st.markdown(f'<span class="mac {d.macro}">{d.codigo}</span> '
                            f'<a href="documentos?doc={d.codigo}" target="_self"><b>{html.escape(d.titulo)}</b></a>'
                            f'<br><span class="muted">{html.escape(snip)}</span>', unsafe_allow_html=True)
        return

    pol = r.docs.get("EST-SGC-POL-001")
    if pol:
        st.markdown(f'<a class="raiz" href="documentos?doc={pol.codigo}" target="_self">'
                    f'<span>{pol.codigo} · Documento raíz</span><b>{pol.titulo}</b>'
                    f'<small>{html.escape(pol.resumen)}</small></a>', unsafe_allow_html=True)
    for mac in MACRO_ORDER:
        with st.expander(f"{mac} · {MACROS[mac]}", expanded=True):
            def rama(code, nivel):
                d = r.docs[code]
                a, b = st.columns([0.9, 5], vertical_alignment="top")
                a.markdown(f'<span class="tipo">{d.tipo_nombre}</span>', unsafe_allow_html=True)
                b.markdown(f'{"&emsp;" * nivel}{"└ " if nivel else ""}<a href="documentos?doc={code}" target="_self">'
                           f'<b>{html.escape(d.titulo)}</b></a> <span class="mono muted">{code} · v{d.version}</span>'
                           f'<br>{"&emsp;" * nivel}<span class="muted">{html.escape(d.resumen)}</span>',
                           unsafe_allow_html=True)
                for h in d.hijos:
                    rama(h, nivel + 1)
            for d in r.raices(mac):
                rama(d.codigo, 0)


def ficha(code: str) -> None:
    r = repo()
    d = r.docs.get(code)
    st.page_link(P["documentos"], label="← Todos los documentos")
    if not d:
        st.header(code, anchor=False)
        st.warning("Este código no tiene archivo en el repositorio.")
        if code in r.citas:
            st.markdown("Está citado en: " + ", ".join(link(c) for c in r.citas[code]), unsafe_allow_html=True)
        if code in r.registros:
            st.info("Es un registro que se genera al aplicar el documento que lo exige. Vea la página Registros.")
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
    b1, b2, b3 = st.columns([1.5, 1.3, 2.2])
    b1.link_button(f"Abrir original en Drive (.{d.formato})", d.drive_url, type="primary", width="stretch")
    if d.padre in r.docs:
        with b2:
            ir_doc(d.padre, label="↑ Documento superior")
    if code in ("APO-THU-CER-INS-001", "APO-THU-GDR-MAT-001"):
        with b3:
            st.page_link(P["hab_control"], label="Ver el estado real del personal →")

    izq, der = st.columns([3, 1.15], gap="large")
    with izq:
        st.markdown(enlazar(d.body), unsafe_allow_html=True)
    with der:
        with st.container(border=True):
            st.caption("FICHA")
            prox = next((c for c in sgc.calendario_revision(r, hoy()) if c["Código"] == code), None)
            st.markdown(f"**Tipo:** {d.tipo_nombre}  \n**Proceso:** {PROCS.get(d.proc, d.proc)}  \n"
                        f"**Revisión:** {d.revision}  \n"
                        f"**Próxima revisión:** {prox['Próxima revisión'].strftime('%d/%m/%Y') if prox and prox['Próxima revisión'] else prox['Estado'] if prox else '—'}  \n"
                        f"**Archivo:** .{d.formato} en Drive")
        if d.tipo in ("POL", "MAN"):
            with st.container(border=True):
                st.caption("AUTORIZACIONES")
                st.markdown("**Elaboró:** Gestión y Control  \n**Revisó:** Gerente General  \n**Aprobó:** Representante Legal")
        with st.container(border=True):
            st.caption("RELACIONES")
            partes = [f"<small>{html.escape(d.relacion)} de</small><br>{link(d.padre)}" if d.padre
                      else f"<small>{html.escape(d.relacion)}</small>"]
            if d.hijos:
                partes.append("<small>Lo desarrollan</small><br>" + "<br>".join(link(h) for h in d.hijos))
            otros = [c for c in r.citas.get(code, []) if c != d.padre and c not in d.hijos]
            if otros:
                partes.append("<small>También lo citan</small><br>" + "<br>".join(link(c) for c in otros))
            st.markdown('<div class="rel">' + "<br><br>".join(partes) + "</div>", unsafe_allow_html=True)
        regs = [x for x in r.registros.values() if code in x.origen]
        if regs:
            with st.container(border=True):
                st.caption("REGISTROS QUE GENERA")
                st.markdown('<div class="rel">' + "<br>".join(
                    f"{link(x.codigo)}<br><small>{html.escape(x.nombre)} · {x.retencion}</small>" for x in regs)
                    + "</div>", unsafe_allow_html=True)


# ------------------------------------------------------------------------------ LISTADO
def listado() -> None:
    r = repo()
    encabezado("EST-SGC-DOC-REG-001", "Listado maestro de documentos",
               "Versión vigente, dueño, frecuencia y próxima revisión de cada documento. Seleccione una fila para abrirlo.")
    c1, c2 = st.columns(2)
    macros = c1.pills("Macroproceso", MACRO_ORDER, format_func=lambda m: f"{m} · {MACROS[m]}", selection_mode="multi")
    tipos = c2.pills("Tipo", [t for t in TYPE_ORDER if any(d.tipo == t for d in r.docs.values())],
                     format_func=lambda t: TYPES[t][0], selection_mode="multi")
    cal = {c["Código"]: c for c in sgc.calendario_revision(r, hoy())}
    docs = [d for d in r.ordenados() if (not macros or d.macro in macros) and (not tipos or d.tipo in tipos)]
    df = pd.DataFrame([{"Código": d.codigo, "Documento": d.titulo, "Tipo": d.tipo_nombre, "Versión": d.version,
                        "Dueño": d.dueno, "Próxima revisión": cal[d.codigo]["Próxima revisión"],
                        "Estado de revisión": cal[d.codigo]["Estado"], "Original": d.drive_url} for d in docs])
    ev = st.dataframe(df, hide_index=True, width="stretch", on_select="rerun", selection_mode="single-row",
                      height=min(36 * (len(df) + 1) + 4, 760),
                      column_config={"Original": st.column_config.LinkColumn("Original", display_text="Drive ↗"),
                                     "Próxima revisión": st.column_config.DateColumn(format="DD/MM/YYYY")})
    st.caption(f"{len(docs)} de {len(r.docs)} documentos")
    if ev.selection.rows:
        st.switch_page(P["documentos"], query_params={"doc": docs[ev.selection.rows[0]].codigo})

    faltan = r.sin_archivo()
    if faltan:
        st.subheader("Códigos citados que no existen", anchor=False)
        st.write("Los documentos los mencionan, pero no hay archivo con ese código ni figuran como registro. "
                 "Corrija la cita o cree el documento.")
        st.markdown("| Código | Citado en |\n|---|---|\n" + "".join(
            f"| {link(c)} | {', '.join(link(o) for o in r.citas[c])} |\n" for c in faltan), unsafe_allow_html=True)


# ------------------------------------------------------------------------------ REGISTROS
def registros() -> None:
    r = repo()
    encabezado("Cláusula 7.5.3 · Retención", "Registros y tiempos de retención",
               "Cada registro que los documentos ordenan llevar, quién lo archiva y cuánto tiempo se conserva. "
               "Los códigos subrayados tienen plantilla en el repositorio; los punteados se generan en el día a día "
               "(órdenes de trabajo, facturas, actas) o aún no tienen plantilla.")
    resp = sorted({x.responsable for x in r.registros.values()})
    filtro = st.pills("Responsable del archivo", resp, selection_mode="multi")
    regs = [x for x in sorted(r.registros.values(), key=lambda x: x.codigo) if not filtro or x.responsable in filtro]
    st.markdown("| Código | Registro | Responsable del archivo | Retención | Lo exige |\n|---|---|---|---|---|\n" + "".join(
        f"| {link(x.codigo)} | {html.escape(x.nombre)} | {html.escape(x.responsable)} | {x.retencion} | "
        f"{'<br>'.join(link(o) for o in x.origen)} |\n" for x in regs), unsafe_allow_html=True)
    st.caption(f"{len(regs)} registro(s). Los registros de Personal habilitado (certificados y su base de datos) "
               "se gestionan en esa sección.")


# ------------------------------------------------------------------------------ RIESGOS
def riesgos() -> None:
    r = repo()
    todos = sgc.riesgos(r)
    encabezado("EST-SGC-RIE-MAT-001 · Cláusula 6.1", "Riesgos y controles",
               "La matriz unificada y los riesgos que declara cada procedimiento, en un solo lugar. "
               "Filtre por proceso, nivel o responsable del control.")
    c1, c2, c3 = st.columns(3)
    procs = c1.multiselect("Proceso", sorted({x["Proceso"] for x in todos}))
    niveles = c2.pills("Nivel", ["ALTO", "MEDIO", "BAJO"], selection_mode="multi")
    ejec = c3.multiselect("Ejecutor del control", sorted({x["Ejecutor"] for x in todos}))
    sel = [x for x in todos if (not procs or x["Proceso"] in procs) and (not niveles or x["Nivel"] in niveles)
           and (not ejec or x["Ejecutor"] in ejec)]

    a, b = st.columns([1.1, 2], gap="large")
    with a:
        st.markdown("**Mapa de calor** · probabilidad × impacto")
        celdas = {}
        for x in sel:
            if x["P"]:
                celdas[(x["P"], x["I"])] = celdas.get((x["P"], x["I"]), 0) + 1
        filas = ""
        for p in (5, 3, 1):
            filas += f'<tr><th>P {p}</th>' + "".join(
                f'<td class="hm {"hi" if p * i >= 15 else "md" if p * i >= 5 else "lo"}">'
                f'{celdas.get((p, i), "")}</td>' for i in (1, 3, 5)) + "</tr>"
        st.markdown(f'<table class="heat"><tbody>{filas}<tr><th></th><th>I 1</th><th>I 3</th><th>I 5</th></tr>'
                    f'</tbody></table>', unsafe_allow_html=True)
        st.caption("Cada número es la cantidad de riesgos de la matriz unificada en esa celda. "
                   "Los de los procedimientos no tienen P × I y no aparecen aquí.")
        cuenta = pd.Series([x["Nivel"] for x in sel]).value_counts()
        m1, m2, m3 = st.columns(3)
        m1.metric("ALTO", int(cuenta.get("ALTO", 0)))
        m2.metric("MEDIO", int(cuenta.get("MEDIO", 0)))
        m3.metric("BAJO", int(cuenta.get("BAJO", 0)))
    with b:
        st.markdown(f"**{len(sel)} riesgo(s)**, ordenados por nivel")
        df = pd.DataFrame(sorted(sel, key=lambda x: (sgc.NIVEL_ORDEN.get(x["Nivel"], 3), -(x["PxI"] or 0))))
        if not df.empty:
            df["Nivel"] = df["Nivel"].map({"ALTO": "🔴 ALTO", "MEDIO": "🟡 MEDIO", "BAJO": "🟢 BAJO"}).fillna(df["Nivel"])
            st.dataframe(df[["Nivel", "Proceso", "Etapa", "Riesgo", "Control", "Ejecutor", "Frecuencia", "PxI", "Fuente"]],
                         hide_index=True, width="stretch", height=560,
                         column_config={"Riesgo": st.column_config.TextColumn(width="medium"),
                                        "Control": st.column_config.TextColumn(width="large"),
                                        "PxI": st.column_config.NumberColumn("P×I")})
    st.caption("Una no conformidad se clasifica con estos mismos niveles (EST-SGC-NCF-PRO-001, 5.2).")


# ------------------------------------------------------------------------------ INDICADORES
def indicadores() -> None:
    r = repo()
    encabezado("Cláusulas 9.1 y 9.3", "Indicadores y revisión documental",
               "Todos los indicadores que fijan los procedimientos, con su meta. Los que el sistema puede medir solo "
               "muestran su valor actual; el resto se registra en el acta de revisión por la dirección (EST-DIR-PLA-REG-001).")
    cal = sgc.calendario_revision(r, hoy())
    con_fecha = [c for c in cal if c["Próxima revisión"]]
    al_dia = sum(c["Estado"] == "Al día" for c in con_fecha)
    pct_cal = round(al_dia / len(con_fecha) * 100) if con_fecha else 0
    m = personal_habilitado()

    medidos = {"Cumplimiento del calendario de revisión": f"{pct_cal}%",
               "% de cumplimiento documental": f'{m["cobertura"]["porcentaje"]}%' if m else "Sin conexión"}
    filas = sgc.indicadores(r)
    for f in filas:
        f["Valor actual"] = medidos.get(f["Indicador"], "Registrar en el acta")
    st.dataframe(pd.DataFrame(filas)[["Indicador", "Meta", "Valor actual", "Cálculo", "Documento", "Responsable"]],
                 hide_index=True, width="stretch",
                 column_config={"Cálculo": st.column_config.TextColumn(width="large")})

    st.subheader("Calendario de revisión de documentos", anchor=False)
    st.markdown(enlazar("Políticas y manuales se revisan según su propia frecuencia; procedimientos, instructivos, "
                        "matrices, registros y formatos cada 2 años (EST-SGC-DOC-PRO-001, 5.6)."), unsafe_allow_html=True)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Al día", al_dia)
    c2.metric("Próximas (≤ 60 días)", sum(c["Estado"].startswith("Próxima") for c in cal))
    c3.metric("Vencidas", sum(c["Estado"] == "Vencida" for c in cal))
    c4.metric("Sin fecha de aprobación", sum(c["Estado"] == "Sin fecha de aprobación" for c in cal))
    df = pd.DataFrame(cal)
    st.dataframe(df, hide_index=True, width="stretch",
                 column_config={"Aprobado": st.column_config.DateColumn(format="DD/MM/YYYY"),
                                "Próxima revisión": st.column_config.DateColumn(format="DD/MM/YYYY")})
    st.caption("Para los documentos sin fecha de aprobación, registre la fecha en su archivo y en el encabezado "
               "del Markdown (campo «fecha») y el calendario se completará solo.")


# ------------------------------------------------------------------------------ MI CARGO
def mi_cargo() -> None:
    r = repo()
    encabezado("Cláusula 5.3 · Roles y responsabilidades", "Lo que le toca a cada cargo",
               "Elija un cargo y verá todo lo que el sistema le asigna, leído directamente de los documentos: "
               "su rol, las políticas que debe cumplir, sus tareas en los procedimientos, los registros que archiva, "
               "los riesgos que controla y los certificados que necesita para trabajar.")
    cargo = st.pills("Cargo", list(sgc.CARGOS), default="Supervisor de campo", selection_mode="single")
    if not cargo:
        return
    x = sgc.responsabilidades(r, cargo)
    if x["rol"]:
        st.info(f"**Rol en el SGC:** {x['rol']}")

    t1, t2, t3, t4, t5, t6 = st.tabs([
        f"Políticas ({len(x['politicas'])})", f"Tareas ({len(x['tareas'])})", f"Registros ({len(x['registros'])})",
        f"Riesgos ({len(x['riesgos'])})", "Certificados", f"Para todo el personal ({len(x['todos'])})"])

    def lista(filas, vacio):
        if not filas:
            st.caption(vacio)
            return
        st.markdown("| Documento | Qué | Cláusula |\n|---|---|---|\n" + "".join(
            f"| {link(f['Documento'])} | {html.escape(f['Qué'])} | {f.get('Cláusula', '')} |\n" for f in filas),
            unsafe_allow_html=True)
    with t1:
        lista(x["politicas"], "Ninguna política lo nombra como responsable.")
    with t2:
        if x["tareas"]:
            st.markdown("| Documento | Tarea |\n|---|---|\n" + "".join(
                f"| {link(f['Documento'])} | {html.escape(f['Qué'])} |\n" for f in x["tareas"]), unsafe_allow_html=True)
        else:
            st.caption("No figura en la sección Responsables de ningún procedimiento.")
    with t3:
        if x["registros"]:
            st.markdown("| Registro | Nombre | Retención | Lo exige |\n|---|---|---|---|\n" + "".join(
                f"| {link(g.codigo)} | {html.escape(g.nombre)} | {g.retencion} | {', '.join(link(o) for o in g.origen)} |\n"
                for g in x["registros"]), unsafe_allow_html=True)
        else:
            st.caption("No tiene registros a su cargo.")
    with t4:
        if x["riesgos"]:
            df = pd.DataFrame(x["riesgos"])[["Nivel", "Proceso", "Etapa", "Riesgo", "Control", "Frecuencia", "Fuente"]]
            st.dataframe(df, hide_index=True, width="stretch")
        else:
            st.caption("No ejecuta controles de la matriz de riesgos.")
    with t5:
        if x["habilitantes"]:
            st.markdown(enlazar("Según APO-THU-GDR-MAT-001, antes de asignarle trabajo debe tener:"), unsafe_allow_html=True)
            for k, v in x["habilitantes"].items():
                if v and v != "No":
                    st.markdown(f"- **{k}:** {html.escape(v)}")
            st.page_link(P["hab_control"], label="Ver quién de este cargo está en regla →")
        else:
            st.caption("La matriz de habilitantes no tiene una fila para este cargo.")
    with t6:
        lista(x["todos"], "—")


# ------------------------------------------------------------------------------ CÓDIGOS
def codigos() -> None:
    r = repo()
    encabezado("EST-SGC-DOC-PRO-001 · Sección 5.1", "Cómo se leen los códigos",
               "Todo documento se identifica con la estructura **MACROPROCESO-PROCESO-(SUBPROCESO)-TIPO-SECUENCIAL**. "
               "Escriba un código para descifrarlo, o arme uno nuevo con el generador.")
    code = st.text_input("Descifrar un código", value="MIS-OPS-CHK-FOR-001")
    segs, veredicto = descifrar(code, r)
    if segs:
        cols = st.columns(len(segs))
        for c, s in zip(cols, segs):
            with c.container(border=True):
                st.caption(s["parte"].upper())
                st.markdown(f"### `{s['valor']}` {'✓' if s['ok'] else '✗'}")
                st.write(s["significado"])
    (st.success if veredicto.startswith(("Existe", "Código bien", "Es un registro")) else st.warning)(veredicto)

    st.subheader("Generar el código de un documento nuevo", anchor=False)
    st.write("Elija dónde vive el documento y de qué tipo es. El generador propone el siguiente número libre, "
             "revisando todos los códigos que ya existen o están citados.")
    c1, c2, c3 = st.columns(3)
    proc = c1.selectbox("Proceso", list(PROCS), format_func=lambda p: f"{PROC_MACRO[p]}-{p} · {PROCS[p]}")
    sub = c2.selectbox("Subproceso (opcional)", [""] + list(SUBS), format_func=lambda s: f"{s} · {SUBS[s]}" if s else "— Ninguno —")
    tipo = c3.selectbox("Tipo", TYPE_ORDER, format_func=lambda t: f"{t} · {TYPES[t][0]}")
    nuevo, usados = r.siguiente_codigo(proc, sub, tipo)
    st.code(nuevo, language=None)
    st.caption((f"Ya existen {usados} con este prefijo. " if usados else "Primer documento con este prefijo. ")
               + "Para publicarlo, cree documentos/" + nuevo + ".md siguiendo el README del repositorio.")

    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Tipos de documento", anchor=False)
        st.dataframe(pd.DataFrame([{"Sigla": t, "Tipo": n, "Para qué sirve": d} for t, (n, d) in TYPES.items()]),
                     hide_index=True, width="stretch")
    with c2:
        st.subheader("Macroprocesos y procesos", anchor=False)
        st.dataframe(pd.DataFrame([{"Macro": PROC_MACRO[p], "Proceso": p, "Nombre": n} for p, n in PROCS.items()]),
                     hide_index=True, width="stretch")


# ------------------------------------------------------------------------------ AYUDA
def ayuda() -> None:
    encabezado("Guía de uso", "Cómo usar ISOtools",
               "ISOtools reúne el sistema documental del SGC y el control de certificados del personal. Aquí se "
               "consulta y se controla; los originales firmados viven en la carpeta iso de Google Drive.")
    pasos = [
        ("Busque o navegue", "Use el buscador de la barra lateral o las tareas de Inicio. El menú agrupa las páginas en Sistema documental, Gestión y Personal habilitado."),
        ("Lea la ficha del documento", "Carátula con código, versión y fecha; resumen; contenido completo con los códigos citados como enlaces; y a la derecha sus relaciones, registros y próxima revisión."),
        ("Consulte lo que le toca", "En Mi cargo verá sus políticas, tareas, registros, riesgos y los certificados que necesita."),
        ("Controle al personal", "En Personal habilitado se cargan los certificados, se ve quién está en regla y llegan los avisos de vencimiento por correo."),
    ]
    for i, (t, d) in enumerate(pasos, 1):
        st.markdown(f"**{i}. {t}**  \n{d}")

    st.subheader("Reglas que todos debemos recordar", anchor=False)
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

    st.subheader("Canal de denuncias y sugerencias", anchor=False)
    st.markdown(enlazar("Anónimo y protegido contra represalias (EST-DIR-GOB-POL-001 y EST-DIR-RSE-POL-001)."),
                unsafe_allow_html=True)
    st.code("Ec. Fernando Zapatier · fzapatier@startec.com.ec · 0969424471", language=None)

    st.subheader("¿A quién le pregunto?", anchor=False)
    st.markdown("""
| Si su duda es sobre… | Pregunte a |
|---|---|
| Códigos, versiones, dónde está un documento, auditorías, no conformidades, proveedores, talento humano, certificados del personal | **Gestión y Control** |
| Cómo se ejecuta un servicio, checklist, entregas al cliente | **Jefa de Operaciones** |
| Facturación, pagos, soportes contables | **Contabilidad** |
| Aprobación de presupuestos, proveedores nuevos, recursos | **Gerencia General** |
""")
    st.link_button("Abrir la carpeta iso en Google Drive", DRIVE_FOLDER)
