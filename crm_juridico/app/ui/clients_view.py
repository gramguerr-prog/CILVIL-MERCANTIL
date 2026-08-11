from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QHBoxLayout, QHeaderView, QMessageBox, QPushButton, QTableWidget,
    QTableWidgetItem, QVBoxLayout, QWidget,
)

from app.models import clients as m_clients
from app.ui.client_detail_view import ClientDetailDialog
from app.ui.client_edit_dialog import ClientEditDialog
from app.ui.widgets.common import (
    DangerButton, PrimaryButton, SearchBar, SectionTitle, autofit_columns,
    configure_table,
)


class ClientsView(QWidget):
    client_opened = pyqtSignal(int)

    def __init__(self):
        super().__init__()
        self._build()
        self.refresh()

    def _build(self):
        lay = QVBoxLayout(self)
        lay.addWidget(SectionTitle("Clientes"))

        top = QHBoxLayout()
        self.search = SearchBar("Buscar por nombre, apellidos, NIF o email...", self._on_search)
        top.addWidget(self.search, 1)
        btn_new = PrimaryButton("+ Nuevo cliente")
        btn_new.clicked.connect(self._on_new)
        top.addWidget(btn_new)
        lay.addLayout(top)

        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels(
            ["#", "Nombre", "Apellidos", "NIF", "Tipo", "Email", "Teléfono"]
        )
        self.table.verticalHeader().setVisible(False)
        configure_table(self.table, elastic=5)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.doubleClicked.connect(self._on_open)
        lay.addWidget(self.table, 1)

        actions = QHBoxLayout()
        btn_open = PrimaryButton("Abrir ficha")
        btn_open.clicked.connect(self._on_open)
        btn_edit = QPushButton("Editar")
        btn_edit.clicked.connect(self._on_edit)
        btn_del = DangerButton("Eliminar")
        btn_del.clicked.connect(self._on_delete)
        actions.addWidget(btn_open)
        actions.addWidget(btn_edit)
        actions.addStretch(1)
        actions.addWidget(btn_del)
        lay.addLayout(actions)

    # --- Data ---

    def refresh(self):
        self._reload("")

    def _on_search(self, text: str):
        self._reload(text)

    def _reload(self, search: str):
        rows = m_clients.list_clients(search=search)
        self.table.setRowCount(len(rows))
        self._row_ids = []
        for i, r in enumerate(rows):
            self._row_ids.append(r["id"])
            self.table.setItem(i, 0, QTableWidgetItem(str(r["id"])))
            self.table.setItem(i, 1, QTableWidgetItem(r["nombre"] or ""))
            self.table.setItem(i, 2, QTableWidgetItem(r["apellidos"] or ""))
            self.table.setItem(i, 3, QTableWidgetItem(r["nif"] or ""))
            self.table.setItem(i, 4, QTableWidgetItem(r["tipo"] or ""))
            self.table.setItem(i, 5, QTableWidgetItem(r["email"] or ""))
            self.table.setItem(i, 6, QTableWidgetItem(r["telefono"] or ""))
        autofit_columns(self.table)

    def _selected_id(self) -> int | None:
        row = self.table.currentRow()
        if row < 0 or row >= len(self._row_ids):
            return None
        return self._row_ids[row]

    # --- Actions ---

    def _on_new(self):
        dlg = ClientEditDialog(self)
        if dlg.exec():
            self.refresh()

    def _on_edit(self):
        cid = self._selected_id()
        if cid is None:
            return
        dlg = ClientEditDialog(self, client_id=cid)
        if dlg.exec():
            self.refresh()

    def _on_delete(self):
        cid = self._selected_id()
        if cid is None:
            return
        c = m_clients.get_client(cid)
        if c is None:
            return
        name = f"{c['nombre']} {c['apellidos'] or ''}".strip()
        ans = QMessageBox.question(
            self, "Eliminar cliente",
            f"¿Eliminar a {name}?\nSe borrarán también sus asuntos, documentos, "
            "gastos imputados y pagos. Las facturas no podrán borrarse si tienen relación.",
        )
        if ans != QMessageBox.StandardButton.Yes:
            return
        try:
            m_clients.delete_client(cid)
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
            return
        self.refresh()

    def _on_open(self):
        cid = self._selected_id()
        if cid is None:
            return
        self.open_detail(cid)

    def open_detail(self, client_id: int):
        dlg = ClientDetailDialog(self, client_id=client_id)
        dlg.exec()
        self.refresh()
