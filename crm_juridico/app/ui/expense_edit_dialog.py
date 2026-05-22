from PyQt6.QtCore import QDate
from PyQt6.QtWidgets import (
    QCheckBox, QComboBox, QDateEdit, QDialog, QDialogButtonBox,
    QDoubleSpinBox, QFormLayout, QLineEdit, QMessageBox, QPlainTextEdit,
    QVBoxLayout,
)

from app.models import cases as m_cases
from app.models import clients as m_clients
from app.models import expenses as m_expenses


CATEGORIAS = [
    "alquiler", "suministros", "material oficina", "telefonía/internet",
    "asesoría", "formación", "colegios profesionales", "seguros",
    "marketing", "dietas y viajes", "amortizaciones", "tasas",
    "subcontratación", "otros",
]


class ExpenseEditDialog(QDialog):
    def __init__(self, parent=None, expense_id: int | None = None,
                 client_id: int | None = None):
        super().__init__(parent)
        self.expense_id = expense_id
        self.preset_client_id = client_id
        self.setWindowTitle("Gasto")
        self.setMinimumWidth(560)
        self._build()
        if expense_id:
            self._load()
        elif client_id:
            idx = self.cmb_cliente.findData(client_id)
            if idx >= 0:
                self.cmb_cliente.setCurrentIndex(idx)
                self._on_client_change()
        self._recalc()

    def _build(self):
        lay = QVBoxLayout(self)
        form = QFormLayout()

        self.in_fecha = QDateEdit(calendarPopup=True)
        self.in_fecha.setDate(QDate.currentDate())
        self.in_concepto = QLineEdit()
        self.in_categoria = QComboBox()
        self.in_categoria.setEditable(True)
        self.in_categoria.addItems(CATEGORIAS)
        self.in_proveedor = QLineEdit()

        self.in_base = QDoubleSpinBox()
        self.in_base.setRange(0, 10_000_000)
        self.in_base.setDecimals(2)
        self.in_base.valueChanged.connect(self._recalc)
        self.in_iva = QDoubleSpinBox()
        self.in_iva.setRange(0, 100)
        self.in_iva.setDecimals(2)
        self.in_iva.setValue(21)
        self.in_iva.setSuffix(" %")
        self.in_iva.valueChanged.connect(self._recalc)
        from PyQt6.QtWidgets import QLabel
        self.lbl_iva_eur = QLabel("0,00 €")
        self.lbl_total = QLabel("0,00 €")
        f = self.lbl_total.font()
        f.setBold(True)
        self.lbl_total.setFont(f)

        self.chk_deducible = QCheckBox("Deducible (entra en el balance fiscal)")
        self.chk_deducible.setChecked(True)

        self.cmb_cliente = QComboBox()
        self.cmb_cliente.addItem("(General del despacho)", None)
        for c in m_clients.list_clients(only_active=False):
            nombre = f"{c['nombre']} {c['apellidos'] or ''}".strip()
            self.cmb_cliente.addItem(nombre, c["id"])
        self.cmb_cliente.currentIndexChanged.connect(self._on_client_change)

        self.cmb_caso = QComboBox()
        self.cmb_caso.addItem("(Sin asunto)", None)
        self.chk_repercutible = QCheckBox("Repercutible (lo facturaré al cliente)")
        self.in_notas = QPlainTextEdit()
        self.in_notas.setFixedHeight(70)

        form.addRow("Fecha*", self.in_fecha)
        form.addRow("Concepto*", self.in_concepto)
        form.addRow("Categoría", self.in_categoria)
        form.addRow("Proveedor", self.in_proveedor)
        form.addRow("Base imponible", self.in_base)
        form.addRow("IVA", self.in_iva)
        form.addRow("Importe IVA", self.lbl_iva_eur)
        form.addRow("TOTAL", self.lbl_total)
        form.addRow("", self.chk_deducible)
        form.addRow("Cliente", self.cmb_cliente)
        form.addRow("Asunto", self.cmb_caso)
        form.addRow("", self.chk_repercutible)
        form.addRow("Notas", self.in_notas)
        lay.addLayout(form)

        bb = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        bb.accepted.connect(self._save)
        bb.rejected.connect(self.reject)
        lay.addWidget(bb)

    def _on_client_change(self):
        cid = self.cmb_cliente.currentData()
        self.cmb_caso.clear()
        self.cmb_caso.addItem("(Sin asunto)", None)
        if cid is not None:
            for c in m_cases.list_cases_by_client(cid):
                self.cmb_caso.addItem(f"{c['titulo']} ({c['estado']})", c["id"])

    def _recalc(self):
        base = float(self.in_base.value())
        tipo = float(self.in_iva.value())
        iva = round(base * tipo / 100.0, 2)
        total = round(base + iva, 2)
        from app.ui.widgets.common import fmt_eur
        self.lbl_iva_eur.setText(fmt_eur(iva))
        self.lbl_total.setText(fmt_eur(total))

    def _load(self):
        e = m_expenses.get_expense(self.expense_id)
        if e is None:
            return
        if e["fecha"]:
            self.in_fecha.setDate(QDate.fromString(e["fecha"], "yyyy-MM-dd"))
        self.in_concepto.setText(e["concepto"] or "")
        if e["categoria"]:
            self.in_categoria.setCurrentText(e["categoria"])
        self.in_proveedor.setText(e["proveedor"] or "")
        self.in_base.setValue(float(e["base_imponible"] or 0))
        self.in_iva.setValue(float(e["tipo_iva"] or 0))
        self.chk_deducible.setChecked(bool(e["deducible"]))
        idx = self.cmb_cliente.findData(e["client_id"])
        if idx < 0:
            idx = 0
        self.cmb_cliente.setCurrentIndex(idx)
        self._on_client_change()
        if e["case_id"]:
            ci = self.cmb_caso.findData(e["case_id"])
            if ci >= 0:
                self.cmb_caso.setCurrentIndex(ci)
        self.chk_repercutible.setChecked(bool(e["repercutible"]))
        self.in_notas.setPlainText(e["notas"] or "")

    def _save(self):
        if not self.in_concepto.text().strip():
            QMessageBox.warning(self, "Concepto", "El concepto es obligatorio.")
            return
        base = float(self.in_base.value())
        tipo_iva = float(self.in_iva.value())
        iva = round(base * tipo_iva / 100.0, 2)
        total = round(base + iva, 2)
        data = {
            "fecha": self.in_fecha.date().toString("yyyy-MM-dd"),
            "concepto": self.in_concepto.text().strip(),
            "categoria": self.in_categoria.currentText().strip() or None,
            "proveedor": self.in_proveedor.text().strip() or None,
            "base_imponible": base,
            "tipo_iva": tipo_iva,
            "importe_iva": iva,
            "total": total,
            "deducible": 1 if self.chk_deducible.isChecked() else 0,
            "client_id": self.cmb_cliente.currentData(),
            "case_id": self.cmb_caso.currentData(),
            "repercutible": 1 if self.chk_repercutible.isChecked() else 0,
            "notas": self.in_notas.toPlainText().strip() or None,
        }
        if self.expense_id:
            m_expenses.update_expense(self.expense_id, data)
        else:
            m_expenses.create_expense(data)
        self.accept()
