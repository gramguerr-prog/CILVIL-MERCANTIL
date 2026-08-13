from __future__ import annotations

from datetime import date

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtCore import QUrl
from PyQt6.QtWidgets import (
    QApplication, QComboBox, QDateEdit, QDialog, QDoubleSpinBox, QFileDialog,
    QFormLayout, QHBoxLayout, QHeaderView, QInputDialog, QLabel, QLineEdit,
    QMessageBox, QPlainTextEdit, QPushButton, QTabWidget, QTableWidget,
    QTableWidgetItem, QVBoxLayout, QWidget,
)
from PyQt6.QtCore import QDate

from app.models import cases as m_cases
from app.models import clients as m_clients
from app.models import documents as m_docs
from app.models import expenses as m_expenses
from app.models import invoices as m_invoices
from app.models import patrimonio as m_patrimonio
from app.services import ai_agent
from app.ui.patrimonio_tab import FamiliaTab, PatrimonioTab
from app.ui.widgets.common import (
    DangerButton, PrimaryButton, SectionTitle, autofit_columns,
    configure_table, fmt_eur,
)


class ClientDetailDialog(QDialog):
    def __init__(self, parent, client_id: int):
        super().__init__(parent)
        self.client_id = client_id
        self.setMinimumSize(1000, 720)
        self._build()
        self._load()

    def _build(self):
        lay = QVBoxLayout(self)
        self.title = SectionTitle("")
        lay.addWidget(self.title)

        self.tabs = QTabWidget()
        lay.addWidget(self.tabs, 1)

        self.tab_info = self._build_info_tab()
        self.tab_familia = FamiliaTab(self, self.client_id)
        self.tab_patrimonio = PatrimonioTab(self, self.client_id)
        self.tab_seguimiento = self._build_followup_tab()
        self.tab_docs = self._build_docs_tab()
        self.tab_facturacion = self._build_billing_tab()
        self.tab_gastos = self._build_expenses_tab()
        self.tab_comercial = self._build_commercial_tab()

        self.tabs.addTab(self.tab_info, "Información general")
        self.tabs.addTab(self.tab_familia, "Familia")
        self.tabs.addTab(self.tab_patrimonio, "Patrimonio")
        self.tabs.addTab(self.tab_seguimiento, "Seguimiento")
        self.tabs.addTab(self.tab_docs, "Documentos")
        self.tabs.addTab(self.tab_facturacion, "Facturación y pagos")
        self.tabs.addTab(self.tab_gastos, "Gastos")
        self.tabs.addTab(self.tab_comercial, "Análisis comercial")

        cerrar = QPushButton("Cerrar")
        cerrar.clicked.connect(self.accept)
        bottom = QHBoxLayout()
        bottom.addStretch(1)
        bottom.addWidget(cerrar)
        lay.addLayout(bottom)

    # ---------- Tab: Info ----------
    def _build_info_tab(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)

        form = QFormLayout()
        self.in_nombre = QLineEdit()
        self.in_apellidos = QLineEdit()
        self.in_nif = QLineEdit()
        self.in_tipo = QComboBox()
        self.in_tipo.addItems(["particular", "empresa", "autonomo"])
        self.in_email = QLineEdit()
        self.in_tel = QLineEdit()
        self.in_dir = QLineEdit()
        self.in_ciudad = QLineEdit()
        self.in_cp = QLineEdit()
        self.in_pais = QLineEdit()
        from PyQt6.QtWidgets import QCheckBox
        self.in_irpf_nuevo = QCheckBox("Retención IRPF reducida (7 %)")
        self.in_activo = QCheckBox("Activo")
        self.in_notas = QPlainTextEdit()
        self.in_notas.setFixedHeight(100)

        form.addRow("Nombre", self.in_nombre)
        form.addRow("Apellidos", self.in_apellidos)
        form.addRow("NIF/CIF", self.in_nif)
        form.addRow("Tipo", self.in_tipo)
        form.addRow("Email", self.in_email)
        form.addRow("Teléfono", self.in_tel)
        form.addRow("Dirección", self.in_dir)
        form.addRow("Ciudad", self.in_ciudad)
        form.addRow("Código postal", self.in_cp)
        form.addRow("País", self.in_pais)
        form.addRow("", self.in_irpf_nuevo)
        form.addRow("", self.in_activo)
        form.addRow("Notas internas", self.in_notas)
        lay.addLayout(form)

        self.lbl_balance = QLabel()
        self.lbl_balance.setStyleSheet(
            "background: #ECF0F1; padding: 8px; border-radius: 4px;"
        )
        lay.addWidget(self.lbl_balance)

        btns = QHBoxLayout()
        btns.addStretch(1)
        b = PrimaryButton("Guardar cambios")
        b.clicked.connect(self._save_info)
        btns.addWidget(b)
        lay.addLayout(btns)
        return w

    # ---------- Tab: Seguimiento (cases + events) ----------
    def _build_followup_tab(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)

        # Cases
        row1 = QHBoxLayout()
        row1.addWidget(QLabel("<b>Asuntos del cliente</b>"))
        row1.addStretch(1)
        b_new = PrimaryButton("+ Nuevo asunto")
        b_new.clicked.connect(self._new_case)
        b_edit = QPushButton("Editar asunto")
        b_edit.clicked.connect(self._edit_case)
        b_del = DangerButton("Eliminar asunto")
        b_del.clicked.connect(self._del_case)
        row1.addWidget(b_new)
        row1.addWidget(b_edit)
        row1.addWidget(b_del)
        lay.addLayout(row1)

        self.tbl_cases = QTableWidget(0, 6)
        self.tbl_cases.setHorizontalHeaderLabels(
            ["#", "Referencia", "Título", "Materia", "Estado", "Inicio"]
        )
        self.tbl_cases.verticalHeader().setVisible(False)
        self.tbl_cases.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tbl_cases.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        configure_table(self.tbl_cases, elastic=2)
        self.tbl_cases.itemSelectionChanged.connect(self._reload_events)
        lay.addWidget(self.tbl_cases, 1)

        # Events
        row2 = QHBoxLayout()
        row2.addWidget(QLabel("<b>Cronología del asunto seleccionado</b>"))
        row2.addStretch(1)
        b_event = PrimaryButton("+ Añadir entrada")
        b_event.clicked.connect(self._add_event)
        b_event_del = DangerButton("Eliminar entrada")
        b_event_del.clicked.connect(self._del_event)
        row2.addWidget(b_event)
        row2.addWidget(b_event_del)
        lay.addLayout(row2)

        self.tbl_events = QTableWidget(0, 4)
        self.tbl_events.setHorizontalHeaderLabels(
            ["Fecha", "Tipo", "Título", "Detalle"]
        )
        self.tbl_events.verticalHeader().setVisible(False)
        self.tbl_events.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        configure_table(self.tbl_events, elastic=2)
        lay.addWidget(self.tbl_events, 1)
        return w

    # ---------- Tab: Documents ----------
    def _build_docs_tab(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        row = QHBoxLayout()
        row.addWidget(QLabel("<b>Documentos del cliente (orden cronológico)</b>"))
        row.addStretch(1)
        b = PrimaryButton("+ Subir documento")
        b.clicked.connect(self._upload_doc)
        b_open = QPushButton("Abrir")
        b_open.clicked.connect(self._open_doc)
        b_del = DangerButton("Eliminar")
        b_del.clicked.connect(self._del_doc)
        row.addWidget(b)
        row.addWidget(b_open)
        row.addWidget(b_del)
        lay.addLayout(row)

        self.tbl_docs = QTableWidget(0, 5)
        self.tbl_docs.setHorizontalHeaderLabels(
            ["Fecha doc", "Nombre", "Asunto", "Tamaño", "Descripción"]
        )
        self.tbl_docs.verticalHeader().setVisible(False)
        self.tbl_docs.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        configure_table(self.tbl_docs, elastic=1)
        self.tbl_docs.doubleClicked.connect(self._open_doc)
        lay.addWidget(self.tbl_docs, 1)
        return w

    # ---------- Tab: Billing ----------
    def _build_billing_tab(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)

        row = QHBoxLayout()
        row.addWidget(QLabel("<b>Facturas emitidas</b>"))
        row.addStretch(1)
        b_inv = PrimaryButton("+ Nueva factura")
        b_inv.clicked.connect(self._new_invoice_for_client)
        row.addWidget(b_inv)
        lay.addLayout(row)

        self.tbl_invoices = QTableWidget(0, 6)
        self.tbl_invoices.setHorizontalHeaderLabels(
            ["Nº", "Fecha", "Base", "IVA", "IRPF", "Total"]
        )
        self.tbl_invoices.verticalHeader().setVisible(False)
        self.tbl_invoices.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        configure_table(self.tbl_invoices, elastic=0)
        lay.addWidget(self.tbl_invoices, 1)

        row2 = QHBoxLayout()
        row2.addWidget(QLabel("<b>Pagos recibidos</b>"))
        row2.addStretch(1)
        b_pay = PrimaryButton("+ Registrar pago")
        b_pay.clicked.connect(self._add_payment)
        b_pay_del = DangerButton("Eliminar pago")
        b_pay_del.clicked.connect(self._del_payment)
        row2.addWidget(b_pay)
        row2.addWidget(b_pay_del)
        lay.addLayout(row2)

        self.tbl_payments = QTableWidget(0, 5)
        self.tbl_payments.setHorizontalHeaderLabels(
            ["Fecha", "Importe", "Factura", "Método", "Notas"]
        )
        self.tbl_payments.verticalHeader().setVisible(False)
        self.tbl_payments.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        configure_table(self.tbl_payments, elastic=4)
        lay.addWidget(self.tbl_payments, 1)

        self.lbl_bal_pestaña = QLabel()
        self.lbl_bal_pestaña.setStyleSheet(
            "background: #ECF0F1; padding: 8px; border-radius: 4px;"
        )
        lay.addWidget(self.lbl_bal_pestaña)
        return w

    # ---------- Tab: Expenses ----------
    def _build_expenses_tab(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        row = QHBoxLayout()
        row.addWidget(QLabel("<b>Gastos imputados a este cliente</b>"))
        row.addStretch(1)
        b = PrimaryButton("+ Nuevo gasto del cliente")
        b.clicked.connect(self._add_expense_for_client)
        row.addWidget(b)
        lay.addLayout(row)
        self.tbl_expenses = QTableWidget(0, 6)
        self.tbl_expenses.setHorizontalHeaderLabels(
            ["Fecha", "Concepto", "Categoría", "Base", "Total", "Repercutible"]
        )
        self.tbl_expenses.verticalHeader().setVisible(False)
        self.tbl_expenses.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        configure_table(self.tbl_expenses, elastic=1)
        lay.addWidget(self.tbl_expenses, 1)
        return w

    # ---------- Tab: Commercial ----------
    def _build_commercial_tab(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.addWidget(QLabel(
            "<b>Análisis personalizado con IA</b><br>"
            "Cruza la ficha, la familia, el patrimonio, los asuntos y la "
            "facturación de este cliente. El motor de IA se elige en "
            "<i>Ajustes &gt; Inteligencia artificial</i>."
        ))
        row = QHBoxLayout()
        b_perfil = PrimaryButton("Analizar perfil")
        b_perfil.clicked.connect(self._generate_profile)
        b = PrimaryButton("Propuesta comercial")
        b.clicked.connect(self._generate_proposal)
        row.addWidget(b_perfil)
        row.addWidget(b)
        row.addStretch(1)
        self.lbl_ia_uso = QLabel()
        self.lbl_ia_uso.setStyleSheet("color:#7F8C8D; font-size:11px;")
        row.addWidget(self.lbl_ia_uso)
        lay.addLayout(row)
        self.txt_comercial = QPlainTextEdit()
        self.txt_comercial.setPlaceholderText(
            "Aquí aparecerá la propuesta. Puedes editarla y guardarla."
        )
        lay.addWidget(self.txt_comercial, 1)
        return w

    # ============ DATA ============

    def _load(self):
        c = m_clients.get_client(self.client_id)
        if c is None:
            QMessageBox.critical(self, "Error", "Cliente no encontrado")
            self.reject()
            return
        nombre = f"{c['nombre']} {c['apellidos'] or ''}".strip()
        self.title.setText(f"Cliente: {nombre}")
        self.in_nombre.setText(c["nombre"] or "")
        self.in_apellidos.setText(c["apellidos"] or "")
        self.in_nif.setText(c["nif"] or "")
        idx = self.in_tipo.findText(c["tipo"] or "particular")
        if idx >= 0:
            self.in_tipo.setCurrentIndex(idx)
        self.in_email.setText(c["email"] or "")
        self.in_tel.setText(c["telefono"] or "")
        self.in_dir.setText(c["direccion"] or "")
        self.in_ciudad.setText(c["ciudad"] or "")
        self.in_cp.setText(c["codigo_postal"] or "")
        self.in_pais.setText(c["pais"] or "España")
        self.in_irpf_nuevo.setChecked(bool(c["irpf_nuevo"]))
        self.in_activo.setChecked(bool(c["activo"]))
        self.in_notas.setPlainText(c["notas"] or "")
        self._reload_balance()
        self._reload_cases()
        self._reload_docs()
        self._reload_invoices()
        self._reload_expenses()
        if hasattr(self, "tab_familia"):
            self.tab_familia.reload()
        if hasattr(self, "tab_patrimonio"):
            self.tab_patrimonio.reload()

    def _reload_balance(self):
        b = m_clients.client_balance(self.client_id)
        text = (
            f"<b>Facturado:</b> {fmt_eur(b['facturado'])}   "
            f"<b>Cobrado:</b> {fmt_eur(b['cobrado'])}   "
            f"<b style='color:{'#C0392B' if b['pendiente']>0 else '#27AE60'}'>"
            f"Pendiente: {fmt_eur(b['pendiente'])}</b>"
        )
        self.lbl_balance.setText(text)
        self.lbl_bal_pestaña.setText(text)

    def _save_info(self):
        data = {
            "nombre": self.in_nombre.text().strip(),
            "apellidos": self.in_apellidos.text().strip() or None,
            "nif": self.in_nif.text().strip() or None,
            "tipo": self.in_tipo.currentText(),
            "email": self.in_email.text().strip() or None,
            "telefono": self.in_tel.text().strip() or None,
            "direccion": self.in_dir.text().strip() or None,
            "ciudad": self.in_ciudad.text().strip() or None,
            "codigo_postal": self.in_cp.text().strip() or None,
            "pais": self.in_pais.text().strip() or None,
            "irpf_nuevo": 1 if self.in_irpf_nuevo.isChecked() else 0,
            "activo": 1 if self.in_activo.isChecked() else 0,
            "notas": self.in_notas.toPlainText().strip() or None,
        }
        if not data["nombre"]:
            QMessageBox.warning(self, "Nombre vacío", "El nombre es obligatorio.")
            return
        m_clients.update_client(self.client_id, data)
        self._load()
        QMessageBox.information(self, "Guardado", "Datos del cliente actualizados.")

    # --- Cases ---

    def _reload_cases(self):
        cases = m_cases.list_cases_by_client(self.client_id)
        self.tbl_cases.setRowCount(len(cases))
        self._case_ids = []
        for i, c in enumerate(cases):
            self._case_ids.append(c["id"])
            self.tbl_cases.setItem(i, 0, QTableWidgetItem(str(c["id"])))
            self.tbl_cases.setItem(i, 1, QTableWidgetItem(c["referencia"] or ""))
            self.tbl_cases.setItem(i, 2, QTableWidgetItem(c["titulo"] or ""))
            self.tbl_cases.setItem(i, 3, QTableWidgetItem(c["materia"] or ""))
            self.tbl_cases.setItem(i, 4, QTableWidgetItem(c["estado"] or ""))
            self.tbl_cases.setItem(i, 5, QTableWidgetItem(c["fecha_inicio"] or ""))
        autofit_columns(self.tbl_cases)
        if cases:
            self.tbl_cases.selectRow(0)

    def _selected_case_id(self) -> int | None:
        row = self.tbl_cases.currentRow()
        if row < 0 or row >= len(self._case_ids):
            return None
        return self._case_ids[row]

    def _new_case(self):
        dlg = CaseEditDialog(self, client_id=self.client_id)
        if dlg.exec():
            self._reload_cases()

    def _edit_case(self):
        cid = self._selected_case_id()
        if cid is None:
            return
        dlg = CaseEditDialog(self, client_id=self.client_id, case_id=cid)
        if dlg.exec():
            self._reload_cases()

    def _del_case(self):
        cid = self._selected_case_id()
        if cid is None:
            return
        ans = QMessageBox.question(
            self, "Eliminar asunto",
            "¿Eliminar este asunto y todas sus entradas de seguimiento?",
        )
        if ans == QMessageBox.StandardButton.Yes:
            m_cases.delete_case(cid)
            self._reload_cases()
            self.tbl_events.setRowCount(0)

    def _reload_events(self):
        cid = self._selected_case_id()
        if cid is None:
            self.tbl_events.setRowCount(0)
            return
        events = m_cases.list_events(cid)
        self.tbl_events.setRowCount(len(events))
        self._event_ids = []
        for i, e in enumerate(events):
            self._event_ids.append(e["id"])
            self.tbl_events.setItem(i, 0, QTableWidgetItem(e["fecha"] or ""))
            self.tbl_events.setItem(i, 1, QTableWidgetItem(e["tipo"] or ""))
            self.tbl_events.setItem(i, 2, QTableWidgetItem(e["titulo"] or ""))
            self.tbl_events.setItem(i, 3, QTableWidgetItem(e["detalle"] or ""))
        autofit_columns(self.tbl_events)

    def _add_event(self):
        cid = self._selected_case_id()
        if cid is None:
            QMessageBox.information(self, "Selecciona un asunto",
                                    "Primero crea o selecciona un asunto.")
            return
        dlg = EventEditDialog(self, case_id=cid)
        if dlg.exec():
            self._reload_events()

    def _del_event(self):
        row = self.tbl_events.currentRow()
        if row < 0 or row >= len(self._event_ids):
            return
        eid = self._event_ids[row]
        ans = QMessageBox.question(self, "Eliminar", "¿Eliminar la entrada?")
        if ans == QMessageBox.StandardButton.Yes:
            m_cases.delete_event(eid)
            self._reload_events()

    # --- Documents ---

    def _reload_docs(self):
        docs = m_docs.list_documents_by_client(self.client_id)
        self.tbl_docs.setRowCount(len(docs))
        self._doc_ids = []
        for i, d in enumerate(docs):
            self._doc_ids.append(d["id"])
            size_kb = (d["tamano_bytes"] or 0) / 1024
            self.tbl_docs.setItem(
                i, 0, QTableWidgetItem(d["fecha_doc"] or d["fecha_subida"][:10])
            )
            self.tbl_docs.setItem(i, 1, QTableWidgetItem(d["nombre"]))
            self.tbl_docs.setItem(i, 2, QTableWidgetItem(d["caso"] or ""))
            self.tbl_docs.setItem(i, 3, QTableWidgetItem(f"{size_kb:.1f} KB"))
            self.tbl_docs.setItem(i, 4, QTableWidgetItem(d["descripcion"] or ""))
        autofit_columns(self.tbl_docs)

    def _upload_doc(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, "Selecciona documento(s) para subir", "",
            "Documentos (*.pdf *.docx *.doc *.txt *.md *.csv *.png *.jpg *.jpeg)"
        )
        if not files:
            return
        # Vincular opcionalmente a un asunto
        cases = m_cases.list_cases_by_client(self.client_id)
        case_id = None
        if cases:
            names = ["(Sin asunto)"] + [f"{c['id']} · {c['titulo']}" for c in cases]
            choice, ok = QInputDialog.getItem(
                self, "Vincular a asunto", "Asunto:", names, 0, False
            )
            if ok and choice != "(Sin asunto)":
                case_id = int(choice.split(" · ", 1)[0])
        desc, _ = QInputDialog.getText(self, "Descripción", "Descripción (opcional):")
        for f in files:
            try:
                m_docs.import_document(
                    self.client_id, f, case_id=case_id, descripcion=desc or ""
                )
            except Exception as e:
                QMessageBox.warning(self, "Error al subir", f"{f}\n{e}")
        self._reload_docs()

    def _open_doc(self):
        row = self.tbl_docs.currentRow()
        if row < 0 or row >= len(self._doc_ids):
            return
        path = m_docs.absolute_path(self._doc_ids[row])
        if path is None or not path.exists():
            QMessageBox.warning(self, "No encontrado", "El archivo no existe.")
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))

    def _del_doc(self):
        row = self.tbl_docs.currentRow()
        if row < 0 or row >= len(self._doc_ids):
            return
        ans = QMessageBox.question(self, "Eliminar", "¿Eliminar este documento?")
        if ans == QMessageBox.StandardButton.Yes:
            m_docs.delete_document(self._doc_ids[row])
            self._reload_docs()

    # --- Invoices & payments ---

    def _reload_invoices(self):
        invs = m_invoices.list_invoices_by_client(self.client_id)
        self.tbl_invoices.setRowCount(len(invs))
        for i, inv in enumerate(invs):
            self.tbl_invoices.setItem(i, 0, QTableWidgetItem(inv["numero"]))
            self.tbl_invoices.setItem(i, 1, QTableWidgetItem(inv["fecha_emision"]))
            self.tbl_invoices.setItem(i, 2, QTableWidgetItem(fmt_eur(inv["base_imponible"])))
            self.tbl_invoices.setItem(i, 3, QTableWidgetItem(fmt_eur(inv["importe_iva"])))
            self.tbl_invoices.setItem(i, 4, QTableWidgetItem(fmt_eur(inv["importe_irpf"])))
            self.tbl_invoices.setItem(i, 5, QTableWidgetItem(fmt_eur(inv["total"])))
        autofit_columns(self.tbl_invoices)
        pays = m_invoices.list_payments_by_client(self.client_id)
        self.tbl_payments.setRowCount(len(pays))
        self._pay_ids = []
        for i, p in enumerate(pays):
            self._pay_ids.append(p["id"])
            self.tbl_payments.setItem(i, 0, QTableWidgetItem(p["fecha"]))
            self.tbl_payments.setItem(i, 1, QTableWidgetItem(fmt_eur(p["importe"])))
            self.tbl_payments.setItem(i, 2, QTableWidgetItem(p["numero"] or ""))
            self.tbl_payments.setItem(i, 3, QTableWidgetItem(p["metodo"] or ""))
            self.tbl_payments.setItem(i, 4, QTableWidgetItem(p["notas"] or ""))
        autofit_columns(self.tbl_payments)
        self._reload_balance()

    def _new_invoice_for_client(self):
        from app.ui.invoice_editor import InvoiceEditor
        dlg = InvoiceEditor(self, client_id=self.client_id)
        if dlg.exec():
            self._reload_invoices()

    def _add_payment(self):
        dlg = PaymentDialog(self, client_id=self.client_id)
        if dlg.exec():
            self._reload_invoices()

    def _del_payment(self):
        row = self.tbl_payments.currentRow()
        if row < 0 or row >= len(self._pay_ids):
            return
        ans = QMessageBox.question(self, "Eliminar", "¿Eliminar este pago?")
        if ans == QMessageBox.StandardButton.Yes:
            m_invoices.delete_payment(self._pay_ids[row])
            self._reload_invoices()

    # --- Expenses ---

    def _reload_expenses(self):
        exps = m_expenses.list_expenses_by_client(self.client_id)
        self.tbl_expenses.setRowCount(len(exps))
        for i, e in enumerate(exps):
            self.tbl_expenses.setItem(i, 0, QTableWidgetItem(e["fecha"]))
            self.tbl_expenses.setItem(i, 1, QTableWidgetItem(e["concepto"]))
            self.tbl_expenses.setItem(i, 2, QTableWidgetItem(e["categoria"] or ""))
            self.tbl_expenses.setItem(i, 3, QTableWidgetItem(fmt_eur(e["base_imponible"])))
            self.tbl_expenses.setItem(i, 4, QTableWidgetItem(fmt_eur(e["total"])))
            self.tbl_expenses.setItem(i, 5, QTableWidgetItem("Sí" if e["repercutible"] else "No"))
        autofit_columns(self.tbl_expenses)

    def _add_expense_for_client(self):
        from app.ui.expense_edit_dialog import ExpenseEditDialog
        dlg = ExpenseEditDialog(self, client_id=self.client_id)
        if dlg.exec():
            self._reload_expenses()

    # --- Commercial proposal ---

    def _generate_profile(self):
        self._run_ia(ai_agent.analizar_perfil, "análisis de perfil")

    def _generate_proposal(self):
        self._run_ia(ai_agent.propuesta_comercial, "propuesta comercial")

    def _run_ia(self, funcion, etiqueta: str):
        """Consulta a la IA. Bloquea la ficha mientras dura, que es aceptable
        porque el usuario acaba de pedirla explícitamente."""
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        self.txt_comercial.setPlainText(f"Generando {etiqueta}…")
        self.lbl_ia_uso.setText("")
        try:
            respuesta = funcion(self.client_id)
        except ai_agent.IAError as e:
            QApplication.restoreOverrideCursor()
            self.txt_comercial.setPlainText("")
            QMessageBox.information(self, "IA no disponible", str(e))
            return
        except Exception as e:
            QApplication.restoreOverrideCursor()
            self.txt_comercial.setPlainText("")
            QMessageBox.critical(self, "Error de la IA", str(e))
            return
        QApplication.restoreOverrideCursor()
        self.txt_comercial.setPlainText(respuesta.texto)
        self.lbl_ia_uso.setText(respuesta.resumen_uso())
        if respuesta.aviso:
            QMessageBox.warning(self, "Aviso de la IA", respuesta.aviso)


# ===== Sub-dialogs =====

class CaseEditDialog(QDialog):
    def __init__(self, parent, client_id: int, case_id: int | None = None):
        super().__init__(parent)
        self.client_id = client_id
        self.case_id = case_id
        self.setWindowTitle("Asunto")
        self.setMinimumWidth(520)
        self._build()
        if case_id:
            self._load()

    def _build(self):
        from PyQt6.QtWidgets import QDialogButtonBox
        lay = QVBoxLayout(self)
        form = QFormLayout()
        self.in_ref = QLineEdit()
        self.in_titulo = QLineEdit()
        self.in_materia = QComboBox()
        self.in_materia.setEditable(True)
        self.in_materia.addItems(["civil", "mercantil", "penal", "laboral",
                                  "administrativo", "familia", "fiscal", "extranjería"])
        self.in_estado = QComboBox()
        self.in_estado.addItems(["abierto", "suspendido", "cerrado"])
        self.in_juzgado = QLineEdit()
        self.in_autos = QLineEdit()
        self.in_inicio = QDateEdit(calendarPopup=True)
        self.in_inicio.setDate(QDate.currentDate())
        self.in_cierre = QDateEdit(calendarPopup=True)
        self.in_cierre.setSpecialValueText(" ")
        self.in_cierre.setDate(QDate(2000, 1, 1))
        self.in_desc = QPlainTextEdit()
        self.in_desc.setFixedHeight(80)
        form.addRow("Referencia interna", self.in_ref)
        form.addRow("Título*", self.in_titulo)
        form.addRow("Materia", self.in_materia)
        form.addRow("Estado", self.in_estado)
        form.addRow("Juzgado", self.in_juzgado)
        form.addRow("Nº autos", self.in_autos)
        form.addRow("Fecha inicio", self.in_inicio)
        form.addRow("Fecha cierre", self.in_cierre)
        form.addRow("Descripción", self.in_desc)
        lay.addLayout(form)
        bb = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        bb.accepted.connect(self._save)
        bb.rejected.connect(self.reject)
        lay.addWidget(bb)

    def _load(self):
        c = m_cases.get_case(self.case_id)
        if not c:
            return
        self.in_ref.setText(c["referencia"] or "")
        self.in_titulo.setText(c["titulo"] or "")
        if c["materia"]:
            self.in_materia.setCurrentText(c["materia"])
        idx = self.in_estado.findText(c["estado"] or "abierto")
        if idx >= 0:
            self.in_estado.setCurrentIndex(idx)
        self.in_juzgado.setText(c["juzgado"] or "")
        self.in_autos.setText(c["numero_autos"] or "")
        if c["fecha_inicio"]:
            self.in_inicio.setDate(QDate.fromString(c["fecha_inicio"], "yyyy-MM-dd"))
        if c["fecha_cierre"]:
            self.in_cierre.setDate(QDate.fromString(c["fecha_cierre"], "yyyy-MM-dd"))
        self.in_desc.setPlainText(c["descripcion"] or "")

    def _save(self):
        if not self.in_titulo.text().strip():
            QMessageBox.warning(self, "Título", "El título es obligatorio")
            return
        cierre = self.in_cierre.date().toString("yyyy-MM-dd")
        if cierre == "2000-01-01":
            cierre = None
        data = {
            "client_id": self.client_id,
            "referencia": self.in_ref.text().strip() or None,
            "titulo": self.in_titulo.text().strip(),
            "materia": self.in_materia.currentText().strip() or None,
            "estado": self.in_estado.currentText(),
            "juzgado": self.in_juzgado.text().strip() or None,
            "numero_autos": self.in_autos.text().strip() or None,
            "fecha_inicio": self.in_inicio.date().toString("yyyy-MM-dd"),
            "fecha_cierre": cierre,
            "descripcion": self.in_desc.toPlainText().strip() or None,
        }
        if self.case_id:
            m_cases.update_case(self.case_id, data)
        else:
            m_cases.create_case(data)
        self.accept()


class EventEditDialog(QDialog):
    def __init__(self, parent, case_id: int):
        super().__init__(parent)
        self.case_id = case_id
        self.setWindowTitle("Nueva entrada de seguimiento")
        self.setMinimumWidth(480)
        from PyQt6.QtWidgets import QDialogButtonBox
        lay = QVBoxLayout(self)
        form = QFormLayout()
        self.in_fecha = QDateEdit(calendarPopup=True)
        self.in_fecha.setDate(QDate.currentDate())
        self.in_tipo = QComboBox()
        self.in_tipo.setEditable(True)
        self.in_tipo.addItems(["nota", "audiencia", "escrito presentado",
                               "resolución", "llamada", "reunión", "plazo"])
        self.in_titulo = QLineEdit()
        self.in_detalle = QPlainTextEdit()
        form.addRow("Fecha", self.in_fecha)
        form.addRow("Tipo", self.in_tipo)
        form.addRow("Título*", self.in_titulo)
        form.addRow("Detalle", self.in_detalle)
        lay.addLayout(form)
        bb = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        bb.accepted.connect(self._save)
        bb.rejected.connect(self.reject)
        lay.addWidget(bb)

    def _save(self):
        if not self.in_titulo.text().strip():
            QMessageBox.warning(self, "Título", "El título es obligatorio")
            return
        m_cases.add_event(
            self.case_id,
            self.in_tipo.currentText().strip(),
            self.in_titulo.text().strip(),
            self.in_detalle.toPlainText().strip(),
            fecha=self.in_fecha.date().toString("yyyy-MM-dd"),
        )
        self.accept()


class PaymentDialog(QDialog):
    def __init__(self, parent, client_id: int):
        super().__init__(parent)
        self.client_id = client_id
        self.setWindowTitle("Registrar pago")
        self.setMinimumWidth(420)
        from PyQt6.QtWidgets import QDialogButtonBox
        lay = QVBoxLayout(self)
        form = QFormLayout()
        self.in_fecha = QDateEdit(calendarPopup=True)
        self.in_fecha.setDate(QDate.currentDate())
        self.in_importe = QDoubleSpinBox()
        self.in_importe.setMaximum(10_000_000)
        self.in_importe.setDecimals(2)
        self.in_metodo = QComboBox()
        self.in_metodo.setEditable(True)
        self.in_metodo.addItems(["transferencia", "efectivo", "tarjeta",
                                 "bizum", "domiciliación", "cheque"])
        self.in_factura = QComboBox()
        self.in_factura.addItem("(Sin factura asignada)", None)
        for inv in m_invoices.list_invoices_by_client(client_id):
            self.in_factura.addItem(f"{inv['numero']} · {fmt_eur(inv['total'])}", inv["id"])
        self.in_notas = QLineEdit()
        form.addRow("Fecha", self.in_fecha)
        form.addRow("Importe*", self.in_importe)
        form.addRow("Método", self.in_metodo)
        form.addRow("Factura", self.in_factura)
        form.addRow("Notas", self.in_notas)
        lay.addLayout(form)
        bb = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        bb.accepted.connect(self._save)
        bb.rejected.connect(self.reject)
        lay.addWidget(bb)

    def _save(self):
        if self.in_importe.value() <= 0:
            QMessageBox.warning(self, "Importe", "Importe debe ser mayor que 0")
            return
        m_invoices.add_payment(
            self.client_id,
            float(self.in_importe.value()),
            self.in_fecha.date().toString("yyyy-MM-dd"),
            self.in_metodo.currentText(),
            invoice_id=self.in_factura.currentData(),
            notas=self.in_notas.text().strip(),
        )
        self.accept()
