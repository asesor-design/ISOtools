"""
No conformidades y acciones correctivas (EST-SGC-NCF-PRO-001 · registro EST-SGC-NCF-REG-001).

Lógica del flujo y almacenamiento en la pestaña «No conformidades» de la misma
hoja de Google que usa Personal habilitado. Sin conexión a Google el módulo no
puede guardar y lo indica; el resto de ISOtools sigue funcionando.

Flujo (sección 5 del procedimiento):
    Registrada → Análisis de causa → Acción en curso → En verificación → Cerrada
                      ↑                                        │
                      └──────────── Reabierta (no eficaz) ─────┘
Las de severidad BAJA pueden pasar directo a la acción: el análisis de causa raíz
es obligatorio solo para MEDIO y ALTO (5.3).
"""
from __future__ import annotations

from datetime import date, datetime, timedelta

import numpy as np
import pandas as pd
import streamlit as st

HOJA = "No conformidades"
COLUMNAS = [
    "ID", "Fecha_Deteccion", "Fecha_Registro", "Reportado_Por", "Origen", "Proceso", "Documento",
    "Descripcion", "Severidad", "Correccion_Inmediata", "Porques", "Causa_Raiz", "Accion_Correctiva",
    "Responsable", "Fecha_Compromiso", "Requiere_Aprobacion", "Aprobado_Por", "Fecha_Implementacion",
    "Fecha_Verificacion", "Resultado_Verificacion", "Evidencia", "Verificaciones_No_Eficaces",
    "Estado", "Fecha_Cierre", "Actualizado",
]

ORIGENES = ["Queja o reclamo de cliente", "Auditoría interna", "Proceso interno", "Proveedor o contratista",
            "Incumplimiento de una política", "Falla técnica en servicio"]
SEVERIDADES = ["ALTO", "MEDIO", "BAJO"]
ESTADOS = ["Registrada", "Análisis de causa", "Acción en curso", "En verificación", "Cerrada", "Reabierta"]
ETAPAS = ["Registrada", "Análisis de causa", "Acción en curso", "En verificación", "Cerrada"]
ABIERTOS = {"Registrada", "Análisis de causa", "Acción en curso", "En verificación", "Reabierta"}

DIAS_REGISTRO = 3          # días hábiles para registrar (5.1)
VERIF_MIN, VERIF_MAX = 30, 90   # ventana de verificación de eficacia (5.5)
META_CIERRE = 45           # días (indicador 7)
META_EFICACIA = 85         # %  (indicador 7)

FORMATO = "%d/%m/%Y"


# ------------------------------------------------------------------------------ fechas
def a_fecha(valor) -> date | None:
    if isinstance(valor, datetime):
        return valor.date()
    if isinstance(valor, date):
        return valor
    texto = str(valor or "").strip()
    for fmt in (FORMATO, "%Y-%m-%d", "%d/%m/%Y %H:%M:%S", "%d/%m/%Y %H:%M"):
        try:
            return datetime.strptime(texto, fmt).date()
        except ValueError:
            continue
    return None


def texto_fecha(d: date | None) -> str:
    return d.strftime(FORMATO) if d else ""


def dias_habiles(desde: date, hasta: date) -> int:
    """Días hábiles (lunes a viernes) transcurridos entre dos fechas."""
    return int(np.busday_count(desde, hasta))


def hoy() -> date:
    try:
        import reglas
        return reglas.hoy()
    except Exception:
        return date.today()


# ------------------------------------------------------------------------------ almacenamiento
class AlmacenSheets:
    """Pestaña «No conformidades» del libro de Personal habilitado."""

    def __init__(self):
        import personas
        self._personas = personas
        self.hoja, self.encabezados = personas._abrir(HOJA, COLUMNAS)

    def leer(self) -> pd.DataFrame:
        return self._personas._leer(self.hoja, COLUMNAS)

    def agregar(self, fila: dict) -> None:
        self.hoja.append_row([fila.get(c, "") for c in self.encabezados], value_input_option="USER_ENTERED")

    def actualizar(self, ident: str, cambios: dict) -> None:
        import gspread
        ids = self.hoja.col_values(self.encabezados.index("ID") + 1)
        if ident not in ids:
            raise KeyError(f"No existe la no conformidad {ident}.")
        fila = ids.index(ident) + 1
        celdas = []
        for clave, valor in cambios.items():
            if clave in self.encabezados:
                celdas.append(gspread.Cell(fila, self.encabezados.index(clave) + 1, str(valor)))
        if celdas:
            self.hoja.update_cells(celdas, value_input_option="USER_ENTERED")


class AlmacenMemoria:
    """Almacén en memoria para pruebas."""

    def __init__(self, filas: list[dict] | None = None):
        self.filas = [dict(f) for f in (filas or [])]

    def leer(self) -> pd.DataFrame:
        df = pd.DataFrame(self.filas, columns=COLUMNAS)
        return df.fillna("")

    def agregar(self, fila: dict) -> None:
        self.filas.append({c: fila.get(c, "") for c in COLUMNAS})

    def actualizar(self, ident: str, cambios: dict) -> None:
        for f in self.filas:
            if f["ID"] == ident:
                f.update({k: str(v) for k, v in cambios.items()})
                return
        raise KeyError(ident)


_PRUEBA: AlmacenMemoria | None = None   # las pruebas pueden inyectar un almacén aquí


def disponible() -> bool:
    if _PRUEBA is not None:
        return True
    try:
        return "gcp_service_account" in st.secrets
    except Exception:
        return False


@st.cache_resource(show_spinner=False)
def _sheets() -> AlmacenSheets:
    return AlmacenSheets()


def almacen():
    return _PRUEBA if _PRUEBA is not None else _sheets()


@st.cache_data(ttl=120, show_spinner=False)
def _leer_cache() -> pd.DataFrame:
    return almacen().leer()


def leer() -> pd.DataFrame:
    """Registro completo con columnas calculadas (días, alertas, etapa)."""
    df = (almacen().leer() if _PRUEBA is not None else _leer_cache()).copy()
    return enriquecer(df)


def invalidar() -> None:
    _leer_cache.clear()


def _bitacora(accion: str, ident: str, detalle: str = "") -> None:
    if _PRUEBA is not None:
        return
    try:
        import personas
        personas.registrar(accion, ident, detalle, origen="No conformidades")
    except Exception:
        pass


# ------------------------------------------------------------------------------ reglas
def siguiente_id(df: pd.DataFrame, anio: int) -> str:
    prefijo = f"NC-{anio}-"
    nums = [int(x.split("-")[-1]) for x in df.get("ID", pd.Series(dtype=str)) if str(x).startswith(prefijo)
            and str(x).split("-")[-1].isdigit()]
    return f"{prefijo}{(max(nums) if nums else 0) + 1:03d}"


def requiere_analisis(severidad: str) -> bool:
    return severidad in ("ALTO", "MEDIO")


def alertas(fila: pd.Series, h: date) -> list[str]:
    """Situaciones que incumplen los plazos del procedimiento."""
    out = []
    det, reg = a_fecha(fila["Fecha_Deteccion"]), a_fecha(fila["Fecha_Registro"])
    if det and reg and dias_habiles(det, reg) > DIAS_REGISTRO:
        out.append(f"Registrada fuera de plazo ({dias_habiles(det, reg)} días hábiles; máximo {DIAS_REGISTRO})")
    estado = fila["Estado"]
    comp = a_fecha(fila["Fecha_Compromiso"])
    if estado in ("Registrada", "Análisis de causa", "Acción en curso", "Reabierta") and comp and comp < h:
        out.append(f"Acción vencida desde el {texto_fecha(comp)}")
    impl = a_fecha(fila["Fecha_Implementacion"])
    if estado == "En verificación" and impl:
        if h > impl + timedelta(days=VERIF_MAX):
            out.append(f"Verificación de eficacia vencida (más de {VERIF_MAX} días)")
    if estado == "Registrada" and reg and dias_habiles(reg, h) > 5:
        out.append("Sin análisis ni acción desde hace más de una semana")
    return out


def proxima_accion(fila: pd.Series, h: date) -> str:
    estado = fila["Estado"]
    if estado == "Registrada":
        return ("Analizar la causa raíz (5 porqués)" if requiere_analisis(fila["Severidad"])
                else "Definir la acción correctiva")
    if estado in ("Análisis de causa", "Reabierta"):
        return "Definir la acción correctiva, responsable y plazo"
    if estado == "Acción en curso":
        if fila["Requiere_Aprobacion"] == "Sí" and not fila["Aprobado_Por"]:
            return "Obtener aprobación de la Gerencia General"
        return "Marcar la acción como implementada"
    if estado == "En verificación":
        impl = a_fecha(fila["Fecha_Implementacion"])
        if impl and h < impl + timedelta(days=VERIF_MIN):
            return f"Esperar: verificar eficacia desde el {texto_fecha(impl + timedelta(days=VERIF_MIN))}"
        return "Verificar la eficacia y cerrar"
    return "—"


def enriquecer(df: pd.DataFrame) -> pd.DataFrame:
    h = hoy()
    if df.empty:
        for c in ("Dias_Abierta", "Alertas", "Proxima_Accion", "Abierta"):
            df[c] = pd.Series(dtype=object)
        return df
    df = df[df["ID"].astype(str).str.strip() != ""].copy()
    regs = df["Fecha_Registro"].map(a_fecha)
    cierres = df["Fecha_Cierre"].map(a_fecha)
    df["Abierta"] = df["Estado"].isin(ABIERTOS)
    df["Dias_Abierta"] = [((c or h) - r).days if r else None for r, c in zip(regs, cierres)]
    df["Alertas"] = [alertas(f, h) for _, f in df.iterrows()]
    df["Proxima_Accion"] = [proxima_accion(f, h) for _, f in df.iterrows()]
    return df.reset_index(drop=True)


def indicadores(df: pd.DataFrame) -> dict:
    """Indicadores de la sección 7 del procedimiento."""
    cerradas = df[df["Estado"] == "Cerrada"] if not df.empty else df
    dias = [d for d in cerradas.get("Dias_Abierta", []) if d is not None]
    no_eficaces = sum(int(x or 0) for x in df.get("Verificaciones_No_Eficaces", [])) if not df.empty else 0
    eficaces = len(cerradas)
    verificadas = eficaces + no_eficaces
    return {
        "abiertas": int(df["Abierta"].sum()) if not df.empty else 0,
        "con_alerta": int(sum(bool(a) for a, ab in zip(df.get("Alertas", []), df.get("Abierta", [])) if ab)) if not df.empty else 0,
        "altas_abiertas": int(((df["Severidad"] == "ALTO") & df["Abierta"]).sum()) if not df.empty else 0,
        "cerradas": eficaces,
        "tiempo_cierre": round(sum(dias) / len(dias)) if dias else None,
        "eficacia": round(eficaces / verificadas * 100) if verificadas else None,
        "total": len(df),
    }


# ------------------------------------------------------------------------------ operaciones
def ahora_texto() -> str:
    try:
        import reglas
        return reglas.sello()
    except Exception:
        return datetime.now().strftime("%d/%m/%Y %H:%M")


def registrar(datos: dict) -> str:
    """Crea la no conformidad (5.1) y devuelve su ID."""
    df = almacen().leer()
    h = hoy()
    ident = siguiente_id(df, h.year)
    fila = {c: "" for c in COLUMNAS}
    fila.update({k: v for k, v in datos.items() if k in COLUMNAS})
    fila.update({"ID": ident, "Fecha_Registro": texto_fecha(h), "Estado": "Registrada",
                 "Verificaciones_No_Eficaces": "0", "Actualizado": ahora_texto()})
    fila["Fecha_Deteccion"] = texto_fecha(a_fecha(fila["Fecha_Deteccion"]) or h)
    almacen().agregar(fila)
    invalidar()
    _bitacora("No conformidad registrada", ident, f'{fila["Severidad"]} · {fila["Descripcion"][:200]}')
    return ident


def actualizar(ident: str, cambios: dict, accion: str) -> None:
    cambios = {**cambios, "Actualizado": ahora_texto()}
    almacen().actualizar(ident, cambios)
    invalidar()
    _bitacora(accion, ident, ", ".join(f"{k}: {v}" for k, v in cambios.items() if k != "Actualizado")[:380])


def guardar_analisis(ident: str, porques: list[str], causa: str) -> None:
    """Análisis de causa raíz (5.3)."""
    actualizar(ident, {"Porques": " | ".join(p.strip() for p in porques if p.strip()), "Causa_Raiz": causa.strip(),
                       "Estado": "Análisis de causa"}, "Análisis de causa raíz")


def definir_accion(ident: str, accion: str, responsable: str, compromiso: date, requiere_aprob: bool) -> None:
    """Acción correctiva con responsable y plazo (5.4)."""
    actualizar(ident, {"Accion_Correctiva": accion.strip(), "Responsable": responsable,
                       "Fecha_Compromiso": texto_fecha(compromiso),
                       "Requiere_Aprobacion": "Sí" if requiere_aprob else "No",
                       "Estado": "Acción en curso"}, "Acción correctiva definida")


def aprobar(ident: str, quien: str) -> None:
    actualizar(ident, {"Aprobado_Por": quien.strip()}, "Acción aprobada por Gerencia General")


def implementar(ident: str, fecha_impl: date, evidencia: str) -> None:
    actualizar(ident, {"Fecha_Implementacion": texto_fecha(fecha_impl), "Evidencia": evidencia.strip(),
                       "Estado": "En verificación"}, "Acción implementada")


def verificar(ident: str, eficaz: bool, nota: str, previos_no_eficaces: int) -> None:
    """Verificación de eficacia (5.5) y cierre (5.6) o reapertura."""
    h = hoy()
    if eficaz:
        actualizar(ident, {"Fecha_Verificacion": texto_fecha(h),
                           "Resultado_Verificacion": "Eficaz" + (f": {nota.strip()}" if nota.strip() else ""),
                           "Estado": "Cerrada", "Fecha_Cierre": texto_fecha(h)}, "Cerrada: acción eficaz")
    else:
        actualizar(ident, {"Fecha_Verificacion": texto_fecha(h), "Resultado_Verificacion": f"No eficaz: {nota.strip()}",
                           "Verificaciones_No_Eficaces": str(previos_no_eficaces + 1), "Estado": "Reabierta",
                           "Fecha_Implementacion": "", "Aprobado_Por": ""}, "Reabierta: acción no eficaz")
