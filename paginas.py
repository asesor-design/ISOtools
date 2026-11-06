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


def encabezado(eyebrow: str, titulo: str, texto: str = "", guia_pasos: list[str] | None = None) -> None:
    """Título de página con una línea de contexto y, si se da, la guía «¿Cómo se usa esta página?»."""
    st.markdown(f'<div class="eyebrow">{eyebrow}</div>', unsafe_allow_html=True)
    st.header(titulo, anchor=False)
    if texto:
        st.markdown(f'<p class="bajada">{enlazar(texto)}</p>', unsafe_allow_html=True)
    if guia_pasos:
        guia(guia_pasos)


def guia(pasos_: list[str], titulo: str = "¿Cómo se usa esta página?") -> None:
    """Pasos numerados plegables: la ayuda está donde se necesita, sin estorbar a quien ya sabe."""
    with st.expander(f":material/school: {titulo}"):
        st.markdown('<ol class="guia">' + "".join(f"<li>{enlazar(p)}</li>" for p in pasos_) + "</ol>",
                    unsafe_allow_html=True)


def tarjetas(items: list[tuple]) -> None:
    """Fila de indicadores ejecutivos: (valor, etiqueta, variante, ayuda)."""
    html_ = '<div class="kpi-barra">'
    for valor, etiqueta, variante, ayuda in items:
        html_ += (f'<div class="kpi kpi--{variante}" title="{html.escape(ayuda)}">'
                  f'<span class="kpi-valor">{valor}</span><span class="kpi-etiqueta">{etiqueta}</span>'
                  f'<span class="kpi-ayuda">{html.escape(ayuda)}</span></div>')
    st.markdown(html_ + "</div>", unsafe_allow_html=True)


def barra_salud(titulo: str, pct: int, detalle: str) -> str:
    nivel = "ok" if pct >= 85 else ("medio" if pct >= 60 else "bajo")
    return (f'<div class="salud"><div class="salud-top"><b>{titulo}</b><span class="salud-pct {nivel}">{pct}%</span></div>'
            f'<div class="salud-barra"><span class="{nivel}" style="width:{max(pct, 2)}%"></span></div>'
            f'<small>{detalle}</small></div>')


def a_excel(hojas: dict[str, pd.DataFrame]) -> bytes:
    """Libro de Excel con una hoja por tabla, encabezados en negrita y columnas ajustadas."""
    from io import BytesIO
    from openpyxl.styles import Font, PatternFill
    buf = BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as xw:
        for nombre, df in hojas.items():
            df.to_excel(xw, sheet_name=nombre[:31], index=False)
            ws = xw.sheets[nombre[:31]]
            for c in ws[1]:
                c.font = Font(bold=True, color="FFFFFF")
                c.fill = PatternFill("solid", fgColor="25292D")
            for col in ws.columns:
                largo = max(len(str(c.value or "")) for c in col)
                ws.column_dimensions[col[0].column_letter].width = min(max(10, largo + 2), 60)
            ws.freeze_panes = "A2"
    return buf.getvalue()


def paquete_sgc() -> dict[str, pd.DataFrame]:
    """Tablas del SGC para exportar: listado, registros, riesgos, indicadores y calendario."""
    r = repo()
    cal = sgc.calendario_revision(r, hoy())
    return {
        "Listado maestro": pd.DataFrame([{"Código": d.codigo, "Documento": d.titulo, "Tipo": d.tipo_nombre,
                                          "Macroproceso": MACROS[d.macro], "Proceso": PROCS.get(d.proc, d.proc),
                                          "Versión": d.version, "Fecha": d.fecha, "Dueño": d.dueno,
                                          "Revisión": d.revision, "Original": d.drive_url} for d in r.ordenados()]),
        "Calendario de revisión": pd.DataFrame(cal),
        "Indicadores": pd.DataFrame(sgc.indicadores(r)),
        "Riesgos": pd.DataFrame(sgc.riesgos(r)),
        "Registros": pd.DataFrame([{"Código": x.codigo, "Registro": x.nombre, "Responsable": x.responsable,
                                    "Retención": x.retencion, "Lo exige": ", ".join(x.origen)}
                                   for x in sorted(r.registros.values(), key=lambda x: x.codigo)]),
    }


def ir_doc(code: str, label: str | None = None, **kw) -> None:
    st.page_link(P["documentos"], label=label or code, query_params={"doc": code}, **kw)


def hay_google() -> bool:
    """True si la app tiene configurada la cuenta de servicio de Google."""
    try:
        return "gcp_service_account" in st.secrets
    except Exception:
        return False


def nc_resumen():
    """(DataFrame, indicadores) de no conformidades, o (None, None) si no hay conexión."""
    try:
        import mejora as mj
        if not mj.disponible():
            return None, None
        df = mj.leer()
        return df, mj.indicadores(df)
    except Exception:
        return None, None


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



def boton_original(d, contenedor) -> None:
    """
    Descarga del original controlado. La app lo trae de Drive con su cuenta de servicio,
    así funciona para cualquiera que entró con la contraseña. Si la cuenta aún no tiene
    acceso a la carpeta iso, ofrece el enlace a Drive (solo sirve a quien tenga permiso).
    """
    import originales as og
    est = og.estado()
    if est["ok"] and d.drive:
        try:
            with st.spinner("Preparando el original…"):
                datos = og.contenido(d.drive)
            contenedor.download_button(
                f"Descargar original (.{d.formato})", data=datos, type="primary", width="stretch",
                file_name=f"{d.codigo}.{d.formato}", mime=og.MIME.get(d.formato, "application/octet-stream"),
                icon=":material/download:", on_click="ignore",
                help="Archivo Word/Excel vigente de la carpeta iso. Ábralo para llenar, firmar o imprimir.")
            return
        except Exception as e:
            contenedor.link_button(f"Abrir en Drive (.{d.formato})", d.drive_url, type="primary", width="stretch",
                                   icon=":material/open_in_new:")
            st.warning(f"No se pudo traer el archivo desde Drive ({str(e)[:120]}). Pruebe de nuevo en un momento "
                       "o use «Abrir en Drive».")
            return
    contenedor.link_button(f"Abrir en Drive (.{d.formato})", d.drive_url, type="primary", width="stretch",
                           icon=":material/open_in_new:",
                           help="Solo abre si su cuenta de Google tiene acceso a la carpeta iso.")
    if est["motivo"] == "sin_permiso":
        with st.expander(":material/lock: ¿Le aparece «Necesitas acceso» en Drive? Así se soluciona"):
            st.markdown(og.instrucciones_permiso())
    elif est["motivo"] == "sin_google":
        st.caption("Para que todos puedan descargar los originales, configure la cuenta de servicio de Google "
                   "en los secretos de la app y comparta con ella la carpeta iso (vea Ayuda ▸ Archivos originales).")


# ------------------------------------------------------------------------------ INICIO
TAREAS = [
    ("Ejecutar un servicio en campo", "De la orden de trabajo a la firma del cliente.", "doc", "MIS-OPS-EJE-PRO-001"),
    ("Llenar el checklist antes de salir", "Personal, herramientas, EPP y sitio.", "doc", "MIS-OPS-CHK-FOR-001"),
    ("Cargar un certificado de un colaborador", "Médico, alturas, eléctrico, IESS…", "hab_cargar", None),
    ("¿Cómo está el expediente de alguien?", "Vencimientos y lo que le falta.", "hab_control", None),
    ("Saber qué me toca según mi cargo", "Políticas, tareas, registros y riesgos.", "cargo", None),
    ("Evaluar o aprobar un proveedor", "Criterios, puntajes y quién aprueba.", "doc", "APO-COM-EVP-PRO-001"),
    ("Reportar algo que no se cumplió", "No conformidad: se reporta en 3 días hábiles.", "nc", None),
    ("Contratar a una persona", "Vacante, entrevistas, contrato e inducción.", "doc", "APO-THU-SEL-PRO-001"),
    ("Consultar los riesgos de un proceso", "Mapa de calor y controles por etapa.", "riesgos", None),
    ("Preparar una auditoría interna", "Programa anual y regla de independencia.", "doc", "EST-SGC-AUD-PRO-001"),
    ("Preparar la revisión por la dirección", "Indicadores y calendario de revisión.", "indicadores", None),
    ("Crear o cambiar un documento", "Codificación, aprobación y versiones.", "codigos", None),
]


def inicio() -> None:
    r = repo()
    try:
        import reglas
        hora = reglas.ahora().hour
    except Exception:
        hora = 9
    saludo = "Buenos días" if hora < 12 else ("Buenas tardes" if hora < 19 else "Buenas noches")
    encabezado("Resumen ejecutivo", f"{saludo}. Así está el SGC hoy",
               "Lo que requiere atención primero, luego los accesos a las tareas más frecuentes.")

    if not st.session_state.get("bienvenida_vista"):
        with st.container(border=True):
            st.markdown("**¿Primera vez en ISOtools?** En tres pasos:")
            c1, c2, c3 = st.columns(3)
            c1.markdown('<div class="paso"><span>1</span><b>Encuentre</b>Busque cualquier documento con el buscador '
                        'de la izquierda o entre por una tarea de «Accesos rápidos».</div>', unsafe_allow_html=True)
            c2.markdown('<div class="paso"><span>2</span><b>Entienda</b>Cada documento trae un resumen, sus pasos en '
                        'un vistazo y a quién afecta. En «Mi cargo» ve lo que le toca a usted.</div>', unsafe_allow_html=True)
            c3.markdown('<div class="paso"><span>3</span><b>Aprenda</b>La sección «Aprende» explica ISO 9001 con '
                        'ejemplos de STARTEC y tiene una prueba rápida para la inducción.</div>', unsafe_allow_html=True)
            if st.button("Entendido, no volver a mostrar", key="ok_bienvenida"):
                st.session_state["bienvenida_vista"] = True
                st.rerun()

    cal = sgc.calendario_revision(r, hoy())
    riesgos_ = sgc.riesgos(r)
    altos = [x for x in riesgos_ if x["Nivel"] == "ALTO"]
    con_fecha = [c for c in cal if c["Próxima revisión"]]
    al_dia = [c for c in con_fecha if c["Estado"] == "Al día"]
    vencer = [c for c in cal if c["Estado"] in ("Vencida", "Próxima (≤ 60 días)")]
    sin_fecha = [c for c in cal if c["Estado"] == "Sin fecha de aprobación"]
    revisables = [c for c in cal if c["Estado"] != "Se actualiza con cada uso"]
    m = personal_habilitado()

    pct_fecha = round(len(con_fecha) / len(revisables) * 100) if revisables else 0
    pct_cal = round(len(al_dia) / len(revisables) * 100) if revisables else 0
    pct_riesgo = round(sum(1 for x in riesgos_ if x["Ejecutor"]) / len(riesgos_) * 100) if riesgos_ else 0

    tarjetas([
        (len(r.docs), "Documentos controlados", "neutro", "Archivos del SGC publicados en ISOtools"),
        (f"{pct_cal}%", "Revisiones al día", "acento", "Documentos con fecha y revisión vigente sobre el total revisable"),
        (len(altos), "Riesgos en nivel ALTO", "critico", "De la matriz unificada y de los procedimientos"),
        (f'{m["cobertura"]["porcentaje"]}%' if m else "—", "Personal en regla",
         "ok" if m else "historico", "Colaboradores activos con todo su expediente vigente"
         if m else "Se activa al conectar Personal habilitado con Google"),
    ])

    izq, der = st.columns([1.15, 1], gap="large")
    with izq:
        st.markdown('<div class="rotulo"><h2>Salud del sistema</h2><p>Qué tan completo y al día está el SGC</p></div>',
                    unsafe_allow_html=True)
        st.markdown(
            barra_salud("Documentos con fecha de aprobación", pct_fecha,
                        f"{len(con_fecha)} de {len(revisables)}. Sin fecha no se puede programar su revisión.")
            + barra_salud("Calendario de revisión al día", pct_cal,
                          "Meta ≥ 95% según EST-SGC-DOC-PRO-001.")
            + barra_salud("Riesgos con responsable del control", pct_riesgo,
                          f"{len(riesgos_)} riesgos identificados en total.")
            + (barra_salud("Personal con expediente completo", m["cobertura"]["porcentaje"],
                           f'{m["cobertura"]["personas_ok"]} de {m["cobertura"]["personas"]} colaboradores activos.')
               if m else ""), unsafe_allow_html=True)
    with der:
        st.markdown('<div class="rotulo"><h2>Requiere atención</h2><p>Ordenado por urgencia</p></div>',
                    unsafe_allow_html=True)
        avisos = []
        if m and m["vencidos"]:
            avisos.append(("critico", f'{m["vencidos"]} certificado(s) vencido(s)',
                           "Esas personas no pueden ejecutar tareas de riesgo.", "hab_control"))
        if m and (m["renovar"] or m["revision"]):
            avisos.append(("alerta", f'{m["renovar"] + m["revision"]} certificado(s) por renovar',
                           "Vencen en los próximos 30 días o por exigencia del cliente.", "hab_control"))
        if vencer:
            avisos.append(("alerta", f"{len(vencer)} documento(s) con revisión vencida o próxima",
                           ", ".join(c["Código"] for c in vencer[:4]), "indicadores"))
        if sin_fecha:
            avisos.append(("alerta", f"{len(sin_fecha)} documento(s) sin fecha de aprobación",
                           "Registre la fecha para programar su revisión.", "indicadores"))
        nc_df, nc_ind = nc_resumen()
        if nc_ind and nc_ind["con_alerta"]:
            avisos.insert(0, ("critico", f'{nc_ind["con_alerta"]} no conformidad(es) con plazo vencido',
                              "Acciones vencidas, registro tardío o verificación pendiente.", "nc"))
        elif nc_ind and nc_ind["abiertas"]:
            avisos.append(("info", f'{nc_ind["abiertas"]} no conformidad(es) abiertas',
                           f'{nc_ind["altas_abiertas"]} de gravedad ALTA.', "nc"))
        import originales as og
        est_og = og.estado()
        if est_og["motivo"] == "sin_permiso":
            avisos.append(("critico", "Los originales de Drive no se pueden descargar",
                           "Falta compartir la carpeta iso con la cuenta de servicio de la app.", "ayuda"))
        faltan = r.sin_archivo()
        if faltan:
            avisos.append(("info", f"{len(faltan)} código(s) citado(s) que no existen",
                           ", ".join(faltan), "listado"))
        if not m:
            avisos.append(("info", "Personal habilitado sin conectar",
                           "Configure la cuenta de servicio de Google en los secretos de la app.", "hab_control"))
        if not avisos:
            st.success("Todo al día. No hay pendientes.")
        for nivel, titulo, detalle, destino in avisos:
            with st.container(border=True):
                a, b = st.columns([3.2, 1.6], vertical_alignment="center")
                a.markdown(f'<div class="pendiente {nivel}"><b>{titulo}</b><small>{html.escape(detalle)}</small></div>',
                           unsafe_allow_html=True)
                b.page_link(P[destino], label="Resolver")

    st.markdown('<div class="rotulo"><h2>Accesos rápidos</h2><p>Las tareas más frecuentes, a un clic</p></div>',
                unsafe_allow_html=True)
    cols = st.columns(4)
    for i, (titulo, sub, destino, code) in enumerate(TAREAS):
        with cols[i % 4].container(border=True):
            st.markdown(f'<div class="tarea"><b>{titulo}</b><small>{sub}</small></div>', unsafe_allow_html=True)
            if destino == "doc":
                ir_doc(code, label=code, icon=":material/description:")
            else:
                st.page_link(P[destino], label=P[destino].title, icon=P[destino].icon)

    st.markdown('<div class="rotulo"><h2>Mapa del sistema</h2><p>Todo nace de la Política de Calidad y se '
                'desarrolla en manuales, procedimientos, formatos y registros</p></div>', unsafe_allow_html=True)
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
               "Busque por código, título o palabra, o recorra el árbol por macroproceso.",
               ["Escriba una palabra (por ejemplo «arnés» o «factura»): busca dentro de todos los documentos, sin importar tildes.",
                "O recorra el árbol: cada macroproceso muestra sus manuales y, debajo, los documentos que los desarrollan.",
                "En la ficha, «En pocas palabras» resume el documento y «Los pasos en un vistazo» muestra el procedimiento.",
                "Los códigos dentro del texto son enlaces: tóquelos para saltar al documento citado."])
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
    st.markdown(f'<div class="resumen"><span>En pocas palabras</span>{enlazar(html.escape(d.resumen))}</div>',
                unsafe_allow_html=True)
    lista_pasos = sgc.pasos(d)
    if lista_pasos:
        etiqueta = "Lo que se verifica" if d.tipo == "FOR" else "Los pasos en un vistazo"
        st.markdown(f'<div class="flujo-tit">{etiqueta}</div><div class="flujo">' + "".join(
            f'<div class="flujo-paso"><span>{i}</span>{html.escape(t)}</div>' for i, t in enumerate(lista_pasos, 1))
            + "</div>", unsafe_allow_html=True)
    b1, b2, b3, b4 = st.columns([1.5, 1.1, 1.1, 1.6])
    boton_original(d, b1)
    b3.download_button("Descargar texto", data=(f"# {d.codigo} · {d.titulo}\n\nVersión {d.version}\n\n" + d.body).encode(),
                       file_name=f"{d.codigo}.md", mime="text/markdown", width="stretch", icon=":material/download:",
                       help="Copia de consulta en Markdown. Recuerde: toda copia descargada es «no controlada».")
    if d.padre in r.docs:
        with b2:
            ir_doc(d.padre, label="↑ Documento superior")
    st.page_link(P["nc"], label="¿Algo de este documento no se está cumpliendo? Repórtelo como no conformidad",
                 icon=":material/report:", query_params={"doc_nc": code})
    if code in ("APO-THU-CER-INS-001", "APO-THU-GDR-MAT-001"):
        with b4:
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
               "Versión vigente, dueño, frecuencia y próxima revisión de cada documento. Seleccione una fila para abrirlo.",
               ["Filtre por macroproceso o tipo con los botones de arriba; puede marcar varios.",
                "Toque una fila para abrir la ficha completa del documento.",
                "En la ficha, el botón «Descargar original» entrega el Word o Excel vigente.",
                "Descargue el listado en Excel para auditorías o para la revisión por la dirección."])
    c1, c2 = st.columns(2)
    macros = c1.pills("Macroproceso", MACRO_ORDER, format_func=lambda m: f"{m} · {MACROS[m]}", selection_mode="multi")
    tipos = c2.pills("Tipo", [t for t in TYPE_ORDER if any(d.tipo == t for d in r.docs.values())],
                     format_func=lambda t: TYPES[t][0], selection_mode="multi")
    cal = {c["Código"]: c for c in sgc.calendario_revision(r, hoy())}
    docs = [d for d in r.ordenados() if (not macros or d.macro in macros) and (not tipos or d.tipo in tipos)]
    df = pd.DataFrame([{"Código": d.codigo, "Documento": d.titulo, "Tipo": d.tipo_nombre, "Versión": d.version,
                        "Dueño": d.dueno, "Próxima revisión": cal[d.codigo]["Próxima revisión"],
                        "Estado de revisión": cal[d.codigo]["Estado"]} for d in docs])
    ev = st.dataframe(df, hide_index=True, width="stretch", on_select="rerun", selection_mode="single-row",
                      height=min(36 * (len(df) + 1) + 4, 760),
                      column_config={"Próxima revisión": st.column_config.DateColumn(format="DD/MM/YYYY")})
    a, b = st.columns([3, 1.2], vertical_alignment="center")
    a.caption(f"{len(docs)} de {len(r.docs)} documentos")
    b.download_button("Descargar en Excel", data=a_excel({"Listado maestro": df}), width="stretch",
                      file_name="listado_maestro_SGC.xlsx", icon=":material/download:",
                      mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
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
               "(órdenes de trabajo, facturas, actas) o aún no tienen plantilla.",
               ["Un registro es la evidencia de que algo se hizo: no se modifica y se conserva el tiempo indicado.",
                "Filtre por responsable para ver lo que archiva cada área.",
                "La columna «Lo exige» indica el documento que ordena llevar ese registro.",
                "Cumplido el tiempo de retención, la disposición final se documenta (APO-ADM-MAN-001, política 4)."])
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
               "Filtre por proceso, nivel o responsable del control.",
               ["Cada riesgo se califica con Probabilidad × Impacto (1, 3 o 5). 15 = ALTO, 5 a 9 = MEDIO, 3 = BAJO.",
                "El mapa de calor muestra dónde se concentran: arriba a la derecha está lo más grave.",
                "Use los filtros para ver los riesgos de su proceso o los controles que usted ejecuta.",
                "Si un control falla, se trata como no conformidad (EST-SGC-NCF-PRO-001)."])
    c1, c2, c3 = st.columns(3)
    procs = c1.multiselect("Proceso", sorted({x["Proceso"] for x in todos}), placeholder="Todos")
    niveles = c2.pills("Nivel", ["ALTO", "MEDIO", "BAJO"], selection_mode="multi")
    ejec = c3.multiselect("Ejecutor del control", sorted({x["Ejecutor"] for x in todos}), placeholder="Todos")
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
               "muestran su valor actual; el resto se registra en el acta de revisión por la dirección (EST-DIR-PLA-REG-001).",
               ["Un indicador mide si un proceso cumple su objetivo; la meta es el valor mínimo aceptable.",
                "«Valor actual» se calcula solo cuando el dato vive en ISOtools; el resto se mide en cada proceso.",
                "El calendario indica cuándo toca revisar cada documento según su frecuencia.",
                "Antes de la revisión por la dirección descargue el paquete en Excel: trae todo junto."])
    cal = sgc.calendario_revision(r, hoy())
    con_fecha = [c for c in cal if c["Próxima revisión"]]
    al_dia = sum(c["Estado"] == "Al día" for c in con_fecha)
    pct_cal = round(al_dia / len(con_fecha) * 100) if con_fecha else 0
    m = personal_habilitado()

    nc_df, nc_ind = nc_resumen()
    medidos = {"Cumplimiento del calendario de revisión": f"{pct_cal}%",
               "Tiempo promedio de cierre": (f'{nc_ind["tiempo_cierre"]} días' if nc_ind and nc_ind["tiempo_cierre"] is not None
                                             else "Sin casos cerrados" if nc_ind else "Sin conexión"),
               "Eficacia de las acciones correctivas": (f'{nc_ind["eficacia"]}%' if nc_ind and nc_ind["eficacia"] is not None
                                                         else "Sin verificaciones" if nc_ind else "Sin conexión"),
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

    st.markdown('<div class="rotulo"><h2>Paquete para la revisión por la dirección</h2>'
                '<p>Cláusula 9.3 · todo lo que pide el acta EST-DIR-PLA-REG-001 en un solo archivo</p></div>',
                unsafe_allow_html=True)
    hojas = paquete_sgc()
    if nc_df is not None and not nc_df.empty:
        import mejora as mj
        hojas["No conformidades"] = nc_df[mj.COLUMNAS]
    if m:
        hojas = {"Personal habilitado": pd.DataFrame([{
            "Colaboradores activos": m["cobertura"]["personas"], "Con expediente completo": m["cobertura"]["personas_ok"],
            "% en regla": m["cobertura"]["porcentaje"], "Certificados vencidos": m["vencidos"],
            "Por renovar (30 días)": m["renovar"]}]), **hojas}
    st.download_button("Descargar paquete en Excel", data=a_excel(hojas), type="primary",
                       file_name=f"paquete_revision_direccion_{hoy().isoformat()}.xlsx", icon=":material/download:",
                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    st.caption("Incluye: " + ", ".join(hojas) + ".")


# ------------------------------------------------------------------------------ MI CARGO
def mi_cargo() -> None:
    r = repo()
    encabezado("Cláusula 5.3 · Roles y responsabilidades", "Lo que le toca a cada cargo",
               "Elija un cargo y verá todo lo que el sistema le asigna, leído directamente de los documentos: "
               "su rol, las políticas que debe cumplir, sus tareas en los procedimientos, los registros que archiva, "
               "los riesgos que controla y los certificados que necesita para trabajar.",
               ["Elija su cargo en los botones.",
                "Recorra las pestañas: cada una muestra una parte de sus responsabilidades.",
                "Toque un código para abrir el documento y leer el detalle.",
                "Descargue su ficha para la inducción o para tenerla a mano."])
    cargo = st.pills("Cargo", list(sgc.CARGOS), default="Supervisor de campo", selection_mode="single")
    if not cargo:
        return
    x = sgc.responsabilidades(r, cargo)
    if x["rol"]:
        st.info(f"**Rol en el SGC:** {x['rol']}")

    nc_df, _ = nc_resumen()
    mias = nc_df[(nc_df["Responsable"] == cargo) & nc_df["Abierta"]] if nc_df is not None and not nc_df.empty else None
    if mias is not None and len(mias):
        with st.container(border=True):
            st.markdown(f"**Acciones correctivas abiertas a cargo de {cargo}: {len(mias)}**")
            for _, f in mias.iterrows():
                alerta = f" · :red[{f['Alertas'][0]}]" if f["Alertas"] else ""
                st.page_link(P["nc"], label=f"{f['ID']} · {f['Proxima_Accion']} · plazo {f['Fecha_Compromiso'] or '—'}",
                             query_params={"nc": f["ID"]}, icon=":material/report:")
                if alerta:
                    st.markdown(alerta)
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

    ficha_md = [f"# {cargo} · responsabilidades en el SGC de STARTEC S.A.", "", f"**Rol:** {x['rol']}", "",
                "## Políticas a mi cargo"] + [f"- {f['Qué']} ({f['Documento']})" for f in x["politicas"]] + \
               ["", "## Tareas en procedimientos"] + [f"- {f['Qué']} ({f['Documento']})" for f in x["tareas"]] + \
               ["", "## Registros que archivo"] + [f"- {g.codigo} · {g.nombre} · {g.retencion}" for g in x["registros"]] + \
               ["", "## Controles de riesgo que ejecuto"] + [f"- [{f['Nivel']}] {f['Riesgo']} → {f['Control']}" for f in x["riesgos"]] + \
               ["", "## Certificados que necesito"] + [f"- {k}: {v}" for k, v in x["habilitantes"].items() if v and v != "No"]
    st.download_button(f"Descargar la ficha de {cargo}", data="\n".join(ficha_md).encode(),
                       file_name=f"responsabilidades_{cargo.replace(' ', '_')}.md", mime="text/markdown",
                       icon=":material/download:")


# ------------------------------------------------------------------------------ CÓDIGOS
def codigos() -> None:
    r = repo()
    encabezado("EST-SGC-DOC-PRO-001 · Sección 5.1", "Cómo se leen los códigos",
               "Todo documento se identifica con la estructura **MACROPROCESO-PROCESO-(SUBPROCESO)-TIPO-SECUENCIAL**. "
               "Escriba un código para descifrarlo, o arme uno nuevo con el generador.",
               ["Lea el código de izquierda a derecha: área grande (macroproceso), proceso, tema (opcional), tipo y número.",
                "Escriba cualquier código en el descifrador: le dice qué significa cada parte y si existe.",
                "Para un documento nuevo elija proceso, tema y tipo: el generador propone el número libre.",
                "Luego cree el archivo siguiendo el README y regístrelo en el listado maestro."])
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
    st.subheader("Archivos originales (Word y Excel)", anchor=False)
    import originales as og
    est = og.estado()
    if est["ok"]:
        st.success("Conectado: cualquiera que entre con la contraseña puede descargar los originales desde la "
                   "ficha de cada documento, botón «Descargar original».")
    elif est["motivo"] == "sin_permiso":
        st.error("La app no puede leer la carpeta iso todavía.")
        st.markdown(og.instrucciones_permiso())
    elif est["motivo"] == "sin_google":
        st.warning("Falta la cuenta de servicio de Google en los secretos de la app (bloque `[gcp_service_account]`). "
                   "Es la misma que usa Personal habilitado. Mientras tanto, los botones abren Drive y solo "
                   "funcionan para quien tenga acceso a la carpeta.")
    else:
        st.warning("No se pudo comprobar el acceso a Drive en este momento. Recargue la página en unos minutos.")
        st.caption(est["detalle"])
    st.link_button("Abrir la carpeta iso en Google Drive", DRIVE_FOLDER)


# ------------------------------------------------------------------------------ APRENDE
def iso9001() -> None:
    r = repo()
    encabezado("Aprende · ISO 9001:2015", "ISO 9001 explicada con los documentos de STARTEC",
               "La norma se organiza en capítulos del 4 al 10 que siguen el ciclo Planificar, Hacer, Verificar y "
               "Actuar. Aquí verá qué pide cada capítulo, en lenguaje simple, y qué documentos de STARTEC lo cumplen.",
               ["Lea el ciclo de arriba: es la lógica de toda la norma.",
                "Abra un capítulo para ver qué pide y con qué documentos lo cumple STARTEC.",
                "Toque un código para leer ese documento.",
                "Útil para preparar auditorías: muestra dónde está la evidencia de cada cláusula."])
    st.markdown('<div class="ciclo">' + "".join(
        f'<div class="ciclo-fase f{i}"><span>{i}</span><b>{fase}</b><small>Capítulos {caps}</small><p>{txt}</p></div>'
        for i, (fase, (caps, txt)) in enumerate(sgc.CICLO.items(), 1)) + "</div>", unsafe_allow_html=True)
    st.caption("Al terminar «Actuar» el ciclo vuelve a empezar: así funciona la mejora continua.")

    mapa = sgc.clausulas(r)
    for cap, (nombre, fase, txt) in sgc.CAPITULOS.items():
        docs = mapa.get(cap, {})
        with st.expander(f"**Capítulo {cap} · {nombre}** · {fase} · {len(docs)} documento(s)", expanded=cap == "8"):
            st.markdown(f"**Qué pide, en simple:** {txt}")
            if not docs:
                st.warning("Ningún documento cita este capítulo.")
                continue
            filas = []
            for code in sorted(docs, key=lambda c: (sgc.MACRO_ORDER.index(c[:3]), c)):
                cls = sorted(docs[code], key=lambda x: [int(n) for n in x.split(".")])
                nota = " (exclusión declarada de diseño)" if code == "EST-SGC-MAN-001" and "8.3" in cls else ""
                filas.append(f"| {link(code)} | {html.escape(r.docs[code].titulo)} | {', '.join(cls)}{nota} |")
            st.markdown("| Documento | Título | Cláusulas que cubre |\n|---|---|---|\n" + "\n".join(filas),
                        unsafe_allow_html=True)


def glosario() -> None:
    r = repo()
    terminos = sgc.glosario(r)
    encabezado("Aprende · Vocabulario", "Glosario del SGC",
               f"{len(terminos)} términos: los que definen los propios manuales de STARTEC y los básicos de ISO 9001. "
               "Úselo cuando un documento use una palabra que no conoce.")
    q = st.text_input("Buscar un término", placeholder="Ej.: no conformidad, riesgo, registro")
    letras = sorted({sgc.norm(t["Término"])[0].upper() for t in terminos})
    letra = st.pills("Inicial", letras, selection_mode="single")
    sel = [t for t in terminos if (not q or sgc.norm(q) in sgc.norm(t["Término"] + " " + t["Definición"]))
           and (not letra or sgc.norm(t["Término"]).upper().startswith(letra))]
    if not sel:
        st.info("No hay términos con ese criterio.")
    cols = st.columns(2)
    for i, t in enumerate(sel):
        with cols[i % 2].container(border=True):
            fuente = "Definición general" if t["Fuente"] == "ISOtools" else f"Definido en {link(t['Fuente'])}"
            st.markdown(f'<div class="termino"><b>{html.escape(t["Término"])}</b><p>{html.escape(t["Definición"])}</p>'
                        f'<small>{fuente}</small></div>', unsafe_allow_html=True)


PREGUNTAS = [
    ("Un técnico llega al sitio y falta el arnés. ¿Puede empezar el trabajo en altura?",
     ["Sí, si el supervisor lo autoriza verbalmente", "No: sin checklist completo y firmado el trabajo no se inicia",
      "Sí, si el cliente lo pide con urgencia"], 1, "MIS-OPS-EJE-PRO-001",
     "El checklist previo debe estar firmado y todas sus verificaciones cumplir. Si algo falla, se decide con la Jefa de Operaciones y queda registrado."),
    ("¿En cuánto tiempo se debe reportar una no conformidad?",
     ["Dentro de 3 días hábiles", "Al final del mes", "Solo cuando la detecta una auditoría"], 0, "EST-SGC-NCF-PRO-001",
     "Cualquier colaborador la reporta a Gestión y Control, que la registra dentro de los 3 días hábiles."),
    ("Un colaborador tiene su certificado de riesgo eléctrico en rojo. ¿Qué significa?",
     ["Que vence en menos de 30 días", "Que está vencido o no cargado: no puede ejecutar labores de riesgo",
      "Que debe renovarlo el próximo año"], 1, "APO-THU-CER-INS-001",
     "Rojo es vencido o ausente: está prohibido trabajar hasta actualizarlo. Amarillo es «vence en menos de 30 días»."),
    ("Necesita un proveedor que no está en la lista aprobada por una urgencia. ¿Qué hace?",
     ["Lo contrata y lo informa después", "Pide aprobación expresa y documentada a la Gerencia General antes de contratar",
      "Busca otra cotización y contrata la más barata"], 1, "APO-COM-EVP-PRO-001",
     "Las excepciones existen, pero solo con aprobación escrita de la Gerencia General antes de contratar."),
    ("Imprimió un procedimiento hace un año. ¿Puede seguir usándolo?",
     ["Sí, mientras esté legible", "Solo si nadie lo ha cambiado", "No sin verificar: toda copia impresa es «no controlada»"], 2,
     "EST-SGC-DOC-PRO-001", "Solo vale la versión digital vigente del repositorio. Confirme la versión antes de usar una copia."),
    ("Un proveedor le ofrece un regalo por adjudicarle un contrato. ¿Qué indica la política?",
     ["Aceptarlo si es de bajo valor", "Rechazarlo: está prohibido recibir obsequios de clientes o proveedores",
      "Aceptarlo y declararlo a fin de año"], 1, "EST-DIR-GOB-POL-001",
     "La Política Antisoborno prohíbe solicitar o recibir obsequios, comisiones o invitaciones de clientes y proveedores."),
    ("¿Quién no puede auditar el proceso de Gestión y Control?",
     ["La Gerencia General", "Un auditor externo", "Gestión y Control"], 2, "EST-SGC-AUD-PRO-001",
     "Regla de independencia: nadie audita su propio proceso. Ese proceso lo audita la Gerencia General o un externo."),
    ("¿Qué hace falta para que Contabilidad facture un servicio?",
     ["Solo la cotización aprobada", "La orden de trabajo, el informe técnico y la firma de conformidad del cliente",
      "Un correo del supervisor"], 1, "APO-FIN-CTB-MAN-001",
     "No se procesa ninguna factura sin orden de trabajo aprobada e informe técnico; la firma del cliente es condición previa."),
]


def prueba() -> None:
    encabezado("Aprende · Autoevaluación", "Ponte a prueba",
               f"{len(PREGUNTAS)} situaciones reales de STARTEC. Responda y al final verá su resultado con la "
               "explicación y el documento donde está la regla. Sirve para la inducción y para repasar antes de una auditoría.")
    ronda = st.session_state.setdefault("prueba_ronda", 0)
    with st.form(f"prueba_{ronda}"):
        respuestas = []
        for i, (preg, opciones, _, _, _) in enumerate(PREGUNTAS, 1):
            respuestas.append(st.radio(f"**{i}.** {preg}", opciones, index=None, key=f"p{ronda}_{i}"))
        enviado = st.form_submit_button("Ver mi resultado", type="primary")
    if not enviado:
        return
    if any(x is None for x in respuestas):
        st.warning(f"Le faltan {sum(x is None for x in respuestas)} pregunta(s) por responder.")
        return
    aciertos = 0
    detalle = []
    for (preg, opciones, ok, code, expl), resp in zip(PREGUNTAS, respuestas):
        bien = opciones.index(resp) == ok
        aciertos += bien
        detalle.append((bien, preg, opciones[ok], code, expl))
    pct = round(aciertos / len(PREGUNTAS) * 100)
    (st.success if pct >= 85 else st.warning if pct >= 60 else st.error)(
        f"**{aciertos} de {len(PREGUNTAS)} correctas ({pct}%).** "
        + ("Excelente: conoce las reglas clave del SGC." if pct >= 85 else
           "Bien, pero repase las que falló." if pct >= 60 else "Conviene repasar los documentos indicados."))
    for bien, preg, correcta, code, expl in detalle:
        with st.container(border=True):
            st.markdown(f'{"✅" if bien else "❌"} **{preg}**  \nRespuesta correcta: *{correcta}*  \n'
                        f'{expl} · Ver {link(code)}', unsafe_allow_html=True)
    if st.button("Volver a intentarlo"):
        st.session_state["prueba_ronda"] = ronda + 1
        st.rerun()
