"""Punto de entrada del CRM Jurídico.

Ejecutar con:  python main.py   (Windows / macOS / Linux)
"""
import os
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


def _preparar_qt() -> None:
    """Le dice a Qt dónde están sus complementos antes de cargarlo.

    Qt los busca junto al ejecutable de Python. Con el Python que trae macOS,
    que es un *framework*, esa ruta apunta dentro de Python.app y allí no hay
    nada, de modo que el programa aborta nada más arrancar con «Could not find
    the Qt platform plugin cocoa». Los complementos viajan dentro del paquete
    PyQt6, así que basta con señalar esa carpeta.

    Se respeta cualquier valor que ya venga del entorno, por si alguien usa una
    instalación de Qt propia.
    """
    if os.environ.get("QT_QPA_PLATFORM_PLUGIN_PATH"):
        return
    try:
        import PyQt6  # solo el paquete: no carga aún ninguna librería de Qt
    except ImportError:
        return  # sin PyQt6 el fallo se explica solo, más abajo
    plugins = Path(PyQt6.__file__).resolve().parent / "Qt6" / "plugins"
    if (plugins / "platforms").is_dir():
        os.environ.setdefault("QT_PLUGIN_PATH", str(plugins))
        os.environ["QT_QPA_PLATFORM_PLUGIN_PATH"] = str(plugins / "platforms")


def main() -> int:
    # Antes de nada, la ruta de los complementos de Qt.
    _preparar_qt()

    try:
        from PyQt6.QtGui import QIcon
        from PyQt6.QtWidgets import QApplication, QMessageBox
    except ImportError as e:
        sys.exit(
            f"\nNo se ha podido cargar PyQt6: {e}\n\n"
            "Instálalo con:  pip install -r requirements.txt\n"
        )

    from app.config import APP_NAME, AVISO_DATOS, ICON_PATH
    from app.database.db import init_db

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
