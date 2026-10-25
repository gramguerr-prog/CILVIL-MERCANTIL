from datetime import date

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QFormLayout, QFrame, QGridLayout, QGroupBox, QHBoxLayout, QHeaderView,
    QLabel, QPushButton, QSizePolicy, QTableWidget, QTableWidgetItem,
    QVBoxLayout, QWidget,
)

from app.services import balance
from app.ui.widgets.common import SectionTitle, fmt_eur


class StatCard(QFrame):
    def __init__(self, title: str, color: str = "#2E86DE"):
        super().__init__()
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setStyleSheet(
            f"QFrame {{ background: white; border-radius: 8px; "
            f"border-left: 5px solid {color}; padding: 10px; }}"
        )
        lay = QVBoxLayout(self)
        lay.setContentsMargins(12, 8, 12, 8)
        self.lbl_title = QLabel(title)
        self.lbl_title.setStyleSheet("color: #7F8C8D; font-size: 11px;")
        self.lbl_value = QLabel("—")
        f = self.lbl_value.font()
        f.setPointSize(f.pointSize() + 6)
        f.setBold(True)
        self.lbl_value.setFont(f)
        lay.addWidget(self.lbl_title)
        lay.addWidget(self.lbl_value)

    def set_value(self, text: str) -> None:
        self.lbl_value.setText(text)


class DashboardView(QWidget):
    def __init__(self):
        super().__init__()
        self._build()
        self.refresh()

    def _build(self):
        lay = QVBoxLayout(self)
        lay.addWidget(SectionTitle("Panel del despacho"))

        grid = QGridLayout()
        grid.setSpacing(10)
        self.card_ingresos = StatCard("Ingresos (base imponible)", "#27AE60")
        self.card_gastos = StatCard("Gastos (base deducible)", "#E74C3C")
        self.card_beneficio = StatCard("Beneficio", "#2E86DE")
        self.card_iva = StatCard("IVA a liquidar", "#8E44AD")
        self.card_irpf = StatCard("IRPF retenido", "#16A085")
        self.card_pendiente = StatCard("Pendiente de cobro", "#E67E22")
        grid.addWidget(self.card_ingresos, 0, 0)
        grid.addWidget(self.card_gastos, 0, 1)
        grid.addWidget(self.card_beneficio, 0, 2)
        grid.addWidget(self.card_iva, 1, 0)
        grid.addWidget(self.card_irpf, 1, 1)
        grid.addWidget(self.card_pendiente, 1, 2)
        lay.addLayout(grid)

        # Tabla mensual
        box = QGroupBox(f"Evolución mensual {date.today().year}")
        v = QVBoxLayout(box)
        self.tbl_meses = QTableWidget(12, 4)
        self.tbl_meses.setHorizontalHeaderLabels(
            ["Mes", "Ingresos", "Gastos", "Resultado"]
        )
        self.tbl_meses.verticalHeader().setVisible(False)
        self.tbl_meses.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self.tbl_meses.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        v.addWidget(self.tbl_meses)
        lay.addWidget(box)

        # Top clientes
        box2 = QGroupBox("Top clientes por facturación")
        v2 = QVBoxLayout(box2)
        self.tbl_top = QTableWidget(0, 2)
        self.tbl_top.setHorizontalHeaderLabels(["Cliente", "Facturado"])
        self.tbl_top.verticalHeader().setVisible(False)
        self.tbl_top.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self.tbl_top.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        v2.addWidget(self.tbl_top)
        lay.addWidget(box2)

        btn = QPushButton("Actualizar")
        btn.clicked.connect(self.refresh)
        btn.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed)
        lay.addWidget(btn, alignment=Qt.AlignmentFlag.AlignRight)

    def refresh(self):
        s = balance.summary()
        self.card_ingresos.set_value(fmt_eur(s["ingresos_base"]))
        self.card_gastos.set_value(fmt_eur(s["gastos_base"]))
        self.card_beneficio.set_value(fmt_eur(s["beneficio"]))
        self.card_iva.set_value(fmt_eur(s["iva_a_liquidar"]))
        self.card_irpf.set_value(fmt_eur(s["irpf_retenido"]))
        self.card_pendiente.set_value(fmt_eur(s["pendiente_cobro"]))

        meses = balance.monthly_series()
        nombres = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul",
                   "Ago", "Sep", "Oct", "Nov", "Dic"]
        for i, fila in enumerate(meses):
            ing = fila["ingresos"]
            gas = fila["gastos"]
            res = ing - gas
            self.tbl_meses.setItem(i, 0, QTableWidgetItem(nombres[i]))
            self.tbl_meses.setItem(i, 1, QTableWidgetItem(fmt_eur(ing)))
            self.tbl_meses.setItem(i, 2, QTableWidgetItem(fmt_eur(gas)))
            item = QTableWidgetItem(fmt_eur(res))
            if res < 0:
                item.setForeground(Qt.GlobalColor.red)
            self.tbl_meses.setItem(i, 3, item)
            for col in (1, 2, 3):
                self.tbl_meses.item(i, col).setTextAlignment(
                    Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
                )

        top = balance.top_clients(limit=10)
        self.tbl_top.setRowCount(len(top))
        for i, t in enumerate(top):
            self.tbl_top.setItem(i, 0, QTableWidgetItem(t["cliente"]))
            cell = QTableWidgetItem(fmt_eur(t["total"]))
            cell.setTextAlignment(
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
            )
            self.tbl_top.setItem(i, 1, cell)
