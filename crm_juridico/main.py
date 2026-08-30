"""Punto de entrada del CRM Jurídico.

Ejecutar con:  python main.py   (Windows / macOS / Linux)
"""
import sys
from pathlib import Path

# El programa usa sintaxis y librerías disponibles desde Python 3.9, que es la
# versión que trae macOS de fábrica. Con una anterior el fallo aparecería más
# tarde y de forma confusa, así que se avisa aquí.
if sys.version_info < (3, 9):
    sys.exit(
        "\nEste programa necesita Python 3.9 o superior.\n"
        f"Estás usando Python {sys.version.split()[0]}.\n\n"
        "Descarga una versión actual desde https://www.python.org/downloads/\n"
    )

# Permite ejecutar `python main.py` desde la raíz del proyecto.
ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication, QMessageBox

from app.config import APP_NAME, AVISO_DATOS, ICON_PATH
from app.database.db import init_db


def main() -> int:
    # La base de datos se prepara ANTES de importar la interfaz. Algunos
    # módulos consultan ajustes al cargarse, y con la base todavía sin tablas
    # el arranque moría con un «no such table». Importar aquí lo garantiza.
    init_db()

    from app.ui.main_window import MainWindow

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setStyle("Fusion")
    if ICON_PATH.exists():
        app.setWindowIcon(QIcon(str(ICON_PATH)))
    win = MainWindow()
    win.show()
    if AVISO_DATOS:
        QMessageBox.warning(win, "Carpeta de datos", AVISO_DATOS)
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
