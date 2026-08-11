"""Punto de entrada del CRM Jurídico.

Ejecutar con:  python main.py   (Windows / macOS / Linux)
"""
import sys
from pathlib import Path

# Permite ejecutar `python main.py` desde la raíz del proyecto.
ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication, QMessageBox

from app.config import APP_NAME, AVISO_DATOS, ICON_PATH
from app.database.db import init_db
from app.ui.main_window import MainWindow


def main() -> int:
    init_db()
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
