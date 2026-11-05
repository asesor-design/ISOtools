"""
Personal habilitado · Control documental de colaboradores
Streamlit · Google Drive · Google Sheets

Implementa APO-THU-CER-INS-001 (Instructivo de control de certificados) dentro de
ISOtools. Antes era la app independiente gestion-de-datos; aquí sus paneles se
exponen como tres páginas: Panel de control, Cargar documentos y Equipo.

Paneles
    Colaboradores      alta, estado, etiqueta y asignación a supervisores
    Documento          carga individual y por lotes
    Documento común    un archivo que cubre a varios colaboradores (planilla IESS)
    Dashboard          semáforo, filtros y exportación
"""

from datetime import datetime

import pandas as pd
import streamlit as st

import ajustes as cfg
import estilos
import nucleo as nu
import personas as pe
import reglas as r



# ==========================================================================================
# AUXILIARES DE INTERFAZ
# ==========================================================================================
def aviso(tipo, titulo, detalle=""):
    st.markdown(estilos.aviso(tipo, titulo, detalle), unsafe_allow_html=True)


def rotulo(titulo, ayuda=""):
    st.markdown(estilos.rotulo(titulo, ayuda), unsafe_allow_html=True)


def vacio(titulo, detalle):
    st.markdown(estilos.vacio(titulo, detalle), unsafe_allow_html=True)


def multiselect_con_todos(etiqueta, opciones, base, ayuda="", proporcion=(4, 1)):
    """
    Multiselect con un botón «Todos».

    Streamlit prohíbe escribir en la clave de un widget ya instanciado, así que
    no se puede rellenar el multiselect desde un botón que está a su lado. La
    selección se guarda en un estado propio y el widget se recrea con una clave
    versionada, que es la forma admitida de cambiarle el valor por defecto.
    """
    estado, version = f"{base}_sel", f"{base}_ver"
    st.session_state.setdefault(estado, [])
    st.session_state.setdefault(version, 0)

    #  Se descartan las opciones que ya no existen, para que el widget no falle
    #  si alguien se dio de baja entre una recarga y otra.
    previa = [o for o in st.session_state[estado] if o in opciones]

    izq, der = st.columns(proporcion)
    with der:
        st.write("")
        if st.button("Todos", key=f"{base}_todos", width='stretch',
                     disabled=not opciones or previa == list(opciones)):
            st.session_state[estado] = list(opciones)
            st.session_state[version] += 1
            st.rerun()
        if previa and st.button("Ninguno", key=f"{base}_ninguno", width='stretch'):
            st.session_state[estado] = []
            st.session_state[version] += 1
            st.rerun()

    with izq:
        seleccion = st.multiselect(
            etiqueta, opciones, default=previa, help=ayuda,
            key=f"{base}_ms_{st.session_state[version]}")

    st.session_state[estado] = seleccion
    if opciones:
        st.caption(f"{len(seleccion)} de {len(opciones)} seleccionados")
    return seleccion


def selector_persona(clave, solo_activos=True, etiqueta="Colaborador"):
    """Desplegable de colaboradores. Devuelve la ficha completa o None."""
    opciones = pe.opciones(solo_activos)
    if not opciones:
        vacio("Aún no hay colaboradores",
              "Los documentos se cargan siempre sobre una ficha. Crea la primera en "
              "el panel <b>Equipo</b>.")
        return None
    elegido = st.selectbox(etiqueta, opciones, index=None, key=clave,
                           placeholder="Busca por cédula o nombre")
    return pe.ficha(pe.cedula_de(elegido)) if elegido else None


def campo_caducidad(tipo, emision, clave):
    """
    Muestra la caducidad. Cuando el tipo tiene vigencia parametrizada el campo
    va bloqueado y calculado; solo se pide a mano en los tipos sin regla fija.
    """
    automatica = r.caducidad_automatica(tipo, emision) if tipo else None
    if automatica:
        regla = cfg.VIGENCIAS.get(tipo)
        st.date_input("Fecha de caducidad", value=automatica.date(), format="DD-MM-YYYY",
                      disabled=True, key=f"{clave}_auto",
                      help=f"Calculada: emisión + {regla[0]} {regla[1].replace('anios','años')}")
        return automatica
    elegida = st.date_input("Fecha de caducidad", value=None, format="DD-MM-YYYY",
                            key=clave, help="Este tipo no tiene vigencia fija")
    return r.parsear_fecha(elegida)


# ==========================================================================================
# BARRA LATERAL
# ==========================================================================================
def barra_lateral():
    with st.sidebar:
        rotulo("Estado del sistema")
        diag = nu.diagnostico()
        if diag["error"]:
            #  El diagnóstico distingue un corte de red de un problema de
            #  configuración, para no mandar a revisar permisos cuando lo que
            #  falló fue la conexión.
            if diag.get("transitorio"):
                aviso("info", "Conexión interrumpida", diag["error"])
                st.markdown(
                    '<div class="nota"><strong>No es un problema de configuración.</strong> '
                    'La conexión con Google se cortó, algo que ocurre de vez en cuando. '
                    'El sistema ya reintentó tres veces reconstruyendo la conexión. '
                    'Pulsa <strong>Reintentar</strong>; si insiste durante varios minutos, '
                    'revisa el estado de los servicios de Google.</div>',
                    unsafe_allow_html=True)
            else:
                aviso("error", "Sin conexión", diag["error"])
                st.markdown(
                    '<div class="nota">Parece un problema de acceso o de datos. Revisa que '
                    'la cuenta de servicio tenga permiso de <strong>Administrador de '
                    'contenido</strong> en la unidad compartida y que los identificadores '
                    'de <code>ajustes.py</code> sean correctos.</div>',
                    unsafe_allow_html=True)

            st.write("")
            if st.button("Reintentar", type="primary", width='stretch', key="reintentar"):
                st.cache_resource.clear()
                st.cache_data.clear()
                st.rerun()
            return diag

        fichas = pe.colaboradores()
        activos = len(pe.activos())
        st.markdown(
            f'<div class="estado-linea">Carpeta · <b>{diag["drive"]}</b></div>'
            f'<div class="estado-linea">Hoja · <b>{diag["hoja"]}</b></div>'
            f'<div class="estado-linea">Documentos · <b>{diag["registros"]}</b></div>'
            f'<div class="estado-linea">Colaboradores · <b>{activos} activos</b> '
            f'de {len(fichas)}</div>', unsafe_allow_html=True)

        pendientes = pe.sin_correo()
        if pendientes:
            st.write("")
            aviso("info", f"{len(pendientes)} supervisor(es) sin correo",
                  "No recibirán los avisos hasta completarlo.")

        purgas = pe.pendientes_de_purga()
        if not purgas.empty:
            st.write("")
            aviso("info", f"{len(purgas)} inactivo(s) para depurar",
                  "Cumplieron un año fuera. Revísalos en la página Equipo.")

        st.write("")
        if st.button("Recargar datos", width='stretch'):
            nu.invalidar_cache()
            pe.invalidar()
            st.rerun()

        with st.expander("Vigencias por documento"):
            lineas = "".join(
            f'<div class="estado-linea">{t.replace("Certificado de Riesgos de Trabajo ","RT ")} · '
            f'<b>{v[0]} {v[1].replace("anios","años")}</b></div>'
                for t, v in cfg.VIGENCIAS.items() if v and t in cfg.TIPOS_DOCUMENTO)
            st.markdown(lineas, unsafe_allow_html=True)
            st.markdown(
                f'<div class="nota">Con etiqueta <strong>{cfg.ETIQUETA_ESPECIAL}</strong>, '
                f'los certificados de riesgos se renuevan cada año aunque legalmente '
                f'duren cuatro.</div>', unsafe_allow_html=True)
        return diag


# ==========================================================================================
# PANEL · COLABORADORES
# ==========================================================================================
def panel_colaboradores():
    alta, gestion, supervisores = st.tabs(
        ["Colaboradores", "Etiquetas y equipos", "Supervisores"])

    # ---------------------------------------------------------------- Alta
    with alta:
        rotulo("Nueva ficha o edición")
        registrados = pe.colaboradores()
        lista_sup = [""] + pe.nombres_supervisores()

        izq, der = st.columns(2, gap="large")
        with izq:
            cedula = st.text_input("Número de cédula", key="c_cedula",
                                   placeholder="Ej. 0104567890",
                                   help="Llave del expediente. Si ya existe, se actualiza")
            nombre = st.text_input("Nombre completo", key="c_nombre",
                                   placeholder="Ej. María Fernanda Loja Peralta")
            rol = st.selectbox("Rol / Cargo", cfg.ROLES, index=None, key="c_rol",
                               placeholder="Selecciona o escribe",
                               accept_new_options=True)
        with der:
            supervisor = st.selectbox("Supervisor asignado", lista_sup, key="c_sup",
                                      help="Recibirá los avisos de vencimiento de esta persona")
            etiqueta = st.toggle(
                f"Etiqueta {cfg.ETIQUETA_ESPECIAL}", key="c_etiqueta",
                help=f"Renueva certificados de riesgos cada año en lugar de cada cuatro")
            adicionales = st.multiselect(
                "Documentos exigibles además de los básicos", cfg.OPCIONALES,
                default=cfg.sugeridos(rol), key="c_requeridos",
                help="Los certificados de riesgos dependen de la tarea que hace la "
                     "persona, no de su cargo. Marca solo los que le correspondan.")
            observaciones = st.text_area("Observaciones", key="c_obs", height=80)

        basicos = " · ".join(f"<code>{t}</code>" for t in cfg.REQUERIDOS_BASE)
        st.markdown(
            f'<div class="nota">A todos se les exige: {basicos}. Lo que marques '
            f'arriba se suma solo para esta persona.</div>',
            unsafe_allow_html=True)

        if st.button("Guardar ficha", type="primary", key="c_guardar"):
            if not (cedula or "").strip() or not (nombre or "").strip():
                aviso("error", "Faltan datos", "La cédula y el nombre son obligatorios.")
            else:
                try:
                    pe.guardar(cedula, nombre, rol, supervisor, etiqueta, cfg.ACTIVO,
                               observaciones=observaciones, adicionales=adicionales)
                except Exception as e:
                    aviso("error", "No se pudo guardar la ficha", str(e))
                else:
                    marca = f" · {cfg.ETIQUETA_ESPECIAL}" if etiqueta else ""
                    aviso("ok", "Ficha guardada",
                          f"{nombre.strip().title()} · {cedula}{marca}")
                    st.rerun()

        # ---- Migración desde el historial ----
        docs = nu.leer_hoja()
        cedulas_doc = (set(docs["Cedula"].astype(str).str.strip()) - {""}
                       if not docs.empty and "Cedula" in docs.columns else set())
        sin_ficha = cedulas_doc - (set(registrados["Cedula"]) if not registrados.empty
                                   else set())
        if sin_ficha:
            st.write("")
            rotulo("Reconocer historial")
            st.markdown(
                f'<div class="nota"><strong>{len(sin_ficha)} persona(s)</strong> aparecen '
                f'en documentos ya cargados pero todavía no tienen ficha. Puedes crearlas '
                f'de una sola vez: el sistema toma el nombre y el rol de su documento más '
                f'reciente y hereda la etiqueta si alguno vino marcado. Después solo '
                f'tendrás que asignarles supervisor.<br>Los documentos y los archivos de '
                f'Drive <strong>no se tocan</strong>.</div>', unsafe_allow_html=True)
            if st.button(f"Reconocer {len(sin_ficha)} colaborador(es) del historial",
                         type="primary", key="c_importar"):
                with st.spinner("Importando..."):
                    creados, sups, faltan = pe.migrar_desde_historial(docs)
                aviso("ok", f"{creados} ficha(s) y {sups} supervisor(es) creados",
                      "Los ya registrados no se tocaron. Revisa los roles y asigna "
                      "los equipos en la pestaña siguiente.")
                st.rerun()

        if not registrados.empty:
            st.write("")
            rotulo("Registrados")
            #  reindex en vez de indexar: si falta una columna la crea vacía en
            #  lugar de fallar, y el orden queda garantizado.
            vista_reg = registrados.reindex(columns=cfg.COLUMNAS_COLABORADORES,
                                            fill_value="").copy()
            #  Google Sheets guarda las cédulas como número y les quita el cero
            #  inicial; se restituye solo para mostrarlas.
            vista_reg["Cedula"] = vista_reg["Cedula"].map(r.cedula_visible)
            st.dataframe(
                vista_reg.astype("string"),
                hide_index=True, width='stretch', height=280,
                column_config={"Requeridos": st.column_config.TextColumn(
                    "Documentos exigibles", width="medium")})

    # ------------------------------------------------------- Estado y asignación
    with gestion:
        rotulo("Estado del colaborador")
        st.markdown(
            '<div class="nota">Un colaborador inactivo conserva todo su expediente pero '
            'desaparece de los indicadores y deja de generar avisos de vencimiento. Al '
            'cumplir un año inactivo, el sistema lo lista para que decidas si depurar sus '
            'datos: <strong>nunca borra nada por su cuenta.</strong></div>',
            unsafe_allow_html=True)

        fichas = pe.colaboradores()
        if fichas.empty:
            vacio("Sin colaboradores",
                  "Crea la primera ficha en la pestaña anterior.")
        else:
            col_a, col_b = st.columns([3, 1])
            with col_a:
                elegido = st.selectbox("Colaborador", pe.opciones(solo_activos=False),
                                       index=None, key="g_persona",
                                       placeholder="Busca por cédula o nombre")
            ficha = pe.ficha(pe.cedula_de(elegido)) if elegido else None

            if ficha:
                activo = str(ficha.get("Estado", cfg.ACTIVO)).upper() == cfg.ACTIVO
                clase = "ficha" + ("" if activo else " ficha--inactivo")
                pastillas = ""
                if str(ficha.get("Etiqueta", "")).strip():
                    pastillas += (f'<span class="pastilla pastilla--etiqueta">'
                                  f'{cfg.ETIQUETA_ESPECIAL}</span>')
                if not activo:
                    pastillas += '<span class="pastilla pastilla--inactivo">Inactivo</span>'
                st.markdown(
                    f'<div class="{clase}"><b>{ficha.get("Nombre","")}</b>{pastillas}'
                    f'<div class="meta">{ficha.get("Cedula","")} · '
                    f'{ficha.get("Rol","") or "sin rol"} · supervisor: '
                    f'{ficha.get("Supervisor","") or "sin asignar"}'
                    + (f' · inactivo desde {ficha.get("Fecha_Inactivacion","")}'
                       if not activo else "")
                    + '</div></div>', unsafe_allow_html=True)

                with col_b:
                    st.write("")
                    etiqueta_boton = "Desactivar" if activo else "Reactivar"
                    if st.button(etiqueta_boton, type="primary", key="g_toggle",
                                 width='stretch'):
                        n = pe.cambiar_estado(ficha["Cedula"], not activo)
                        detalle = ficha.get("Nombre", "")
                        if n > 1:
                            detalle += f" · {n} fichas duplicadas actualizadas"
                        aviso("ok", f"Colaborador {etiqueta_boton.lower()[:-1]}ado",
                              detalle)
                        st.rerun()

        st.write("")
        rotulo(f"Etiqueta {cfg.ETIQUETA_ESPECIAL}",
               "Selección en bloque: los marcados la reciben, el resto la pierde")
        st.markdown(
            f'<div class="nota">Marca aquí <strong>todos</strong> los colaboradores que '
            f'llevan la etiqueta. Es un reemplazo, no una suma: al aplicar, los '
            f'seleccionados quedan etiquetados y <strong>a los demás se les quita</strong>. '
            f'Sirve para corregir de golpe la asignación heredada del historial.</div>',
            unsafe_allow_html=True)

        todos = pe.opciones(solo_activos=False)
        actuales = set(pe.etiquetados())
        preseleccion = [o for o in todos if pe.cedula_de(o) in actuales]

        elegidos = st.multiselect(
            f"Colaboradores con etiqueta {cfg.ETIQUETA_ESPECIAL}", todos,
            default=preseleccion, key="e_etiquetados",
            help="Empieza marcado como está hoy. Quita y agrega según corresponda.")

        nuevos = {pe.cedula_de(o) for o in elegidos}
        agregar = nuevos - actuales
        quitar = actuales - nuevos

        if agregar or quitar:
            resumen = []
            if agregar:
                resumen.append(f"{len(agregar)} recibirá(n) la etiqueta")
            if quitar:
                resumen.append(f"{len(quitar)} la perderá(n)")
            aviso("info", "Cambios pendientes de aplicar", " · ".join(resumen))
        else:
            aviso("ok", f"{len(actuales)} colaborador(es) con etiqueta",
                  "No hay cambios pendientes.")

        if st.button("Aplicar etiquetas", type="primary", key="e_aplicar",
                     disabled=not (agregar or quitar)):
            with st.spinner("Actualizando fichas..."):
                puestas, sacadas = pe.establecer_etiqueta(nuevos)
            aviso("ok", "Etiquetas actualizadas",
                  f"{puestas} agregada(s) · {sacadas} retirada(s). Los certificados de "
                  f"riesgos recalculan su fecha de revisión al instante.")
            st.rerun()

        st.write("")
        rotulo("Documentos exigibles",
               "Cambia en bloque qué se le pide a una cuadrilla")
        st.markdown(
            '<div class="nota">Cuando un grupo empieza a trabajar en alturas o deja de '
            'hacerlo, el requisito cambia para todos a la vez. Usa <strong>Agregar</strong> '
            'o <strong>Quitar</strong> para no pisar lo que cada quien ya tenía; '
            '<strong>Reemplazar</strong> deja exactamente la lista marcada.</div>',
            unsafe_allow_html=True)

        col_r1, col_r2 = st.columns([3, 2])
        with col_r1:
            personas_req = st.multiselect("Colaboradores", pe.opciones(),
                                          key="r_personas")
        with col_r2:
            modo = st.radio("Operación", ["Agregar", "Quitar", "Reemplazar"],
                            horizontal=True, key="r_modo")
        docs_req = st.multiselect("Documentos", cfg.OPCIONALES, key="r_docs")

        if personas_req and docs_req:
            resumen = ", ".join(d.replace("Certificado de Riesgos de Trabajo ", "")
                                for d in docs_req)
            aviso("info", f"{modo}: {len(personas_req)} colaborador(es)", resumen)

        if st.button("Aplicar a la selección", type="primary", key="r_aplicar",
                     disabled=not personas_req or (not docs_req and modo != "Reemplazar")):
            n = pe.establecer_requisitos(
                [pe.cedula_de(x) for x in personas_req], docs_req,
                modo={"Agregar": "agregar", "Quitar": "quitar"}.get(modo, "reemplazar"))
            aviso("ok", f"{n} ficha(s) actualizadas",
                  "El panel de cumplimiento ya refleja los nuevos requisitos.")
            st.rerun()

        # Quién tiene exigido cada certificado de riesgos, de un vistazo
        activos_df = pe.activos()
        if not activos_df.empty:
            resumen = []
            for tipo in cfg.TIPOS_REVISION_ANUAL:
                cuantos = len(pe.con_requisito(tipo))
                corto = tipo.replace("Certificado de Riesgos de Trabajo ", "")
                resumen.append(f'<div class="estado-linea">{corto} · '
                               f'<b>{cuantos}</b> colaborador(es)</div>')
            with st.expander("Quién tiene exigido cada certificado de riesgos"):
                st.markdown("".join(resumen), unsafe_allow_html=True)

        st.write("")
        rotulo("Equipos", "Asigna varios colaboradores a un supervisor de una vez")
        sup_df = pe.supervisores()
        if sup_df.empty:
            aviso("info", "Sin supervisores registrados",
                  "Regístralos en la pestaña Supervisores para poder asignar equipos.")
        else:
            destino = st.selectbox("Supervisor", pe.nombres_supervisores(), key="a_sup")

            todos_colab = pe.opciones()
            seleccion = multiselect_con_todos(
                "Colaboradores a asignar", todos_colab, "a_personas",
                ayuda="Puedes asignar varios de una sola vez")

            if st.button("Asignar", type="primary", key="a_guardar") and seleccion:
                with st.spinner("Actualizando fichas..."):
                    n, huerfanas = pe.asignar_lote(
                        [pe.cedula_de(x) for x in seleccion], destino)
                if n:
                    aviso("ok", f"{n} ficha(s) asignadas a {destino}",
                          f"De {len(seleccion)} seleccionados. Sus avisos de "
                          f"vencimiento llegarán a ese supervisor.")
                else:
                    aviso("info", "No hubo cambios",
                          f"Los {len(seleccion)} seleccionados ya estaban asignados "
                          f"a {destino}.")
                if huerfanas:
                    aviso("error", f"{len(huerfanas)} sin ficha encontrada",
                          ", ".join(huerfanas[:8]))
                st.rerun()

            duplicadas = pe.cedulas_duplicadas()
            if duplicadas:
                total = sum(len(n) for n in duplicadas.values())
                aviso("info", f"{len(duplicadas)} cédula(s) con ficha duplicada",
                      f"{total} fichas para {len(duplicadas)} personas. Las operaciones "
                      f"las actualizan todas, pero conviene consolidarlas: una persona "
                      f"repetida aparece dos veces en las listas y descuadra el conteo.")
                with st.expander("Ver cédulas repetidas"):
                    st.markdown("".join(
                        f'<div class="estado-linea">{c} · '
                        f'{" / ".join(n)}</div>'
                        for c, n in list(duplicadas.items())[:20]),
                        unsafe_allow_html=True)
                if st.button("Consolidar fichas duplicadas", key="g_depurar"):
                    with st.spinner("Consolidando..."):
                        ced, borradas = pe.depurar_duplicadas()
                    aviso("ok", f"{ced} cédula(s) consolidadas",
                          f"Se conservó la ficha más completa de cada persona y se "
                          f"eliminaron {borradas} repetidas. Los documentos en Drive "
                          f"y el historial no se tocan.")
                    st.rerun()

        equipos = pe.activos()
        if not equipos.empty:
            st.write("")
            resumen = (equipos.assign(
                Supervisor=equipos["Supervisor"].replace("", "— sin asignar —"))
                .groupby("Supervisor").size().reset_index(name="Colaboradores"))
            st.dataframe(resumen.astype({"Supervisor": "string"}), hide_index=True,
                         width='stretch')

    # ------------------------------------------------------------- Supervisores
    with supervisores:
        rotulo("Supervisores", "El correo decide a dónde llegan los avisos")
        st.markdown('<div class="nota">El correo es el destino de los recordatorios '
                    'automáticos. Cada supervisor recibe únicamente los vencimientos de '
                    'los colaboradores a su cargo.</div>', unsafe_allow_html=True)
        st.markdown(
            f'<div class="nota"><strong>{cfg.PERFIL_SUPERVISOR}</strong> recibe solo los '
            f'vencimientos de los colaboradores a su cargo. '
            f'<strong>{cfg.PERFIL_ADMIN}</strong> recibe el consolidado de toda la '
            f'plantilla, incluidos los que no tienen supervisor asignado. Una misma '
            f'persona puede ser ambas cosas si además lidera un equipo.</div>',
            unsafe_allow_html=True)

        col1, col2, col3, col4 = st.columns([2, 3, 2, 1])
        with col1:
            s_nombre = st.text_input("Nombre", key="s_nombre")
        with col2:
            s_correo = st.text_input("Correo", key="s_correo",
                                     placeholder="nombre@startec.ec")
        with col3:
            s_perfil = st.selectbox("Perfil", cfg.PERFILES, key="s_perfil")
        with col4:
            st.write("")
            guardar = st.button("Guardar", type="primary", key="s_guardar",
                                width='stretch')
        if guardar:
            if not s_nombre.strip() or "@" not in s_correo:
                aviso("error", "Datos incompletos", "Se requiere nombre y correo válido.")
            else:
                pe.guardar_supervisor(s_nombre, s_correo, perfil=s_perfil)
                aviso("ok", f"{s_perfil} guardado", f"{s_nombre.strip()} · {s_correo}")
                st.rerun()

        admins = pe.administradores()
        if not admins:
            aviso("info", "Sin administrador definido",
                  f"Nadie recibe el consolidado desde la aplicación. Registra al menos "
                  f"uno con perfil {cfg.PERFIL_ADMIN}.")
        else:
            aviso("ok", f"{len(admins)} administrador(es) del consolidado",
                  " · ".join(admins))

        pendientes = pe.sin_correo()
        if pendientes:
            aviso("info", f"{len(pendientes)} supervisor(es) sin correo",
                  "Se reconocieron por su rol en el historial, pero el correo no se "
                  "puede deducir: " + ", ".join(pendientes[:6])
                  + ("…" if len(pendientes) > 6 else "")
                  + ". Sin él no reciben los avisos de vencimiento.")

        df = pe.supervisores()
        if not df.empty:
            st.dataframe(df.astype("string"), hide_index=True, width='stretch')


# ==========================================================================================
# PANEL · DOCUMENTO INDIVIDUAL
# ==========================================================================================
def panel_documentos():
    """
    Un solo panel para las tres formas de cargar. Antes eran tres pestañas de
    primer nivel, lo que obligaba a decidir el modo antes de entender la tarea;
    ahora la tarea es una —cargar documentos— y el modo es una opción.
    """
    modo = st.radio(
        "¿Qué vas a cargar?",
        ["Un documento", "Varios de una persona", "Uno que cubre a varias personas"],
        horizontal=True, key="modo_carga",
        captions=["Lo más habitual", f"Hasta {cfg.MAX_LOTE} archivos",
                  "Planilla del IESS y similares"])
    st.write("")
    if modo == "Un documento":
        panel_individual()
    elif modo == "Varios de una persona":
        panel_masivo()
    else:
        panel_compartido()


def panel_individual():
    rotulo("Documento individual", "Un archivo para una persona")
    izq, der = st.columns(2, gap="large")

    with izq:
        ficha = selector_persona("i_persona")
        tipo = st.selectbox("Tipo de documento", cfg.TIPOS_DOCUMENTO, index=None,
                            key="i_tipo", placeholder="Selecciona el tipo")
        archivo = st.file_uploader("Archivo (PDF o imagen)", type=cfg.EXTENSIONES,
                                   key="i_archivo")
    with der:
        emision = st.date_input("Fecha de emisión", value=r.hoy(), format="DD-MM-YYYY",
                                key="i_emision")
        caducidad = campo_caducidad(tipo, emision, "i_caducidad")
        observaciones = st.text_area("Observaciones", key="i_obs", height=80)

    if ficha and tipo:
        etiquetado = str(ficha.get("Etiqueta", "")).strip() != ""
        revision = r.fecha_revision(tipo, emision, etiquetado)
        if revision:
            aviso("info", f"Revisión anticipada por etiqueta {cfg.ETIQUETA_ESPECIAL}",
                  f"El certificado caduca el "
                  f"{caducidad.strftime(cfg.FORMATO_FECHA) if caducidad else '—'}, pero se "
                  f"pedirá renovarlo el {revision.strftime(cfg.FORMATO_FECHA)}.")

    if st.button("Guardar y cargar documento", type="primary", key="i_guardar"):
        emision_dt = r.parsear_fecha(emision)
        if not ficha or not tipo or archivo is None:
            aviso("error", "Faltan datos",
                  "Colaborador, tipo de documento y archivo son obligatorios.")
        elif caducidad is None:
            aviso("error", "Falta la caducidad",
                  "Este tipo no tiene vigencia fija: indícala a mano.")
        elif caducidad <= emision_dt:
            aviso("error", "Fechas incoherentes",
                  "La caducidad debe ser posterior a la emisión.")
        else:
            with st.spinner("Subiendo a Drive y registrando..."):
                try:
                    etiquetado = str(ficha.get("Etiqueta", "")).strip() != ""
                    fila, carpeta = nu.cargar_documento(
                        ficha["Cedula"], ficha["Nombre"], ficha.get("Rol"), etiquetado,
                        tipo, archivo.getvalue(), archivo.name, archivo.type,
                        emision_dt, caducidad, observaciones)
                    nu.escribir_filas([fila])
                    archivados = nu.reconciliar([(ficha["Cedula"], tipo)])
                    pe.registrar(cfg.ACCION_CARGA,
                                 f'{ficha["Cedula"]} · {ficha["Nombre"]}',
                                 f'{tipo} · emisión {fila["Fecha_Emision"]} · '
                                 f'vence {fila["Fecha_Caducidad"]}')
                    if archivados:
                        pe.registrar(cfg.ACCION_REEMPLAZO,
                                     f'{ficha["Cedula"]} · {ficha["Nombre"]}',
                                     f'{tipo} · {archivados} versión(es) al histórico')
                except Exception as e:
                    aviso("error", "No se pudo completar la carga", str(e))
                else:
                    dias, estado = r.calcular_estado(fila["Fecha_Caducidad"],
                                                     fila["Fecha_Revision"])
                    detalle = (f'Carpeta «{carpeta}» · vence el '
                               f'{caducidad.strftime(cfg.FORMATO_FECHA)} '
                               f'({dias} días) · {estado}')
                    if archivados:
                        detalle += f" · {archivados} versión anterior archivada"
                    aviso("ok", "Documento cargado y registrado", detalle)


# ==========================================================================================
# PANEL · CARGA MASIVA
# ==========================================================================================
def panel_masivo():
    rotulo("Carga masiva", "Varios archivos de una misma persona")
    izq, der = st.columns(2, gap="large")
    with izq:
        ficha = selector_persona("m_persona")
        observaciones = st.text_area("Observaciones del lote", key="m_obs", height=80)
    with der:
        archivos = st.file_uploader(f"Documentos (hasta {cfg.MAX_LOTE})",
                                    type=cfg.EXTENSIONES, accept_multiple_files=True,
                                    key="m_archivos")
        emision_def = st.date_input("Emisión por defecto", value=r.hoy(),
                                    format="DD-MM-YYYY", key="m_emision")

    if not archivos:
        vacio("Sin archivos todavía",
              "Suelta aquí arriba los documentos de esta persona. Se genera una fila "
              "por archivo con su tipo y su fecha, y la caducidad se calcula sola.")
        return

    archivos = archivos[:cfg.MAX_LOTE]
    firma = tuple(a.name for a in archivos)
    if st.session_state.get("firma_lote") != firma:
        st.session_state.firma_lote = firma
        st.session_state.detalle_lote = pd.DataFrame([
            {"Archivo": a.name,
             "Tipo de documento": r.inferir_tipo(a.name) or cfg.SIN_TIPO,
             "Emisión": emision_def} for a in archivos])
        for c in ("Archivo", "Tipo de documento"):
            st.session_state.detalle_lote[c] = st.session_state.detalle_lote[c].astype("string")
        st.session_state.detalle_lote["Emisión"] = pd.to_datetime(
            st.session_state.detalle_lote["Emisión"], errors="coerce")

    rotulo("Detalle", "La caducidad se calcula sola según el tipo")
    st.markdown('<div class="nota">La caducidad ya no se escribe: se calcula sola a '
                'partir del tipo y la fecha de emisión de cada fila.</div>',
                unsafe_allow_html=True)

    detalle = st.data_editor(
        st.session_state.detalle_lote, key="editor_lote", hide_index=True,
        width='stretch', num_rows="fixed", disabled=["Archivo"],
        column_config={
            "Archivo": st.column_config.TextColumn("Archivo", width="large"),
            "Tipo de documento": st.column_config.SelectboxColumn(
                "Tipo de documento", width="medium", required=True,
                options=[cfg.SIN_TIPO] + cfg.TIPOS_DOCUMENTO),
            "Emisión": st.column_config.DateColumn("Emisión", format="DD-MM-YYYY"),
        })

    sin_tipo = detalle[detalle["Tipo de documento"] == cfg.SIN_TIPO]
    if not sin_tipo.empty:
        aviso("info", f"{len(sin_tipo)} documento(s) sin tipo asignado",
              "Elige el tipo en su celda. No se sube nada mientras quede alguno sin clasificar.")

    if st.button("Cargar lote completo", type="primary", key="m_cargar"):
        if not ficha:
            aviso("error", "Falta el colaborador", "Selecciónalo arriba.")
            return
        if not sin_tipo.empty:
            aviso("error", "Hay documentos sin clasificar",
                  ", ".join(sin_tipo["Archivo"].tolist()[:6]))
            return
        procesar_lote(ficha, archivos, detalle.to_dict("records"), observaciones)


def procesar_lote(ficha, archivos, filas_detalle, observaciones):
    etiquetado = str(ficha.get("Etiqueta", "")).strip() != ""
    filas, exitos, fallos, tipos = [], [], [], set()
    barra = st.progress(0.0, text="Preparando...")

    for i, (archivo, det) in enumerate(zip(archivos, filas_detalle), start=1):
        tipo = det["Tipo de documento"]
        emision = r.parsear_fecha(det["Emisión"])
        caducidad = r.caducidad_automatica(tipo, emision)

        if emision is None:
            fallos.append(f"<li><strong>{archivo.name}</strong> → emisión inválida</li>")
            continue
        if caducidad is None:
            fallos.append(f"<li><strong>{archivo.name}</strong> → «{tipo}» no tiene "
                          f"vigencia fija: cárgalo desde el panel individual</li>")
            continue

        barra.progress(i / (len(archivos) + 1), text=f"Subiendo {i} de {len(archivos)}")
        try:
            fila, _ = nu.cargar_documento(
                ficha["Cedula"], ficha["Nombre"], ficha.get("Rol"), etiquetado, tipo,
                archivo.getvalue(), archivo.name, archivo.type, emision, caducidad,
                observaciones)
            filas.append(fila)
            tipos.add(tipo)
            _, estado = r.calcular_estado(fila["Fecha_Caducidad"], fila["Fecha_Revision"])
            exitos.append(f'<li><strong>{archivo.name}</strong> → {tipo} · vence '
                          f'{caducidad.strftime(cfg.FORMATO_FECHA)} · {estado}</li>')
        except Exception as e:
            fallos.append(f"<li><strong>{archivo.name}</strong> → {e}</li>")

    archivados = 0
    if filas:
        barra.progress(0.97, text="Registrando...")
        try:
            nu.escribir_filas(filas)
            archivados = nu.reconciliar([(ficha["Cedula"], t) for t in tipos])
            pe.registrar(cfg.ACCION_CARGA, f'{ficha["Cedula"]} · {ficha["Nombre"]}',
                         f'lote de {len(filas)}: ' + ", ".join(sorted(tipos)))
        except Exception as e:
            barra.empty()
            aviso("error", "Los archivos se subieron, pero falló el registro", str(e))
            return
    barra.empty()

    detalle = f"{len(exitos)} de {len(archivos)} documentos"
    if archivados:
        detalle += f" · {archivados} versión(es) anterior(es) archivada(s)"
    aviso("ok" if not fallos else "info", "Carga finalizada", detalle)
    if exitos:
        st.markdown(f'<ul class="lista-carga">{"".join(exitos)}</ul>',
                    unsafe_allow_html=True)
    if fallos:
        st.markdown(f'<ul class="lista-carga lista-error">{"".join(fallos)}</ul>',
                    unsafe_allow_html=True)


# ==========================================================================================
# PANEL · DOCUMENTO COMPARTIDO
# ==========================================================================================
def panel_compartido():
    rotulo("Documento compartido", "Un archivo que cubre a varias personas")
    st.markdown(
        '<div class="nota">Pensado para la <strong>planilla del IESS</strong> y otros '
        'documentos colectivos. El archivo se sube <strong>una sola vez</strong> a la '
        'carpeta de documentos compartidos y aparece en el expediente de cada persona '
        'cubierta, sin duplicar el PDF. Cada colaborador genera su propia fila, así que '
        'el semáforo y las alertas funcionan igual que con cualquier otro documento.</div>',
        unsafe_allow_html=True)

    izq, der = st.columns(2, gap="large")
    with izq:
        tipo = st.selectbox("Tipo de documento", cfg.TIPOS_COMPARTIBLES, key="k_tipo")
        archivo = st.file_uploader("Archivo (PDF o imagen)", type=cfg.EXTENSIONES,
                                   key="k_archivo")
        observaciones = st.text_area("Observaciones", key="k_obs", height=80,
                                     placeholder="Ej. Planilla de aportes julio 2026")
    with der:
        emision = st.date_input("Fecha de emisión", value=r.hoy(), format="DD-MM-YYYY",
                                key="k_emision")
        caducidad = campo_caducidad(tipo, emision, "k_caducidad")

    opciones = pe.opciones()
    if not opciones:
        vacio("Sin colaboradores activos",
              "Registra al menos uno en el panel <b>Equipo</b> para poder cargar "
              "documentos compartidos.")
        return

    seleccion = multiselect_con_todos(
        f"Colaboradores cubiertos (hasta {cfg.MAX_COMPARTIDO})", opciones, "k_personas",
        ayuda="Solo aparecen los colaboradores activos")

    if seleccion:
        etiquetados = sum(1 for s in seleccion if pe.esta_etiquetado(pe.cedula_de(s)))
        detalle = f"{len(seleccion)} colaborador(es)"
        if etiquetados:
            detalle += f" · {etiquetados} con etiqueta {cfg.ETIQUETA_ESPECIAL}"
        aviso("info", "Alcance del documento", detalle)

    if st.button("Cargar documento compartido", type="primary", key="k_cargar"):
        emision_dt = r.parsear_fecha(emision)
        if archivo is None or not seleccion:
            aviso("error", "Faltan datos", "Se requiere el archivo y al menos un colaborador.")
        elif caducidad is None:
            aviso("error", "Falta la caducidad", "Este tipo no tiene vigencia fija.")
        elif caducidad <= emision_dt:
            aviso("error", "Fechas incoherentes",
                  "La caducidad debe ser posterior a la emisión.")
        else:
            with st.spinner(f"Subiendo y registrando {len(seleccion)} expedientes..."):
                try:
                    cubiertos = []
                    for opcion in seleccion[:cfg.MAX_COMPARTIDO]:
                        f = pe.ficha(pe.cedula_de(opcion))
                        cubiertos.append({
                            "cedula": f["Cedula"], "nombre": f["Nombre"],
                            "rol": f.get("Rol"),
                            "etiquetado": str(f.get("Etiqueta", "")).strip() != ""})
                    filas, nombre_archivo, grupo = nu.cargar_compartido(
                        cubiertos, tipo, archivo.getvalue(), archivo.name, archivo.type,
                        emision_dt, caducidad, observaciones)
                    nu.escribir_filas(filas)
                    archivados = nu.reconciliar([(c["cedula"], tipo) for c in cubiertos])
                    pe.registrar(cfg.ACCION_COMPARTIDO, f"{len(cubiertos)} colaborador(es)",
                                 f"{tipo} · grupo {grupo} · vence "
                                 f"{caducidad.strftime(cfg.FORMATO_FECHA)}")
                except Exception as e:
                    aviso("error", "No se pudo completar la carga", str(e))
                else:
                    detalle = (f'Un archivo · {len(filas)} expedientes actualizados · '
                               f'vence el {caducidad.strftime(cfg.FORMATO_FECHA)}')
                    if archivados:
                        detalle += f" · {archivados} versión(es) anterior(es) marcada(s)"
                    aviso("ok", "Documento compartido cargado", detalle)
                    st.caption(f"Grupo {grupo} · {nombre_archivo}")


# ==========================================================================================
# PANEL · DASHBOARD
# ==========================================================================================
def panel_cumplimiento(tabla, fichas):
    """
    Qué falta, no solo qué vence.

    Un colaborador sin certificado médico jamás aparece en las alertas de
    vencimiento —no hay nada que venza— y sin embargo es el incumplimiento más
    grave. Esta vista cruza lo exigible por rol contra lo efectivamente cargado.
    """
    cob = nu.cobertura(tabla, fichas)
    if cob.empty:
        vacio("Sin datos de cobertura",
              "Registra colaboradores para ver qué documentos les faltan.")
        return

    m = nu.resumen_cobertura(cob)
    rotulo("Cumplimiento del equipo",
           "Obligatorios para todos: " + " · ".join(cfg.REQUERIDOS_BASE)
           + ". El resto se exige según la tarea de cada persona.")

    c1, c2 = st.columns([2, 3])
    with c1:
        st.markdown(
            f'<div class="kpi kpi--{"ok" if m["porcentaje"]>=85 else "alerta"}" '
            f'style="margin-bottom:10px">'
            f'<span class="kpi-valor">{m["porcentaje"]}%</span>'
            f'<span class="kpi-etiqueta">Colaboradores en regla</span></div>'
            + estilos.barra_cumplimiento(m["porcentaje"])
            + f'<p class="kpi-pie">{m["personas_ok"]} de {m["personas"]} personas con '
              f'su expediente completo y vigente</p>', unsafe_allow_html=True)
    with c2:
        st.markdown(
            '<div class="kpi-barra">'
            + f'<div class="kpi kpi--historico"><span class="kpi-valor">{m["faltantes"]}'
              f'</span><span class="kpi-etiqueta">Nunca cargados</span></div>'
            + f'<div class="kpi kpi--critico"><span class="kpi-valor">{m["vencidos"]}'
              f'</span><span class="kpi-etiqueta">Vencidos</span></div>'
            + f'<div class="kpi kpi--ok"><span class="kpi-valor">{m["en_regla"]}'
              f'</span><span class="kpi-etiqueta">En regla</span></div>'
            + '</div>', unsafe_allow_html=True)

    #  Vista por persona: la lectura que pide un jefe, no la lista de casillas.
    porpersona = nu.cumplimiento_por_persona(cob)
    st.write("")
    vista_persona, vista_detalle = st.tabs(["Por colaborador", "Detalle por documento"])

    with vista_persona:
        st.dataframe(
            porpersona, hide_index=True, width='stretch', height=300,
            column_config={
                "Avance": st.column_config.ProgressColumn(
                    "Avance", format="%d%%", min_value=0, max_value=100),
                "Exigibles": st.column_config.NumberColumn(width="small"),
                "En regla": st.column_config.NumberColumn(width="small"),
                "Sin cargar": st.column_config.NumberColumn(width="small"),
                "Vencidos": st.column_config.NumberColumn(width="small"),
            })
        incompletos = porpersona[porpersona["Situación"] != "✅ Completo"]
        if incompletos.empty:
            aviso("ok", "Toda la plantilla en regla",
                  "Cada colaborador activo tiene sus documentos exigibles vigentes.")
        else:
            st.caption(f"{len(incompletos)} de {len(porpersona)} colaboradores requieren "
                       f"gestión · obligatorios para todos: "
                       + ", ".join(cfg.REQUERIDOS_BASE))

    with vista_detalle:
        solo_problemas = st.toggle("Ver solo lo que incumple", value=True,
                                   key="cob_filtro")
        vista = cob[cob["Estado"].isin(cfg.ESTADOS_INCUMPLE)] if solo_problemas else cob
        if vista.empty:
            aviso("ok", "Expedientes completos",
                  "Todos los colaboradores activos tienen sus documentos exigibles "
                  "cargados y vigentes.")
        else:
            st.dataframe(vista, hide_index=True, width='stretch', height=300,
                         column_config={"Días Restantes": st.column_config.NumberColumn(
                             "Días", format="%d", width="small")})

    st.download_button("Exportar cumplimiento a CSV",
                       data=cob.to_csv(index=False).encode("utf-8-sig"),
                       file_name=f"cumplimiento_{r.ahora():%Y%m%d}.csv",
                       mime="text/csv")


def panel_expediente(tabla, fichas):
    """Todo lo de una persona en una pantalla, incluidas las casillas vacías."""
    rotulo("Expediente individual", "Selecciona a alguien para ver su situación completa")

    opciones = pe.opciones(solo_activos=False)
    if not opciones:
        vacio("Sin colaboradores", "Da de alta al menos uno en el panel Equipo.")
        return

    elegido = st.selectbox("Colaborador", opciones, index=None, key="x_persona",
                           placeholder="Busca por cédula o nombre")
    if not elegido:
        return

    cedula = pe.cedula_de(elegido)
    ficha = pe.ficha(cedula) or {}
    activo = str(ficha.get("Estado", cfg.ACTIVO)).upper() == cfg.ACTIVO

    pastillas = ""
    if str(ficha.get("Etiqueta", "")).strip():
        pastillas += (f'<span class="pastilla pastilla--etiqueta">'
                      f'{cfg.ETIQUETA_ESPECIAL}</span>')
    if not activo:
        pastillas += '<span class="pastilla pastilla--inactivo">Inactivo</span>'
    st.markdown(
        f'<div class="ficha{"" if activo else " ficha--inactivo"}">'
        f'<b>{ficha.get("Nombre","")}</b>{pastillas}<div class="meta">{cedula} · '
        f'{ficha.get("Rol","") or "sin rol"} · supervisor: '
        f'{ficha.get("Supervisor","") or "sin asignar"}</div></div>',
        unsafe_allow_html=True)

    docs = nu.expediente(tabla, cedula)
    vigentes = docs[docs["Registro"] == "Actual"] if not docs.empty else docs
    por_tipo = {d["Tipo de Documento"]: d for _, d in vigentes.iterrows()}

    exigibles = cfg.requeridos_de(ficha)
    otros = [t for t in por_tipo if t not in exigibles]

    tarjetas = []
    for tipo in exigibles + otros:
        doc = por_tipo.get(tipo)
        if doc is None:
            tarjetas.append(estilos.tarjeta_documento(tipo, cfg.ESTADO_FALTANTE, None, ""))
        else:
            dias = doc["Días Restantes"]
            tarjetas.append(estilos.tarjeta_documento(
                tipo, doc["Estado"], None if pd.isna(dias) else dias, doc["Caducidad"]))
    st.markdown(f'<div class="rejilla">{"".join(tarjetas)}</div>', unsafe_allow_html=True)

    historico = docs[docs["Registro"] == "Histórico"] if not docs.empty else docs
    if not historico.empty:
        with st.expander(f"Historial de renovaciones ({len(historico)})"):
            st.dataframe(historico[["Tipo de Documento", "Emisión", "Caducidad",
                                    "Estado", "Documento"]],
                         hide_index=True, width='stretch',
                         column_config={"Documento": st.column_config.LinkColumn(
                             "Archivo", display_text="Abrir ↗")})


def panel_dashboard():
    fichas = pe.colaboradores()
    tabla = nu.tabla_control(fichas)

    if tabla.empty and fichas.empty:
        vacio("Todavía no hay nada que controlar",
              "Empieza registrando colaboradores en el panel <b>Equipo</b> y "
              "cargando sus documentos en <b>Cargar documentos</b>.")
        return

    resumen, cumplimiento, individual, auditoria = st.tabs(
        ["Vencimientos", "Cumplimiento", "Expediente", "Auditoría"])

    with cumplimiento:
        panel_cumplimiento(tabla, fichas)
    with individual:
        panel_expediente(tabla, fichas)
    with auditoria:
        panel_auditoria(tabla, fichas)
    with resumen:
        panel_vencimientos(tabla)


def panel_auditoria(tabla, fichas):
    """
    Evidencia para una revisión: qué se hizo, cuándo, y qué no cuadra.

    Una auditoría no pregunta solo por el estado actual sino por cómo se llegó a
    él, y por las inconsistencias que el estado final esconde.
    """
    rotulo("Bitácora de movimientos",
           "Registro de solo-anexado: no se edita ni se borra desde la aplicación")

    log = pe.bitacora()
    if log.empty:
        vacio("Sin movimientos registrados",
              "La bitácora empieza a llenarse con la próxima carga o edición.")
    else:
        st.dataframe(log.astype("string"), hide_index=True, width='stretch', height=300)
        st.download_button("Exportar bitácora a CSV",
                           data=log.to_csv(index=False).encode("utf-8-sig"),
                           file_name=f"bitacora_{r.ahora():%Y%m%d}.csv", mime="text/csv")

    st.write("")
    rotulo("Control de consistencia", "Lo que una revisión encontraría")

    hallazgos = []

    docs_sin_ficha = set()
    if not tabla.empty:
        claves = ({r.clave_cedula(c) for c in fichas["Cedula"]}
                  if not fichas.empty else set())
        docs_sin_ficha = {c for c in tabla["Cédula"].map(r.clave_cedula) if c not in claves}
    if docs_sin_ficha:
        hallazgos.append(("Documentos de personas sin ficha registrada",
                          f"{len(docs_sin_ficha)} cédula(s)"))

    sin_sup = 0
    if not fichas.empty:
        activos = fichas[fichas["Estado"].astype(str).str.upper() == cfg.ACTIVO]
        sin_sup = int((activos["Supervisor"].astype(str).str.strip() == "").sum())
    if sin_sup:
        hallazgos.append(("Colaboradores activos sin supervisor asignado",
                          f"{sin_sup} persona(s) · sus avisos solo llegan al administrador"))

    faltan_correo = pe.sin_correo()
    if faltan_correo:
        hallazgos.append(("Supervisores sin correo",
                          ", ".join(faltan_correo[:5])))

    if not pe.administradores():
        hallazgos.append(("Sin administrador definido",
                          "Nadie recibe el consolidado desde la hoja"))

    sin_fecha = 0
    if not tabla.empty:
        sin_fecha = int((tabla["Estado"] == cfg.ESTADO_SIN_FECHA).sum())
    if sin_fecha:
        hallazgos.append(("Documentos sin fecha de caducidad",
                          f"{sin_fecha} registro(s) fuera del control de vigencia"))

    purgas = pe.pendientes_de_purga()
    if not purgas.empty:
        hallazgos.append(("Inactivos que superaron el plazo de retención",
                          f"{len(purgas)} expediente(s) por depurar"))

    if not hallazgos:
        st.markdown(estilos.aviso("ok", "Sin observaciones",
                                  "No se detectan inconsistencias en la configuración "
                                  "ni en los registros."), unsafe_allow_html=True)
    else:
        for titulo, detalle in hallazgos:
            st.markdown(estilos.aviso("info", titulo, detalle), unsafe_allow_html=True)


def panel_vencimientos(tabla):
    rotulo("Resumen ejecutivo")
    st.markdown(estilos.barra_indicadores(nu.indicadores(tabla),
                                          r.ahora().strftime("%d-%m-%Y %H:%M")),
                unsafe_allow_html=True)

    c1, c2, c3 = st.columns([2, 2, 2])
    with c1:
        estado = st.selectbox("Estado", ["Todos", "⚠️ Requieren acción", "🔴 Vencidos",
                                         "🟠 Renovar por etiqueta", "🟡 Por renovar",
                                         "🟢 Vigentes"], key="f_estado")
    with c2:
        tipo = st.selectbox("Tipo de documento",
                            ["Todos"] + cfg.TIPOS_DOCUMENTO + cfg.TIPOS_HISTORICOS,
                            key="f_tipo")
    with c3:
        lista_sup = ["Todos"] + pe.nombres_supervisores()
        supervisor = st.selectbox("Supervisor", lista_sup, key="f_sup")

    c4, c5, c6, c7 = st.columns([3, 2, 2, 2])
    with c4:
        busqueda = st.text_input("Buscar", key="f_busca",
                                 placeholder="Nombre, cédula o rol")
    with c5:
        etiqueta = st.selectbox("Etiqueta", ["Todos", cfg.ETIQUETA_ESPECIAL, "Sin etiqueta"],
                                key="f_etiqueta")
    with c6:
        st.write("")
        historico = st.toggle("Ver histórico", key="f_hist",
                              help="Incluye documentos ya reemplazados")
    with c7:
        st.write("")
        inactivos = st.toggle("Incluir inactivos", key="f_inact",
                              help="Muestra el expediente de colaboradores dados de baja")

    vista = nu.aplicar_filtros(tabla, estado, tipo, busqueda, historico,
                               supervisor, etiqueta, inactivos)

    st.dataframe(
        vista, hide_index=True, width='stretch', height=440,
        column_config={
            "Días Restantes": st.column_config.NumberColumn("Días", format="%d",
                                                            width="small"),
            "Documento": st.column_config.LinkColumn("Documento", display_text="Abrir ↗",
                                                     width="small"),
        })

    izq, der = st.columns([1, 4])
    with izq:
        st.download_button("Exportar a CSV",
                           data=vista.to_csv(index=False).encode("utf-8-sig"),
                           file_name=f"reporte_{r.ahora():%Y%m%d_%H%M}.csv",
                           mime="text/csv", width='stretch')
    with der:
        st.caption(f"{len(vista)} de {len(tabla)} registros en la vista actual")

    # ---- Vista previa del recordatorio ----
    rotulo("Próximo recordatorio", "Lo que saldría por correo mañana a las 07:00")
    previa = nu.aplicar_filtros(tabla, "⚠️ Requieren acción", "Todos", "", False)
    umbral = max(cfg.DIAS_AVISO)
    if not previa.empty:
        previa = previa[previa["Días Restantes"].fillna(9999) <= umbral]

    if previa.empty:
        aviso("ok", "Nada por avisar hoy",
              f"Ningún documento de colaboradores activos entra en el umbral de "
              f"{umbral} días. El recordatorio no se enviará.")
    else:
        correos = {n: pe.correo_supervisor(n)
                   for n in previa["Supervisor"].unique() if n}
        con_correo = {n: c for n, c in correos.items() if c}
        huerfanos = int((previa["Supervisor"] == "").sum()) + sum(
            int((previa["Supervisor"] == n).sum()) for n, c in correos.items() if not c)

        aviso("info", f"{len(previa)} documento(s) entrarían en el próximo recordatorio",
              f"Se envía de lunes a viernes a las 07:00. Puedes lanzarlo ahora desde "
              f"GitHub ▸ Actions ▸ Recordatorio de certificados ▸ Run workflow.")

        destinos = "".join(
            f'<div class="estado-linea">{n} · <b>{c}</b> → '
            f'{int((previa["Supervisor"] == n).sum())} documento(s)</div>'
            for n, c in con_correo.items())
        destinos += (f'<div class="estado-linea">Administrador → '
                     f'<b>{len(previa)} documento(s)</b> (consolidado)</div>')
        if huerfanos:
            destinos += (f'<div class="estado-linea">Sin supervisor con correo · '
                         f'<b>{huerfanos} documento(s)</b> → solo al administrador</div>')
        st.markdown(destinos, unsafe_allow_html=True)

        with st.expander("Ver el detalle que se enviaría"):
            st.dataframe(
                previa[["Colaborador", "Supervisor", "Tipo de Documento",
                        "Caducidad", "Revisión", "Días Restantes", "Estado"]],
                hide_index=True, width='stretch')

    st.markdown(f"""
    <div class="nota">
      {cfg.ESTADO_VENCIDO} · {cfg.ESTADO_REVISION} (el documento sigue siendo legal, pero
      la etiqueta {cfg.ETIQUETA_ESPECIAL} exige renovarlo al año) ·
      {cfg.ESTADO_POR_RENOVAR} ({cfg.DIAS_ALERTA} días o menos) · {cfg.ESTADO_VIGENTE}.<br>
      Los recordatorios por correo se envían desde GitHub Actions cada mañana, no desde
      esta pantalla: una aplicación web solo ejecuta código cuando alguien la abre.
    </div>""", unsafe_allow_html=True)


# ==========================================================================================
# COMPOSICIÓN
# ==========================================================================================
def migracion_inicial():
    """
    Reconoce el trabajo ya cargado sin pedir permiso.

    En el primer arranque tras la actualización, el registro de personas está
    vacío pero la hoja de documentos no. En vez de exigir que alguien pulse un
    botón —y arriesgar que el equipo vea la app "vacía" y crea que perdió los
    datos—, las fichas y los supervisores se crean solos a partir del historial.

    Solo ocurre cuando el registro está completamente vacío, así que no puede
    pisar nada de lo que se edite después.
    """
    if st.session_state.get("migracion_hecha"):
        return None
    st.session_state.migracion_hecha = True

    try:
        if not pe.colaboradores().empty:
            return None
        documentos = nu.leer_hoja()
        if documentos.empty:
            return None
        with st.spinner("Reconociendo colaboradores del historial..."):
            return pe.migrar_desde_historial(documentos)
    except Exception as e:
        st.session_state.migracion_error = str(e)
        return None


def titular_riesgo():
    """Lo que requiere gestión hoy. Devuelve True si mostró algo."""
    _fichas = pe.colaboradores()
    _tabla = nu.tabla_control(_fichas)
    _m = nu.indicadores(_tabla)
    criticos = _m["vencidos"] + _m["revision"]
    if not (criticos or _m["renovar"]):
        return False
    partes = []
    if _m["vencidos"]:
        partes.append(f'<b>{_m["vencidos"]}</b> vencido(s)')
    if _m["revision"]:
        partes.append(f'<b>{_m["revision"]}</b> por renovar ({cfg.ETIQUETA_ESPECIAL})')
    if _m["renovar"]:
        partes.append(f'<b>{_m["renovar"]}</b> en los próximos {cfg.DIAS_ALERTA} días')
    aviso("error" if criticos else "info", "Requieren gestión hoy", " · ".join(partes))
    return True


def preparar():
    """
    Arranque común de las páginas de Personal habilitado: estado de la conexión
    en la barra lateral, migración inicial y titular de riesgo. Si no hay acceso
    a Google detiene solo esta página; el resto de ISOtools sigue funcionando.
    """
    diag = barra_lateral()
    if diag["error"]:
        aviso("error", "Esta sección necesita acceso a Google",
              "Configura el bloque [gcp_service_account] en los secretos de la app "
              "(Settings ▸ Secrets) y revisa el detalle en la barra lateral. "
              "Las secciones del sistema documental funcionan sin esta conexión.")
        st.stop()

    resultado = migracion_inicial()
    if resultado:
        fichas, sups, faltan = resultado
        aviso("ok", "Historial reconocido",
              f"{fichas} colaborador(es) y {sups} supervisor(es) reconocidos a partir de "
              f"los documentos ya cargados. Nada se volvió a subir.")
        if faltan:
            aviso("info", f"Faltan {faltan} correo(s) de supervisor",
                  "Sin correo no se les puede enviar los avisos de vencimiento. "
                  "Complétalos en Equipo ▸ Supervisores.")
    try:
        titular_riesgo()
    except Exception:
        pass


def pagina_control():
    preparar()
    panel_dashboard()


def pagina_documentos():
    preparar()
    panel_documentos()


def pagina_equipo():
    preparar()
    panel_colaboradores()
