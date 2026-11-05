"""
Registro de colaboradores y supervisores.

Hasta ahora los datos de la persona vivían repetidos en cada fila de documento.
Con estado, etiqueta y supervisor asignado eso deja de servir: si alguien cambia
de supervisor habría que editar todas sus filas. Este módulo mantiene una ficha
única por cédula y los documentos solo la referencian.
"""

from datetime import datetime

import gspread
import pandas as pd
import streamlit as st

import ajustes as cfg
import reglas as r
from nucleo import conexiones, ident, ensanchar as nu_ensanchar


# ==========================================================================================
# ACCESO A LAS HOJAS
# ==========================================================================================
def _abrir(nombre, columnas):
    """Abre (o crea) una pestaña auxiliar y garantiza sus encabezados."""
    cliente, _ = conexiones()
    libro = cliente.open_by_key(ident("sheet_id", cfg.SHEET_ID))
    try:
        hoja = libro.worksheet(nombre)
    except gspread.WorksheetNotFound:
        hoja = libro.add_worksheet(title=nombre, rows=1000, cols=len(columnas) + 2)

    encabezados = hoja.row_values(1)
    if not encabezados:
        hoja.append_row(columnas, value_input_option="USER_ENTERED")
        return hoja, list(columnas)

    faltantes = [c for c in columnas if c not in encabezados]
    if faltantes:
        nu_ensanchar(hoja, len(encabezados) + len(faltantes))
        for columna in faltantes:
            encabezados.append(columna)
            hoja.update_cell(1, len(encabezados), columna)
    return hoja, encabezados


@st.cache_resource(show_spinner=False)
def hoja_colaboradores():
    return _abrir(cfg.HOJA_COLABORADORES, cfg.COLUMNAS_COLABORADORES)


@st.cache_resource(show_spinner=False)
def hoja_bitacora():
    return _abrir(cfg.HOJA_BITACORA, cfg.COLUMNAS_BITACORA)


def registrar(accion, entidad, detalle="", origen="Aplicación"):
    """
    Anota un hecho en la bitácora de auditoría.

    Es un registro de solo-anexado: nunca se edita ni se borra desde la
    aplicación. Sin esto, el sistema puede decir en qué estado está algo pero no
    cómo llegó ahí, que es justo lo que pregunta una auditoría.

    Falla en silencio a propósito: un problema al escribir la bitácora no debe
    impedir la operación que el usuario estaba haciendo.
    """
    try:
        hoja, encabezados = hoja_bitacora()
        fila = {"Marca_Temporal": r.sello(), "Accion": accion,
                "Entidad": str(entidad), "Detalle": str(detalle)[:400],
                "Origen": origen}
        hoja.append_row([fila.get(c, "") for c in encabezados],
                        value_input_option="USER_ENTERED")
    except Exception as e:
        print(f"  (Aviso) No se pudo escribir en la bitácora: {e}")


@st.cache_data(ttl=cfg.TTL_CACHE, show_spinner=False)
def bitacora(limite=300):
    """Últimos movimientos registrados, del más reciente al más antiguo."""
    try:
        hoja, _ = hoja_bitacora()
        df = _leer(hoja, cfg.COLUMNAS_BITACORA)
    except Exception:
        return pd.DataFrame(columns=cfg.COLUMNAS_BITACORA)
    if df.empty:
        return df
    return df.iloc[::-1].head(limite).reset_index(drop=True)


@st.cache_resource(show_spinner=False)
def hoja_supervisores():
    return _abrir(cfg.HOJA_SUPERVISORES, cfg.COLUMNAS_SUPERVISORES)


def _leer(hoja, columnas):
    """
    DataFrame de la pestaña, descartando filas vacías y conservando el índice.

    Garantiza que TODAS las columnas esperadas existan, aunque la hoja sea de una
    versión anterior. Sin esto, cualquier consulta al esquema nuevo revienta con
    KeyError en una hoja vieja, y el resto del código tendría que ir preguntando
    columna por columna si existe.
    """
    valores = hoja.get_all_values()
    if len(valores) < 2:
        return pd.DataFrame(columns=columnas)

    cabecera = valores[0]
    ancho = len(cabecera)
    cuerpo = [(f + [""] * ancho)[:ancho] for f in valores[1:]]
    df = pd.DataFrame(cuerpo, columns=cabecera)
    df = df[df.apply(lambda f: any(str(v).strip() for v in f), axis=1)]

    #  Las columnas que falten se agregan vacías; las propias del usuario se
    #  conservan. El índice no se toca: lo usan las escrituras por fila.
    for columna in columnas:
        if columna not in df.columns:
            df[columna] = ""
    return df


@st.cache_data(ttl=cfg.TTL_CACHE, show_spinner=False)
def colaboradores():
    """Ficha de todos los colaboradores, activos e inactivos."""
    hoja, _ = hoja_colaboradores()
    df = _leer(hoja, cfg.COLUMNAS_COLABORADORES)
    if not df.empty:
        df["Cedula"] = df["Cedula"].astype(str).str.strip()
        df["Estado"] = df["Estado"].astype(str).str.strip().str.upper().replace("", cfg.ACTIVO)
    return df


@st.cache_data(ttl=cfg.TTL_CACHE, show_spinner=False)
def supervisores():
    """Supervisores con su correo, para el enrutamiento de notificaciones."""
    hoja, _ = hoja_supervisores()
    return _leer(hoja, cfg.COLUMNAS_SUPERVISORES)


def invalidar():
    """Se llama tras cada escritura para que la próxima lectura sea fresca."""
    colaboradores.clear()
    supervisores.clear()
    bitacora.clear()


# ==========================================================================================
# CONSULTAS
# ==========================================================================================
def ficha(cedula):
    """Ficha de un colaborador como diccionario, o None si no está registrado."""
    df = colaboradores()
    if df.empty:
        return None
    clave = r.clave_cedula(cedula)
    fila = df[df["Cedula"].map(r.clave_cedula) == clave]
    return None if fila.empty else fila.iloc[0].to_dict()


def esta_etiquetado(cedula):
    """True si el colaborador lleva la etiqueta especial."""
    f = ficha(cedula)
    return bool(f) and str(f.get("Etiqueta", "")).strip().upper() == cfg.ETIQUETA_ESPECIAL.upper()


def esta_activo(cedula):
    f = ficha(cedula)
    return bool(f) and str(f.get("Estado", cfg.ACTIVO)).strip().upper() == cfg.ACTIVO


def activos():
    """
    Colaboradores en servicio, uno por cédula.

    Con fichas duplicadas la misma persona aparecería varias veces en los
    desplegables y en el conteo. Se conserva la primera de cada cédula.
    """
    df = colaboradores()
    if df.empty:
        return df
    vivos = df[df["Estado"] == cfg.ACTIVO].copy()
    if vivos.empty:
        return vivos
    return vivos[~vivos["Cedula"].map(r.clave_cedula).duplicated()]


def unicos(df):
    """Una fila por cédula, para listar sin repetir."""
    if df is None or df.empty:
        return df
    return df[~df["Cedula"].map(r.clave_cedula).duplicated()]


def opciones(solo_activos=True):
    """Lista «cédula — nombre» para los desplegables de la interfaz."""
    df = activos() if solo_activos else unicos(colaboradores())
    if df is None or df.empty:
        return []
    return [f'{r.cedula_visible(c["Cedula"])} — {c["Nombre"]}'
            for _, c in df.iterrows()]


def cedula_de(opcion):
    """Extrae la cédula del texto que muestran los desplegables."""
    return str(opcion).split("—")[0].strip() if opcion else ""


def _clave_nombre(valor):
    """Nombre normalizado para comparar: sin tildes, sin dobles espacios, en mayúsculas."""
    return " ".join(r.limpiar_texto(valor, largo=120).split("_")).strip()


def _presentar(nombre):
    """Escritura limpia de un nombre: sin espacios dobles y con mayúsculas sensatas."""
    limpio = " ".join(str(nombre).split())
    if limpio.islower() or limpio.isupper():
        limpio = limpio.title()
    return limpio


def nombres_supervisores(perfil=None):
    """
    Lista ÚNICA de supervisores, ordenada.

    La hoja puede contener el mismo nombre escrito de dos formas —por la
    importación del historial o por una carga manual repetida—, y eso obligaría
    a asignar dos veces el mismo equipo. Aquí se colapsan en una sola entrada.
    """
    df = supervisores()
    if df.empty:
        return []
    if perfil:
        df = df[df["Rol"].astype(str).str.strip().str.upper() == perfil.upper()]

    unicos = {}
    for _, f in df.iterrows():
        nombre = str(f.get("Nombre", "")).strip()
        if not nombre:
            continue
        clave = _clave_nombre(nombre)
        correo = str(f.get("Correo", "")).strip()
        #  Ante dos escrituras del mismo nombre gana la que tenga correo; el
        #  nombre que se muestra es siempre el mejor formateado del grupo.
        previo = unicos.get(clave)
        if previo is None:
            unicos[clave] = [_presentar(nombre), correo]
        else:
            if correo and not previo[1]:
                previo[1] = correo
            if nombre == _presentar(nombre) and previo[0] != _presentar(nombre):
                previo[0] = _presentar(nombre)
    return sorted(v[0] for v in unicos.values())


def administradores():
    """Correos que reciben el consolidado de toda la plantilla."""
    df = supervisores()
    if df.empty:
        return []
    admin = df[df["Rol"].astype(str).str.strip().str.upper() == cfg.PERFIL_ADMIN.upper()]
    correos = [str(c).strip() for c in admin["Correo"] if str(c).strip()]
    return sorted(set(correos))


def correo_supervisor(nombre):
    """Correo del supervisor indicado, o cadena vacía si no está registrado."""
    df = supervisores()
    if df.empty or not nombre:
        return ""
    clave = _clave_nombre(nombre)
    fila = df[df["Nombre"].map(_clave_nombre) == clave]
    if fila.empty:
        return ""
    #  Si el nombre está duplicado, se toma la entrada que sí tiene correo.
    con_correo = fila[fila["Correo"].astype(str).str.strip() != ""]
    origen = con_correo if not con_correo.empty else fila
    return str(origen.iloc[0].get("Correo", "")).strip()


def pendientes_de_purga():
    """
    Colaboradores inactivos que ya cumplieron el plazo de retención.
    Se listan para que una persona decida; el sistema nunca borra por su cuenta.
    """
    df = colaboradores()
    if df.empty:
        return pd.DataFrame(columns=cfg.COLUMNAS_COLABORADORES)
    inactivos = df[df["Estado"] == cfg.INACTIVO].copy()
    if inactivos.empty:
        return inactivos
    marca = inactivos["Fecha_Inactivacion"].apply(r.requiere_purga)
    return inactivos[marca]


# ==========================================================================================
# ESCRITURA
# ==========================================================================================
def _fila_a1(indice_df):
    """Traduce el índice del DataFrame al número de fila real de la hoja."""
    return indice_df + 2


def guardar(cedula, nombre, rol, supervisor, etiqueta, estado,
            fecha_ingreso=None, observaciones="", adicionales=None):
    """
    Alta o actualización de la ficha. La cédula es la llave: si ya existe, se
    actualiza en su sitio en lugar de duplicar.
    """
    hoja, encabezados = hoja_colaboradores()
    cedula = str(cedula).strip()
    df = colaboradores()

    datos = {
        "Cedula": cedula,
        "Nombre": str(nombre).strip().title(),
        "Rol": str(rol or "").strip(),
        "Supervisor": str(supervisor or "").strip(),
        "Etiqueta": cfg.ETIQUETA_ESPECIAL if etiqueta else "",
        "Requeridos": cfg.serializar(adicionales),
        "Estado": estado,
        "Fecha_Ingreso": (r.parsear_fecha(fecha_ingreso) or r.ahora()).strftime(
            cfg.FORMATO_FECHA),
        "Fecha_Inactivacion": "",
        "Observaciones": str(observaciones or "").strip(),
    }

    clave = r.clave_cedula(cedula)
    existente = df[df["Cedula"].map(r.clave_cedula) == clave] if not df.empty else df
    if existente.empty:
        hoja.append_row([datos.get(c, "") for c in encabezados],
                        value_input_option="USER_ENTERED")
    else:
        # Se conservan los campos que esta operación no debe pisar
        datos["Fecha_Ingreso"] = existente.iloc[0].get("Fecha_Ingreso") or datos["Fecha_Ingreso"]
        datos["Fecha_Inactivacion"] = existente.iloc[0].get("Fecha_Inactivacion", "")
        ultima = gspread.utils.rowcol_to_a1(1, len(encabezados))[0]
        #  Se escriben todas las fichas de esa cédula: si hay duplicadas, dejar
        #  una desactualizada produce comportamientos contradictorios.
        for indice in existente.index:
            fila = _fila_a1(indice)
            hoja.update(f"A{fila}:{ultima}{fila}",
                        [[datos.get(c, "") for c in encabezados]],
                        value_input_option="USER_ENTERED")
    registrar(cfg.ACCION_FICHA, f"{datos['Cedula']} · {datos['Nombre']}",
              f"rol={datos['Rol']} · supervisor={datos['Supervisor'] or 'sin asignar'} · "
              f"etiqueta={datos['Etiqueta'] or 'no'} · exigibles={datos['Requeridos']}")
    invalidar()
    return datos


def _escribir_por_lotes(hoja, cambios, tamano=80):
    """
    Envía las actualizaciones en tandas.

    Una sola petición con cientos de rangos puede ser rechazada por tamaño y
    dejar la operación a medias sin avisar.
    """
    for inicio in range(0, len(cambios), tamano):
        hoja.batch_update(cambios[inicio:inicio + tamano],
                          value_input_option="USER_ENTERED")


def cambiar_estado(cedula, activar):
    """
    Activa o desactiva a un colaborador. Al desactivar se sella la fecha, que es
    la que arranca el conteo de retención antes de avisar para depurar sus datos.

    Actualiza TODAS las fichas de esa cédula. Si existen duplicadas y solo se
    tocara la primera, la persona seguiría apareciendo como activa en los
    desplegables: el sistema la vería dos veces con estados distintos.

    Devuelve el número de fichas modificadas.
    """
    hoja, encabezados = hoja_colaboradores()
    df = colaboradores()
    filas = df[df["Cedula"].map(r.clave_cedula) == r.clave_cedula(cedula)]
    if filas.empty:
        return 0

    col_estado = encabezados.index("Estado") + 1
    col_fecha = encabezados.index("Fecha_Inactivacion") + 1
    estado = cfg.ACTIVO if activar else cfg.INACTIVO
    sello = "" if activar else r.ahora().strftime(cfg.FORMATO_FECHA)

    cambios = []
    for indice in filas.index:
        cambios.append({"range": gspread.utils.rowcol_to_a1(_fila_a1(indice), col_estado),
                        "values": [[estado]]})
        cambios.append({"range": gspread.utils.rowcol_to_a1(_fila_a1(indice), col_fecha),
                        "values": [[sello]]})

    _escribir_por_lotes(hoja, cambios)
    registrar(cfg.ACCION_ESTADO,
              f'{filas.iloc[0]["Cedula"]} · {filas.iloc[0]["Nombre"]}',
              f'{estado} · {len(filas)} ficha(s)')
    invalidar()
    return len(filas)


def importar_desde_documentos(registros):
    """
    Crea las fichas que faltan a partir del historial de documentos.

    Sirve para migrar de una sola vez: recorre los registros existentes, arma la
    lista de cédulas únicas y da de alta a quien no tenga ficha. No toca a los
    ya registrados, así que puede ejecutarse varias veces sin duplicar.

    De cada persona toma el nombre y el rol de su documento MÁS RECIENTE, que es
    el dato más confiable, y hereda la etiqueta si alguno de sus documentos se
    cargó marcado como especial.

    Devuelve (creados, omitidos).
    """
    if registros is None or registros.empty:
        return 0, 0

    existentes = ({r.clave_cedula(c) for c in colaboradores()["Cedula"]}
                  if not colaboradores().empty else set())
    hoja, encabezados = hoja_colaboradores()

    resumen = {}
    for _, reg in registros.iterrows():
        cedula = str(reg.get("Cedula", "")).strip()
        if not cedula or r.clave_cedula(cedula) in existentes:
            continue
        marca = r.parsear_fecha(str(reg.get("Marca_Temporal", "")).split(" ")[0])
        previo = resumen.get(cedula)
        etiquetado = str(reg.get("Diebold", "")).strip().upper().startswith("S")

        if previo is None or (marca and previo["marca"] and marca > previo["marca"]) \
                or (marca and previo["marca"] is None):
            resumen[cedula] = {
                "marca": marca,
                "nombre": str(reg.get("Nombre", "")).strip().title(),
                "rol": str(reg.get("Rol", "")).strip(),
                "etiqueta": etiquetado or bool(previo and previo["etiqueta"]),
            }
        elif etiquetado:
            resumen[cedula]["etiqueta"] = True

    if not resumen:
        return 0, len(existentes)

    filas = []
    for cedula, datos in resumen.items():
        filas.append({
            "Cedula": cedula,
            "Nombre": datos["nombre"],
            "Rol": datos["rol"],
            "Supervisor": "",
            "Etiqueta": cfg.ETIQUETA_ESPECIAL if datos["etiqueta"] else "",
            "Estado": cfg.ACTIVO,
            "Fecha_Ingreso": (datos["marca"] or r.ahora()).strftime(cfg.FORMATO_FECHA),
            "Fecha_Inactivacion": "",
            "Observaciones": "Importado del historial de documentos",
        })

    hoja.append_rows([[f.get(c, "") for c in encabezados] for f in filas],
                     value_input_option="USER_ENTERED")
    invalidar()
    return len(filas), len(existentes)


def importar_supervisores():
    """
    Registra como supervisores a los colaboradores cuyo rol ya lo indica.

    El sistema anterior no tenía una lista de supervisores: la jefatura estaba
    implícita en el campo Rol. Esta función la hace explícita sin que nadie
    reescriba nada.

    El correo queda vacío a propósito: no hay forma de deducirlo del historial y
    es el dato que decide a dónde llegan los avisos. Hay que completarlo a mano.

    Devuelve (creados, ya_existentes).
    """
    fichas = colaboradores()
    if fichas.empty:
        return 0, 0

    candidatos = fichas[fichas["Rol"].astype(str).str.strip().str.upper()
                        .str.contains("SUPERVISOR", na=False)]
    if candidatos.empty:
        return 0, 0

    actuales = supervisores()
    registrados = (set(actuales["Nombre"].astype(str).str.strip())
                   if not actuales.empty else set())

    claves = {_clave_nombre(n) for n in registrados}
    nuevos, vistos = [], set()
    for n in candidatos["Nombre"].astype(str).str.strip():
        clave = _clave_nombre(n)
        if n and clave not in claves and clave not in vistos:
            vistos.add(clave)
            nuevos.append(n)
    if not nuevos:
        return 0, len(registrados)

    hoja, encabezados = hoja_supervisores()
    filas = [{"Nombre": n, "Correo": "", "Rol": cfg.PERFIL_SUPERVISOR,
              "Estado": cfg.ACTIVO} for n in nuevos]
    hoja.append_rows([[f.get(c, "") for c in encabezados] for f in filas],
                     value_input_option="USER_ENTERED")
    invalidar()
    return len(filas), len(registrados)


def migrar_desde_historial(registros):
    """
    Migración completa en un paso: fichas de colaboradores y lista de
    supervisores, deducidas de lo que ya está cargado.

    Es idempotente: puede ejecutarse las veces que haga falta sin duplicar.
    Devuelve (fichas creadas, supervisores creados, sin correo).
    """
    creadas, _ = importar_desde_documentos(registros)
    sups, _ = importar_supervisores()
    faltan_correo = 0
    actuales = supervisores()
    if not actuales.empty:
        faltan_correo = int((actuales["Correo"].astype(str).str.strip() == "").sum())
    return creadas, sups, faltan_correo


def sin_correo():
    """Supervisores registrados a los que aún les falta el correo."""
    df = supervisores()
    if df.empty:
        return []
    faltan = df[df["Correo"].astype(str).str.strip() == ""]["Nombre"].tolist()
    return sorted({n for n in faltan if str(n).strip()})


def guardar_supervisor(nombre, correo, perfil=None, activo=True):
    """
    Alta o actualización de un supervisor.

    La comparación ignora tildes, mayúsculas y espacios sobrantes, de modo que
    «Carlos Mora» y «carlos  mora» no generan dos entradas.
    """
    hoja, encabezados = hoja_supervisores()
    df = supervisores()
    datos = {"Nombre": str(nombre).strip(), "Correo": str(correo).strip(),
             "Rol": perfil or cfg.PERFIL_SUPERVISOR,
             "Estado": cfg.ACTIVO if activo else cfg.INACTIVO}

    existente = (df[df["Nombre"].map(_clave_nombre) == _clave_nombre(datos["Nombre"])]
                 if not df.empty else df)
    if existente.empty:
        hoja.append_row([datos.get(c, "") for c in encabezados],
                        value_input_option="USER_ENTERED")
    else:
        fila = _fila_a1(existente.index[0])
        ultima = gspread.utils.rowcol_to_a1(1, len(encabezados))[0]
        hoja.update(f"A{fila}:{ultima}{fila}",
                    [[datos.get(c, "") for c in encabezados]],
                    value_input_option="USER_ENTERED")
    invalidar()
    return datos


def establecer_etiqueta(cedulas):
    """
    Define de una sola vez quiénes llevan la etiqueta.

    Es una operación de reemplazo, no de suma: las cédulas indicadas quedan
    etiquetadas y **a todas las demás se les quita**. Así se corrige de golpe una
    asignación heredada equivocada, sin tener que abrir ficha por ficha.

    Devuelve (agregadas, quitadas).
    """
    hoja, encabezados = hoja_colaboradores()
    df = colaboradores()
    if df.empty:
        return 0, 0

    objetivo = {r.clave_cedula(c) for c in cedulas}
    columna = encabezados.index("Etiqueta") + 1

    cambios, agregadas, quitadas = [], 0, 0
    for indice, fila in df.iterrows():
        actual = str(fila.get("Etiqueta", "")).strip()
        deseada = (cfg.ETIQUETA_ESPECIAL
                   if r.clave_cedula(fila["Cedula"]) in objetivo else "")
        if actual == deseada:
            continue
        cambios.append({
            "range": gspread.utils.rowcol_to_a1(_fila_a1(indice), columna),
            "values": [[deseada]]})
        if deseada:
            agregadas += 1
        else:
            quitadas += 1

    if cambios:
        _escribir_por_lotes(hoja, cambios)
        registrar(cfg.ACCION_ETIQUETA, f"{len(objetivo)} colaborador(es)",
                  f"{agregadas} con etiqueta {cfg.ETIQUETA_ESPECIAL}, {quitadas} sin ella")
        invalidar()
    return agregadas, quitadas


def establecer_requisitos(cedulas, adicionales, modo="reemplazar"):
    """
    Define en bloque qué documentos se exigen a un grupo de personas.

    Los certificados de riesgos dependen de la tarea asignada, así que casi
    nunca se configuran de a uno: se cambia la cuadrilla que empieza a trabajar
    en alturas, no una persona suelta.

    modo="reemplazar"  deja exactamente la lista indicada
    modo="agregar"     suma lo indicado a lo que ya tenía cada quien
    modo="quitar"      resta lo indicado de lo que ya tenía

    Devuelve el número de fichas modificadas.
    """
    hoja, encabezados = hoja_colaboradores()
    df = colaboradores()
    if df.empty:
        return 0

    objetivo = {r.clave_cedula(c) for c in cedulas}
    columna = encabezados.index("Requeridos") + 1
    pedidos = [t for t in (adicionales or []) if t]

    cambios = []
    for indice, fila in df.iterrows():
        if r.clave_cedula(fila["Cedula"]) not in objetivo:
            continue

        actuales = cfg.adicionales_de(fila)
        if modo == "agregar":
            nuevos = actuales + [t for t in pedidos if t not in actuales]
        elif modo == "quitar":
            nuevos = [t for t in actuales if t not in pedidos]
        else:
            nuevos = pedidos

        texto = cfg.serializar(nuevos)
        if str(fila.get("Requeridos", "") or "").strip() == texto:
            continue
        cambios.append({
            "range": gspread.utils.rowcol_to_a1(_fila_a1(indice), columna),
            "values": [[texto]]})

    if cambios:
        _escribir_por_lotes(hoja, cambios)
        registrar(cfg.ACCION_REQUISITOS, f"{len(cambios)} ficha(s)",
                  f"{modo}: " + ", ".join(pedidos) if pedidos else modo)
        invalidar()
    return len(cambios)


def con_requisito(tipo):
    """Cédulas a las que hoy se les exige ese documento."""
    df = colaboradores()
    if df.empty:
        return []
    return [str(f["Cedula"]).strip() for _, f in df.iterrows()
            if tipo in cfg.requeridos_de(f)]


def _puntaje(fila):
    """Cuántos campos útiles trae una ficha. Sirve para elegir cuál conservar."""
    return sum(1 for c in ("Nombre", "Rol", "Supervisor", "Etiqueta", "Requeridos",
                           "Fecha_Ingreso", "Observaciones")
               if str(fila.get(c, "") or "").strip())


def depurar_duplicados(simular=True):
    """
    Consolida las fichas repetidas de una misma cédula en una sola.

    Conserva la más completa, le traslada los campos que solo tengan las otras
    —para no perder un supervisor o una etiqueta asignados en la copia
    equivocada— y elimina las sobrantes.

    Con simular=True no escribe nada: devuelve el plan para que una persona lo
    revise antes. Borrar filas es irreversible, así que no debe ocurrir sin
    confirmación explícita.

    Devuelve (plan, filas eliminadas).
    """
    df = colaboradores()
    if df.empty:
        return [], 0

    conteo = df["Cedula"].map(r.clave_cedula).value_counts()
    repetidas = conteo[conteo > 1].index.tolist()
    if not repetidas:
        return [], 0

    plan, a_borrar = [], []
    fusiones = {}

    for clave in repetidas:
        filas = df[df["Cedula"].map(r.clave_cedula) == clave]
        conservar = max(filas.index, key=lambda i: _puntaje(filas.loc[i]))
        base = filas.loc[conservar].to_dict()

        #  Se rescata de las copias todo campo que a la ficha elegida le falte.
        rescatado = []
        for indice in filas.index:
            if indice == conservar:
                continue
            for columna in ("Rol", "Supervisor", "Etiqueta", "Requeridos",
                            "Fecha_Ingreso", "Observaciones"):
                valor = str(filas.at[indice, columna] or "").strip()
                if valor and not str(base.get(columna, "") or "").strip():
                    base[columna] = valor
                    rescatado.append(columna)
            a_borrar.append(indice)

        #  Si alguna copia está inactiva, la ficha consolidada hereda ese estado:
        #  ante la duda, no se reactiva a alguien por accidente.
        estados = {str(filas.at[i, "Estado"] or "").strip().upper() for i in filas.index}
        if cfg.INACTIVO in estados:
            base["Estado"] = cfg.INACTIVO

        fusiones[conservar] = base
        plan.append({
            "Cedula": r.cedula_visible(base.get("Cedula")),
            "Nombre": base.get("Nombre", ""),
            "Fichas": len(filas),
            "Se conserva la fila": _fila_a1(conservar),
            "Se eliminan": len(filas) - 1,
            "Campos rescatados": ", ".join(sorted(set(rescatado))) or "—",
            "Estado final": base.get("Estado", cfg.ACTIVO),
        })

    if simular:
        return plan, len(a_borrar)

    hoja, encabezados = hoja_colaboradores()
    ultima = gspread.utils.rowcol_to_a1(1, len(encabezados))[0]

    for indice, base in fusiones.items():
        fila = _fila_a1(indice)
        hoja.update(f"A{fila}:{ultima}{fila}",
                    [[base.get(c, "") for c in encabezados]],
                    value_input_option="USER_ENTERED")

    #  De abajo hacia arriba: borrar una fila desplaza las siguientes.
    for indice in sorted(a_borrar, reverse=True):
        hoja.delete_rows(_fila_a1(indice))

    registrar("DEPURACION_FICHAS", f"{len(plan)} cédula(s)",
              f"{len(a_borrar)} ficha(s) duplicadas eliminadas")
    invalidar()
    return plan, len(a_borrar)


def etiquetados():
    """Cédulas que hoy llevan la etiqueta."""
    df = colaboradores()
    if df.empty:
        return []
    marca = df["Etiqueta"].astype(str).str.strip().str.upper() == cfg.ETIQUETA_ESPECIAL.upper()
    return df[marca]["Cedula"].tolist()


def asignar_lote(cedulas, supervisor):
    """
    Asigna varios colaboradores a un supervisor de una sola vez.

    Actualiza TODAS las filas que correspondan a cada cédula, no solo la
    primera: tras importar del historial puede haber fichas duplicadas, y
    dejarlas a medias hace que el colaborador siga apareciendo sin supervisor.

    Devuelve (filas actualizadas, cédulas sin ficha).
    """
    hoja, encabezados = hoja_colaboradores()
    df = colaboradores()
    col = encabezados.index("Supervisor") + 1
    destino = str(supervisor).strip()

    cambios, huerfanas = [], []
    for cedula in cedulas:
        clave = r.clave_cedula(cedula)
        filas = df[df["Cedula"].map(r.clave_cedula) == clave]
        if filas.empty:
            huerfanas.append(str(cedula))
            continue
        for indice in filas.index:
            if str(df.at[indice, "Supervisor"]).strip() == destino:
                continue
            cambios.append({
                "range": gspread.utils.rowcol_to_a1(_fila_a1(indice), col),
                "values": [[destino]]})

    if cambios:
        _escribir_por_lotes(hoja, cambios)
        registrar(cfg.ACCION_SUPERVISOR, f"{len(cambios)} ficha(s)",
                  f"asignadas a {destino}")
        invalidar()
    return len(cambios), huerfanas


def depurar_duplicadas():
    """
    Consolida las fichas repetidas: conserva la más completa de cada cédula y
    elimina el resto.

    Las filas se borran de abajo hacia arriba; al revés, cada borrado correría
    las de más abajo y se eliminarían las equivocadas.

    Devuelve (cédulas consolidadas, filas eliminadas).
    """
    hoja, _ = hoja_colaboradores()
    df = colaboradores()
    if df.empty:
        return 0, 0

    def riqueza(indice):
        """Cuántos campos con contenido tiene esa ficha."""
        return sum(1 for v in df.loc[indice] if str(v).strip())

    claves = df["Cedula"].map(r.clave_cedula)
    a_borrar, consolidadas = [], 0
    for clave in claves[claves.duplicated()].unique():
        grupo = list(df[claves == clave].index)
        conservar = max(grupo, key=riqueza)
        a_borrar += [i for i in grupo if i != conservar]
        consolidadas += 1

    for indice in sorted(a_borrar, reverse=True):
        hoja.delete_rows(_fila_a1(indice))

    if a_borrar:
        registrar(cfg.ACCION_FICHA, f"{consolidadas} cédula(s)",
                  f"depuración: {len(a_borrar)} ficha(s) duplicadas eliminadas")
        invalidar()
    return consolidadas, len(a_borrar)


def cedulas_duplicadas():
    """Cédulas con más de una ficha: el origen habitual de asignaciones a medias."""
    df = colaboradores()
    if df.empty:
        return {}
    conteo = df["Cedula"].map(r.clave_cedula).value_counts()
    salida = {}
    for clave in conteo[conteo > 1].index.tolist():
        filas = df[df["Cedula"].map(r.clave_cedula) == clave]
        salida[r.cedula_visible(filas.iloc[0]["Cedula"])] = \
            filas["Nombre"].astype(str).tolist()
    return salida
