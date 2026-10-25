from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import (
    QHBoxLayout, QLabel, QListWidget, QListWidgetItem, QMainWindow,
    QStackedWidget, QVBoxLayout, QWidget,
)

from app.config import APP_NAME, APP_VERSION
from app.ui.clients_view import ClientsView
from app.ui.dashboard_view import DashboardView
from app.ui.documents_view import DocumentsView
from app.ui.emails_view import EmailsView
from app.ui.expenses_view import ExpensesView
from app.ui.invoices_view import InvoicesView
from app.ui.ai_view import AIView
from app.ui.settings_view import SettingsView


SECTIONS = [
    ("Panel", "dashboard"),
    ("Clientes", "clients"),
    ("Facturación", "invoices"),
    ("Gastos", "expenses"),
    ("Documentos", "documents"),
    ("Correos", "emails"),
    ("Asistente IA", "ai"),
    ("Ajustes", "settings"),
]


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{APP_NAME} {APP_VERSION}")
        self.resize(1280, 800)
        self._build_menu()
        self._build_ui()

    def _build_menu(self):
        menu = self.menuBar().addMenu("&Archivo")
        salir = QAction("Salir", self)
        salir.setShortcut("Ctrl+Q")
        salir.triggered.connect(self.close)
        menu.addAction(salir)

        ayuda = self.menuBar().addMenu("&Ayuda")
        acerca = QAction("Acerca de", self)
        acerca.triggered.connect(self._show_about)
        ayuda.addAction(acerca)

    def _show_about(self):
        from PyQt6.QtWidgets import QMessageBox
        QMessageBox.information(
            self, "Acerca de",
            f"{APP_NAME} {APP_VERSION}\n\n"
            "CRM y gestión de asuntos jurídicos.\n"
            "Datos almacenados localmente en SQLite.\n"
            "IA local vía Ollama (opcional).",
        )

    def _build_ui(self):
        container = QWidget()
        outer = QHBoxLayout(container)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        self.nav = QListWidget()
        self.nav.setFixedWidth(190)
        self.nav.setStyleSheet(
            "QListWidget { background-color: #2C3E50; border: none; }"
            "QListWidget::item { color: #ECF0F1; padding: 12px 16px; }"
            "QListWidget::item:selected { background-color: #2E86DE; color: white; }"
            "QListWidget::item:hover { background-color: #34495E; }"
        )
        nav_header = QListWidgetItem(APP_NAME)
        f = nav_header.font()
        f.setBold(True)
        f.setPointSize(f.pointSize() + 1)
        nav_header.setFont(f)
        nav_header.setFlags(Qt.ItemFlag.NoItemFlags)
        nav_header.setForeground(Qt.GlobalColor.white)
        self.nav.addItem(nav_header)
        for label, _ in SECTIONS:
            self.nav.addItem(QListWidgetItem(label))

        self.stack = QStackedWidget()
        # placeholder index 0 (corresponds to header)
        self.stack.addWidget(QLabel(""))
        self.dashboard = DashboardView()
        self.clients = ClientsView()
        self.invoices = InvoicesView()
        self.expenses = ExpensesView()
        self.documents = DocumentsView()
        self.emails = EmailsView()
        self.ai = AIView()
        self.settings_view = SettingsView()
        for w in (self.dashboard, self.clients, self.invoices, self.expenses,
                  self.documents, self.emails, self.ai, self.settings_view):
            self.stack.addWidget(w)

        self.nav.currentRowChanged.connect(self._on_nav_change)
        self.nav.setCurrentRow(1)  # Panel por defecto

        # Connections cross-view
        self.clients.client_opened.connect(self._open_client)
        self.invoices.client_link_clicked.connect(self._open_client)

        outer.addWidget(self.nav)

        right = QWidget()
        rlay = QVBoxLayout(right)
        rlay.setContentsMargins(16, 12, 16, 12)
        rlay.setSpacing(8)
        rlay.addWidget(self.stack)
        outer.addWidget(right, 1)

        self.setCentralWidget(container)
        self.statusBar().showMessage("Listo")

    def _on_nav_change(self, row: int) -> None:
        if row <= 0:
            return
        self.stack.setCurrentIndex(row)
        # Refresh on demand
        widget = self.stack.currentWidget()
        if hasattr(widget, "refresh"):
            widget.refresh()

    def _open_client(self, client_id: int) -> None:
        self.nav.setCurrentRow(2)  # Clientes
        self.clients.open_detail(client_id)
