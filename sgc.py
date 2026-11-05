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
