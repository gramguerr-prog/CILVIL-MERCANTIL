from PyQt6.QtCore import QUrl, Qt
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import (
    QComboBox, QFileDialog, QHBoxLayout, QHeaderView, QInputDialog, QLabel,
    QMessageBox, QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout,
    QWidget,
)

from app.database.db import fetch_all
from app.models import clients as m_clients
from app.models import documents as m_docs
from app.ui.widgets.common import (
    DangerButton, PrimaryButton, SearchBar, SectionTitle,
)


class DocumentsView(QWidget):
    def __init__(self):
        super().__init__()
        self._build()
        self.refresh()

    def _build(self):
        lay = QVBoxLayout(self)
        lay.addWidget(SectionTitle("Documentos"))

        top = QHBoxLayout()
        self.cmb_cliente = QComboBox()
        self.cmb_cliente.addItem("(Selecciona cliente)", None)
        for c in m_clients.list_clients(only_active=False):
            nombre = f"{c['nombre']} {c['apellidos'] or ''}".strip()
            self.cmb_cliente.addItem(nombre, c["id"])
        self.cmb_cliente.currentIndexChanged.connect(lambda _: self._reload())
        top.addWidget(QLabel("Cliente:"))
        top.addWidget(self.cmb_cliente, 1)
        b_up = PrimaryButton("+ Subir documento")
        b_up.clicked.connect(self._upload)
        top.addWidget(b_up)
        lay.addLayout(top)

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(
            ["Fecha doc", "Nombre", "Asunto", "Tamaño", "Descripción"]
        )
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.ResizeToContents
        )
        self.table.doubleClicked.connect(self._open)
        lay.addWidget(self.table, 1)

        actions = QHBoxLayout()
        b_open = PrimaryButton("Abrir")
        b_open.clicked.connect(self._open)
        b_del = DangerButton("Eliminar")
        b_del.clicked.connect(self._delete)
        actions.addWidget(b_open)
        actions.addStretch(1)
        actions.addWidget(b_del)
        lay.addLayout(actions)

    def refresh(self):
        self._reload_clients()
        self._reload()

    def _reload_clients(self):
        current = self.cmb_cliente.currentData()
        self.cmb_cliente.blockSignals(True)
        self.cmb_cliente.clear()
        self.cmb_cliente.addItem("(Selecciona cliente)", None)
        for c in m_clients.list_clients(only_active=False):
            nombre = f"{c['nombre']} {c['apellidos'] or ''}".strip()
            self.cmb_cliente.addItem(nombre, c["id"])
        idx = self.cmb_cliente.findData(current)
        if idx >= 0:
            self.cmb_cliente.setCurrentIndex(idx)
        self.cmb_cliente.blockSignals(False)

    def _reload(self):
        cid = self.cmb_cliente.currentData()
        if cid is None:
            self.table.setRowCount(0)
            return
        docs = m_docs.list_documents_by_client(cid)
        self.table.setRowCount(len(docs))
        self._ids = []
        for i, d in enumerate(docs):
            self._ids.append(d["id"])
            self.table.setItem(
                i, 0, QTableWidgetItem(d["fecha_doc"] or d["fecha_subida"][:10])
            )
            self.table.setItem(i, 1, QTableWidgetItem(d["nombre"]))
            self.table.setItem(i, 2, QTableWidgetItem(d["caso"] or ""))
            size_kb = (d["tamano_bytes"] or 0) / 1024
            self.table.setItem(i, 3, QTableWidgetItem(f"{size_kb:.1f} KB"))
            self.table.setItem(i, 4, QTableWidgetItem(d["descripcion"] or ""))

    def _upload(self):
        cid = self.cmb_cliente.currentData()
        if cid is None:
            QMessageBox.information(self, "Cliente", "Selecciona primero un cliente.")
            return
        files, _ = QFileDialog.getOpenFileNames(
            self, "Seleccionar documentos", "",
            "Documentos (*.pdf *.docx *.doc *.txt *.md *.csv *.png *.jpg *.jpeg)"
        )
        if not files:
            return
        desc, _ = QInputDialog.getText(self, "Descripción", "Descripción (opcional):")
        for f in files:
            try:
                m_docs.import_document(cid, f, descripcion=desc or "")
            except Exception as e:
                QMessageBox.warning(self, "Error", str(e))
        self._reload()

    def _open(self):
        row = self.table.currentRow()
        if row < 0 or row >= len(self._ids):
            return
        path = m_docs.absolute_path(self._ids[row])
        if path and path.exists():
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))
        else:
            QMessageBox.warning(self, "No encontrado", "El archivo no existe.")

    def _delete(self):
        row = self.table.currentRow()
        if row < 0 or row >= len(self._ids):
            return
        if QMessageBox.question(self, "Eliminar", "¿Eliminar este documento?") \
                == QMessageBox.StandardButton.Yes:
            m_docs.delete_document(self._ids[row])
            self._reload()
