from datetime import date

from PyQt6.QtCore import QDate, Qt
from PyQt6.QtWidgets import (
    QComboBox, QDateEdit, QHBoxLayout, QHeaderView, QLabel, QMessageBox,
    QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

from app.models import expenses as m_expenses
from app.ui.expense_edit_dialog import ExpenseEditDialog
from app.ui.widgets.common import (
    DangerButton, PrimaryButton, SearchBar, SectionTitle, fmt_eur,
)


class ExpensesView(QWidget):
    def __init__(self):
        super().__init__()
        self._build()
        self.refresh()

    def _build(self):
        lay = QVBoxLayout(self)
        lay.addWidget(SectionTitle("Gastos"))

        top = QHBoxLayout()
        self.search = SearchBar("Buscar concepto, proveedor o categoría...", self._on_search)
        top.addWidget(self.search, 2)
        self.in_desde = QDateEdit(calendarPopup=True)
        self.in_desde.setDate(QDate(date.today().year, 1, 1))
        self.in_hasta = QDateEdit(calendarPopup=True)
        self.in_hasta.setDate(QDate.currentDate())
        for w in (self.in_desde, self.in_hasta):
            w.dateChanged.connect(lambda _: self._reload())
        top.addWidget(QLabel("De:"))
        top.addWidget(self.in_desde)
        top.addWidget(QLabel("a:"))
        top.addWidget(self.in_hasta)
        btn_new = PrimaryButton("+ Nuevo gasto")
        btn_new.clicked.connect(self._on_new)
        top.addWidget(btn_new)
        lay.addLayout(top)

        self.table = QTableWidget(0, 8)
        self.table.setHorizontalHeaderLabels(
            ["Fecha", "Concepto", "Categoría", "Proveedor", "Cliente",
             "Base", "IVA", "Total"]
        )
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.ResizeToContents
        )
        self.table.doubleClicked.connect(self._on_edit)
        lay.addWidget(self.table, 1)

        row = QHBoxLayout()
        b_edit = PrimaryButton("Editar")
        b_edit.clicked.connect(self._on_edit)
        b_del = DangerButton("Eliminar")
        b_del.clicked.connect(self._on_delete)
        row.addWidget(b_edit)
        row.addStretch(1)
        row.addWidget(b_del)
        lay.addLayout(row)

        self.lbl_totales = QLabel()
        self.lbl_totales.setStyleSheet(
            "background: #ECF0F1; padding: 8px; border-radius: 4px;"
        )
        lay.addWidget(self.lbl_totales)

    def refresh(self):
        self._reload()

    def _on_search(self, text: str):
        self._reload(text)

    def _reload(self, search: str = ""):
        rows = m_expenses.list_expenses(
            search=search,
            desde=self.in_desde.date().toString("yyyy-MM-dd"),
            hasta=self.in_hasta.date().toString("yyyy-MM-dd"),
        )
        self.table.setRowCount(len(rows))
        self._ids = []
        sum_base = sum_iva = sum_total = 0.0
        for i, r in enumerate(rows):
            self._ids.append(r["id"])
            self.table.setItem(i, 0, QTableWidgetItem(r["fecha"]))
            self.table.setItem(i, 1, QTableWidgetItem(r["concepto"] or ""))
            self.table.setItem(i, 2, QTableWidgetItem(r["categoria"] or ""))
            self.table.setItem(i, 3, QTableWidgetItem(r["proveedor"] or ""))
            self.table.setItem(i, 4, QTableWidgetItem(r["cliente"] or ""))
            self.table.setItem(i, 5, QTableWidgetItem(fmt_eur(r["base_imponible"])))
            self.table.setItem(i, 6, QTableWidgetItem(fmt_eur(r["importe_iva"])))
            self.table.setItem(i, 7, QTableWidgetItem(fmt_eur(r["total"])))
            sum_base += float(r["base_imponible"])
            sum_iva += float(r["importe_iva"])
            sum_total += float(r["total"])
        self.lbl_totales.setText(
            f"<b>Totales del periodo</b>: Base {fmt_eur(sum_base)} · "
            f"IVA soportado {fmt_eur(sum_iva)} · <b>Total {fmt_eur(sum_total)}</b>"
        )

    def _selected_id(self) -> int | None:
        row = self.table.currentRow()
        if row < 0 or row >= len(self._ids):
            return None
        return self._ids[row]

    def _on_new(self):
        dlg = ExpenseEditDialog(self)
        if dlg.exec():
            self._reload()

    def _on_edit(self):
        eid = self._selected_id()
        if eid is None:
            return
        dlg = ExpenseEditDialog(self, expense_id=eid)
        if dlg.exec():
            self._reload()

    def _on_delete(self):
        eid = self._selected_id()
        if eid is None:
            return
        ans = QMessageBox.question(self, "Eliminar", "¿Eliminar el gasto?")
        if ans == QMessageBox.StandardButton.Yes:
            m_expenses.delete_expense(eid)
            self._reload()
