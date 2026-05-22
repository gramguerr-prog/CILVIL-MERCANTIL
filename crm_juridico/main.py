"""Punto de entrada del CRM Jurídico.

Ejecutar con:  python main.py   (Windows / macOS / Linux)
"""
import sys
from pathlib import Path

# Permite ejecutar `python main.py` desde la raíz del proyecto.
ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from PyQt6.QtWidgets import QApplication

from app.database.db import init_db
from app.ui.main_window import MainWindow


def main() -> int:
    init_db()
    app = QApplication(sys.argv)
    app.setApplicationName("CRM Jurídico")
    app.setStyle("Fusion")
    win = MainWindow()
    win.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
