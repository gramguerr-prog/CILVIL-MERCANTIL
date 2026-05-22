from PyQt6.QtCore import QUrl, Qt
from PyQt6.QtGui import QDesktopServices, QGuiApplication
from PyQt6.QtWidgets import (
    QHBoxLayout, QHeaderView, QMessageBox, QPushButton, QTableWidget,
    QTableWidgetItem, QVBoxLayout, QWidget,
)

from app.models import clients as m_clients
from app.ui.widgets.common import PrimaryButton, SearchBar, SectionTitle


class EmailsView(QWidget):
    def __init__(self):
        super().__init__()
        self._build()
        self.refresh()

    def _build(self):
        lay = QVBoxLayout(self)
        lay.addWidget(SectionTitle("Correos electrónicos de clientes"))

        top = QHBoxLayout()
        self.search = SearchBar("Filtrar...", self._on_search)
        top.addWidget(self.search, 1)
        b_copy = PrimaryButton("Copiar todos al portapapeles")
        b_copy.clicked.connect(self._copy_all)
        top.addWidget(b_copy)
        b_mail = QPushButton("Enviar email al seleccionado")
        b_mail.clicked.connect(self._mail_selected)
        top.addWidget(b_mail)
        lay.addLayout(top)

        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["Cliente", "Email", "ID"])
        self.table.setColumnHidden(2, True)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.ResizeToContents
        )
        lay.addWidget(self.table, 1)

    def refresh(self):
        self._reload("")

    def _on_search(self, text: str):
        self._reload(text)

    def _reload(self, search: str):
        rows = m_clients.list_emails()
        filtered = []
        s = search.lower().strip()
        for r in rows:
            nombre = f"{r['nombre']} {r['apellidos'] or ''}".strip()
            if not s or s in nombre.lower() or s in (r["email"] or "").lower():
                filtered.append((r["id"], nombre, r["email"]))
        self.table.setRowCount(len(filtered))
        for i, (cid, nombre, email) in enumerate(filtered):
            self.table.setItem(i, 0, QTableWidgetItem(nombre))
            self.table.setItem(i, 1, QTableWidgetItem(email))
            self.table.setItem(i, 2, QTableWidgetItem(str(cid)))

    def _copy_all(self):
        emails = [
            self.table.item(i, 1).text()
            for i in range(self.table.rowCount())
            if self.table.item(i, 1)
        ]
        if not emails:
            return
        QGuiApplication.clipboard().setText(", ".join(emails))
        QMessageBox.information(self, "Copiado",
                                f"{len(emails)} correos copiados.")

    def _mail_selected(self):
        row = self.table.currentRow()
        if row < 0:
            return
        email = self.table.item(row, 1).text()
        if email:
            QDesktopServices.openUrl(QUrl(f"mailto:{email}"))
