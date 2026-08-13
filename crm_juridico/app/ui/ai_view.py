"""Sección «Asistente IA»: consultas, análisis de clientes, auditoría y documentos."""
from __future__ import annotations

from PyQt6.QtCore import QObject, QThread, Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QComboBox, QFileDialog, QHBoxLayout, QLabel, QMessageBox, QPlainTextEdit,
    QPushButton, QSplitter, QTabWidget, QTableWidget, QTableWidgetItem,
    QVBoxLayout, QWidget,
)

from app.models import clients as m_clients
from app.models import documents as m_docs
from app.services import ai_agent, auditoria
from app.services.ai_provider import IAError, RespuestaIA, proveedor_activo
from app.services.document_text import extract_text
from app.ui.widgets.common import (
    PrimaryButton, SectionTitle, autofit_columns, configure_table,
)

_COLOR_SEVERIDAD = {"alta": "#E74C3C", "media": "#E67E22", "baja": "#7F8C8D"}


class _Trabajo(QObject):
    """Ejecuta una llamada a la IA fuera del hilo de la interfaz."""
    terminado = pyqtSignal(object)
    fallido = pyqtSignal(str)

    def __init__(self, funcion, *args, **kwargs):
        super().__init__()
        self._funcion, self._args, self._kwargs = funcion, args, kwargs

    def run(self):
        try:
            self.terminado.emit(self._funcion(*self._args, **self._kwargs))
        except IAError as e:
            self.fallido.emit(str(e))
        except Exception as e:
            self.fallido.emit(f"Error inesperado: {e}")


class _PanelIA(QWidget):
    """Base con salida de texto y ejecución en segundo plano."""

    def __init__(self, al_terminar=None):
        super().__init__()
        self._hilo: QThread | None = None
        self._al_terminar = al_terminar
        self.salida = QPlainTextEdit()
        self.salida.setReadOnly(True)
        self.estado = QLabel()
        self.estado.setStyleSheet("color: #7F8C8D; font-size: 11px;")

    def ocupado(self) -> bool:
        return self._hilo is not None and self._hilo.isRunning()

    def lanzar(self, funcion, *args, **kwargs):
        if self.ocupado():
            QMessageBox.information(
                self, "IA ocupada",
                "Espera a que termine la consulta que ya está en marcha."
            )
            return
        self.salida.setPlainText("Consultando a la IA…")
        self.estado.setText("Procesando. Puede tardar según el modelo.")
        self._hilo = QThread(self)
        self._trabajo = _Trabajo(funcion, *args, **kwargs)
        self._trabajo.moveToThread(self._hilo)
        self._hilo.started.connect(self._trabajo.run)
        self._trabajo.terminado.connect(self._ok)
        self._trabajo.fallido.connect(self._error)
        self._trabajo.terminado.connect(self._hilo.quit)
        self._trabajo.fallido.connect(self._hilo.quit)
        self._hilo.finished.connect(self._trabajo.deleteLater)
        self._hilo.start()

    def _ok(self, respuesta: RespuestaIA):
        self.salida.setPlainText(respuesta.texto or "(respuesta vacía)")
        self.estado.setText(respuesta.resumen_uso())
        if respuesta.aviso:
            QMessageBox.warning(self, "Aviso de la IA", respuesta.aviso)
        if self._al_terminar:
            self._al_terminar(respuesta)

    def _error(self, mensaje: str):
        self.salida.setPlainText("")
        self.estado.setText("La consulta no se ha completado.")
        QMessageBox.warning(self, "IA", mensaje)


# --------------------------------------------------------------- consulta


class _PanelConsulta(_PanelIA):
    def __init__(self):
        super().__init__()
        lay = QVBoxLayout(self)
        lay.addWidget(QLabel(
            "Pregunta lo que quieras sobre derecho, redacción de escritos o "
            "gestión del despacho. Para preguntas sobre un cliente concreto, "
            "usa la pestaña «Cliente»."
        ))
        self.pregunta = QPlainTextEdit()
        self.pregunta.setFixedHeight(110)
        self.pregunta.setPlaceholderText(
            "Ej.: ¿Qué plazo tengo para recurrir en apelación una sentencia de "
            "juicio ordinario y desde cuándo cuenta?"
        )
        lay.addWidget(self.pregunta)
        fila = QHBoxLayout()
        b = PrimaryButton("Preguntar")
        b.clicked.connect(self._preguntar)
        fila.addWidget(b)
        fila.addStretch(1)
        fila.addWidget(self.estado)
        lay.addLayout(fila)
        lay.addWidget(self.salida, 1)

    def _preguntar(self):
        texto = self.pregunta.toPlainText().strip()
        if not texto:
            QMessageBox.information(self, "Pregunta", "Escribe una pregunta.")
            return
        self.lanzar(ai_agent.consulta_libre, texto)


# ---------------------------------------------------------------- cliente


class _PanelCliente(_PanelIA):
    def __init__(self):
        super().__init__()
        lay = QVBoxLayout(self)
        fila = QHBoxLayout()
        fila.addWidget(QLabel("Cliente:"))
        self.cmb = QComboBox()
        fila.addWidget(self.cmb, 1)
        b_perfil = PrimaryButton("Analizar perfil")
        b_perfil.clicked.connect(self._perfil)
        b_comercial = PrimaryButton("Propuesta comercial")
        b_comercial.clicked.connect(self._comercial)
        b_datos = QPushButton("Ver datos enviados")
        b_datos.clicked.connect(self._ver_datos)
        fila.addWidget(b_perfil)
        fila.addWidget(b_comercial)
        fila.addWidget(b_datos)
        lay.addLayout(fila)
        lay.addWidget(self.estado)
        lay.addWidget(self.salida, 1)

    def recargar(self):
        actual = self.cmb.currentData()
        self.cmb.clear()
        for c in m_clients.list_clients(only_active=False):
            nombre = f"{c['nombre']} {c['apellidos'] or ''}".strip()
            self.cmb.addItem(nombre, c["id"])
        idx = self.cmb.findData(actual)
        if idx >= 0:
            self.cmb.setCurrentIndex(idx)

    def _cliente(self) -> int | None:
        cid = self.cmb.currentData()
        if cid is None:
            QMessageBox.information(self, "Cliente", "No hay ningún cliente creado.")
        return cid

    def _perfil(self):
        cid = self._cliente()
        if cid is not None:
            self.lanzar(ai_agent.analizar_perfil, cid)

    def _comercial(self):
        cid = self._cliente()
        if cid is not None:
            self.lanzar(ai_agent.propuesta_comercial, cid)

    def _ver_datos(self):
        """Transparencia: exactamente qué se manda al proveedor de IA."""
        cid = self.cmb.currentData()
        if cid is None:
            return
        self.salida.setPlainText(ai_agent.contexto_cliente(cid))
        self.estado.setText(
            "Estos son los datos que se envían al proveedor de IA en las "
            "consultas sobre este cliente. No se ha hecho ninguna consulta."
        )


# --------------------------------------------------------------- auditoría


class _PanelAuditoria(_PanelIA):
    def __init__(self):
        super().__init__()
        self._hallazgos: list[auditoria.Hallazgo] = []
        lay = QVBoxLayout(self)
        lay.addWidget(QLabel(
            "Revisa automáticamente todos los datos del despacho buscando "
            "errores: facturas vencidas, huecos en la numeración, retenciones "
            "mal aplicadas, asuntos parados, fichas duplicadas y más.<br>"
            "<b>La detección se hace con reglas exactas, no con IA.</b> La IA "
            "solo interviene después, para ordenar el plan de acción."
        ))
        fila = QHBoxLayout()
        b_rev = PrimaryButton("Revisar ahora")
        b_rev.clicked.connect(self.revisar)
        self.b_explicar = PrimaryButton("Explicar y priorizar con IA")
        self.b_explicar.clicked.connect(self._explicar)
        self.b_explicar.setEnabled(False)
        fila.addWidget(b_rev)
        fila.addWidget(self.b_explicar)
        fila.addStretch(1)
        self.lbl_resumen = QLabel()
        fila.addWidget(self.lbl_resumen)
        lay.addLayout(fila)

        div = QSplitter(Qt.Orientation.Vertical)
        self.tabla = QTableWidget(0, 4)
        self.tabla.setHorizontalHeaderLabels(
            ["Gravedad", "Incidencia", "Detalle", "Afecta a"]
        )
        self.tabla.verticalHeader().setVisible(False)
        self.tabla.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tabla.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        configure_table(self.tabla, elastic=2)
        div.addWidget(self.tabla)
        div.addWidget(self.salida)
        div.setSizes([320, 260])
        lay.addWidget(div, 1)
        lay.addWidget(self.estado)

    def revisar(self):
        self._hallazgos = auditoria.auditar()
        self.tabla.setRowCount(len(self._hallazgos))
        for i, h in enumerate(self._hallazgos):
            celda = QTableWidgetItem(h.severidad.upper())
            celda.setForeground(Qt.GlobalColor.white)
            from PyQt6.QtGui import QColor
            celda.setBackground(QColor(_COLOR_SEVERIDAD.get(h.severidad, "#7F8C8D")))
            self.tabla.setItem(i, 0, celda)
            self.tabla.setItem(i, 1, QTableWidgetItem(h.titulo))
            self.tabla.setItem(i, 2, QTableWidgetItem(h.detalle))
            self.tabla.setItem(i, 3, QTableWidgetItem(h.entidad))
        autofit_columns(self.tabla)
        r = auditoria.resumen(self._hallazgos)
        if not self._hallazgos:
            self.lbl_resumen.setText(
                "<b style='color:#27AE60'>Sin incidencias detectadas.</b>")
        else:
            self.lbl_resumen.setText(
                f"<b style='color:#E74C3C'>{r['alta']} altas</b> · "
                f"<b style='color:#E67E22'>{r['media']} medias</b> · "
                f"{r['baja']} bajas"
            )
        self.b_explicar.setEnabled(bool(self._hallazgos))

    def _explicar(self):
        if not self._hallazgos:
            return
        self.lanzar(ai_agent.explicar_auditoria, self._hallazgos)


# -------------------------------------------------------------- documentos


class _PanelDocumentos(_PanelIA):
    def __init__(self):
        super().__init__()
        lay = QVBoxLayout(self)
        sel = QHBoxLayout()
        sel.addWidget(QLabel("Cliente:"))
        self.cmb_cliente = QComboBox()
        self.cmb_cliente.currentIndexChanged.connect(self._recargar_docs)
        sel.addWidget(self.cmb_cliente, 1)
        sel.addWidget(QLabel("Documento:"))
        self.cmb_doc = QComboBox()
        sel.addWidget(self.cmb_doc, 1)
        b_cargar = PrimaryButton("Cargar")
        b_cargar.clicked.connect(self._cargar_doc)
        b_externo = QPushButton("Archivo externo…")
        b_externo.clicked.connect(self._cargar_externo)
        sel.addWidget(b_cargar)
        sel.addWidget(b_externo)
        lay.addLayout(sel)

        div = QSplitter(Qt.Orientation.Horizontal)
        izq = QWidget()
        li = QVBoxLayout(izq)
        li.addWidget(QLabel("<b>Texto extraído del documento</b>"))
        self.texto = QPlainTextEdit()
        self.texto.setPlaceholderText("Carga un documento para empezar…")
        li.addWidget(self.texto, 1)
        b_res = PrimaryButton("Resumir documento")
        b_res.clicked.connect(self._resumir)
        li.addWidget(b_res)

        der = QWidget()
        ld = QVBoxLayout(der)
        ld.addWidget(QLabel("<b>Pregunta sobre el documento</b>"))
        self.pregunta = QPlainTextEdit()
        self.pregunta.setFixedHeight(80)
        self.pregunta.setPlaceholderText(
            "Ej.: ¿Qué plazo de recurso concede y desde qué fecha?"
        )
        ld.addWidget(self.pregunta)
        b_pre = PrimaryButton("Preguntar")
        b_pre.clicked.connect(self._preguntar)
        ld.addWidget(b_pre, alignment=Qt.AlignmentFlag.AlignRight)
        ld.addWidget(QLabel("<b>Respuesta</b>"))
        ld.addWidget(self.salida, 1)

        div.addWidget(izq)
        div.addWidget(der)
        div.setSizes([520, 520])
        lay.addWidget(div, 1)
        lay.addWidget(self.estado)

    def recargar(self):
        actual = self.cmb_cliente.currentData()
        self.cmb_cliente.blockSignals(True)
        self.cmb_cliente.clear()
        for c in m_clients.list_clients(only_active=False):
            nombre = f"{c['nombre']} {c['apellidos'] or ''}".strip()
            self.cmb_cliente.addItem(nombre, c["id"])
        idx = self.cmb_cliente.findData(actual)
        if idx >= 0:
            self.cmb_cliente.setCurrentIndex(idx)
        self.cmb_cliente.blockSignals(False)
        self._recargar_docs()

    def _recargar_docs(self):
        self.cmb_doc.clear()
        cid = self.cmb_cliente.currentData()
        if cid is None:
            return
        for d in m_docs.list_documents_by_client(cid):
            self.cmb_doc.addItem(d["nombre"], d["id"])

    def _cargar_doc(self):
        doc_id = self.cmb_doc.currentData()
        if doc_id is None:
            QMessageBox.information(self, "Documento",
                                    "Este cliente no tiene documentos subidos.")
            return
        ruta = m_docs.absolute_path(doc_id)
        if ruta is None or not ruta.exists():
            QMessageBox.warning(self, "Documento", "El archivo no existe.")
            return
        self.texto.setPlainText(extract_text(ruta))

    def _cargar_externo(self):
        ruta, _ = QFileDialog.getOpenFileName(
            self, "Abrir documento", "", "Documentos (*.pdf *.docx *.txt *.md *.csv)"
        )
        if ruta:
            self.texto.setPlainText(extract_text(ruta))

    def _resumir(self):
        texto = self.texto.toPlainText().strip()
        if not texto:
            QMessageBox.information(self, "Documento", "Carga un documento primero.")
            return
        self.lanzar(ai_agent.resumir_documento, texto, self.cmb_doc.currentText())

    def _preguntar(self):
        texto = self.texto.toPlainText().strip()
        pregunta = self.pregunta.toPlainText().strip()
        if not texto or not pregunta:
            QMessageBox.information(
                self, "Faltan datos",
                "Carga un documento y escribe una pregunta."
            )
            return
        self.lanzar(ai_agent.preguntar_documento, texto, pregunta)


# ----------------------------------------------------------------- cartera


class _PanelCartera(_PanelIA):
    def __init__(self):
        super().__init__()
        lay = QVBoxLayout(self)
        lay.addWidget(QLabel(
            "Busca oportunidades comerciales en el conjunto de la cartera: "
            "grupos de clientes que comparten una misma necesidad legal y a los "
            "que puede dirigirse una acción conjunta."
        ))
        fila = QHBoxLayout()
        b = PrimaryButton("Analizar cartera")
        b.clicked.connect(lambda: self.lanzar(ai_agent.oportunidades_cartera))
        fila.addWidget(b)
        fila.addStretch(1)
        fila.addWidget(self.estado)
        lay.addLayout(fila)
        lay.addWidget(self.salida, 1)


# -------------------------------------------------------------------- vista


class AIView(QWidget):
    def __init__(self):
        super().__init__()
        self._build()
        self.refresh()

    def _build(self):
        lay = QVBoxLayout(self)
        lay.addWidget(SectionTitle("Asistente IA"))

        self.lbl_estado = QLabel()
        self.lbl_estado.setWordWrap(True)
        lay.addWidget(self.lbl_estado)

        self.tabs = QTabWidget()
        self.p_consulta = _PanelConsulta()
        self.p_cliente = _PanelCliente()
        self.p_auditoria = _PanelAuditoria()
        self.p_documentos = _PanelDocumentos()
        self.p_cartera = _PanelCartera()
        self.tabs.addTab(self.p_consulta, "Consulta")
        self.tabs.addTab(self.p_cliente, "Cliente")
        self.tabs.addTab(self.p_auditoria, "Auditoría")
        self.tabs.addTab(self.p_documentos, "Documentos")
        self.tabs.addTab(self.p_cartera, "Cartera")
        lay.addWidget(self.tabs, 1)

    def refresh(self):
        proveedor = proveedor_activo()
        ok, mensaje = proveedor.disponible()
        if ok:
            fondo, color = ("#D4EDDA", "#155724")
            texto = f"<b>{proveedor.etiqueta}</b> — {mensaje}"
            if proveedor.nombre == "claude":
                texto += ("<br><b>Aviso:</b> los datos de las consultas salen "
                          "de tu equipo hacia la API de Anthropic. Valóralo "
                          "frente al secreto profesional y el RGPD.")
                fondo, color = ("#FFF3CD", "#856404")
        else:
            fondo, color = ("#F8D7DA", "#721C24")
            texto = f"<b>{proveedor.etiqueta} no disponible.</b><br>{mensaje}"
        self.lbl_estado.setStyleSheet(
            f"background:{fondo}; color:{color}; padding:8px; border-radius:4px;"
        )
        self.lbl_estado.setText(texto)
        self.p_cliente.recargar()
        self.p_documentos.recargar()
