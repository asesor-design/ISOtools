"""
Configuración del Sistema de Control Documental de Colaboradores.

Identificadores, catálogos y reglas de negocio. Para cambiar el comportamiento
del sistema no hace falta tocar ningún otro archivo.
"""

# ==========================================================================================
# IDENTIFICADORES DE GOOGLE
# ==========================================================================================
SHEET_ID = "1a8P_3oGyIQO7Cx_HAzyJu-cnbTidR2GGLQ5zCw8vQ90"
SHEET_GID = 1504686367            # pestaña de documentos; se prioriza sobre el nombre
NOMBRE_HOJA = "Registros"
HOJA_COLABORADORES = "Colaboradores"
HOJA_SUPERVISORES = "Supervisores"
HOJA_BITACORA = "Bitácora"

CARPETA_RAIZ_ID = "1jkpGgoGuhIvn9GdkYLl_Bt1iYvXCPfTy"
CARPETA_LOGO_ID = "1qBrt2L2j6f1b2DQklxW3Ty382uCt8Wqi"

# Subcarpeta para documentos que cubren a varios colaboradores (planillas IESS)
NOMBRE_COMPARTIDOS = "Documentos compartidos"
NOMBRE_HISTORICO = "Histórico"

# ==========================================================================================
# ZONA HORARIA
# ------------------------------------------------------------------------------------------
# Toda fecha que el sistema escribe o muestra usa esta zona, no la del servidor.
# UTC_OFFSET es el respaldo por si el contenedor no trae la base de zonas.
# ==========================================================================================
ZONA_HORARIA = "America/Guayaquil"
UTC_OFFSET = -5

# ==========================================================================================
# IDENTIDAD
# ==========================================================================================
NOMBRE_EMPRESA = "STARTEC S.A."
UNIDAD = "Gestión de Talento Humano · Cumplimiento"
TITULO_APP = "Control Documental de Colaboradores"

# ==========================================================================================
# VIGENCIAS POR TIPO DE DOCUMENTO
# ------------------------------------------------------------------------------------------
# La caducidad se calcula sola a partir de la fecha de emisión. El operador ya
# no la escribe: elige el tipo, pone la emisión y el sistema hace el resto.
# Formato: (cantidad, "anios" | "meses" | "dias"). None = se registra a mano.
# ==========================================================================================
VIGENCIAS = {
    "Certificado Médico": (1, "anios"),
    "Antecedentes Penales": (3, "meses"),
    "Fiscalía": (3, "meses"),
    "Certificado de Riesgos de Trabajo en Alturas": (4, "anios"),
    "Certificado de Riesgos de Trabajo Eléctrico": (4, "anios"),
    "Certificado de Riesgos de Trabajo en Caliente y Soldadura": (4, "anios"),
    "Certificado de Riesgos de Trabajo en Obra Gris y Construcción": (4, "anios"),
    "Afiliación IESS": (1, "meses"),      # planilla mensual
    "Otros": None,                        # sin vigencia fija: fecha manual
    "Competencias": (1, "anios"),         # tipo heredado
}

TIPOS_DOCUMENTO = [
    "Certificado Médico",
    "Antecedentes Penales",
    "Fiscalía",
    "Certificado de Riesgos de Trabajo en Alturas",
    "Certificado de Riesgos de Trabajo Eléctrico",
    "Certificado de Riesgos de Trabajo en Caliente y Soldadura",
    "Certificado de Riesgos de Trabajo en Obra Gris y Construcción",
    "Afiliación IESS",
    "Otros",
]

TIPOS_HISTORICOS = ["Competencias"]

# Tipos que se cargan normalmente como documento compartido de varios colaboradores
TIPOS_COMPARTIBLES = ["Afiliación IESS", "Otros"]

# ==========================================================================================
# ETIQUETA DIEBOLD  ·  ahora es una propiedad del COLABORADOR, no del documento
# ------------------------------------------------------------------------------------------
# Los certificados de riesgos de trabajo duran 4 años por ley, pero para los
# colaboradores etiquetados el cliente exige renovarlos cada año. El sistema
# guarda ambas fechas: la caducidad legal y la revisión anticipada.
# ==========================================================================================
ETIQUETA_ESPECIAL = "Diebold"
REGLA_REVISION = (1, "anios")
TIPOS_REVISION_ANUAL = [
    "Certificado de Riesgos de Trabajo en Alturas",
    "Certificado de Riesgos de Trabajo Eléctrico",
    "Certificado de Riesgos de Trabajo en Caliente y Soldadura",
    "Certificado de Riesgos de Trabajo en Obra Gris y Construcción",
]

# ==========================================================================================
# DOCUMENTOS EXIGIBLES POR ROL
# ------------------------------------------------------------------------------------------
# Hasta aquí el sistema solo sabía de los documentos que EXISTEN. Un control de
# cumplimiento tiene que saber además cuáles FALTAN: un colaborador sin
# certificado médico no aparece en ninguna alerta, porque no hay nada que
# vencer, y es el caso más grave de todos.
#
# Ajusta estas listas a la realidad de la operación antes de presentarlo.
# ==========================================================================================
#  Exigibles a TODA la plantilla, sin excepción. Es el mínimo común: cualquier
#  otro documento se pide persona por persona según la tarea que ejecuta.
#  Quitar un tipo de esta lista lo vuelve opcional en todo el sistema; agregarlo
#  lo hace obligatorio para todos de inmediato.
REQUERIDOS_BASE = [
    "Antecedentes Penales",
    "Fiscalía",
]

#  Sugerencia por cargo. Solo se usa para PROPONER los requisitos al crear una
#  ficha nueva; nunca los impone. Los certificados de riesgos dependen de la
#  tarea que cada persona ejecuta, no de su título: dos guardias del mismo
#  puesto pueden necesitar uno alturas y el otro nada.
SUGERIDOS_POR_ROL = {
    "Guardia de Seguridad": ["Certificado Médico", "Afiliación IESS"],
    "Supervisor": ["Certificado Médico", "Afiliación IESS"],
    "Operador de Monitoreo": ["Certificado Médico", "Afiliación IESS"],
    "Conductor": ["Certificado Médico", "Afiliación IESS"],
    "Jefe de Operaciones": ["Certificado Médico", "Afiliación IESS"],
    "Técnico": ["Certificado Médico", "Afiliación IESS"],
    "Administrativo": ["Afiliación IESS"],
}

#  Documentos que pueden exigirse a una persona además de los de base.
OPCIONALES = [t for t in TIPOS_DOCUMENTO if t not in REQUERIDOS_BASE and t != "Otros"]

#  Marca que distingue «solo los de base» de «ficha sin configurar todavía».
SIN_ADICIONALES = "NINGUNO"

#  Separador de la lista de requisitos dentro de la celda de la hoja.
SEPARADOR = " | "


def sugeridos(rol):
    """Requisitos que se proponen al dar de alta a alguien con ese cargo."""
    return SUGERIDOS_POR_ROL.get(str(rol or "").strip(), [])


def adicionales_de(ficha):
    """
    Requisitos propios de una persona, leídos de su ficha.

    Celda vacía significa «aún no se configuró»: se cae a la sugerencia del
    cargo para no romper las fichas creadas antes de esta versión. La marca
    NINGUNO significa, explícitamente, que solo se le exigen los de base.
    """
    if ficha is None:
        return []
    crudo = str((ficha.get("Requeridos") if hasattr(ficha, "get") else "") or "").strip()
    if not crudo:
        return sugeridos(ficha.get("Rol") if hasattr(ficha, "get") else "")
    if crudo.upper() == SIN_ADICIONALES:
        return []
    return [t.strip() for t in crudo.split("|") if t.strip()]


def requeridos_de(ficha):
    """Lista completa de documentos exigibles a esa persona."""
    vistos, salida = set(), []
    for tipo in REQUERIDOS_BASE + adicionales_de(ficha):
        if tipo not in vistos:
            vistos.add(tipo)
            salida.append(tipo)
    return salida


def serializar(adicionales):
    """Convierte la selección de la interfaz al texto que se guarda en la hoja."""
    limpios = [t for t in (adicionales or []) if t]
    return SEPARADOR.join(limpios) if limpios else SIN_ADICIONALES


ESTADO_FALTANTE = "⬛ NO CARGADO"

# ==========================================================================================
# ESTADOS
# ==========================================================================================
DIAS_ALERTA = 30                  # umbral de la alerta amarilla

ESTADO_VENCIDO = "🔴 VENCIDO"
ESTADO_REVISION = "🟠 RENOVAR POR ETIQUETA"
ESTADO_POR_RENOVAR = "🟡 POR RENOVAR"
ESTADO_VIGENTE = "🟢 VIGENTE"
ESTADO_SIN_FECHA = "⚪ SIN FECHA"

ESTADOS_CRITICOS = [ESTADO_VENCIDO, ESTADO_REVISION, ESTADO_POR_RENOVAR]
ESTADOS_INCUMPLE = [ESTADO_VENCIDO, ESTADO_FALTANTE]

ACTIVO = "ACTIVO"
INACTIVO = "INACTIVO"

# Retención de datos de colaboradores inactivos antes de avisar para depurarlos
REGLA_PURGA = (1, "anios")

ROLES = [
    "Guardia de Seguridad",
    "Supervisor",
    "Operador de Monitoreo",
    "Conductor",
    "Técnico",
    "Administrativo",
    "Jefe de Operaciones",
]

ABREVIATURAS_TIPO = {
    "Certificado Médico": "CERT_MEDICO",
    "Antecedentes Penales": "ANTEC_PENALES",
    "Fiscalía": "FISCALIA",
    "Certificado de Riesgos de Trabajo en Alturas": "RT_ALTURAS",
    "Certificado de Riesgos de Trabajo Eléctrico": "RT_ELECTRICO",
    "Certificado de Riesgos de Trabajo en Caliente y Soldadura": "RT_CALIENTE_SOLDADURA",
    "Certificado de Riesgos de Trabajo en Obra Gris y Construcción": "RT_OBRA_GRIS",
    "Afiliación IESS": "AFILIACION_IESS",
    "Competencias": "COMPETENCIAS",
    "Otros": "OTROS",
}

CLAVES_TIPO = {
    "Certificado Médico":
        (["MEDIC", "MEDIK", "SALUD", "APTITUD", "OCUPACIONAL", "EXAMEN",
          "PREOCUPACIONAL"], ["CM", "CCM", "MED", "EMO"]),
    "Antecedentes Penales":
        (["ANTECEDENT", "PENAL", "POLICIAL", "JUDICIAL", "RECORD"], ["AP", "ANT"]),
    "Fiscalía":
        (["FISCAL", "SATJE", "DENUNCIA"], ["FIS", "FGE"]),
    "Certificado de Riesgos de Trabajo en Alturas":
        (["ALTURA", "ANDAMIO", "ARNES"], ["TA", "RTA"]),
    "Certificado de Riesgos de Trabajo Eléctrico":
        (["ELECTRIC", "ELECTRIK", "BAJA_TENSION", "ALTA_TENSION"], ["RTE", "TE"]),
    "Certificado de Riesgos de Trabajo en Caliente y Soldadura":
        (["CALIENTE", "SOLDAD", "OXICORTE"], ["RTC", "TC"]),
    "Certificado de Riesgos de Trabajo en Obra Gris y Construcción":
        (["OBRA_GRIS", "OBRAGRIS", "CONSTRUC", "ALBANIL", "CIVIL"], ["RTO", "OG"]),
    "Afiliación IESS":
        (["IESS", "AFILIA", "HISTORIAL_LABORAL", "PLANILLA", "PATRONAL"], ["IESS"]),
}

SIN_TIPO = "⚠ Elegir tipo"

# ==========================================================================================
# ESQUEMAS DE LAS HOJAS
# ==========================================================================================
COLUMNAS_SHEET = [
    "Marca_Temporal", "Nombre", "Cedula", "Rol", "Diebold", "Tipo_Documento",
    "Fecha_Emision", "Fecha_Caducidad", "Fecha_Revision", "Nombre_Archivo",
    "Carpeta_Colaborador", "Enlace_Drive", "ID_Archivo", "Grupo_Documento",
    "Observaciones", "Vigencia_Registro",
]

COLUMNAS_COLABORADORES = [
    "Cedula", "Nombre", "Rol", "Supervisor", "Etiqueta", "Requeridos", "Estado",
    "Fecha_Ingreso", "Fecha_Inactivacion", "Observaciones",
]

COLUMNAS_SUPERVISORES = ["Nombre", "Correo", "Rol", "Estado"]

#  Bitácora de auditoría: registro de solo-anexado de todo cambio con efecto
#  sobre el expediente. Es lo que permite responder «quién cambió esto y cuándo»
#  ante una revisión, en lugar de deducirlo del estado final.
COLUMNAS_BITACORA = ["Marca_Temporal", "Accion", "Entidad", "Detalle", "Origen"]

ACCION_CARGA = "CARGA_DOCUMENTO"
ACCION_COMPARTIDO = "CARGA_COMPARTIDA"
ACCION_REEMPLAZO = "REEMPLAZO_VERSION"
ACCION_FICHA = "FICHA_COLABORADOR"
ACCION_ESTADO = "CAMBIO_ESTADO"
ACCION_ETIQUETA = "CAMBIO_ETIQUETA"
ACCION_REQUISITOS = "CAMBIO_REQUISITOS"
ACCION_SUPERVISOR = "ASIGNACION_SUPERVISOR"

#  Perfiles de notificación.
#    SUPERVISOR    recibe solo los vencimientos de su equipo
#    ADMINISTRADOR recibe el consolidado completo, de toda la plantilla
PERFIL_SUPERVISOR = "Supervisor"
PERFIL_ADMIN = "Administrador"
PERFILES = [PERFIL_SUPERVISOR, PERFIL_ADMIN]

RENOMBRES_COLUMNA = {"Cliente_Especial": "Diebold"}
VALORES_DEFECTO = {"Vigencia_Registro": "ACTUAL"}

FORMATO_FECHA = "%d-%m-%Y"

# ==========================================================================================
# NOTIFICACIONES  (las usa notificar.py desde GitHub Actions)
# ==========================================================================================
DIAS_AVISO = [30, 15, 7, 1]       # se avisa cuando faltan estos días o menos
ASUNTO_RECORDATORIO = "Certificados por renovar · {empresa}"
ASUNTO_PURGA = "Colaboradores inactivos para depurar · {empresa}"

# ==========================================================================================
# RENDIMIENTO Y PALETA
# ==========================================================================================
TTL_CACHE = 120
TTL_LOGO = 3600
MAX_LOTE = 10
MAX_COMPARTIDO = 60               # colaboradores por documento compartido
EXTENSIONES = ["pdf", "png", "jpg", "jpeg", "webp"]
LOGO_ALTURA = 96
