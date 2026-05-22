from PyQt6.QtCore import QDate, Qt
from PyQt6.QtWidgets import (
    QComboBox, QDateEdit, QDialog, QDialogButtonBox, QDoubleSpinBox,
    QFormLayout, QHBoxLayout, QHeaderView, QLabel, QMessageBox,
    QPlainTextEdit, QPushButton, QSpinBox, QTableWidget, QTableWidgetItem,
    QVBoxLayout, QWidget,
)

from app.database.db import get_setting
from app.models import cases as m_cases
from app.models import clients as m_clients
from app.models import invoices as m_invoices
from app.services.tax import (
    applies_irpf, compute_totals, line_subtotal, sum_lines,
)
from app.ui.widgets.common import (
    DangerButton, PrimaryButton, fmt_eur,
)


IVA_OPTIONS = [21, 10, 4, 0]


class InvoiceEditor(QDialog):
    def __init__(self, parent=None, invoice_id: int | None = None,
                 client_id: int | None = None):
        super().__init__(parent)
        self.invoice_id = invoice_id
        self.preset_client_id = client_id
        self.setWindowTitle("Factura")
        self.setMinimumSize(900, 640)
        self._build()
        if invoice_id:
            self._load()
        else:
            self._init_new()

    def _build(self):
        lay = QVBoxLayout(self)
        head = QFormLayout()

        self.lbl_numero = QLabel("(se asignará al guardar)")
        self.lbl_numero.setStyleSheet("font-weight: bold;")
        head.addRow("Número:", self.lbl_numero)

        self.in_fecha = QDateEdit(calendarPopup=True)
        self.in_fecha.setDate(QDate.currentDate())
        head.addRow("Fecha emisión", self.in_fecha)

        self.in_venc = QDateEdit(calendarPopup=True)
        self.in_venc.setDate(QDate.currentDate().addDays(30))
        head.addRow("Vencimiento", self.in_venc)

        self.cmb_cliente = QComboBox()
        for c in m_clients.list_clients(only_active=False):
            nombre = f"{c['nombre']} {c['apellidos'] or ''}".strip()
            tipo = c["tipo"] or "particular"
            self.cmb_cliente.addItem(f"{nombre} · {tipo}", c["id"])
        self.cmb_cliente.currentIndexChanged.connect(self._on_client_change)
        head.addRow("Cliente*", self.cmb_cliente)

        self.cmb_caso = QComboBox()
        self.cmb_caso.addItem("(Sin asunto)", None)
        head.addRow("Asunto", self.cmb_caso)

        self.cmb_estado = QComboBox()
        self.cmb_estado.addItems(["borrador", "emitida", "cobrada", "parcial", "anulada"])
        self.cmb_estado.setCurrentText("emitida")
        head.addRow("Estado", self.cmb_estado)

        lay.addLayout(head)

        # Líneas
        lines_box = QVBoxLayout()
        l_head = QHBoxLayout()
        l_head.addWidget(QLabel("<b>Líneas</b>"))
        l_head.addStretch(1)
        b_add = PrimaryButton("+ Línea")
        b_add.clicked.connect(self._add_line)
        b_del = DangerButton("Quitar línea")
        b_del.clicked.connect(self._del_line)
        l_head.addWidget(b_add)
        l_head.addWidget(b_del)
        lines_box.addLayout(l_head)

        self.tbl_lines = QTableWidget(0, 4)
        self.tbl_lines.setHorizontalHeaderLabels(
            ["Descripción", "Cantidad", "Precio unitario", "Subtotal"]
        )
        self.tbl_lines.horizontalHeader().setStretchLastSection(False)
        self.tbl_lines.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Stretch
        )
        self.tbl_lines.setColumnWidth(1, 90)
        self.tbl_lines.setColumnWidth(2, 130)
        self.tbl_lines.setColumnWidth(3, 130)
        self.tbl_lines.itemChanged.connect(self._on_line_changed)
        lines_box.addWidget(self.tbl_lines, 1)
        lay.addLayout(lines_box, 1)

        # Totales
        tot = QFormLayout()
        self.in_iva = QComboBox()
        for v in IVA_OPTIONS:
            self.in_iva.addItem(f"{v} %", v)
        self.in_iva.currentIndexChanged.connect(self._recalc)

        self.in_irpf = QDoubleSpinBox()
        self.in_irpf.setRange(0, 100)
        self.in_irpf.setDecimals(2)
        self.in_irpf.setSuffix(" %")
        self.in_irpf.valueChanged.connect(self._recalc)

        self.lbl_base = QLabel("0,00 €")
        self.lbl_iva = QLabel("0,00 €")
        self.lbl_irpf = QLabel("0,00 €")
        self.lbl_total = QLabel("0,00 €")
        f = self.lbl_total.font()
        f.setBold(True)
        f.setPointSize(f.pointSize() + 2)
        self.lbl_total.setFont(f)

        tot.addRow("Tipo IVA", self.in_iva)
        tot.addRow("Retención IRPF", self.in_irpf)
        tot.addRow("Base imponible", self.lbl_base)
        tot.addRow("IVA", self.lbl_iva)
        tot.addRow("IRPF (-)", self.lbl_irpf)
        tot.addRow("TOTAL", self.lbl_total)
        lay.addLayout(tot)

        self.in_notas = QPlainTextEdit()
        self.in_notas.setFixedHeight(60)
        self.in_notas.setPlaceholderText("Notas / pie de factura")
        lay.addWidget(self.in_notas)

        bb = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        bb.accepted.connect(self._on_save)
        bb.rejected.connect(self.reject)
        lay.addWidget(bb)

    def _init_new(self):
        if self.preset_client_id is not None:
            idx = self.cmb_cliente.findData(self.preset_client_id)
            if idx >= 0:
                self.cmb_cliente.setCurrentIndex(idx)
        self._on_client_change()
        self._add_line()

    def _on_client_change(self):
        cid = self.cmb_cliente.currentData()
        # cargar casos
        self.cmb_caso.clear()
        self.cmb_caso.addItem("(Sin asunto)", None)
        if cid is not None:
            for c in m_cases.list_cases_by_client(cid):
                self.cmb_caso.addItem(f"{c['titulo']} ({c['estado']})", c["id"])
        # IRPF según tipo
        c = m_clients.get_client(cid) if cid else None
        if c and applies_irpf(c["tipo"] or "particular"):
            if c["irpf_nuevo"]:
                self.in_irpf.setValue(float(get_setting("irpf_nuevo") or 7))
            else:
                self.in_irpf.setValue(float(get_setting("irpf_general") or 15))
        else:
            self.in_irpf.setValue(0)
        self._recalc()

    def _load(self):
        inv = m_invoices.get_invoice(self.invoice_id)
        if not inv:
            QMessageBox.critical(self, "Error", "Factura no encontrada")
            self.reject()
            return
        self.lbl_numero.setText(inv["numero"])
        self.in_fecha.setDate(QDate.fromString(inv["fecha_emision"], "yyyy-MM-dd"))
        if inv["fecha_vencimiento"]:
            self.in_venc.setDate(QDate.fromString(inv["fecha_vencimiento"], "yyyy-MM-dd"))
        idx = self.cmb_cliente.findData(inv["client_id"])
        if idx >= 0:
            self.cmb_cliente.setCurrentIndex(idx)
        self._on_client_change()
        if inv["case_id"]:
            ci = self.cmb_caso.findData(inv["case_id"])
            if ci >= 0:
                self.cmb_caso.setCurrentIndex(ci)
        self.cmb_estado.setCurrentText(inv["estado"])
        idx = self.in_iva.findData(int(inv["tipo_iva"]))
        if idx < 0:
            self.in_iva.addItem(f"{inv['tipo_iva']:g} %", float(inv["tipo_iva"]))
            idx = self.in_iva.count() - 1
        self.in_iva.setCurrentIndex(idx)
        self.in_irpf.setValue(float(inv["tipo_irpf"]))
        self.in_notas.setPlainText(inv["notas"] or "")

        self.tbl_lines.blockSignals(True)
        self.tbl_lines.setRowCount(0)
        for ln in m_invoices.get_lines(self.invoice_id):
            self._append_line_row(
                ln["descripcion"], float(ln["cantidad"]),
                float(ln["precio_unitario"])
            )
        self.tbl_lines.blockSignals(False)
        self._recalc()

    def _append_line_row(self, desc: str = "", cantidad: float = 1.0,
                         precio: float = 0.0):
        row = self.tbl_lines.rowCount()
        self.tbl_lines.insertRow(row)
        self.tbl_lines.setItem(row, 0, QTableWidgetItem(desc))
        item_c = QTableWidgetItem(f"{cantidad:.2f}")
        item_c.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.tbl_lines.setItem(row, 1, item_c)
        item_p = QTableWidgetItem(f"{precio:.2f}")
        item_p.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.tbl_lines.setItem(row, 2, item_p)
        sub = QTableWidgetItem(fmt_eur(line_subtotal(cantidad, precio)))
        sub.setFlags(sub.flags() & ~Qt.ItemFlag.ItemIsEditable)
        sub.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.tbl_lines.setItem(row, 3, sub)

    def _add_line(self):
        self._append_line_row()
        self._recalc()

    def _del_line(self):
        row = self.tbl_lines.currentRow()
        if row < 0:
            row = self.tbl_lines.rowCount() - 1
        if row >= 0:
            self.tbl_lines.removeRow(row)
        self._recalc()

    def _on_line_changed(self, item):
        if item.column() in (1, 2):
            row = item.row()
            try:
                cantidad = float(self.tbl_lines.item(row, 1).text().replace(",", "."))
                precio = float(self.tbl_lines.item(row, 2).text().replace(",", "."))
            except (ValueError, AttributeError):
                cantidad, precio = 0.0, 0.0
            sub = line_subtotal(cantidad, precio)
            self.tbl_lines.blockSignals(True)
            sub_item = QTableWidgetItem(fmt_eur(sub))
            sub_item.setFlags(sub_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            sub_item.setTextAlignment(
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
            )
            self.tbl_lines.setItem(row, 3, sub_item)
            self.tbl_lines.blockSignals(False)
        self._recalc()

    def _collect_lines(self) -> list[dict]:
        lines = []
        for r in range(self.tbl_lines.rowCount()):
            desc = (self.tbl_lines.item(r, 0).text()
                    if self.tbl_lines.item(r, 0) else "")
            try:
                cantidad = float(self.tbl_lines.item(r, 1).text().replace(",", "."))
                precio = float(self.tbl_lines.item(r, 2).text().replace(",", "."))
            except (ValueError, AttributeError):
                cantidad, precio = 0.0, 0.0
            if not desc.strip() and cantidad == 0 and precio == 0:
                continue
            lines.append({
                "descripcion": desc.strip(),
                "cantidad": cantidad,
                "precio_unitario": precio,
                "subtotal": line_subtotal(cantidad, precio),
            })
        return lines

    def _recalc(self):
        lines = self._collect_lines()
        base = sum_lines(lines)
        tipo_iva = float(self.in_iva.currentData() or 0)
        tipo_irpf = float(self.in_irpf.value())
        tot = compute_totals(base, tipo_iva, tipo_irpf)
        self.lbl_base.setText(fmt_eur(tot.base_imponible))
        self.lbl_iva.setText(fmt_eur(tot.importe_iva))
        self.lbl_irpf.setText("-" + fmt_eur(tot.importe_irpf))
        self.lbl_total.setText(fmt_eur(tot.total))

    def _on_save(self):
        cid = self.cmb_cliente.currentData()
        if cid is None:
            QMessageBox.warning(self, "Cliente", "Selecciona un cliente.")
            return
        lines = self._collect_lines()
        if not lines:
            QMessageBox.warning(self, "Líneas", "Añade al menos una línea.")
            return
        base = sum_lines(lines)
        tipo_iva = float(self.in_iva.currentData() or 0)
        tipo_irpf = float(self.in_irpf.value())
        tot = compute_totals(base, tipo_iva, tipo_irpf)
        header = {
            "client_id": cid,
            "case_id": self.cmb_caso.currentData(),
            "fecha_emision": self.in_fecha.date().toString("yyyy-MM-dd"),
            "fecha_vencimiento": self.in_venc.date().toString("yyyy-MM-dd"),
            "base_imponible": tot.base_imponible,
            "tipo_iva": tot.tipo_iva,
            "importe_iva": tot.importe_iva,
            "tipo_irpf": tot.tipo_irpf,
            "importe_irpf": tot.importe_irpf,
            "total": tot.total,
            "estado": self.cmb_estado.currentText(),
            "notas": self.in_notas.toPlainText().strip(),
        }
        try:
            if self.invoice_id is None:
                serie = get_setting("factura_serie") or "2024"
                prefijo = get_setting("factura_prefijo") or ""
                correlativo = m_invoices.next_correlativo(serie)
                header["serie"] = serie
                header["correlativo"] = correlativo
                header["numero"] = m_invoices.format_numero(prefijo, serie, correlativo)
                self.invoice_id = m_invoices.create_invoice(header, lines)
            else:
                m_invoices.update_invoice(self.invoice_id, header, lines)
        except Exception as e:
            QMessageBox.critical(self, "Error al guardar", str(e))
            return
        self.accept()
