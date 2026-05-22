from pathlib import Path

APP_NAME = "CRM Jurídico"
APP_VERSION = "0.1.0"

ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"
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
    "ollama_url": "http://localhost:11434",
    "ollama_model": "llama3.1",
}
