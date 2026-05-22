from PyQt6.QtCore import QObject, QThread, Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QComboBox, QFileDialog, QHBoxLayout, QLabel, QMessageBox, QPlainTextEdit,
    QPushButton, QSplitter, QVBoxLayout, QWidget,
)

from app.models import clients as m_clients
from app.models import documents as m_docs
from app.services import ai_agent
from app.services.document_text import extract_text
from app.ui.widgets.common import PrimaryButton, SectionTitle


class AIWorker(QObject):
    finished = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, task, *args, **kwargs):
        super().__init__()
        self.task = task
        self.args = args
        self.kwargs = kwargs

    def run(self):
        try:
            result = self.task(*self.args, **self.kwargs)
            self.finished.emit(result)
        except ai_agent.OllamaUnavailable as e:
            self.error.emit(str(e))
        except Exception as e:
            self.error.emit(f"Error en la IA: {e}")


class AIView(QWidget):
    def __init__(self):
        super().__init__()
        self._thread = None
        self._build()
        self.refresh()

    def _build(self):
        lay = QVBoxLayout(self)
        lay.addWidget(SectionTitle("Asistente de IA local"))

        self.lbl_status = QLabel()
        self.lbl_status.setStyleSheet(
            "background:#FFF3CD; color:#856404; padding:6px; border-radius:4px;"
        )
        lay.addWidget(self.lbl_status)

        # Selección de documento
        sel = QHBoxLayout()
        sel.addWidget(QLabel("Cliente:"))
        self.cmb_cliente = QComboBox()
        self.cmb_cliente.addItem("(Sin cliente)", None)
        sel.addWidget(self.cmb_cliente, 1)
        self.cmb_cliente.currentIndexChanged.connect(self._reload_docs)
        sel.addWidget(QLabel("Documento:"))
        self.cmb_doc = QComboBox()
        sel.addWidget(self.cmb_doc, 1)
        b_pick = QPushButton("Cargar archivo externo...")
        b_pick.clicked.connect(self._pick_file)
        sel.addWidget(b_pick)
        lay.addLayout(sel)

        # Split: texto del documento + chat
        split = QSplitter(Qt.Orientation.Horizontal)

        left = QWidget()
        ll = QVBoxLayout(left)
        ll.addWidget(QLabel("<b>Contenido extraído del documento</b>"))
        self.txt_doc = QPlainTextEdit()
        self.txt_doc.setPlaceholderText("Selecciona un documento o carga un archivo...")
        ll.addWidget(self.txt_doc)
        actions_l = QHBoxLayout()
        b_load = PrimaryButton("Cargar documento seleccionado")
        b_load.clicked.connect(self._load_selected_doc)
        actions_l.addWidget(b_load)
        b_sum = PrimaryButton("Resumir documento")
        b_sum.clicked.connect(self._summarize)
        actions_l.addWidget(b_sum)
        ll.addLayout(actions_l)

        right = QWidget()
        rl = QVBoxLayout(right)
        rl.addWidget(QLabel("<b>Pregunta sobre el documento</b>"))
        self.txt_question = QPlainTextEdit()
        self.txt_question.setFixedHeight(80)
        self.txt_question.setPlaceholderText(
            "Ej: ¿Cuál es la fecha límite para recurrir? ¿Qué partes intervienen?"
        )
        rl.addWidget(self.txt_question)
        b_ask = PrimaryButton("Preguntar")
        b_ask.clicked.connect(self._ask)
        rl.addWidget(b_ask, alignment=Qt.AlignmentFlag.AlignRight)
        rl.addWidget(QLabel("<b>Respuesta</b>"))
        self.txt_answer = QPlainTextEdit()
        self.txt_answer.setReadOnly(True)
        rl.addWidget(self.txt_answer, 1)

        split.addWidget(left)
        split.addWidget(right)
        split.setSizes([500, 500])
        lay.addWidget(split, 1)

    def refresh(self):
        self._check_status()
        self._reload_clients()

    def _check_status(self):
        if ai_agent.is_available():
            modelos = ai_agent.list_models()
            modelo = ai_agent._model()
            ok = modelo in modelos
            color = "#D4EDDA" if ok else "#FFF3CD"
            text_color = "#155724" if ok else "#856404"
            mensaje = (
                f"Ollama detectado · Modelo: <b>{modelo}</b>"
                + ("" if ok else f" (no instalado — ejecuta: ollama pull {modelo})")
                + f" · Modelos disponibles: {', '.join(modelos) or '—'}"
            )
            self.lbl_status.setStyleSheet(
                f"background:{color}; color:{text_color}; padding:6px; border-radius:4px;"
            )
            self.lbl_status.setText(mensaje)
        else:
            self.lbl_status.setStyleSheet(
                "background:#F8D7DA; color:#721C24; padding:6px; border-radius:4px;"
            )
            self.lbl_status.setText(
                "Ollama no detectado. Instálalo desde https://ollama.com y "
                "ejecuta 'ollama pull llama3.1' para poder usar la IA local."
            )

    def _reload_clients(self):
        current = self.cmb_cliente.currentData()
        self.cmb_cliente.blockSignals(True)
        self.cmb_cliente.clear()
        self.cmb_cliente.addItem("(Sin cliente)", None)
        for c in m_clients.list_clients(only_active=False):
            nombre = f"{c['nombre']} {c['apellidos'] or ''}".strip()
            self.cmb_cliente.addItem(nombre, c["id"])
        idx = self.cmb_cliente.findData(current)
        if idx >= 0:
            self.cmb_cliente.setCurrentIndex(idx)
        self.cmb_cliente.blockSignals(False)
        self._reload_docs()

    def _reload_docs(self):
        self.cmb_doc.clear()
        cid = self.cmb_cliente.currentData()
        if cid is None:
            return
        for d in m_docs.list_documents_by_client(cid):
            self.cmb_doc.addItem(d["nombre"], d["id"])

    def _pick_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Archivo", "",
            "Documentos (*.pdf *.docx *.txt *.md *.csv)"
        )
        if not path:
            return
        text = extract_text(path)
        self.txt_doc.setPlainText(text)

    def _load_selected_doc(self):
        doc_id = self.cmb_doc.currentData()
        if doc_id is None:
            QMessageBox.information(self, "Documento", "Selecciona un documento.")
            return
        path = m_docs.absolute_path(doc_id)
        if path is None or not path.exists():
            QMessageBox.warning(self, "Documento", "Archivo no encontrado.")
            return
        text = extract_text(path)
        self.txt_doc.setPlainText(text)

    def _run_ai(self, task, *args):
        if self._thread and self._thread.isRunning():
            QMessageBox.information(self, "IA ocupada", "Espera a que termine la consulta actual.")
            return
        self.txt_answer.setPlainText("Procesando...")
        self._thread = QThread(self)
        self._worker = AIWorker(task, *args)
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.finished.connect(self._on_done)
        self._worker.error.connect(self._on_error)
        self._worker.finished.connect(self._thread.quit)
        self._worker.error.connect(self._thread.quit)
        self._thread.finished.connect(self._worker.deleteLater)
        self._thread.start()

    def _summarize(self):
        text = self.txt_doc.toPlainText().strip()
        if not text:
            QMessageBox.information(self, "Documento vacío",
                                    "Carga un documento primero.")
            return
        self._run_ai(ai_agent.summarize_document, text)

    def _ask(self):
        text = self.txt_doc.toPlainText().strip()
        q = self.txt_question.toPlainText().strip()
        if not text or not q:
            QMessageBox.information(self, "Faltan datos",
                                    "Carga un documento y escribe una pregunta.")
            return
        self._run_ai(ai_agent.ask_about_document, text, q)

    def _on_done(self, result: str):
        self.txt_answer.setPlainText(result)

    def _on_error(self, msg: str):
        self.txt_answer.setPlainText("")
        QMessageBox.warning(self, "IA", msg)
