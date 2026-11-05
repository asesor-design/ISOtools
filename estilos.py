"""
Identidad visual: hoja de estilos y componentes HTML de la interfaz.

Paleta ejecutiva
    Tinta #25292D · Pizarra #2F6DAA · Latón #E8820C · Lienzo #F3F5F7
    Granate #9C2B24 · Ámbar #B4770B · Bosque #1D6B4C

Tipografía
    Archivo para títulos · Inter para cuerpo · IBM Plex Mono para cifras y fechas
"""

import ajustes as cfg

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Archivo:wght@600;700&family=Inter:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500;600&display=swap');

/* ---- Lienzo ---- */
.stApp { background: #F3F5F7; }
html, body, [class*="css"] { font-family: 'Inter', system-ui, sans-serif; color: #25292D; }
[data-testid="stHeader"] { background: transparent; }
.block-container { padding-top: 1.6rem; padding-bottom: 3rem; max-width: 1360px; }
#MainMenu, footer { visibility: hidden; }

/* ---- Cabecera institucional: logo STARTEC sobre blanco + franja de marca ---- */
.cabecera {
  display: flex; align-items: center; gap: 22px; flex-wrap: wrap;
  background: #FFFFFF; border: 1px solid #DFE3E8; border-bottom: 0;
  padding: 18px 26px 16px; margin-bottom: 0; position: relative;
}
.cabecera-franja { height: 5px; margin-bottom: 22px;
  background: linear-gradient(90deg, #F9BB06 0%, #E8820C 38%, #E8820C 52%, #4488C8 52%, #2F6DAA 100%); }
.cabecera .logo { height: 46px; width: auto; flex: 0 0 auto; object-fit: contain; }
.cabecera .monograma {
  display: flex; align-items: center; justify-content: center; width: 46px; height: 46px;
  background: #E8820C; color: #FFFFFF; font-family: 'Archivo', sans-serif; font-weight: 700; font-size: 18px;
}
.cabecera .divisor { width: 1px; align-self: stretch; background: #DFE3E8; }
.cabecera .textos { min-width: 0; flex: 1 1 260px; }
.cabecera .marca {
  font-family: 'IBM Plex Mono', monospace; font-size: 10.5px; letter-spacing: .2em;
  text-transform: uppercase; color: #2F6DAA; display: block; margin-bottom: 3px;
}
.cabecera h1 {
  font-family: 'Archivo', system-ui, sans-serif; font-size: 25px; font-weight: 700;
  color: #25292D; margin: 0; padding: 0; letter-spacing: -.01em; line-height: 1.15;
}
.cabecera .empresa { color: #66717C; font-size: 13px; margin: 3px 0 0; }
.cabecera .fecha { font-family: 'IBM Plex Mono', monospace; font-size: 11.5px; color: #66717C;
  text-align: right; line-height: 1.5; }
.cabecera .fecha b { color: #25292D; font-weight: 500; }
@media (max-width: 700px) { .cabecera .divisor, .cabecera .fecha { display: none; } }

/* ---- Encabezado de sección sin numeración arbitraria ---- */
.rotulo {
  display:flex; align-items:baseline; gap:12px; margin:18px 0 12px;
  border-bottom:1px solid #DFE3E8; padding-bottom:8px;
}
.rotulo h2 {
  font-family:'Archivo',system-ui,sans-serif; font-size:16px; font-weight:600;
  color:#25292D; margin:0; letter-spacing:-.01em;
}
.rotulo p { font-size:12px; color:#77818B; margin:0; }

/* ---- Estado vacío ---- */
.vacio {
  border:1px dashed #CED4DA; background:#F8F9FA; padding:28px 24px;
  text-align:center; color:#66717C; font-size:13px;
}
.vacio b { display:block; color:#2F6DAA; font-size:14px; margin-bottom:5px; }

/* ---- Expediente ---- */
.rejilla { display:grid; grid-template-columns:repeat(auto-fill,minmax(215px,1fr)); gap:10px; }
.doc {
  background:#FFF; border:1px solid #DFE3E8; border-top:3px solid #9AA3AC;
  padding:12px 14px; font-size:12.5px;
}
.doc .tipo { font-weight:600; color:#25292D; display:block; margin-bottom:6px;
             line-height:1.3; min-height:2.6em; }
.doc .plazo { font-family:'IBM Plex Mono',monospace; font-size:19px; font-weight:600;
              display:block; line-height:1.1; }
.doc .fecha { font-size:11px; color:#77818B; display:block; margin-top:3px; }
.doc--vigente  { border-top-color:#1D6B4C; } .doc--vigente .plazo  { color:#1D6B4C; }
.doc--renovar  { border-top-color:#B4770B; } .doc--renovar .plazo  { color:#B4770B; }
.doc--revision { border-top-color:#C25A17; } .doc--revision .plazo { color:#C25A17; }
.doc--vencido  { border-top-color:#9C2B24; } .doc--vencido .plazo  { color:#9C2B24; }
.doc--falta { border-top-color:#66717C; background:#F3F4F6; border-style:dashed; }
.doc--falta .plazo { color:#66717C; font-size:14px; }

/* ---- Barra de cumplimiento ---- */
.barra { height:8px; background:#E9ECEF; overflow:hidden; margin:6px 0 4px; }
.barra span { display:block; height:100%; background:#1D6B4C; }
.barra--bajo span { background:#9C2B24; }
.barra--medio span { background:#B4770B; }

/* ---- Encabezados de sección ---- */
.seccion {
  font-family: 'IBM Plex Mono', monospace; font-size: 11px; letter-spacing: .16em;
  text-transform: uppercase; color: #2F6DAA; border-bottom: 1px solid #DFE3E8;
  padding-bottom: 7px; margin: 6px 0 14px;
}
.seccion span { color: #C96A00; margin-right: 8px; }

/* ---- Pestañas ---- */
.stTabs [data-baseweb="tab-list"] { gap: 4px; border-bottom: 1px solid #DFE3E8; }
.stTabs [data-baseweb="tab"] {
  background: transparent; border-radius: 0; padding: 10px 18px;
  font-size: 13px; font-weight: 500; color: #66717C;
}
.stTabs [aria-selected="true"] {
  color: #25292D !important; border-bottom: 2px solid #E8820C;
  background: #FFFFFF;
}

/* ---- Indicadores ---- */
.kpi-barra { display: flex; gap: 12px; flex-wrap: wrap; margin-bottom: 6px; }
.kpi { flex: 1 1 130px; background: #FFFFFF; border: 1px solid #DFE3E8;
       border-left: 4px solid #2F6DAA; padding: 14px 16px; }
.kpi-valor { display: block; font-family: 'IBM Plex Mono', monospace; font-size: 28px;
             font-weight: 600; color: #25292D; line-height: 1.1; }
.kpi-etiqueta { display: block; font-size: 10.5px; letter-spacing: .07em;
                text-transform: uppercase; color: #66717C; margin-top: 4px; }
.kpi--critico { border-left-color: #9C2B24; } .kpi--critico .kpi-valor { color: #9C2B24; }
.kpi--alerta  { border-left-color: #B4770B; } .kpi--alerta  .kpi-valor { color: #B4770B; }
.kpi--ok      { border-left-color: #1D6B4C; } .kpi--ok      .kpi-valor { color: #1D6B4C; }
.kpi--acento  { border-left-color: #E8820C; } .kpi--acento  .kpi-valor { color: #C96A00; }
.kpi--historico { border-left-color: #9AA3AC; background: #F8F9FA; }
.kpi--historico .kpi-valor { color: #66717C; }
.kpi--revision { border-left-color: #C25A17; } .kpi--revision .kpi-valor { color: #C25A17; }

/* ---- Fichas de colaborador ---- */
.ficha { background:#FFF; border:1px solid #DFE3E8; border-left:4px solid #2F6DAA;
         padding:12px 16px; margin-bottom:8px; font-size:13px; }
.ficha--inactivo { border-left-color:#9AA3AC; background:#F8F9FA; color:#66717C; }
.ficha b { font-size:14px; }
.ficha .meta { font-family:'IBM Plex Mono',monospace; font-size:11.5px; color:#66717C; }
.pastilla { display:inline-block; font-size:10px; letter-spacing:.08em;
            text-transform:uppercase; padding:2px 7px; border-radius:2px; margin-left:6px; }
.pastilla--etiqueta { background:#E8820C; color:#25292D; }
.pastilla--inactivo { background:#DFE3E8; color:#66717C; }
.kpi-pie { font-size: 11px; color: #77818B; margin: 8px 0 18px; }

/* ---- Notas ---- */
.nota {
  background: #F6F8FA; border: 1px solid #DFE3E8; border-left: 3px solid #E8820C;
  padding: 12px 16px; font-size: 12.5px; color: #3E4751; line-height: 1.65;
  margin-top: 14px;
}
.nota strong { color: #25292D; }
.nota code {
  font-family: 'IBM Plex Mono', monospace; font-size: 11.5px;
  background: #E9ECEF; color: #25292D; padding: 1px 5px; border-radius: 2px;
}

/* ---- Avisos ---- */
.aviso { display: flex; gap: 12px; align-items: flex-start; padding: 14px 16px;
         border: 1px solid; margin: 10px 0; font-size: 13px; }
.aviso-icono { font-size: 16px; font-weight: 700; line-height: 1.3; }
.aviso strong { display: block; font-size: 14px; }
.aviso-detalle { display: block; font-size: 12.5px; opacity: .9; margin-top: 3px; }
.aviso-ok    { background: #EDF6F1; border-color: #1D6B4C; color: #14523A; }
.aviso-error { background: #FBEFEE; border-color: #9C2B24; color: #7C221D; }
.aviso-info  { background: #FEF5E7; border-color: #E8820C; color: #8A4B00; }
.lista-carga { margin: 4px 0 10px; padding: 10px 16px 10px 32px; background: #F6F8FA;
               border: 1px solid #DFE3E8; font-size: 12.5px; color: #3E4751; }
.lista-carga li { margin: 2px 0; }
.lista-error { color: #7C221D; }

/* ---- Botones ---- */
.stButton > button, .stDownloadButton > button {
  border-radius: 3px; font-weight: 500; font-size: 13px;
  border: 1px solid #CED4DA; color: #25292D;
}
.stButton > button[kind="primary"] {
  background: #25292D; border-color: #25292D; color: #FFFFFF;
}
.stButton > button[kind="primary"]:hover { background: #2F6DAA; border-color: #2F6DAA; }

/* ---- Formularios y tablas ---- */
.stTextInput input, .stDateInput input, .stTextArea textarea { font-size: 13px; }
[data-testid="stWidgetLabel"] p { font-size: 13px; font-weight: 600; color: #25292D; }
[data-testid="stMetricValue"] { font-family: 'IBM Plex Mono', monospace; }
[data-testid="stDataFrame"] { border: 1px solid #DFE3E8; }
[data-testid="stFileUploaderDropzone"] { background: #F8F9FA; border-color: #CED4DA; }

/* ---- Barra lateral ---- */
[data-testid="stSidebar"] { background: #FFFFFF; border-right: 1px solid #DFE3E8; }
[data-testid="stSidebar"] .stMarkdown p { font-size: 12.5px; color: #3E4751; }
.estado-linea { font-family: 'IBM Plex Mono', monospace; font-size: 11.5px;
                color: #3E4751; padding: 3px 0; }
.estado-linea b { color: #25292D; }
</style>
"""



def logo_local():
    """Logo de STARTEC incluido en el repositorio (assets/), como data URI."""
    import base64
    from pathlib import Path
    ruta = Path(__file__).parent / "assets" / "logo_startec.png"
    if not ruta.exists():
        return None
    return "data:image/png;base64," + base64.b64encode(ruta.read_bytes()).decode()


def cabecera(logo_uri=None, titulo=None, unidad=None, detalle=None):
    """Banda superior: logo, título de la sección y fecha. Usa el logo local si no se pasa otro."""
    logo_uri = logo_uri or logo_local()
    if logo_uri:
        bloque = f'<img class="logo" src="{logo_uri}" alt="{cfg.NOMBRE_EMPRESA}">'
    else:
        iniciales = (cfg.NOMBRE_EMPRESA.split() or ["ST"])[0][:2].upper()
        bloque = f'<div class="logo monograma">{iniciales}</div>'
    try:
        import reglas
        hoy = reglas.hoy()
    except Exception:
        from datetime import date
        hoy = date.today()
    meses = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
             "septiembre", "octubre", "noviembre", "diciembre"]
    fecha = f"{hoy.day} de {meses[hoy.month - 1]} de {hoy.year}"
    return f"""
    <div class="cabecera">
      {bloque}
      <div class="divisor"></div>
      <div class="textos">
        <span class="marca">{unidad or cfg.UNIDAD}</span>
        <h1>{titulo or cfg.TITULO_APP}</h1>
        <p class="empresa">{detalle or cfg.NOMBRE_EMPRESA}</p>
      </div>
      <div class="fecha">Hoy<br><b>{fecha}</b></div>
    </div>
    <div class="cabecera-franja"></div>"""


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
