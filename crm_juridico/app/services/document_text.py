"""Extracción de texto plano de PDF, DOCX y TXT para alimentar la IA."""
from pathlib import Path


def extract_text(path: str | Path, max_chars: int = 60_000) -> str:
    p = Path(path)
    ext = p.suffix.lower()
    text = ""
    try:
        if ext == ".pdf":
            text = _from_pdf(p)
        elif ext == ".docx":
            text = _from_docx(p)
        elif ext in (".txt", ".md", ".csv"):
            text = p.read_text(encoding="utf-8", errors="ignore")
        else:
            return f"[Tipo de archivo no soportado para extracción: {ext}]"
    except Exception as e:
        return f"[Error al extraer texto: {e}]"
    if len(text) > max_chars:
        text = text[:max_chars] + "\n\n[...documento truncado...]"
    return text


def _from_pdf(path: Path) -> str:
    from pypdf import PdfReader
    reader = PdfReader(str(path))
    parts = []
    for page in reader.pages:
        try:
            parts.append(page.extract_text() or "")
        except Exception:
            continue
    return "\n".join(parts)


def _from_docx(path: Path) -> str:
    import docx
    doc = docx.Document(str(path))
    return "\n".join(p.text for p in doc.paragraphs)
