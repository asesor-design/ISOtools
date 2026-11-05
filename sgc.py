"""Carga y relaciones de los documentos del SGC.

Cada documento es un archivo Markdown en ``documentos/`` con un encabezado
(front matter) entre líneas ``---``. Este módulo lo lee, arma el árbol de
relaciones, extrae los registros y resuelve los códigos citados.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path

DOCS_DIR = Path(__file__).parent / "documentos"
DRIVE_FOLDER = "https://drive.google.com/drive/folders/1_NRypfzbhWwKJAxRqxEC0ZfAfCGE7hA0"

# Patrón de código: MACRO-PROCESO-(SUBPROCESO)-TIPO-SECUENCIAL
CODE_RE = re.compile(r"\b(?:EST|MIS|APO)-[A-Z]{3}(?:-[A-Z]{3}){0,2}-\d{3}\b")

MACROS = {"EST": "Estratégico", "MIS": "Misional", "APO": "Apoyo"}
PROCS = {
    "SGC": "Sistema de Gestión de Calidad",
    "DIR": "Dirección y Gobierno",
    "OPS": "Operaciones y Servicios",
    "COM": "Compras y Contratación",
    "ADM": "Administración",
    "FIN": "Finanzas y Contabilidad",
    "THU": "Talento Humano",
}
PROC_MACRO = {"SGC": "EST", "DIR": "EST", "OPS": "MIS", "COM": "APO", "ADM": "APO", "FIN": "APO", "THU": "APO"}
SUBS = {
    "DOC": "Información documentada", "NCF": "No conformidades", "AUD": "Auditoría interna",
    "RIE": "Riesgos y oportunidades", "PLA": "Planificación / revisión por la dirección",
    "GOB": "Gobierno y ética", "RSE": "Responsabilidad social", "REP": "Reputación corporativa",
    "EJE": "Ejecución del servicio", "CHK": "Checklist previo", "ENT": "Entrega al cliente",
    "EVP": "Evaluación de proveedores", "COT": "Cotización", "PRE": "Presupuesto",
    "CTB": "Contabilidad y registro", "TES": "Tesorería", "FAD": "Facturación",
    "SEL": "Selección", "IND": "Inducción", "CAP": "Capacitación",
    "EVD": "Evaluación del desempeño", "CER": "Certificados", "GDR": "Documentos habilitantes",
    "RDO": "Recepción de documentos", "CLA": "Clasificación y archivo",
}
TYPES = {
    "POL": ("Política", "Declara compromisos y reglas de alto nivel. Aprueba el Representante Legal."),
    "MAN": ("Manual", "Reúne las políticas de un proceso con su responsable y cláusula ISO."),
    "PRO": ("Procedimiento", "Paso a paso de una actividad: quién la hace y qué registros deja."),
    "INS": ("Instructivo", "Instrucciones detalladas de una herramienta o tarea puntual."),
    "MAT": ("Matriz", "Tabla de análisis o referencia cruzada (riesgos, habilitantes por cargo)."),
    "REG": ("Registro", "Evidencia de que algo se hizo; se llena y se archiva."),
    "FOR": ("Formato", "Plantilla en blanco que se llena para generar un registro."),
}
TYPE_ORDER = list(TYPES)
MACRO_ORDER = list(MACROS)


@dataclass
class Doc:
    codigo: str
    titulo: str
    version: str
    fecha: str
    drive: str
    formato: str
    dueno: str
    padre: str
    relacion: str
    revision: str
    resumen: str
    body: str
    macro: str = ""
    proc: str = ""
    sub: str = ""
    tipo: str = ""
    seq: str = ""
    path: Path | None = None
    hijos: list[str] = field(default_factory=list)

    @property
    def drive_url(self) -> str:
        return f"https://drive.google.com/file/d/{self.drive}/view" if self.drive else DRIVE_FOLDER

    @property
    def tipo_nombre(self) -> str:
        return TYPES.get(self.tipo, (self.tipo,))[0]


@dataclass
class Registro:
    codigo: str
    nombre: str
    responsable: str
    retencion: str
    origen: list[str]


def parse_code(code: str) -> dict:
    parts = code.split("-")
    seq, tipo = parts.pop(), parts.pop()
    return {"macro": parts[0], "proc": parts[1], "sub": parts[2] if len(parts) > 2 else "", "tipo": tipo, "seq": seq}


def norm(text: str) -> str:
    """Minúsculas y sin tildes, para buscar."""
    text = unicodedata.normalize("NFD", str(text).lower())
    return "".join(c for c in text if unicodedata.category(c) != "Mn")


def _read(path: Path) -> Doc:
    raw = path.read_text(encoding="utf-8")
    _, head, body = raw.split("---\n", 2)
    meta = {}
    for line in head.strip().splitlines():
        key, _, value = line.partition(":")
        meta[key.strip()] = value.strip()
    body = body.strip()
    body = re.sub(r"^# .*\n+", "", body)  # el título ya va en la carátula
    doc = Doc(
        codigo=meta["codigo"], titulo=meta.get("titulo", ""), version=meta.get("version", ""),
        fecha=meta.get("fecha", ""), drive=meta.get("drive", ""), formato=meta.get("formato", ""),
        dueno=meta.get("dueno", ""), padre=meta.get("padre", ""), relacion=meta.get("relacion", ""),
        revision=meta.get("revision", ""), resumen=meta.get("resumen", ""), body=body, path=path,
    )
    for k, v in parse_code(doc.codigo).items():
        setattr(doc, k, v)
    return doc


def _tables(body: str):
    """Devuelve (encabezado, filas) de cada tabla Markdown del texto."""
    lines = body.splitlines()
    i = 0
    while i < len(lines):
        if lines[i].startswith("|"):
            block = []
            while i < len(lines) and lines[i].startswith("|"):
                block.append([c.strip() for c in lines[i].strip().strip("|").split("|")])
                i += 1
            yield block[0], block[2:]
        else:
            i += 1


class Repositorio:
    def __init__(self, folder: Path = DOCS_DIR):
        self.docs: dict[str, Doc] = {}
        for path in sorted(folder.glob("*.md")):
            d = _read(path)
            self.docs[d.codigo] = d
        for d in self.docs.values():
            if d.padre in self.docs:
                self.docs[d.padre].hijos.append(d.codigo)

        self.registros: dict[str, Registro] = {}
        for d in self.docs.values():
            for head, rows in _tables(d.body):
                if not head or head[0] != "Código del registro":
                    continue
                for cells in rows:
                    row = dict(zip(head, cells))
                    resp = row.get("Responsable del archivo") or f"Gestión y Control ({row.get('Soporte', '')})"
                    reg = self.registros.setdefault(
                        cells[0], Registro(cells[0], cells[1], resp, cells[-1], []))
                    if d.codigo not in reg.origen:
                        reg.origen.append(d.codigo)

        self.citas: dict[str, list[str]] = {}
        for d in self.docs.values():
            for c in sorted(set(CODE_RE.findall(d.body))):
                if c != d.codigo:
                    self.citas.setdefault(c, []).append(d.codigo)

    # --- consultas -------------------------------------------------------
    def ordenados(self) -> list[Doc]:
        return sorted(self.docs.values(), key=lambda d: (MACRO_ORDER.index(d.macro), d.codigo))

    def raices(self, macro: str) -> list[Doc]:
        """Documentos de primer nivel bajo la Política de Calidad para un macroproceso."""
        return [d for d in self.ordenados()
                if d.macro == macro and d.codigo != "EST-SGC-POL-001"
                and (d.padre == "EST-SGC-POL-001" or d.padre not in self.docs)]

    def codigos_conocidos(self) -> set[str]:
        return set(self.docs) | set(self.registros) | set(self.citas)

    def sin_archivo(self) -> list[str]:
        """Códigos citados que no son documento ni registro declarado."""
        return sorted(c for c in self.citas if c not in self.docs and c not in self.registros)

    def siguiente_codigo(self, proc: str, sub: str, tipo: str) -> tuple[str, int]:
        prefix = "-".join(p for p in (PROC_MACRO[proc], proc, sub, tipo) if p) + "-"
        usados = [int(c[-3:]) for c in self.codigos_conocidos() if c.startswith(prefix) and c.count("-") == prefix.count("-")]
        return f"{prefix}{(max(usados) if usados else 0) + 1:03d}", len(usados)

    def buscar(self, texto: str, limite: int = 15) -> list[tuple[Doc, str]]:
        palabras = norm(texto).split()
        if not palabras:
            return []
        hits = []
        for d in self.docs.values():
            plano = re.sub(r"[|*#]", " ", d.body)
            campos = (norm(d.codigo), norm(d.titulo), norm(d.resumen), norm(plano))
            score = 0
            for w in palabras:
                for peso, campo in zip((50, 20, 8, 2), campos):
                    if w in campo:
                        score += peso
                        break
                else:
                    score = -1
                    break
            if score > 0:
                plano = re.sub(r"\s+", " ", plano)
                i = norm(plano).find(palabras[0])
                snip = ("…" if i > 50 else "") + plano[max(0, i - 50): i + 110] + "…" if i >= 0 else d.resumen
                hits.append((score, d, snip))
        hits.sort(key=lambda h: -h[0])
        return [(d, s) for _, d, s in hits[:limite]]


def descifrar(code: str, repo: Repositorio) -> tuple[list[dict], str]:
    """Explica cada parte de un código y si existe en el sistema."""
    code = code.strip().upper()
    parts = [p for p in code.split("-") if p]
    if len(parts) not in (4, 5):
        return [], "Un código tiene 4 o 5 partes separadas por guiones, por ejemplo EST-SGC-POL-001 o MIS-OPS-EJE-PRO-001."
    m, pr, seq, t = parts[0], parts[1], parts[-1], parts[-2]
    sub = parts[2] if len(parts) == 5 else ""
    segs = [
        {"parte": "Macroproceso", "valor": m, "significado": MACROS.get(m, "No existe. Use EST, MIS o APO."), "ok": m in MACROS},
        {"parte": "Proceso", "valor": pr,
         "significado": (PROCS[pr] + ("" if PROC_MACRO[pr] == m else f" (pertenece a {PROC_MACRO[pr]})")) if pr in PROCS else "Proceso no registrado.",
         "ok": pr in PROCS and PROC_MACRO.get(pr) == m},
    ]
    if sub:
        segs.append({"parte": "Subproceso", "valor": sub, "significado": SUBS.get(sub, "Subproceso nuevo (válido si tiene 3 letras)."), "ok": bool(re.fullmatch(r"[A-Z]{3}", sub))})
    segs.append({"parte": "Tipo", "valor": t, "significado": TYPES[t][0] if t in TYPES else "Tipo no válido. Use POL, MAN, PRO, INS, MAT, REG o FOR.", "ok": t in TYPES})
    segs.append({"parte": "Secuencial", "valor": seq, "significado": "Número de orden" if re.fullmatch(r"\d{3}", seq) else "Debe tener 3 dígitos (001).", "ok": bool(re.fullmatch(r"\d{3}", seq))})

    full = "-".join(parts)
    if full in repo.docs:
        veredicto = f"Existe en el repositorio: {repo.docs[full].titulo} (versión {repo.docs[full].version})."
    elif not all(s["ok"] for s in segs):
        veredicto = "Revise las partes marcadas con ✗."
        if full in repo.citas:
            veredicto += " Este código está citado en " + ", ".join(repo.citas[full]) + " y conviene corregirlo allí."
    elif full in repo.registros:
        veredicto = "Es un registro que se genera al aplicar " + ", ".join(repo.registros[full].origen) + ". Vea la sección Registros."
    elif full in repo.citas:
        veredicto = "Está citado en " + ", ".join(repo.citas[full]) + ", pero no tiene archivo propio."
    else:
        veredicto = "Código bien formado y disponible: aún no lo usa ningún documento."
    return segs, veredicto


# ==========================================================================================
# ANÁLISIS TRANSVERSAL: tablas, riesgos, indicadores, calendario y responsabilidades
# ==========================================================================================
def tablas_con_seccion(doc: Doc):
    """Cada tabla del documento con el título (##) de la sección donde está."""
    seccion, sub, salida = "", "", []
    lines = doc.body.splitlines()
    i = 0
    while i < len(lines):
        ln = lines[i]
        if ln.startswith("## "):
            seccion, sub = ln[3:].strip(), ""
        elif ln.startswith("### "):
            sub = ln[4:].strip()
        if ln.startswith("|"):
            block = []
            while i < len(lines) and lines[i].startswith("|"):
                block.append([c.strip() for c in lines[i].strip().strip("|").split("|")])
                i += 1
            head = block[0]
            filas = [dict(zip(head, r)) for r in block[2:]]
            salida.append((seccion, sub, head, filas))
            continue
        i += 1
    return salida


NIVEL_ORDEN = {"ALTO": 0, "MEDIO": 1, "BAJO": 2}


def riesgos(repo: "Repositorio") -> list[dict]:
    """
    Riesgos de la matriz unificada (EST-SGC-RIE-MAT-001) más los que declara cada
    procedimiento en su sección «Matriz de riesgos y controles asociados».
    """
    salida = []
    mat = repo.docs.get("EST-SGC-RIE-MAT-001")
    if mat:
        for seccion, _, head, filas in tablas_con_seccion(mat):
            if "P × I" not in head:
                continue
            nombre = re.sub(r"\s*\(.*\)$", "", seccion)
            for f in filas:
                m = re.match(r"(\d+)\s*×\s*(\d+)\s*=\s*(\d+)", f["P × I"])
                p, i, pxi = (int(x) for x in m.groups()) if m else (None, None, None)
                salida.append({
                    "Proceso": nombre, "Etapa": f["Etapa"], "Riesgo": f["Riesgo identificado"],
                    "Tipo": f["Tipo"], "P": p, "I": i, "PxI": pxi, "Nivel": f["Nivel"],
                    "Control": f["Control / prevención"], "Ejecutor": f["Ejecutor"],
                    "Frecuencia": f["Frecuencia"], "Fuente": mat.codigo})
    for d in repo.ordenados():
        if d.codigo == "EST-SGC-RIE-MAT-001":
            continue
        for seccion, _, head, filas in tablas_con_seccion(d):
            if not seccion.lower().startswith("matriz de riesgos"):
                continue
            for f in filas:
                nivel = (f.get("Nivel") or f.get("Nivel inherente") or "").split(" ")[0]
                salida.append({
                    "Proceso": PROCS.get(d.proc, d.proc), "Etapa": d.titulo,
                    "Riesgo": f.get("Riesgo identificado", ""), "Tipo": "",
                    "P": None, "I": None, "PxI": None, "Nivel": nivel,
                    "Control": f.get("Control aplicado") or f.get("Medida de control (automatizada)", ""),
                    "Ejecutor": f.get("Ejecutor", d.dueno), "Frecuencia": "",
                    "Fuente": d.codigo})
    return salida


def indicadores(repo: "Repositorio") -> list[dict]:
    """Indicadores declarados en la sección «Indicadores de gestión» de cada documento."""
    salida = []
    for d in repo.ordenados():
        dentro = False
        for ln in d.body.splitlines():
            if ln.startswith("## "):
                dentro = ln[3:].lower().startswith("indicadores")
                continue
            if dentro and ln.startswith("- **"):
                m = re.match(r"- \*\*(.+?):?\*\*:?\s*(.*)", ln)
                if not m:
                    continue
                nombre, resto = m.group(1).rstrip(":"), m.group(2)
                meta = ""
                mm = re.search(r"Meta:\s*([^.]+(?:\.\d+)?)\.?\s*$", resto)
                if mm:
                    meta = mm.group(1).strip()
                    resto = resto[:mm.start()].strip()
                salida.append({"Documento": d.codigo, "Indicador": nombre,
                               "Cálculo": resto.rstrip("."), "Meta": meta or "—",
                               "Responsable": d.dueno})
            elif ln.startswith("**Indicador de gestión:**"):
                texto = ln.split(":**", 1)[1].strip()
                meta = re.search(r"meta ([^)]+)", texto)
                salida.append({"Documento": d.codigo, "Indicador": texto.split("(")[0].strip().capitalize(),
                               "Cálculo": texto, "Meta": meta.group(1) if meta else "—",
                               "Responsable": d.dueno})
    return salida


def meses_revision(doc: Doc) -> int:
    """Frecuencia de revisión en meses según el propio documento (o 24 por defecto, DOC-PRO 5.6)."""
    texto = norm(doc.revision)
    if texto.startswith("anual"):
        return 12
    if "permanente" in texto:
        return 0
    m = re.search(r"cada (\d+) anos", texto)
    return int(m.group(1)) * 12 if m else 24


def calendario_revision(repo: "Repositorio", hoy) -> list[dict]:
    """Próxima revisión de cada documento a partir de su fecha y su frecuencia."""
    from datetime import datetime
    salida = []
    for d in repo.ordenados():
        meses = meses_revision(d)
        fecha = None
        if d.fecha:
            try:
                fecha = datetime.strptime(d.fecha, "%d/%m/%Y").date()
            except ValueError:
                fecha = None
        if meses == 0:
            prox, estado = None, "Se actualiza con cada uso"
        elif not fecha:
            prox, estado = None, "Sin fecha de aprobación"
        else:
            y, m = divmod(fecha.month - 1 + meses, 12)
            import calendar
            dia = min(fecha.day, calendar.monthrange(fecha.year + y, m + 1)[1])
            prox = fecha.replace(year=fecha.year + y, month=m + 1, day=dia)
            faltan = (prox - hoy).days
            estado = "Vencida" if faltan < 0 else ("Próxima (≤ 60 días)" if faltan <= 60 else "Al día")
        salida.append({"Código": d.codigo, "Documento": d.titulo, "Versión": d.version,
                       "Aprobado": fecha, "Frecuencia": d.revision, "Próxima revisión": prox,
                       "Estado": estado, "Dueño": d.dueno})
    return salida


# Cargos del organigrama (EST-SGC-MAN-001, sección 8) y cómo aparecen escritos en los documentos
CARGOS = {
    "Representante Legal": ["representante legal"],
    "Gerencia General": ["gerencia general", "gerente general"],
    "Jefa de Operaciones": ["jefa de operaciones"],
    "Supervisor de campo": ["supervisor de campo", "supervisores de campo"],
    "Técnicos de campo": ["tecnicos de campo", "tecnico de campo", "personal operativo"],
    "Contabilidad": ["contabilidad"],
    "Gestión y Control": ["gestion y control"],
}
TODOS = ["todo el personal", "dueno del proceso", "duenos de cada proceso", "colaboradores"]


def _menciona(texto: str, claves: list[str]) -> bool:
    t = norm(texto)
    return any(k in t for k in claves)


def responsabilidades(repo: "Repositorio", cargo: str) -> dict:
    """Todo lo que el sistema le asigna a un cargo, leído de los propios documentos."""
    claves = CARGOS[cargo]
    out = {"rol": "", "politicas": [], "tareas": [], "registros": [], "riesgos": [], "habilitantes": {},
           "todos": []}
    man = repo.docs.get("EST-SGC-MAN-001")
    if man:
        for _, _, head, filas in tablas_con_seccion(man):
            if head and head[0] == "Cargo real":
                for f in filas:
                    if norm(f["Cargo real"]) == norm(cargo):
                        out["rol"] = f["Rol dentro del SGC"]
    for d in repo.ordenados():
        # Políticas con responsable nombrado (manuales) y tablas de responsabilidades (políticas)
        for seccion, _, head, filas in tablas_con_seccion(d):
            if "Responsable" in head and ("Política" in head or "Responsabilidad" in head):
                for f in filas:
                    texto = f.get("Política") or f.get("Responsabilidad")
                    fila = {"Documento": d.codigo, "Qué": texto, "Cláusula": f.get("Cláusula", "")}
                    if _menciona(f["Responsable"], claves):
                        out["politicas"].append(fila)
                    elif _menciona(f["Responsable"], TODOS):
                        out["todos"].append(fila)
        # Responsables de procedimientos: «- **Cargo:** tarea»
        dentro = False
        for ln in d.body.splitlines():
            if ln.startswith("## "):
                dentro = norm(ln[3:]).startswith("responsable")
                continue
            m = re.match(r"- \*\*(.+?):\*\*\s*(.*)", ln) if dentro else None
            if m and _menciona(m.group(1), claves):
                out["tareas"].append({"Documento": d.codigo, "Qué": m.group(2)})
            elif m and _menciona(m.group(1), TODOS):
                out["todos"].append({"Documento": d.codigo, "Qué": m.group(2), "Cláusula": ""})
    for r in repo.registros.values():
        if _menciona(r.responsable, claves):
            out["registros"].append(r)
    out["riesgos"] = [x for x in riesgos(repo) if _menciona(x["Ejecutor"], claves)]
    gdr = repo.docs.get("APO-THU-GDR-MAT-001")
    if gdr:
        for _, _, head, filas in tablas_con_seccion(gdr):
            for f in filas:
                if norm(f.get("Cargo", "")) == norm(cargo):
                    out["habilitantes"] = {k: v for k, v in f.items() if k != "Cargo"}
    # quitar duplicados de «todo el personal»
    vistos, unicos = set(), []
    for f in out["todos"]:
        k = (f["Documento"], f["Qué"])
        if k not in vistos:
            vistos.add(k)
            unicos.append(f)
    out["todos"] = unicos
    return out


# ==========================================================================================
# APRENDIZAJE: ISO 9001 en STARTEC, glosario y pasos de cada procedimiento
# ==========================================================================================
CAPITULOS = {
    "4": ("Contexto de la organización", "Planificar",
          "Entender dónde estamos: qué nos afecta, quién espera algo de nosotros y qué abarca el sistema."),
    "5": ("Liderazgo", "Planificar",
          "La dirección se compromete, fija la política de calidad y asigna quién responde por qué."),
    "6": ("Planificación", "Planificar",
          "Pensar antes de actuar: identificar riesgos y oportunidades y fijar objetivos medibles."),
    "7": ("Apoyo", "Hacer",
          "Tener lo necesario: personas competentes, recursos, comunicación y documentos bajo control."),
    "8": ("Operación", "Hacer",
          "Hacer el trabajo como se planificó: de la solicitud del cliente a la entrega, con proveedores controlados."),
    "9": ("Evaluación del desempeño", "Verificar",
          "Comprobar si funciona: medir indicadores, auditar y revisar el sistema con la dirección."),
    "10": ("Mejora", "Actuar",
           "Corregir lo que falló atacando la causa y mejorar de forma continua."),
}
CICLO = {
    "Planificar": ("4, 5 y 6", "Definir qué queremos lograr y cómo."),
    "Hacer": ("7 y 8", "Ejecutar lo planificado con los recursos adecuados."),
    "Verificar": ("9", "Medir y revisar los resultados."),
    "Actuar": ("10", "Corregir y mejorar."),
}
# Cláusulas que un documento cubre por su contenido aunque no las cite con número
CLAUSULAS_IMPLICITAS = {
    "EST-SGC-MAN-001": ["4.1", "4.2", "4.3", "4.4", "5.3"],
    "EST-SGC-POL-001": ["5.1", "5.2"],
    "EST-SGC-RIE-MAT-001": ["6.1"],
    "EST-DIR-PLA-REG-001": ["9.3"],
    "APO-THU-CER-INS-001": ["7.2"],
    "APO-THU-GDR-MAT-001": ["7.2"],
    "MIS-OPS-CHK-FOR-001": ["8.1", "8.5.1"],
    "APO-COM-EVP-FOR-001": ["8.4"],
    "APO-COM-EVP-REG-001": ["8.4"],
    "APO-THU-CAP-REG-001": ["7.2"],
}
_CLAUSULA_RE = re.compile(r"\b(10|[4-9])\.(\d)(?:\.(\d))?\b")


def clausulas(repo: "Repositorio") -> dict[str, dict[str, set[str]]]:
    """capítulo → {código de documento → cláusulas que cubre}."""
    out: dict[str, dict[str, set[str]]] = {c: {} for c in CAPITULOS}

    def agregar(cap, doc, cl):
        out.setdefault(cap, {}).setdefault(doc, set()).add(cl)

    for d in repo.docs.values():
        texto = d.body
        for seccion, _, head, filas in tablas_con_seccion(d):
            if "Cláusula" in head:
                texto += " " + " ".join(f.get("Cláusula", "") for f in filas)
        # solo números que aparecen junto a la palabra cláusula o en columnas Cláusula
        candidatos = re.findall(r"(?:cl[aá]usulas?|ISO 9001)(?:[^.\n]|\.\d){0,50}", texto, flags=re.I)
        for seccion, _, head, filas in tablas_con_seccion(d):
            if "Cláusula" in head:
                candidatos += [f.get("Cláusula", "") for f in filas]
        for frag in candidatos:
            for m in _CLAUSULA_RE.finditer(frag):
                cl = ".".join(x for x in m.groups() if x)
                agregar(m.group(1), d.codigo, cl)
        for cl in CLAUSULAS_IMPLICITAS.get(d.codigo, []):
            agregar(cl.split(".")[0], d.codigo, cl)
    return out


GLOSARIO_BASE = {
    "Sistema de Gestión de Calidad (SGC)": "Conjunto de políticas, procesos, documentos y responsables con que STARTEC asegura que sus servicios cumplen lo que el cliente necesita.",
    "ISO 9001:2015": "Norma internacional que define los requisitos de un sistema de gestión de calidad. Es la base de la certificación.",
    "Ciclo PHVA": "Planificar, Hacer, Verificar y Actuar. Es la lógica de mejora continua sobre la que está construida la norma.",
    "Información documentada": "Todo documento o registro que el sistema debe controlar: políticas, manuales, procedimientos, formatos y evidencias.",
    "Registro": "Evidencia de que algo se hizo (un checklist firmado, un acta, una evaluación). Se archiva y no se modifica.",
    "Formato": "Plantilla en blanco que, al llenarse, se convierte en registro.",
    "Procedimiento": "Documento que explica paso a paso cómo se hace una actividad, quién la hace y qué evidencia deja.",
    "Auditoría interna": "Revisión planificada e imparcial para comprobar si el sistema se cumple y funciona.",
    "Hallazgo": "Resultado de una auditoría. Puede ser una no conformidad, una observación o una oportunidad de mejora.",
    "Revisión por la dirección": "Reunión, al menos anual, en la que la alta dirección evalúa el sistema y decide mejoras y recursos.",
    "Riesgo": "Efecto de la incertidumbre sobre un resultado esperado. Se califica por probabilidad e impacto.",
    "Causa raíz": "Motivo de fondo de un problema. Se busca, por ejemplo, con la técnica de los cinco porqués.",
    "Copia no controlada": "Cualquier copia impresa o descargada de un documento. Pierde validez frente a la versión digital vigente.",
    "Documento habilitante": "Certificado cuya vigencia condiciona que una persona pueda ejecutar una tarea (alturas, riesgo eléctrico, médico).",
    "Dueño del proceso": "Cargo que responde por que un proceso se cumpla y mejore.",
    "EPP": "Equipo de protección personal: casco, guantes, gafas, calzado, arnés, entre otros.",
    "LOTO": "Bloqueo y etiquetado de fuentes de energía antes de intervenir un equipo eléctrico.",
}


def glosario(repo: "Repositorio") -> list[dict]:
    """Términos definidos en los vocabularios de los manuales más los términos base del SGC."""
    vistos: dict[str, dict] = {}
    for t, dfn in GLOSARIO_BASE.items():
        vistos[norm(t)] = {"Término": t, "Definición": dfn, "Fuente": "ISOtools"}
    for d in repo.ordenados():
        for seccion, _, head, filas in tablas_con_seccion(d):
            if head[:2] == ["Término", "Definición"]:
                for f in filas:
                    k = norm(f["Término"])
                    if k not in vistos or vistos[k]["Fuente"] == "ISOtools":
                        vistos[k] = {"Término": f["Término"], "Definición": f["Definición"], "Fuente": d.codigo}
    return sorted(vistos.values(), key=lambda x: norm(x["Término"]))


def pasos(doc: Doc) -> list[str]:
    """Títulos de los pasos (###) dentro de la sección de descripción o instrucciones."""
    salida, dentro = [], False
    for ln in doc.body.splitlines():
        if ln.startswith("## "):
            dentro = norm(ln[3:]).startswith(("descripcion", "instrucciones", "verificacion previa"))
            continue
        if dentro and ln.startswith("### "):
            salida.append(re.sub(r"^\d+(\.\d+)*\.?\s*", "", ln[4:]).strip())
    return salida
