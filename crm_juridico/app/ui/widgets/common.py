from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QHBoxLayout, QHeaderView, QLabel, QLineEdit, QPushButton, QSizePolicy,
    QTableWidget, QWidget,
)

# Ancho máximo (px) que puede alcanzar una columna ajustada al contenido.
MAX_COL_WIDTH = 260
MIN_COL_WIDTH = 55


def configure_table(table: QTableWidget, elastic: int | None = None,
                    max_width: int = MAX_COL_WIDTH) -> None:
    """Prepara una tabla para que las columnas ocupen lo que necesitan.

    `elastic` es el índice de la columna que absorbe el espacio sobrante
    (normalmente la de texto libre). El resto se ajusta al contenido, con
    un tope para que un valor largo no desplace a las demás. Todas las
    columnas siguen siendo redimensionables a mano por el usuario.
    """
    header = table.horizontalHeader()
    header.setStretchLastSection(False)
    header.setMinimumSectionSize(MIN_COL_WIDTH)
    for i in range(table.columnCount()):
        header.setSectionResizeMode(i, QHeaderView.ResizeMode.Interactive)
    if elastic is not None and 0 <= elastic < table.columnCount():
        header.setSectionResizeMode(elastic, QHeaderView.ResizeMode.Stretch)
        table.setProperty("_elastic_col", elastic)
    else:
        table.setProperty("_elastic_col", -1)
    table.setProperty("_max_col_width", max_width)


def autofit_columns(table: QTableWidget) -> None:
    """Reajusta los anchos al contenido actual. Llamar tras rellenar datos."""
    elastic = table.property("_elastic_col")
    elastic = -1 if elastic is None else int(elastic)
    max_width = table.property("_max_col_width") or MAX_COL_WIDTH
    table.resizeColumnsToContents()
    for i in range(table.columnCount()):
        if i == elastic:
            continue
        ancho = table.columnWidth(i)
        table.setColumnWidth(i, max(MIN_COL_WIDTH, min(ancho, int(max_width))))


def fmt_eur(value: float | int | None) -> str:
    if value is None:
        return "0,00 €"
    return f"{float(value):,.2f} €".replace(",", "X").replace(".", ",").replace("X", ".")


def fmt_pct(value: float | int | None) -> str:
    if value is None:
        return "0 %"
    return f"{float(value):g} %"


class SearchBar(QWidget):
    def __init__(self, placeholder: str = "Buscar...", on_search=None, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.input = QLineEdit()
        self.input.setPlaceholderText(placeholder)
        self.input.setClearButtonEnabled(True)
        self.input.returnPressed.connect(lambda: on_search and on_search(self.input.text()))
        self.input.textChanged.connect(lambda t: on_search and on_search(t))
        self.input.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        layout.addWidget(self.input)


class SectionTitle(QLabel):
    def __init__(self, text: str, parent=None):
        super().__init__(text, parent)
        f = self.font()
        f.setPointSize(f.pointSize() + 3)
        f.setBold(True)
        self.setFont(f)
        self.setContentsMargins(0, 6, 0, 6)


class PrimaryButton(QPushButton):
    def __init__(self, text: str, parent=None):
        super().__init__(text, parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet(
            "QPushButton { background-color: #2E86DE; color: white; "
            "border: none; padding: 6px 14px; border-radius: 4px; }"
            "QPushButton:hover { background-color: #1B6FBF; }"
            "QPushButton:disabled { background-color: #95A5A6; }"
        )


class DangerButton(QPushButton):
    def __init__(self, text: str, parent=None):
        super().__init__(text, parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet(
            "QPushButton { background-color: #E74C3C; color: white; "
            "border: none; padding: 6px 14px; border-radius: 4px; }"
            "QPushButton:hover { background-color: #C0392B; }"
        )
