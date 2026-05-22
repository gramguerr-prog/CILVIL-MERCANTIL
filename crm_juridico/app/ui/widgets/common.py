from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QHBoxLayout, QLabel, QLineEdit, QPushButton, QSizePolicy, QWidget,
)


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
