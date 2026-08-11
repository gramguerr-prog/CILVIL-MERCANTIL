from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtCore import QUrl
from PyQt6.QtWidgets import (
    QComboBox, QHBoxLayout, QHeaderView, QLabel, QMessageBox, QPushButton,
    QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

from app.models import invoices as m_invoices
from app.services import pdf_invoice
from app.ui.invoice_editor import InvoiceEditor
from app.ui.widgets.common import (
    DangerButton, PrimaryButton, SearchBar, SectionTitle, autofit_columns,
    configure_table, fmt_eur,
)


class InvoicesView(QWidget):
    client_link_clicked = pyqtSignal(int)

    def __init__(self):
        super().__init__()
        self._build()
        self.refresh()

    def _build(self):
        lay = QVBoxLayout(self)
        lay.addWidget(SectionTitle("Facturación"))

        top = QHBoxLayout()
        self.search = SearchBar("Buscar por número o cliente...", self._on_search)
        top.addWidget(self.search, 1)
        self.cmb_estado = QComboBox()
        self.cmb_estado.addItem("Todos los estados", None)
        for e in ("borrador", "emitida", "cobrada", "parcial", "anulada"):
            self.cmb_estado.addItem(e, e)
        self.cmb_estado.currentIndexChanged.connect(lambda _: self._reload())
        top.addWidget(QLabel("Estado:"))
        top.addWidget(self.cmb_estado)
        btn_new = PrimaryButton("+ Nueva factura")
        btn_new.clicked.connect(self._on_new)
        top.addWidget(btn_new)
        lay.addLayout(top)

        self.table = QTableWidget(0, 8)
        self.table.setHorizontalHeaderLabels(
            ["Nº", "Fecha", "Cliente", "Base", "IVA", "IRPF", "Total", "Estado"]
        )
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        configure_table(self.table, elastic=2)
        self.table.doubleClicked.connect(self._on_edit)
        lay.addWidget(self.table, 1)

        row = QHBoxLayout()
        b_edit = PrimaryButton("Abrir / editar")
        b_edit.clicked.connect(self._on_edit)
        b_pdf = QPushButton("Generar PDF")
        b_pdf.clicked.connect(self._on_pdf)
        b_open_client = QPushButton("Abrir cliente")
        b_open_client.clicked.connect(self._on_open_client)
        b_del = DangerButton("Eliminar")
        b_del.clicked.connect(self._on_delete)
        row.addWidget(b_edit)
        row.addWidget(b_pdf)
        row.addWidget(b_open_client)
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
        estado = self.cmb_estado.currentData()
        rows = m_invoices.list_invoices(search=search, estado=estado)
        self.table.setRowCount(len(rows))
        self._ids = []
        self._client_ids = []
        sum_base = sum_iva = sum_irpf = sum_total = 0.0
        for i, r in enumerate(rows):
            self._ids.append(r["id"])
            self._client_ids.append(r["client_id"])
            self.table.setItem(i, 0, QTableWidgetItem(r["numero"]))
            self.table.setItem(i, 1, QTableWidgetItem(r["fecha_emision"]))
            self.table.setItem(i, 2, QTableWidgetItem(r["cliente"]))
            self.table.setItem(i, 3, QTableWidgetItem(fmt_eur(r["base_imponible"])))
            self.table.setItem(i, 4, QTableWidgetItem(fmt_eur(r["importe_iva"])))
            self.table.setItem(i, 5, QTableWidgetItem(fmt_eur(r["importe_irpf"])))
            self.table.setItem(i, 6, QTableWidgetItem(fmt_eur(r["total"])))
            self.table.setItem(i, 7, QTableWidgetItem(r["estado"]))
            sum_base += float(r["base_imponible"])
            sum_iva += float(r["importe_iva"])
            sum_irpf += float(r["importe_irpf"])
            sum_total += float(r["total"])
        autofit_columns(self.table)
        self.lbl_totales.setText(
            f"<b>Totales</b>: Base {fmt_eur(sum_base)} · "
            f"IVA {fmt_eur(sum_iva)} · IRPF {fmt_eur(sum_irpf)} · "
            f"<b>Total {fmt_eur(sum_total)}</b>"
        )

    def _selected_id(self) -> int | None:
        row = self.table.currentRow()
        if row < 0 or row >= len(self._ids):
            return None
        return self._ids[row]

    def _on_new(self):
        dlg = InvoiceEditor(self)
        if dlg.exec():
            self._reload()

    def _on_edit(self):
        iid = self._selected_id()
        if iid is None:
            return
        dlg = InvoiceEditor(self, invoice_id=iid)
        if dlg.exec():
            self._reload()

    def _on_delete(self):
        iid = self._selected_id()
        if iid is None:
            return
        ans = QMessageBox.question(
            self, "Eliminar", "¿Eliminar esta factura? Esta acción no se puede deshacer.",
        )
        if ans == QMessageBox.StandardButton.Yes:
            try:
                m_invoices.delete_invoice(iid)
            except Exception as e:
                QMessageBox.critical(self, "No se puede eliminar", str(e))
                return
            self._reload()

    def _on_pdf(self):
        iid = self._selected_id()
        if iid is None:
            return
        inv = m_invoices.get_invoice(iid)
        lines = [dict(r) for r in m_invoices.get_lines(iid)]
        try:
            path = pdf_invoice.generate_invoice_pdf(dict(inv), lines)
        except Exception as e:
            QMessageBox.critical(self, "Error al generar PDF", str(e))
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))

    def _on_open_client(self):
        row = self.table.currentRow()
        if row < 0 or row >= len(self._client_ids):
            return
        self.client_link_clicked.emit(self._client_ids[row])
