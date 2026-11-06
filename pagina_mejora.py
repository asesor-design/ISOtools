"""
Página «No conformidades» de ISOtools: reportar, dar seguimiento y cerrar,
paso a paso según EST-SGC-NCF-PRO-001.
"""
from __future__ import annotations

import html
from datetime import timedelta

import pandas as pd
import streamlit as st

import mejora as mj
import paginas as pg
import sgc

CARGOS = list(sgc.CARGOS)


def _sin_conexion() -> None:
    st.warning("Para guardar no conformidades la app necesita la cuenta de servicio de Google "
               "(bloque `[gcp_service_account]` en los secretos), la misma de Personal habilitado. "
               "Se guardan en la pestaña «No conformidades» de esa hoja de cálculo.")
    with st.expander("Mientras tanto: cómo se trata una no conformidad", expanded=True):
        _explicacion()


def _explicacion() -> None:
    st.markdown(pg.enlazar(
        "Una **no conformidad** es cualquier incumplimiento de un requisito: del cliente, legal o de nuestros "
        "propios documentos. Ejemplos: una queja de cliente, un trabajo iniciado sin checklist, un proveedor "
        "contratado sin evaluación, un hallazgo de auditoría. Así se trata según EST-SGC-NCF-PRO-001:"),
        unsafe_allow_html=True)
    pasos = [
        ("Reportar", "Quien la detecta la reporta. Se registra dentro de **3 días hábiles**."),
        ("Analizar la causa", "Si es MEDIO o ALTO, el dueño del proceso busca la causa raíz con los **5 porqués**."),
        ("Corregir", "Se define la acción, el responsable y el plazo. Si requiere recursos importantes, aprueba la Gerencia General."),
        ("Verificar", "Entre **30 y 90 días** después, Gestión y Control comprueba que el problema no se repite."),
        ("Cerrar", "Solo se cierra si la acción fue eficaz. Si no, se reabre y se vuelve a analizar."),
    ]
    st.markdown('<div class="flujo">' + "".join(
        f'<div class="flujo-paso"><span>{i}</span><b>{t}</b><br>{pg.enlazar(d).replace("**", "")}</div>'
        for i, (t, d) in enumerate(pasos, 1)) + "</div>", unsafe_allow_html=True)


def _etapas(fila: pd.Series) -> None:
    """Barra de progreso del caso con la etapa actual resaltada."""
    actual = "Análisis de causa" if fila["Estado"] == "Reabierta" else fila["Estado"]
    idx = mj.ETAPAS.index(actual) if actual in mj.ETAPAS else 0
    html_ = '<div class="etapas">'
    for i, e in enumerate(mj.ETAPAS):
        clase = "hecha" if i < idx else ("actual" if i == idx else "")
        html_ += f'<div class="etapa {clase}"><span>{i + 1}</span>{e}</div>'
    st.markdown(html_ + "</div>", unsafe_allow_html=True)


def _detalle(ident: str, df: pd.DataFrame) -> None:
    fila = df[df["ID"] == ident]
    if fila.empty:
        st.warning(f"No se encontró {ident}.")
        return
    f = fila.iloc[0]
    st.markdown(f'<div class="eyebrow">{ident}</div>', unsafe_allow_html=True)
    st.subheader(f["Descripcion"][:140] + ("…" if len(f["Descripcion"]) > 140 else ""), anchor=False)
    color = {"ALTO": "red", "MEDIO": "orange", "BAJO": "green"}.get(f["Severidad"], "gray")
    st.markdown(f':{color}-badge[{f["Severidad"]}] :gray-badge[{f["Origen"]}] :gray-badge[{f["Proceso"]}] '
                f':blue-badge[{f["Estado"]}]' + (f" · Documento {pg.link(f['Documento'])}" if f["Documento"] else ""),
                unsafe_allow_html=True)
    if f["Estado"] == "Reabierta":
        st.error(f"Reabierta: la acción anterior no fue eficaz ({f['Resultado_Verificacion']}). Analice de nuevo la causa.")
    _etapas(f)
    for a in f["Alertas"]:
        st.warning(a, icon=":material/schedule:")

    izq, der = st.columns([1.6, 1], gap="large")
    with der:
        with st.container(border=True):
            st.caption("DATOS DEL CASO")
            st.markdown(
                f"**Detectada:** {f['Fecha_Deteccion']}  \n**Registrada:** {f['Fecha_Registro']}  \n"
                f"**Reportó:** {html.escape(f['Reportado_Por'] or '—')}  \n"
                f"**Corrección inmediata:** {html.escape(f['Correccion_Inmediata'] or '—')}  \n"
                f"**Días abierta:** {f['Dias_Abierta'] if f['Dias_Abierta'] is not None else '—'}")
        if f["Causa_Raiz"]:
            with st.container(border=True):
                st.caption("ANÁLISIS DE CAUSA")
                for i, p in enumerate([x for x in f["Porques"].split(" | ") if x], 1):
                    st.markdown(f"{i}. ¿Por qué? {html.escape(p)}")
                st.markdown(f"**Causa raíz:** {html.escape(f['Causa_Raiz'])}")
        if f["Accion_Correctiva"]:
            with st.container(border=True):
                st.caption("ACCIÓN CORRECTIVA")
                st.markdown(f"{html.escape(f['Accion_Correctiva'])}  \n**Responsable:** {f['Responsable']}  \n"
                            f"**Plazo:** {f['Fecha_Compromiso']}" +
                            (f"  \n**Aprobó:** {html.escape(f['Aprobado_Por'])}" if f["Aprobado_Por"] else "") +
                            (f"  \n**Implementada:** {f['Fecha_Implementacion']}" if f["Fecha_Implementacion"] else "") +
                            (f"  \n**Evidencia:** {html.escape(f['Evidencia'])}" if f["Evidencia"] else ""))
        if f["Resultado_Verificacion"]:
            st.caption(f"Última verificación ({f['Fecha_Verificacion']}): {f['Resultado_Verificacion']}")

    with izq:
        h = mj.hoy()
        st.markdown(f"**Siguiente paso:** {f['Proxima_Accion']}")
        estado = f["Estado"]

        necesita_analisis = estado == "Reabierta" or (estado == "Registrada" and mj.requiere_analisis(f["Severidad"]))
        necesita_accion = estado == "Análisis de causa" or (estado == "Registrada" and not mj.requiere_analisis(f["Severidad"]))

        if necesita_analisis:
            with st.form(f"analisis_{ident}"):
                st.markdown("**Análisis de causa raíz · 5 porqués** (EST-SGC-NCF-PRO-001, 5.3)")
                st.caption("Pregunte «¿por qué pasó?» y luego «¿por qué?» a cada respuesta, hasta llegar a algo que "
                           "se pueda corregir para que no vuelva a ocurrir. No siempre hacen falta los cinco.")
                porques = [st.text_input(f"¿Por qué? {i}", key=f"pq_{ident}_{i}") for i in range(1, 6)]
                causa = st.text_area("Causa raíz encontrada",
                                     placeholder="Ej.: el checklist no incluye la revisión del arnés para trabajos menores a 2 m")
                if st.form_submit_button("Guardar análisis", type="primary"):
                    if sum(1 for x in porques if x.strip()) < 2 or not causa.strip():
                        st.error("Responda al menos dos «¿por qué?» y escriba la causa raíz.")
                    else:
                        mj.guardar_analisis(ident, porques, causa)
                        st.toast("Análisis guardado. Ahora defina la acción correctiva.")
                        st.rerun()

        elif necesita_accion:
            with st.form(f"accion_{ident}"):
                st.markdown("**Acción correctiva** (5.4)")
                st.caption("Debe atacar la causa raíz, no solo el síntoma. Ej.: «agregar el arnés al checklist y "
                           "capacitar a los supervisores», no «comprar otro arnés».")
                accion = st.text_area("¿Qué se va a hacer?")
                c1, c2 = st.columns(2)
                resp = c1.selectbox("Responsable", CARGOS, index=CARGOS.index("Gestión y Control"))
                plazo = c2.date_input("Fecha compromiso", value=h + timedelta(days=30), min_value=h, format="DD/MM/YYYY")
                aprob = st.checkbox("Implica inversión o recursos significativos (la aprueba la Gerencia General)")
                if st.form_submit_button("Guardar acción", type="primary"):
                    if len(accion.strip()) < 10:
                        st.error("Describa la acción con un poco más de detalle.")
                    else:
                        mj.definir_accion(ident, accion, resp, plazo, aprob)
                        st.toast("Acción correctiva registrada")
                        st.rerun()

        elif estado == "Acción en curso":
            if f["Requiere_Aprobacion"] == "Sí" and not f["Aprobado_Por"]:
                with st.form(f"aprob_{ident}"):
                    st.markdown("**Aprobación de la Gerencia General** (5.4)")
                    quien = st.text_input("Nombre de quien aprueba")
                    if st.form_submit_button("Registrar aprobación", type="primary"):
                        if not quien.strip():
                            st.error("Escriba el nombre de quien aprueba.")
                        else:
                            mj.aprobar(ident, quien)
                            st.rerun()
            else:
                with st.form(f"impl_{ident}"):
                    st.markdown("**Implementación**")
                    fecha_impl = st.date_input("Fecha en que se implementó", value=h, max_value=h, format="DD/MM/YYYY")
                    evid = st.text_area("Evidencia", placeholder="Ej.: checklist v1.1 publicado; acta de capacitación del 12/11")
                    if st.form_submit_button("Marcar como implementada", type="primary"):
                        if not evid.strip():
                            st.error("Indique la evidencia de lo que se hizo.")
                        else:
                            mj.implementar(ident, fecha_impl, evid)
                            st.toast(f"Implementada. Verifique la eficacia desde el "
                                     f"{mj.texto_fecha(fecha_impl + timedelta(days=mj.VERIF_MIN))}.")
                            st.rerun()

        elif estado == "En verificación":
            impl = mj.a_fecha(f["Fecha_Implementacion"])
            desde = impl + timedelta(days=mj.VERIF_MIN) if impl else h
            if h < desde:
                st.info(f"La eficacia se verifica entre 30 y 90 días después de implementar: desde el "
                        f"**{mj.texto_fecha(desde)}** hasta el **{mj.texto_fecha(impl + timedelta(days=mj.VERIF_MAX))}**. "
                        "Así se comprueba que el problema realmente no se repite.")
            with st.form(f"verif_{ident}"):
                st.markdown("**Verificación de eficacia** (5.5) · la realiza Gestión y Control")
                res = st.radio("¿Se eliminó la causa? ¿La no conformidad no se volvió a presentar?",
                               ["Sí, la acción fue eficaz", "No, el problema persiste o se repitió"], index=None)
                nota = st.text_input("Cómo se comprobó", placeholder="Ej.: revisados 20 checklists de noviembre, todos completos")
                if st.form_submit_button("Registrar verificación", type="primary"):
                    if res is None or not nota.strip():
                        st.error("Elija el resultado y explique cómo se comprobó.")
                    else:
                        mj.verificar(ident, res.startswith("Sí"), nota, int(f["Verificaciones_No_Eficaces"] or 0))
                        st.toast("Cerrada" if res.startswith("Sí") else "Reabierta para un nuevo análisis")
                        st.rerun()

        elif estado == "Cerrada":
            st.success(f"Cerrada el {f['Fecha_Cierre']} tras verificar que la acción fue eficaz.")


def _reportar() -> None:
    q = st.query_params
    doc_pre = q.get("doc_nc", "")
    r = pg.repo()
    st.markdown("Cualquier persona puede reportar. No hace falta saber la causa ni la solución: "
                "solo describa **qué pasó, dónde y cuándo**. Gestión y Control lo registra y le da seguimiento.")
    with st.form("reportar", clear_on_submit=True):
        desc = st.text_area("¿Qué pasó? *", placeholder="Ej.: El 4/11 en la planta del cliente X se inició el "
                            "mantenimiento del chiller sin el checklist firmado.")
        c1, c2, c3 = st.columns(3)
        origen = c1.selectbox("¿Cómo se detectó? *", mj.ORIGENES)
        proceso = c2.selectbox("Proceso afectado *", list(sgc.PROCS.values()), index=2)
        fecha = c3.date_input("Fecha en que se detectó", value=mj.hoy(), max_value=mj.hoy(), format="DD/MM/YYYY")
        c1, c2 = st.columns(2)
        sev = c1.radio("Gravedad *", mj.SEVERIDADES, index=1, horizontal=True,
                       help="ALTO: afecta al cliente, la seguridad o un requisito legal. MEDIO: incumple un procedimiento "
                            "sin daño mayor. BAJO: desviación menor y aislada.")
        docs = [""] + [d.codigo for d in r.ordenados()]
        doc = c2.selectbox("Documento que se incumplió (opcional)", docs,
                           index=docs.index(doc_pre) if doc_pre in docs else 0,
                           format_func=lambda c: f"{c} · {r.docs[c].titulo}" if c else "— No sé / ninguno —")
        corr = st.text_input("¿Se hizo algo de inmediato para contenerlo? (opcional)",
                             placeholder="Ej.: se detuvo el trabajo hasta completar el checklist")
        quien = st.text_input("Su nombre y cargo *")
        if st.form_submit_button("Reportar no conformidad", type="primary"):
            if len(desc.strip()) < 15 or not quien.strip():
                st.error("Describa qué pasó (al menos una frase) y escriba su nombre.")
            else:
                ident = mj.registrar({"Descripcion": desc.strip(), "Origen": origen, "Proceso": proceso,
                                      "Fecha_Deteccion": mj.texto_fecha(fecha), "Severidad": sev, "Documento": doc,
                                      "Correccion_Inmediata": corr.strip(), "Reportado_Por": quien.strip()})
                st.success(f"Registrada como **{ident}**. Gracias: reportar es la forma en que el sistema mejora.")
                if mj.dias_habiles(fecha, mj.hoy()) > mj.DIAS_REGISTRO:
                    st.warning("Se detectó hace más de 3 días hábiles: quedará marcada como registro fuera de plazo.")


def no_conformidades() -> None:
    pg.encabezado("EST-SGC-NCF-PRO-001 · Cláusula 10.2", "No conformidades y acciones correctivas",
                  "Reporte lo que no se cumplió y siga cada caso hasta comprobar que no se repite. Es el registro "
                  "EST-SGC-NCF-REG-001 que exige el procedimiento.",
                  ["Para reportar, use la pestaña «Reportar»: basta con contar qué pasó.",
                   "En «Bandeja» toque un caso para ver su avance y el siguiente paso.",
                   "Cada paso se completa con un formulario corto; la app controla los plazos del procedimiento.",
                   "Los indicadores de cierre y eficacia se calculan solos y llegan al paquete de revisión por la dirección."])
    if not mj.disponible():
        _sin_conexion()
        return
    try:
        df = mj.leer()
    except Exception as e:
        st.error(f"No se pudo leer la hoja de no conformidades: {str(e)[:200]}")
        return

    if st.query_params.get("doc_nc"):
        if st.button("← Ver la bandeja de no conformidades"):
            del st.query_params["doc_nc"]
            st.rerun()
        st.subheader("Reportar una no conformidad", anchor=False)
        _reportar()
        return

    abierto = st.query_params.get("nc", "")
    if abierto:
        if st.button("← Volver a la bandeja"):
            del st.query_params["nc"]
            st.rerun()
        _detalle(abierto, df)
        return

    tab_b, tab_r, tab_c = st.tabs([":material/inbox: Bandeja", ":material/add_alert: Reportar",
                                   ":material/school: Cómo funciona"])
    with tab_r:
        _reportar()
    with tab_c:
        _explicacion()
        st.caption("Plazos del procedimiento: registro en 3 días hábiles · verificación de eficacia entre 30 y 90 días "
                   "· metas: cierre promedio ≤ 45 días y eficacia ≥ 85%.")
    with tab_b:
        ind = mj.indicadores(df)
        pg.tarjetas([
            (ind["abiertas"], "Abiertas", "neutro", "Casos que aún no se cierran"),
            (ind["con_alerta"], "Con plazo vencido", "critico" if ind["con_alerta"] else "ok",
             "Registro tardío, acción vencida o verificación pendiente"),
            (f'{ind["tiempo_cierre"]} d' if ind["tiempo_cierre"] is not None else "—", "Cierre promedio",
             "acento", f"Meta ≤ {mj.META_CIERRE} días"),
            (f'{ind["eficacia"]}%' if ind["eficacia"] is not None else "—", "Eficacia de acciones",
             "ok", f"Meta ≥ {mj.META_EFICACIA}%"),
        ])
        if df.empty:
            st.info("Todavía no hay no conformidades registradas. Cuando alguien reporte una, aparecerá aquí.")
            return
        c1, c2, c3 = st.columns(3)
        ver = c1.pills("Mostrar", ["Abiertas", "Con plazo vencido", "Cerradas", "Todas"], default="Abiertas")
        sev = c2.pills("Gravedad", mj.SEVERIDADES, selection_mode="multi")
        resp = c3.multiselect("Responsable", sorted({x for x in df["Responsable"] if x}), placeholder="Todos")
        sel = df
        if ver == "Abiertas":
            sel = sel[sel["Abierta"]]
        elif ver == "Con plazo vencido":
            sel = sel[sel["Abierta"] & sel["Alertas"].map(bool)]
        elif ver == "Cerradas":
            sel = sel[sel["Estado"] == "Cerrada"]
        if sev:
            sel = sel[sel["Severidad"].isin(sev)]
        if resp:
            sel = sel[sel["Responsable"].isin(resp)]
        orden = {"ALTO": 0, "MEDIO": 1, "BAJO": 2}
        sel = sel.assign(_o=sel["Severidad"].map(orden), _a=~sel["Alertas"].map(bool)).sort_values(["_a", "_o", "ID"])
        vista = pd.DataFrame({
            "ID": sel["ID"], "Gravedad": sel["Severidad"].map({"ALTO": "🔴 ALTO", "MEDIO": "🟡 MEDIO", "BAJO": "🟢 BAJO"}),
            "Estado": sel["Estado"], "Qué pasó": sel["Descripcion"], "Proceso": sel["Proceso"],
            "Responsable": sel["Responsable"], "Siguiente paso": sel["Proxima_Accion"],
            "Alerta": sel["Alertas"].map(lambda a: "⚠ " + a[0] if a else ""), "Días": sel["Dias_Abierta"],
        })
        ev = st.dataframe(vista, hide_index=True, width="stretch", on_select="rerun", selection_mode="single-row",
                          column_config={"Qué pasó": st.column_config.TextColumn(width="large")})
        a, b = st.columns([3, 1.2], vertical_alignment="center")
        a.caption(f"{len(vista)} caso(s). Toque una fila para ver el detalle y avanzar al siguiente paso.")
        b.download_button("Registro en Excel", data=pg.a_excel({"No conformidades": df[mj.COLUMNAS]}),
                          file_name=f"EST-SGC-NCF-REG-001_{mj.hoy().isoformat()}.xlsx", width="stretch",
                          icon=":material/download:",
                          mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        if ev.selection.rows:
            st.query_params["nc"] = vista.iloc[ev.selection.rows[0]]["ID"]
            st.rerun()
