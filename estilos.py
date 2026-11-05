"""
Identidad visual: hoja de estilos y componentes HTML de la interfaz.

Paleta ejecutiva
    Tinta #0E2733 · Pizarra #274B5C · Latón #A8802B · Lienzo #EEF1F3
    Granate #9C2B24 · Ámbar #B4770B · Bosque #1D6B4C

Tipografía
    Archivo para títulos · Inter para cuerpo · IBM Plex Mono para cifras y fechas
"""

import ajustes as cfg

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Archivo:wght@600;700&family=Inter:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500;600&display=swap');

/* ---- Lienzo ---- */
.stApp { background: #EEF1F3; }
html, body, [class*="css"] { font-family: 'Inter', system-ui, sans-serif; color: #0E2733; }
[data-testid="stHeader"] { background: transparent; }
.block-container { padding-top: 1.6rem; padding-bottom: 3rem; max-width: 1360px; }
#MainMenu, footer { visibility: hidden; }

/* ---- Cabecera institucional ---- */
.cabecera {
  display: flex; align-items: center; gap: 24px;
  background: #0E2733; border-left: 5px solid #A8802B;
  padding: 22px 30px; margin-bottom: 22px;
}
.cabecera .logo {
  width: __LOGO__px; height: __LOGO__px; flex: 0 0 __LOGO__px; object-fit: contain;
  background: #FFFFFF; padding: 9px; border-radius: 3px;
}
.cabecera .monograma {
  display: flex; align-items: center; justify-content: center;
  background: #A8802B; color: #0E2733; font-family: 'Archivo', sans-serif;
  font-weight: 700; font-size: __LOGO_FUENTE__px; letter-spacing: .04em;
}
.cabecera .marca {
  font-family: 'IBM Plex Mono', monospace; font-size: 11px; letter-spacing: .22em;
  text-transform: uppercase; color: #A8802B; display: block; margin-bottom: 5px;
}
.cabecera h1 {
  font-family: 'Archivo', system-ui, sans-serif; font-size: 27px; font-weight: 700;
  color: #FFFFFF; margin: 0; letter-spacing: -.01em; line-height: 1.15;
}
.cabecera .empresa { color: #C7D6DE; font-size: 13px; margin: 5px 0 0; }

/* ---- Encabezado de sección sin numeración arbitraria ---- */
.rotulo {
  display:flex; align-items:baseline; gap:12px; margin:18px 0 12px;
  border-bottom:1px solid #DAE1E6; padding-bottom:8px;
}
.rotulo h2 {
  font-family:'Archivo',system-ui,sans-serif; font-size:16px; font-weight:600;
  color:#0E2733; margin:0; letter-spacing:-.01em;
}
.rotulo p { font-size:12px; color:#6B818D; margin:0; }

/* ---- Estado vacío ---- */
.vacio {
  border:1px dashed #C9D4DB; background:#F7F9FA; padding:28px 24px;
  text-align:center; color:#5F7784; font-size:13px;
}
.vacio b { display:block; color:#274B5C; font-size:14px; margin-bottom:5px; }

/* ---- Expediente ---- */
.rejilla { display:grid; grid-template-columns:repeat(auto-fill,minmax(215px,1fr)); gap:10px; }
.doc {
  background:#FFF; border:1px solid #DAE1E6; border-top:3px solid #8DA0AB;
  padding:12px 14px; font-size:12.5px;
}
.doc .tipo { font-weight:600; color:#0E2733; display:block; margin-bottom:6px;
             line-height:1.3; min-height:2.6em; }
.doc .plazo { font-family:'IBM Plex Mono',monospace; font-size:19px; font-weight:600;
              display:block; line-height:1.1; }
.doc .fecha { font-size:11px; color:#6B818D; display:block; margin-top:3px; }
.doc--vigente  { border-top-color:#1D6B4C; } .doc--vigente .plazo  { color:#1D6B4C; }
.doc--renovar  { border-top-color:#B4770B; } .doc--renovar .plazo  { color:#B4770B; }
.doc--revision { border-top-color:#C25A17; } .doc--revision .plazo { color:#C25A17; }
.doc--vencido  { border-top-color:#9C2B24; } .doc--vencido .plazo  { color:#9C2B24; }
.doc--falta { border-top-color:#5F7784; background:#F2F5F7; border-style:dashed; }
.doc--falta .plazo { color:#5F7784; font-size:14px; }

/* ---- Barra de cumplimiento ---- */
.barra { height:8px; background:#E4EBEF; overflow:hidden; margin:6px 0 4px; }
.barra span { display:block; height:100%; background:#1D6B4C; }
.barra--bajo span { background:#9C2B24; }
.barra--medio span { background:#B4770B; }

/* ---- Encabezados de sección ---- */
.seccion {
  font-family: 'IBM Plex Mono', monospace; font-size: 11px; letter-spacing: .16em;
  text-transform: uppercase; color: #274B5C; border-bottom: 1px solid #DAE1E6;
  padding-bottom: 7px; margin: 6px 0 14px;
}
.seccion span { color: #A8802B; margin-right: 8px; }

/* ---- Pestañas ---- */
.stTabs [data-baseweb="tab-list"] { gap: 4px; border-bottom: 1px solid #DAE1E6; }
.stTabs [data-baseweb="tab"] {
  background: transparent; border-radius: 0; padding: 10px 18px;
  font-size: 13px; font-weight: 500; color: #5F7784;
}
.stTabs [aria-selected="true"] {
  color: #0E2733 !important; border-bottom: 2px solid #A8802B;
  background: #FFFFFF;
}

/* ---- Indicadores ---- */
.kpi-barra { display: flex; gap: 12px; flex-wrap: wrap; margin-bottom: 6px; }
.kpi { flex: 1 1 130px; background: #FFFFFF; border: 1px solid #DAE1E6;
       border-left: 4px solid #274B5C; padding: 14px 16px; }
.kpi-valor { display: block; font-family: 'IBM Plex Mono', monospace; font-size: 28px;
             font-weight: 600; color: #0E2733; line-height: 1.1; }
.kpi-etiqueta { display: block; font-size: 10.5px; letter-spacing: .07em;
                text-transform: uppercase; color: #5F7784; margin-top: 4px; }
.kpi--critico { border-left-color: #9C2B24; } .kpi--critico .kpi-valor { color: #9C2B24; }
.kpi--alerta  { border-left-color: #B4770B; } .kpi--alerta  .kpi-valor { color: #B4770B; }
.kpi--ok      { border-left-color: #1D6B4C; } .kpi--ok      .kpi-valor { color: #1D6B4C; }
.kpi--acento  { border-left-color: #A8802B; } .kpi--acento  .kpi-valor { color: #A8802B; }
.kpi--historico { border-left-color: #8DA0AB; background: #F7F9FA; }
.kpi--historico .kpi-valor { color: #5F7784; }
.kpi--revision { border-left-color: #C25A17; } .kpi--revision .kpi-valor { color: #C25A17; }

/* ---- Fichas de colaborador ---- */
.ficha { background:#FFF; border:1px solid #DAE1E6; border-left:4px solid #274B5C;
         padding:12px 16px; margin-bottom:8px; font-size:13px; }
.ficha--inactivo { border-left-color:#8DA0AB; background:#F7F9FA; color:#5F7784; }
.ficha b { font-size:14px; }
.ficha .meta { font-family:'IBM Plex Mono',monospace; font-size:11.5px; color:#5F7784; }
.pastilla { display:inline-block; font-size:10px; letter-spacing:.08em;
            text-transform:uppercase; padding:2px 7px; border-radius:2px; margin-left:6px; }
.pastilla--etiqueta { background:#A8802B; color:#0E2733; }
.pastilla--inactivo { background:#DAE1E6; color:#5F7784; }
.kpi-pie { font-size: 11px; color: #6B818D; margin: 8px 0 18px; }

/* ---- Notas ---- */
.nota {
  background: #F5F8FA; border: 1px solid #DAE1E6; border-left: 3px solid #A8802B;
  padding: 12px 16px; font-size: 12.5px; color: #33505F; line-height: 1.65;
  margin-top: 14px;
}
.nota strong { color: #0E2733; }
.nota code {
  font-family: 'IBM Plex Mono', monospace; font-size: 11.5px;
  background: #E4EBEF; color: #0E2733; padding: 1px 5px; border-radius: 2px;
}

/* ---- Avisos ---- */
.aviso { display: flex; gap: 12px; align-items: flex-start; padding: 14px 16px;
         border: 1px solid; margin: 10px 0; font-size: 13px; }
.aviso-icono { font-size: 16px; font-weight: 700; line-height: 1.3; }
.aviso strong { display: block; font-size: 14px; }
.aviso-detalle { display: block; font-size: 12.5px; opacity: .9; margin-top: 3px; }
.aviso-ok    { background: #EDF6F1; border-color: #1D6B4C; color: #14523A; }
.aviso-error { background: #FBEFEE; border-color: #9C2B24; color: #7C221D; }
.aviso-info  { background: #FBF5E9; border-color: #A8802B; color: #6F5417; }
.lista-carga { margin: 4px 0 10px; padding: 10px 16px 10px 32px; background: #F5F8FA;
               border: 1px solid #DAE1E6; font-size: 12.5px; color: #33505F; }
.lista-carga li { margin: 2px 0; }
.lista-error { color: #7C221D; }

/* ---- Botones ---- */
.stButton > button, .stDownloadButton > button {
  border-radius: 3px; font-weight: 500; font-size: 13px;
  border: 1px solid #C9D4DB; color: #0E2733;
}
.stButton > button[kind="primary"] {
  background: #0E2733; border-color: #0E2733; color: #FFFFFF;
}
.stButton > button[kind="primary"]:hover { background: #274B5C; border-color: #274B5C; }

/* ---- Formularios y tablas ---- */
.stTextInput input, .stDateInput input, .stTextArea textarea { font-size: 13px; }
[data-testid="stWidgetLabel"] p { font-size: 13px; font-weight: 600; color: #0E2733; }
[data-testid="stMetricValue"] { font-family: 'IBM Plex Mono', monospace; }
[data-testid="stDataFrame"] { border: 1px solid #DAE1E6; }
[data-testid="stFileUploaderDropzone"] { background: #F7F9FA; border-color: #C9D4DB; }

/* ---- Barra lateral ---- */
[data-testid="stSidebar"] { background: #FFFFFF; border-right: 1px solid #DAE1E6; }
[data-testid="stSidebar"] .stMarkdown p { font-size: 12.5px; color: #33505F; }
.estado-linea { font-family: 'IBM Plex Mono', monospace; font-size: 11.5px;
                color: #33505F; padding: 3px 0; }
.estado-linea b { color: #0E2733; }
</style>
"""

CSS = (CSS.replace("__LOGO_FUENTE__", str(round(cfg.LOGO_ALTURA * 0.32)))
          .replace("__LOGO__", str(cfg.LOGO_ALTURA)))


def cabecera(logo_uri=None, titulo=None, unidad=None):
    """Banda superior con el logo a la izquierda. Título y unidad cambian por sección."""
    if logo_uri:
        bloque = f'<img class="logo" src="{logo_uri}" alt="{cfg.NOMBRE_EMPRESA}">'
    else:
        iniciales = (cfg.NOMBRE_EMPRESA.split() or ["TH"])[0][:2].upper()
        bloque = f'<div class="logo monograma">{iniciales}</div>'

    return f"""
    <div class="cabecera">
      {bloque}
      <div>
        <span class="marca">{unidad or cfg.UNIDAD}</span>
        <h1>{titulo or cfg.TITULO_APP}</h1>
        <p class="empresa">{cfg.NOMBRE_EMPRESA}</p>
      </div>
    </div>"""


def rotulo(titulo, ayuda=""):
    """Encabezado de sección: título y una línea de contexto, sin numeración."""
    extra = f"<p>{ayuda}</p>" if ayuda else ""
    return f'<div class="rotulo"><h2>{titulo}</h2>{extra}</div>'


def vacio(titulo, detalle):
    """Estado vacío: dice qué falta y qué hacer, en vez de dejar la pantalla en blanco."""
    return f'<div class="vacio"><b>{titulo}</b>{detalle}</div>'


def tarjeta_documento(tipo, estado, dias, fecha):
    """Tarjeta de un documento dentro del expediente de una persona."""
    mapa = {cfg.ESTADO_VIGENTE: "vigente", cfg.ESTADO_POR_RENOVAR: "renovar",
            cfg.ESTADO_REVISION: "revision", cfg.ESTADO_VENCIDO: "vencido",
            cfg.ESTADO_FALTANTE: "falta"}
    clase = mapa.get(estado, "falta")

    if estado == cfg.ESTADO_FALTANTE:
        plazo, pie = "Sin cargar", "No consta en el expediente"
    elif dias is None:
        plazo, pie = "—", "Sin fecha registrada"
    elif dias <= 0:
        plazo, pie = f"{abs(int(dias))} d", f"Venció el {fecha}"
    else:
        plazo, pie = f"{int(dias)} d", f"Hasta el {fecha}"

    corto = tipo.replace("Certificado de Riesgos de Trabajo ", "Riesgos · ")
    return (f'<div class="doc doc--{clase}"><span class="tipo">{corto}</span>'
            f'<span class="plazo">{plazo}</span><span class="fecha">{pie}</span></div>')


def barra_cumplimiento(porcentaje):
    """Barra de progreso del cumplimiento general."""
    nivel = "bajo" if porcentaje < 50 else ("medio" if porcentaje < 85 else "")
    clase = f"barra barra--{nivel}" if nivel else "barra"
    return f'<div class="{clase}"><span style="width:{porcentaje}%"></span></div>'


def seccion(numero, titulo):
    """Encabezado de sección numerado."""
    return f'<div class="seccion"><span>{numero}</span>{titulo}</div>'


def aviso(tipo, titulo, detalle=""):
    """Banner de resultado."""
    clase = {"ok": "aviso-ok", "error": "aviso-error", "info": "aviso-info"}[tipo]
    icono = {"ok": "✓", "error": "✕", "info": "•"}[tipo]
    cuerpo = f'<span class="aviso-detalle">{detalle}</span>' if detalle else ""
    return (f'<div class="aviso {clase}"><span class="aviso-icono">{icono}</span>'
            f'<div><strong>{titulo}</strong>{cuerpo}</div></div>')


def barra_indicadores(m, momento):
    """Fila de tarjetas con los indicadores del expediente."""
    def tarjeta(valor, etiqueta, mod="neutro"):
        return (f'<div class="kpi kpi--{mod}"><span class="kpi-valor">{valor}</span>'
                f'<span class="kpi-etiqueta">{etiqueta}</span></div>')

    return (
        '<div class="kpi-barra">'
        + tarjeta(m["colaboradores"], "Colaboradores")
        + tarjeta(m["documentos"], "Documentos")
        + tarjeta(m["vencidos"], "Vencidos", "critico")
        + tarjeta(m.get("revision", 0), f"Renovar por {cfg.ETIQUETA_ESPECIAL}", "revision")
        + tarjeta(m["renovar"], f"Por renovar ({cfg.DIAS_ALERTA} días)", "alerta")
        + tarjeta(m["vigentes"], "Vigentes", "ok")
        + tarjeta(f'{m["cumplimiento"]}%', "Cumplimiento", "acento")
        + tarjeta(m["historicos"], "Renovados (histórico)", "historico")
        + '</div>'
        + f'<p class="kpi-pie">Los indicadores consideran solo el documento vigente de '
          f'cada colaborador · Datos al {momento}</p>'
    )
