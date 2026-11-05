"""
Reglas de negocio puras: fechas, vigencias y semáforo.

Este módulo NO importa Streamlit ni las librerías de Google. Es la capa que
comparten la aplicación web y el notificador que corre en GitHub Actions, de
modo que ambos apliquen exactamente el mismo criterio de vencimiento.
"""

import os
import re
import unicodedata
from datetime import datetime, date, timedelta, timezone

try:
    from zoneinfo import ZoneInfo
except ImportError:                                    # pragma: no cover
    ZoneInfo = None

import ajustes as cfg


# ==========================================================================================
# HORA LOCAL
# ------------------------------------------------------------------------------------------
# Los servidores de Streamlit y de GitHub Actions corren en UTC. Sin esto, un
# documento cargado a las 19:00 de Guayaquil quedaría sellado con la fecha del
# día siguiente, y el semáforo contaría un día de menos.
#
# Ecuador continental no aplica horario de verano desde 1993, así que el
# desplazamiento fijo de -5 es un respaldo seguro si falta la base de datos de
# zonas horarias en el contenedor.
# ==========================================================================================
def _zona():
    if ZoneInfo is not None:
        try:
            return ZoneInfo(cfg.ZONA_HORARIA)
        except Exception:
            pass
    return timezone(timedelta(hours=cfg.UTC_OFFSET))


ZONA = _zona()


def ahora():
    """Fecha y hora actuales en la zona configurada, sin información de zona."""
    return datetime.now(ZONA).replace(tzinfo=None)


def hoy():
    """Fecha de hoy en la zona configurada."""
    return ahora().date()


def sello():
    """Marca temporal legible para los registros."""
    return ahora().strftime("%d-%m-%Y %H:%M:%S")


# ==========================================================================================
# TEXTO
# ==========================================================================================
def limpiar_texto(texto, largo=40):
    """Normaliza texto: sin tildes, sin símbolos, en mayúsculas."""
    texto = unicodedata.normalize("NFKD", str(texto)).encode("ascii", "ignore").decode()
    texto = re.sub(r"[^A-Za-z0-9]+", "_", texto).strip("_")
    return texto.upper()[:largo]


def inferir_tipo(nombre_archivo, por_defecto=None):
    """
    Deduce el tipo de documento por el nombre del archivo. Devuelve `por_defecto`
    cuando no hay coincidencia, para que la interfaz lo marque y se elija a mano.
    """
    base = limpiar_texto(os.path.splitext(os.path.basename(str(nombre_archivo)))[0],
                         largo=160)

    for tipo, (fragmentos, _) in cfg.CLAVES_TIPO.items():
        if any(f in base for f in fragmentos):
            return tipo

    palabras = set(base.split("_"))
    for tipo, (_, siglas) in cfg.CLAVES_TIPO.items():
        if palabras & set(siglas):
            return tipo

    return por_defecto


# ==========================================================================================
# FECHAS
# ==========================================================================================
def clave_cedula(valor):
    """
    Normaliza una cédula para comparar.

    Google Sheets interpreta «0104567890» como número y le come el cero inicial.
    Si la ficha se guardó como texto y el documento como número, el cruce falla y
    el expediente entero aparece como no cargado. Se comparan solo los dígitos
    significativos, de modo que ambas formas coinciden.
    """
    digitos = re.sub(r"\D", "", str(valor or ""))
    return digitos.lstrip("0") or digitos or ""


def cedula_visible(valor, largo=10):
    """Cédula con los ceros restituidos, para mostrarla como corresponde."""
    digitos = re.sub(r"\D", "", str(valor or ""))
    return digitos.zfill(largo) if 0 < len(digitos) <= largo else digitos


def parsear_fecha(valor):
    """Convierte a datetime aceptando DD-MM-YYYY, DD/MM/YYYY, YYYY-MM-DD y objetos fecha."""
    if valor is None:
        return None
    if isinstance(valor, datetime):
        return valor
    if isinstance(valor, date):
        return datetime(valor.year, valor.month, valor.day)
    # pandas.Timestamp y NaT, sin importar pandas
    if hasattr(valor, "to_pydatetime"):
        try:
            return valor.to_pydatetime()
        except Exception:
            return None

    texto = str(valor).strip()
    if not texto or texto.lower() in ("nat", "none", "nan", "<na>"):
        return None
    for patron in ("%d-%m-%Y", "%d/%m/%Y", "%Y-%m-%d", "%d-%m-%y", "%d.%m.%Y"):
        try:
            return datetime.strptime(texto, patron)
        except ValueError:
            continue
    return None


def sumar_meses(fecha, meses):
    """
    Suma meses calendario conservando el día. Si el día no existe en el mes
    destino (31 de enero + 1 mes), cae al último día de ese mes.

    Se implementa a mano en vez de usar dateutil para no depender de una
    librería transitiva que podría desaparecer al fijar versiones.
    """
    if fecha is None:
        return None
    total = fecha.month - 1 + int(meses)
    anio = fecha.year + total // 12
    mes = total % 12 + 1

    if mes == 12:
        ultimo = 31
    else:
        ultimo = (datetime(anio + (mes == 12), mes % 12 + 1, 1) - timedelta(days=1)).day
    return fecha.replace(year=anio, month=mes, day=min(fecha.day, ultimo))


def aplicar_vigencia(emision, regla):
    """Aplica una regla (cantidad, unidad) sobre la fecha de emisión."""
    if emision is None or not regla:
        return None
    cantidad, unidad = regla
    if unidad == "anios":
        return sumar_meses(emision, cantidad * 12)
    if unidad == "meses":
        return sumar_meses(emision, cantidad)
    if unidad == "dias":
        return emision + timedelta(days=cantidad)
    return None


def caducidad_automatica(tipo, emision):
    """
    Fecha de caducidad según el catálogo de vigencias. None cuando el tipo no
    tiene vigencia fija (p. ej. "Otros") y hay que registrarla a mano.

    Ejemplo: Certificado Médico emitido el 11-02-2026 vence el 11-02-2027.
    """
    return aplicar_vigencia(parsear_fecha(emision), cfg.VIGENCIAS.get(tipo))


def fecha_revision(tipo, emision, etiquetado):
    """
    Fecha de revisión anticipada por etiqueta del colaborador.

    Los certificados de riesgos de trabajo son legalmente válidos 4 años, pero
    los colaboradores etiquetados requieren renovarlos cada año por exigencia
    del cliente. Esta fecha convive con la caducidad legal, no la reemplaza.
    """
    if not etiquetado or tipo not in cfg.TIPOS_REVISION_ANUAL:
        return None
    return aplicar_vigencia(parsear_fecha(emision), cfg.REGLA_REVISION)


# ==========================================================================================
# SEMÁFORO
# ==========================================================================================
def dias_restantes(fecha, referencia=None):
    """Días entre hoy (o la referencia dada) y la fecha indicada."""
    fecha = parsear_fecha(fecha)
    if fecha is None:
        return None
    referencia = (referencia or ahora()).date()
    return (fecha.date() - referencia).days


def calcular_estado(fecha_caducidad, fecha_revision=None, referencia=None):
    """
    Semáforo del documento. Devuelve (días restantes, etiqueta).

    Cuando existe una fecha de revisión anticipada, manda la más próxima de las
    dos: de nada sirve que el certificado siga siendo legal cuatro años si el
    cliente exige renovarlo al año.
    """
    dias_cad = dias_restantes(fecha_caducidad, referencia)
    dias_rev = dias_restantes(fecha_revision, referencia)

    candidatos = [d for d in (dias_cad, dias_rev) if d is not None]
    if not candidatos:
        return None, cfg.ESTADO_SIN_FECHA

    dias = min(candidatos)
    if dias <= 0:
        # Si lo que se cumplió fue la revisión y el documento sigue vigente, el
        # estado no es "vencido" sino "renovación exigida por la etiqueta".
        if dias_cad is not None and dias_cad > 0:
            return dias, cfg.ESTADO_REVISION
        return dias, cfg.ESTADO_VENCIDO
    if dias <= cfg.DIAS_ALERTA:
        return dias, cfg.ESTADO_POR_RENOVAR
    return dias, cfg.ESTADO_VIGENTE


def requiere_purga(fecha_inactivacion, referencia=None):
    """True si un colaborador inactivo ya cumplió el plazo de retención."""
    dias = dias_restantes(
        aplicar_vigencia(parsear_fecha(fecha_inactivacion), cfg.REGLA_PURGA), referencia)
    return dias is not None and dias <= 0


def lista_tipos(tipos):
    """Enumeración legible de tipos, sin el prefijo largo."""
    return ", ".join(t.replace("Certificado de Riesgos de Trabajo ", "").strip()
                     for t in tipos)
