from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path

from app.config import DOCS_DIR
from app.database.db import execute, fetch_all, fetch_one


def _client_dir(client_id: int) -> Path:
    d = DOCS_DIR / str(client_id)
    d.mkdir(parents=True, exist_ok=True)
    return d


def list_documents_by_client(client_id: int) -> list:
    return fetch_all(
        "SELECT d.id, d.nombre, d.ruta_archivo, d.enlace, d.tipo_mime, "
        "d.tamano_bytes, d.fecha_subida, d.fecha_doc, d.descripcion, d.case_id, "
        "c.titulo AS caso "
        "FROM documents d LEFT JOIN cases c ON c.id = d.case_id "
        "WHERE d.client_id = ? "
        "ORDER BY COALESCE(d.fecha_doc, d.fecha_subida) DESC, d.id DESC",
        (client_id,),
    )


def get_document(document_id: int):
    return fetch_one("SELECT * FROM documents WHERE id = ?", (document_id,))


def import_document(client_id: int, source_path: str | Path,
                    case_id: int | None = None, descripcion: str = "",
                    fecha_doc: str | None = None,
                    nombre: str | None = None) -> int:
    """Copia el archivo dentro de la carpeta de datos y lo registra.

    Con ``nombre`` la ficha lo enseña con el título que se le quiera dar
    («DNI», «Lista de acreedores») en lugar del nombre del fichero, que
    suele venir con fechas y sufijos del escáner.
    """
    src = Path(source_path)
    if not src.exists():
        raise FileNotFoundError(src)
    dest_dir = _client_dir(client_id)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    dest_name = f"{timestamp}_{src.name}"
    dest = dest_dir / dest_name
    shutil.copy2(src, dest)
    rel = dest.relative_to(DOCS_DIR).as_posix()
    size = dest.stat().st_size
    mime = _guess_mime(dest)
    return execute(
        "INSERT INTO documents(client_id, case_id, nombre, ruta_archivo, "
        "tipo_mime, tamano_bytes, fecha_doc, descripcion) "
        "VALUES(?, ?, ?, ?, ?, ?, ?, ?)",
        (client_id, case_id, (nombre or "").strip() or src.name, rel, mime,
         size, fecha_doc, descripcion),
    )


def add_reference(client_id: int, nombre: str, enlace: str,
                  case_id: int | None = None, descripcion: str = "",
                  fecha_doc: str | None = None) -> int:
    """Anota un documento que vive fuera del programa, por ejemplo en Drive.

    No se copia nada: solo se guarda el enlace. Sirve para tener el índice
    completo del expediente en la ficha sin que la carpeta de datos crezca
    con cada escaneo. El archivo de verdad se puede subir después con el
    botón de siempre.
    """
    return execute(
        "INSERT INTO documents(client_id, case_id, nombre, ruta_archivo, "
        "enlace, tipo_mime, tamano_bytes, fecha_doc, descripcion) "
        "VALUES(?, ?, ?, '', ?, 'text/uri-list', 0, ?, ?)",
        (client_id, case_id, nombre, enlace, fecha_doc, descripcion),
    )


def destino(document_id: int) -> tuple[str, str] | None:
    """Dónde está el documento: ('archivo', ruta) o ('enlace', url).

    Devuelve None si la fila ya no existe o si no apunta a ninguna parte.
    """
    row = get_document(document_id)
    if row is None:
        return None
    ruta = (row["ruta_archivo"] or "").strip()
    if ruta:
        path = DOCS_DIR / ruta
        if path.exists():
            return ("archivo", str(path))
    try:
        enlace = (row["enlace"] or "").strip()
    except (IndexError, KeyError):
        enlace = ""
    if enlace:
        return ("enlace", enlace)
    return None


def update_document(document_id: int, *, descripcion: str | None = None,
                    fecha_doc: str | None = None, case_id: int | None = None) -> None:
    row = get_document(document_id)
    if row is None:
        return
    execute(
        "UPDATE documents SET descripcion = ?, fecha_doc = ?, case_id = ? "
        "WHERE id = ?",
        (
            descripcion if descripcion is not None else row["descripcion"],
            fecha_doc if fecha_doc is not None else row["fecha_doc"],
            case_id if case_id is not None else row["case_id"],
            document_id,
        ),
    )


def delete_document(document_id: int) -> None:
    row = get_document(document_id)
    if row is None:
        return
    ruta = (row["ruta_archivo"] or "").strip()
    # Si la fila es solo un enlace no hay nada que borrar del disco.
    if ruta:
        try:
            path = DOCS_DIR / ruta
            if path.exists():
                path.unlink()
        except OSError:
            pass
    execute("DELETE FROM documents WHERE id = ?", (document_id,))


def absolute_path(document_id: int) -> Path | None:
    row = get_document(document_id)
    if row is None:
        return None
    return DOCS_DIR / row["ruta_archivo"]


def _guess_mime(path: Path) -> str:
    import mimetypes
    mime, _ = mimetypes.guess_type(path.name)
    return mime or "application/octet-stream"
