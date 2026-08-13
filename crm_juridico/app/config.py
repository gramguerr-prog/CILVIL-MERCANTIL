import os
from pathlib import Path

APP_NAME = "CRM Jurídico"
APP_VERSION = "0.2.0"

ROOT_DIR = Path(__file__).resolve().parent.parent
ICON_PATH = ROOT_DIR / "recursos" / "crm.ico"

# Fichero opcional con la ruta de la carpeta de datos. Permite guardar los
# datos en una carpeta sincronizada (OneDrive, iCloud Drive, Dropbox...) para
# usar el mismo despacho desde varios equipos.
RUTA_DATOS_FILE = ROOT_DIR / "ruta_datos.txt"

_CABECERA_RUTA = (
    "# Carpeta donde el CRM guarda sus datos (base de datos, documentos y\n"
    "# facturas). Cámbiala desde Ajustes > Carpeta de datos.\n"
    "# Si borras este archivo se usará la carpeta 'data' del programa.\n"
)


def ruta_datos_configurada() -> Path | None:
    """Ruta indicada por el usuario, o None si usa la carpeta por defecto."""
    env = os.environ.get("CRM_DATA_DIR", "").strip()
    if env:
        return Path(env).expanduser()
    if RUTA_DATOS_FILE.exists():
        try:
            texto = RUTA_DATOS_FILE.read_text(encoding="utf-8")
        except OSError:
            return None
        for linea in texto.splitlines():
            linea = linea.strip()
            if linea and not linea.startswith("#"):
                return Path(linea).expanduser()
    return None


def guardar_ruta_datos(ruta: str | Path | None) -> None:
    """Fija la carpeta de datos. Con None vuelve a la carpeta por defecto."""
    if ruta is None:
        RUTA_DATOS_FILE.unlink(missing_ok=True)
        return
    RUTA_DATOS_FILE.write_text(
        _CABECERA_RUTA + str(Path(ruta).expanduser()) + "\n", encoding="utf-8"
    )


def _resolver_data_dir() -> tuple[Path, str | None]:
    """Devuelve la carpeta de datos a usar y un aviso si hubo que recurrir
    a la de por defecto (por ejemplo, si la unidad de red no está montada)."""
    por_defecto = ROOT_DIR / "data"
    elegida = ruta_datos_configurada()
    if elegida is None:
        return por_defecto, None
    try:
        elegida.mkdir(parents=True, exist_ok=True)
        # Comprobar que se puede escribir de verdad.
        prueba = elegida / ".escritura_ok"
        prueba.touch()
        prueba.unlink(missing_ok=True)
        return elegida, None
    except OSError as e:
        return por_defecto, (
            f"No se puede usar la carpeta de datos configurada:\n{elegida}\n\n"
            f"Motivo: {e}\n\n"
            f"Se usará temporalmente la carpeta local del programa. "
            f"Revisa Ajustes > Carpeta de datos."
        )


DATA_DIR, AVISO_DATOS = _resolver_data_dir()
DOCS_DIR = DATA_DIR / "documents"
INVOICES_PDF_DIR = DATA_DIR / "invoices_pdf"
DB_PATH = DATA_DIR / "crm.db"

DATA_DIR.mkdir(parents=True, exist_ok=True)
DOCS_DIR.mkdir(parents=True, exist_ok=True)
INVOICES_PDF_DIR.mkdir(parents=True, exist_ok=True)

DEFAULT_SETTINGS = {
    "iva_general": "21",
    "iva_reducido": "10",
    "iva_superreducido": "4",
    "irpf_general": "15",
    "irpf_nuevo": "7",
    "despacho_nombre": "",
    "despacho_nif": "",
    "despacho_direccion": "",
    "despacho_telefono": "",
    "despacho_email": "",
    "despacho_iban": "",
    "factura_prefijo": "",
    "factura_serie": str(__import__("datetime").date.today().year),
    # Inteligencia artificial. Por defecto el proveedor local, para que ningún
    # dato de cliente salga del equipo mientras no se decida lo contrario.
    "ia_proveedor": "ollama",
    "ollama_url": "http://localhost:11434",
    "ollama_model": "llama3.1",
    "claude_api_key": "",
    "claude_model": "claude-opus-5",
    "claude_effort": "high",
}
