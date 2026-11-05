"""
Recordatorio de certificados por renovar.

Se ejecuta desde GitHub Actions, NO desde la aplicación web: Streamlit solo
corre código cuando alguien abre la página, así que un aviso programado no
puede vivir ahí dentro.

Reparto del correo
    · Cada supervisor recibe solo lo de los colaboradores a su cargo.
    · El administrador recibe el consolidado completo.
    · Los colaboradores inactivos quedan fuera de los avisos de vencimiento,
      pero se listan aparte cuando cumplen el plazo de retención.

Uso local:  python notificar.py --prueba     (calcula y muestra, sin enviar)
"""

import os
import sys
import json
import smtplib
from email.message import EmailMessage
from datetime import datetime

import gspread
from google.oauth2.service_account import Credentials

import ajustes as cfg
import reglas as r

ALCANCES = ["https://www.googleapis.com/auth/spreadsheets"]


# ==========================================================================================
# ENTORNO
# ==========================================================================================
def variable(nombre, obligatoria=True, defecto=""):
    valor = os.environ.get(nombre, defecto)
    if obligatoria and not valor:
        print(f"[ERROR] Falta la variable de entorno {nombre}")
        sys.exit(1)
    return valor


def libro():
    """Abre la hoja con la credencial de la cuenta de servicio."""
    credencial = json.loads(variable("GCP_SERVICE_ACCOUNT"))
    cliente = gspread.authorize(
        Credentials.from_service_account_info(credencial, scopes=ALCANCES))
    return cliente.open_by_key(os.environ.get("SHEET_ID") or cfg.SHEET_ID)


def leer(hoja):
    """Filas de una pestaña como lista de diccionarios, sin filas vacías."""
    valores = hoja.get_all_values()
    if len(valores) < 2:
        return []
    cabecera = valores[0]
    ancho = len(cabecera)
    filas = []
    for fila in valores[1:]:
        fila = (fila + [""] * ancho)[:ancho]
        if any(str(v).strip() for v in fila):
            filas.append(dict(zip(cabecera, fila)))
    return filas


# ==========================================================================================
# CÁLCULO
# ==========================================================================================
def recopilar():
    """
    Devuelve (avisos, purgas).

    `avisos` son los documentos vigentes de colaboradores activos cuyo plazo
    entra en el umbral configurado, ya vencidos incluidos. Se descartan los
    registros reemplazados: solo importa el documento actual de cada persona.
    """
    lb = libro()

    try:
        #  La cédula se indexa normalizada: Google Sheets guarda «0104567890»
        #  como número y le quita el cero, de modo que la ficha y el documento
        #  pueden no coincidir carácter a carácter.
        fichas = {r.clave_cedula(f.get("Cedula")): f
                  for f in leer(lb.worksheet(cfg.HOJA_COLABORADORES))}
    except gspread.WorksheetNotFound:
        fichas = {}
    correos, admins = {}, []
    try:
        for s in leer(lb.worksheet(cfg.HOJA_SUPERVISORES)):
            nombre = str(s.get("Nombre", "")).strip()
            correo = str(s.get("Correo", "")).strip()
            perfil = str(s.get("Rol", "")).strip().upper()
            #  Ante un nombre repetido gana la entrada que sí tiene correo.
            if nombre and (nombre not in correos or (not correos[nombre] and correo)):
                correos[nombre] = correo
            if correo and perfil == cfg.PERFIL_ADMIN.upper():
                admins.append(correo)
    except gspread.WorksheetNotFound:
        pass

    try:
        documentos = leer(lb.get_worksheet_by_id(int(cfg.SHEET_GID)))
    except Exception:
        documentos = leer(lb.worksheet(cfg.NOMBRE_HOJA))

    umbral = max(cfg.DIAS_AVISO)
    avisos = []
    conteo = {"total": len(documentos), "reemplazados": 0, "inactivos": 0,
              "sin_fecha": 0, "lejanos": 0}

    for doc in documentos:
        if str(doc.get("Vigencia_Registro", "ACTUAL")).strip().upper() == "REEMPLAZADO":
            conteo["reemplazados"] += 1
            continue

        cedula = str(doc.get("Cedula", "")).strip()
        ficha = fichas.get(r.clave_cedula(cedula), {})
        if str(ficha.get("Estado", cfg.ACTIVO)).strip().upper() == cfg.INACTIVO:
            conteo["inactivos"] += 1
            continue

        dias, estado = r.calcular_estado(doc.get("Fecha_Caducidad"),
                                         doc.get("Fecha_Revision"))
        if dias is None:
            conteo["sin_fecha"] += 1
            continue
        if dias > umbral:
            conteo["lejanos"] += 1
            continue

        supervisor = str(ficha.get("Supervisor", "")).strip()
        avisos.append({
            "cedula": r.cedula_visible(cedula),
            "nombre": ficha.get("Nombre") or doc.get("Nombre", ""),
            "rol": ficha.get("Rol") or doc.get("Rol", ""),
            "etiqueta": str(ficha.get("Etiqueta", "")).strip(),
            "supervisor": supervisor,
            "correo_supervisor": correos.get(supervisor, ""),
            "tipo": doc.get("Tipo_Documento", ""),
            "caducidad": doc.get("Fecha_Caducidad", ""),
            "revision": doc.get("Fecha_Revision", ""),
            "dias": dias,
            "estado": estado,
            "enlace": doc.get("Enlace_Drive", ""),
        })

    avisos.sort(key=lambda a: a["dias"])

    #  Resumen explícito: si no sale ningún correo, el registro debe decir por qué
    #  en lugar de dejar a alguien adivinando.
    print(f"Documentos leídos: {conteo['total']}")
    print(f"  descartados por ser versión reemplazada : {conteo['reemplazados']}")
    print(f"  descartados por colaborador inactivo    : {conteo['inactivos']}")
    print(f"  descartados por no tener fecha          : {conteo['sin_fecha']}")
    print(f"  vigentes más allá de {umbral} días          : {conteo['lejanos']}")
    print(f"  dentro del umbral de aviso              : {len(avisos)}")
    print(f"Fichas de colaboradores: {len(fichas)} · supervisores con correo: "
          f"{len([c for c in correos.values() if c])} · administradores: {len(admins)}")
    sin_sup = [a["nombre"] for a in avisos if not a["correo_supervisor"]]
    if sin_sup:
        print(f"  sin supervisor con correo: {', '.join(sorted(set(sin_sup)))}")

    purgas = [f for f in fichas.values()
              if str(f.get("Estado", "")).strip().upper() == cfg.INACTIVO
              and r.requiere_purga(f.get("Fecha_Inactivacion"))]

    return avisos, purgas, sorted(set(admins))


# ==========================================================================================
# CORREO
# ==========================================================================================
ESTILO = """
  body{font-family:Inter,Arial,sans-serif;color:#0E2733;background:#EEF1F3;margin:0;padding:24px}
  .caja{background:#fff;border:1px solid #DAE1E6;max-width:760px;margin:0 auto}
  .cab{background:#0E2733;border-left:5px solid #A8802B;padding:20px 24px}
  .cab h1{color:#fff;font-size:19px;margin:0}
  .cab span{color:#A8802B;font-size:10px;letter-spacing:.2em;text-transform:uppercase}
  .cuerpo{padding:20px 24px}
  table{border-collapse:collapse;width:100%;font-size:13px}
  th{background:#274B5C;color:#fff;text-align:left;padding:8px;font-size:11px;
     text-transform:uppercase;letter-spacing:.05em}
  td{padding:8px;border-bottom:1px solid #E4EBEF}
  .v{color:#9C2B24;font-weight:600}.e{color:#B4770B;font-weight:600}
  .pie{font-size:11px;color:#6B818D;padding:0 24px 20px}
"""


def tabla_html(avisos):
    filas = []
    for a in avisos:
        clase = "v" if a["dias"] <= 0 else "e"
        plazo = "Vencido" if a["dias"] <= 0 else f'{a["dias"]} días'
        marca = f' <small>({cfg.ETIQUETA_ESPECIAL})</small>' if a["etiqueta"] else ""
        fecha = a["revision"] if (a["revision"] and a["estado"] == cfg.ESTADO_REVISION) \
            else a["caducidad"]
        enlace = (f'<a href="{a["enlace"]}">Abrir</a>' if a["enlace"].startswith("http")
                  else "—")
        filas.append(
            f'<tr><td>{a["nombre"]}{marca}<br><small>{a["cedula"]}</small></td>'
            f'<td>{a["tipo"]}</td><td>{fecha}</td>'
            f'<td class="{clase}">{plazo}</td><td>{a["estado"]}</td><td>{enlace}</td></tr>')
    return ("<table><tr><th>Colaborador</th><th>Documento</th><th>Fecha límite</th>"
            "<th>Plazo</th><th>Estado</th><th>Archivo</th></tr>"
            + "".join(filas) + "</table>")


def cuerpo_html(titulo, intro, avisos, purgas=None):
    partes = [f'<div class="cuerpo"><p>{intro}</p>{tabla_html(avisos)}</div>']
    if purgas:
        filas = "".join(
            f'<tr><td>{p.get("Nombre","")}</td><td>{p.get("Cedula","")}</td>'
            f'<td>{p.get("Fecha_Inactivacion","")}</td></tr>' for p in purgas)
        partes.append(
            '<div class="cuerpo"><p><strong>Colaboradores inactivos con más de un año.'
            '</strong> Revisa si corresponde depurar su expediente. El sistema no borra '
            'nada por su cuenta.</p><table><tr><th>Nombre</th><th>Cédula</th>'
            f'<th>Inactivo desde</th></tr>{filas}</table></div>')

    return (f'<html><head><meta charset="utf-8"><style>{ESTILO}</style></head><body>'
            f'<div class="caja"><div class="cab"><span>{cfg.UNIDAD}</span>'
            f'<h1>{titulo}</h1></div>{"".join(partes)}'
            f'<p class="pie">{cfg.NOMBRE_EMPRESA} · Generado el '
            f'{r.ahora().strftime("%d-%m-%Y %H:%M")}. Mensaje automático.</p>'
            f'</div></body></html>')


def enviar(destino, asunto, html):
    """Envía por SMTP. Con Gmail o Workspace hace falta una contraseña de aplicación."""
    #  GitHub Actions entrega como texto VACÍO los secretos que no existen, así que
    #  el valor por defecto de os.environ.get() nunca se aplicaba e int("") fallaba
    #  en cada envío. Con «or» el respaldo funciona aunque el secreto no esté creado.
    servidor = os.environ.get("SMTP_HOST", "").strip() or "smtp.gmail.com"
    puerto = int(os.environ.get("SMTP_PORT", "").strip() or "587")
    usuario = variable("SMTP_USER").strip()
    clave = variable("SMTP_PASSWORD").replace(" ", "")   # la contraseña de aplicación se copia con espacios

    mensaje = EmailMessage()
    mensaje["Subject"] = asunto
    mensaje["From"] = f"{cfg.NOMBRE_EMPRESA} <{usuario}>"
    mensaje["To"] = destino
    mensaje.set_content("Este recordatorio requiere un lector de correo con HTML.")
    mensaje.add_alternative(html, subtype="html")

    if puerto == 465:                       # SSL directo (algunos proveedores)
        with smtplib.SMTP_SSL(servidor, puerto, timeout=30) as smtp:
            smtp.login(usuario, clave)
            smtp.send_message(mensaje)
        return
    with smtplib.SMTP(servidor, puerto, timeout=30) as smtp:
        smtp.starttls()
        smtp.login(usuario, clave)
        smtp.send_message(mensaje)


# ==========================================================================================
# EJECUCIÓN
# ==========================================================================================
def main():
    prueba = "--prueba" in sys.argv
    avisos, purgas, admins = recopilar()

    print(f"Documentos por renovar: {len(avisos)} · "
          f"Inactivos para depurar: {len(purgas)}")

    if not avisos and not purgas:
        print("Sin novedades. No se envía correo.")
        return

    # Un correo por supervisor, solo con su gente
    por_supervisor = {}
    for a in avisos:
        if a["correo_supervisor"]:
            por_supervisor.setdefault(a["correo_supervisor"], []).append(a)

    if prueba:
        for a in avisos:
            print(f"  {a['dias']:>5}d  {a['nombre']:<22} {a['tipo']:<34} "
                  f"{a['estado']}  → {a['supervisor'] or 'sin supervisor'}")
        for correo, lista in por_supervisor.items():
            print(f"  [correo] {correo}: {len(lista)} documento(s)")
        for a in (admins or ["(sin administrador en la hoja)"]):
            print(f"  [correo] administrador {a}: {len(avisos)} documento(s), "
                  f"{len(purgas)} purga(s)")
        return

    asunto = cfg.ASUNTO_RECORDATORIO.format(empresa=cfg.NOMBRE_EMPRESA)
    enviados = 0

    for correo, lista in por_supervisor.items():
        try:
            enviar(correo, asunto, cuerpo_html(
                "Certificados por renovar",
                f"Tienes {len(lista)} documento(s) que requieren gestión en tu equipo.",
                lista))
            enviados += 1
            print(f"  Enviado a {correo} ({len(lista)} documentos)")
        except Exception as e:
            print(f"  [ERROR] {correo}: {e}")

    #  Los administradores se definen en la hoja; la variable de entorno queda
    #  como respaldo para no depender de que alguien la haya configurado.
    destinos_admin = admins or [variable("CORREO_ADMIN")]
    respaldo = os.environ.get("CORREO_ADMIN", "").strip()
    if respaldo and respaldo not in destinos_admin:
        destinos_admin.append(respaldo)
    sin_supervisor = [a for a in avisos if not a["correo_supervisor"]]
    intro = f"Consolidado general: {len(avisos)} documento(s) por gestionar."
    if sin_supervisor:
        intro += (f" {len(sin_supervisor)} sin supervisor asignado: solo aparecen "
                  f"en este correo.")
    cuerpo = cuerpo_html("Consolidado de cumplimiento documental", intro, avisos, purgas)
    fallos = 0
    for destino in destinos_admin:
        try:
            enviar(destino, asunto, cuerpo)
            enviados += 1
            print(f"  Enviado al administrador {destino}")
        except Exception as e:
            fallos += 1
            print(f"  [ERROR] administrador {destino}: {e}")
    if fallos == len(destinos_admin):
        sys.exit(1)

    print(f"Correos enviados: {enviados}")


if __name__ == "__main__":
    main()
