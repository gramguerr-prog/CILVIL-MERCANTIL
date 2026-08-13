from PyQt6.QtWidgets import (
    QComboBox, QFileDialog, QFormLayout, QGroupBox, QHBoxLayout, QLabel,
    QLineEdit, QMessageBox, QPushButton, QVBoxLayout, QWidget,
)

from app import config
from app.config import DATA_DIR, DEFAULT_SETTINGS
from app.database.db import get_setting, set_setting
from app.ui.widgets.common import PrimaryButton, SectionTitle


FISCAL_FIELDS = [
    ("iva_general", "IVA general (%)"),
    ("iva_reducido", "IVA reducido (%)"),
    ("iva_superreducido", "IVA superreducido (%)"),
    ("irpf_general", "IRPF profesional general (%)"),
    ("irpf_nuevo", "IRPF profesional nuevo (%)"),
]

DESPACHO_FIELDS = [
    ("despacho_nombre", "Nombre / Razón social"),
    ("despacho_nif", "NIF / CIF"),
    ("despacho_direccion", "Dirección"),
    ("despacho_telefono", "Teléfono"),
    ("despacho_email", "Email"),
    ("despacho_iban", "IBAN"),
]

FACTURA_FIELDS = [
    ("factura_prefijo", "Prefijo (ej: 'F')"),
    ("factura_serie", "Serie / año (ej: '2024')"),
]

AI_FIELDS = [
    ("ollama_url", "URL de Ollama"),
    ("ollama_model", "Modelo local (ej: llama3.1)"),
    ("claude_model", "Modelo de Claude"),
]

NIVELES_ESFUERZO = [
    ("low", "Bajo — rápido y barato, para tareas sencillas"),
    ("medium", "Medio — equilibrio entre calidad y coste"),
    ("high", "Alto — recomendado para análisis jurídico"),
    ("xhigh", "Muy alto — razonamiento largo, más lento y caro"),
    ("max", "Máximo — solo cuando la exactitud importa más que el coste"),
]


class SettingsView(QWidget):
    def __init__(self):
        super().__init__()
        self._inputs: dict[str, QLineEdit] = {}
        self._build()
        self.refresh()

    def _build(self):
        lay = QVBoxLayout(self)
        lay.addWidget(SectionTitle("Ajustes"))

        lay.addWidget(self._grupo_carpeta_datos())
        lay.addWidget(self._group("Datos del despacho (aparecen en facturas)", DESPACHO_FIELDS))
        lay.addWidget(self._group("Facturación", FACTURA_FIELDS))
        lay.addWidget(self._group("Fiscalidad", FISCAL_FIELDS))
        lay.addWidget(self._grupo_ia())

        actions = QHBoxLayout()
        actions.addStretch(1)
        b_reset = QPushButton("Restablecer por defecto")
        b_reset.clicked.connect(self._reset)
        b_save = PrimaryButton("Guardar cambios")
        b_save.clicked.connect(self._save)
        actions.addWidget(b_reset)
        actions.addWidget(b_save)
        lay.addLayout(actions)
        lay.addStretch(1)

    def _grupo_ia(self) -> QGroupBox:
        box = QGroupBox("Inteligencia artificial")
        v = QVBoxLayout(box)

        aviso = QLabel(
            "Elige qué motor de IA usa el programa.<br>"
            "<b>Ollama</b> funciona en tu ordenador: ningún dato sale de él, "
            "así que no plantea problemas de secreto profesional. La calidad "
            "es menor.<br>"
            "<b>Claude</b> da análisis claramente mejores, pero las consultas "
            "viajan a los servidores de Anthropic. Antes de activarlo para "
            "datos de clientes reales, valora tus obligaciones de secreto "
            "profesional y de RGPD (necesitarás un contrato de encargado del "
            "tratamiento con el proveedor)."
        )
        aviso.setWordWrap(True)
        aviso.setStyleSheet("color: #555;")
        v.addWidget(aviso)

        form = QFormLayout()
        self.cmb_proveedor = QComboBox()
        self.cmb_proveedor.addItem("Ollama — local y privado", "ollama")
        self.cmb_proveedor.addItem("Claude — API de Anthropic", "claude")
        form.addRow("Motor en uso", self.cmb_proveedor)

        self.txt_clave = QLineEdit()
        self.txt_clave.setEchoMode(QLineEdit.EchoMode.Password)
        self.txt_clave.setPlaceholderText("sk-ant-…  (se guarda en este equipo)")
        form.addRow("Clave de API de Claude", self.txt_clave)

        self.cmb_esfuerzo = QComboBox()
        for valor, etiqueta in NIVELES_ESFUERZO:
            self.cmb_esfuerzo.addItem(etiqueta, valor)
        form.addRow("Profundidad de análisis", self.cmb_esfuerzo)

        for key, label in AI_FIELDS:
            inp = QLineEdit()
            form.addRow(label, inp)
            self._inputs[key] = inp
        v.addLayout(form)

        nota = QLabel(
            "La clave se guarda sin cifrar en la carpeta de datos. Si prefieres "
            "no guardarla ahí, defínela en la variable de entorno "
            "<code>ANTHROPIC_API_KEY</code>: el programa la usará con "
            "preferencia sobre esta casilla."
        )
        nota.setWordWrap(True)
        nota.setStyleSheet("color: #856404; background:#FFF3CD; padding:6px; "
                           "border-radius:4px;")
        v.addWidget(nota)

        fila = QHBoxLayout()
        b_probar = PrimaryButton("Probar conexión")
        b_probar.clicked.connect(self._probar_ia)
        fila.addWidget(b_probar)
        fila.addStretch(1)
        v.addLayout(fila)
        return box

    def _probar_ia(self):
        """Guarda primero, porque la prueba lee la configuración de la BD."""
        self._guardar_ia()
        from app.services.ai_provider import proveedor_activo
        proveedor = proveedor_activo()
        ok, mensaje = proveedor.disponible()
        if ok:
            QMessageBox.information(self, "Conexión correcta",
                                    f"{proveedor.etiqueta}\n\n{mensaje}")
        else:
            QMessageBox.warning(self, "No disponible",
                                f"{proveedor.etiqueta}\n\n{mensaje}")

    def _guardar_ia(self):
        set_setting("ia_proveedor", self.cmb_proveedor.currentData())
        set_setting("claude_effort", self.cmb_esfuerzo.currentData())
        set_setting("claude_api_key", self.txt_clave.text().strip())

    def _refrescar_ia(self):
        idx = self.cmb_proveedor.findData(get_setting("ia_proveedor") or "ollama")
        self.cmb_proveedor.setCurrentIndex(max(idx, 0))
        idx = self.cmb_esfuerzo.findData(get_setting("claude_effort") or "high")
        self.cmb_esfuerzo.setCurrentIndex(max(idx, 0))
        self.txt_clave.setText(get_setting("claude_api_key") or "")

    def _grupo_carpeta_datos(self) -> QGroupBox:
        box = QGroupBox("Carpeta de datos")
        v = QVBoxLayout(box)

        explicacion = QLabel(
            "Aquí se guardan tus clientes, documentos y facturas. Si la pones "
            "en una carpeta sincronizada (OneDrive, iCloud Drive, Dropbox…) "
            "podrás trabajar con el mismo despacho desde varios ordenadores.<br>"
            "<b>Importante:</b> no abras el programa en dos equipos a la vez; "
            "ciérralo en uno antes de abrirlo en el otro."
        )
        explicacion.setWordWrap(True)
        explicacion.setStyleSheet("color: #555;")
        v.addWidget(explicacion)

        self.lbl_carpeta_datos = QLabel()
        self.lbl_carpeta_datos.setWordWrap(True)
        self.lbl_carpeta_datos.setStyleSheet(
            "background: #ECF0F1; padding: 8px; border-radius: 4px;"
        )
        v.addWidget(self.lbl_carpeta_datos)

        fila = QHBoxLayout()
        b_cambiar = PrimaryButton("Cambiar carpeta…")
        b_cambiar.clicked.connect(self._cambiar_carpeta_datos)
        b_defecto = QPushButton("Usar la carpeta del programa")
        b_defecto.clicked.connect(self._restaurar_carpeta_datos)
        b_abrir = QPushButton("Abrir carpeta")
        b_abrir.clicked.connect(self._abrir_carpeta_datos)
        fila.addWidget(b_cambiar)
        fila.addWidget(b_defecto)
        fila.addWidget(b_abrir)
        fila.addStretch(1)
        v.addLayout(fila)
        return box

    def _refrescar_carpeta_datos(self):
        configurada = config.ruta_datos_configurada()
        if configurada is None:
            texto = (
                f"<b>En uso:</b> {DATA_DIR}<br>"
                "<i>(carpeta propia del programa)</i>"
            )
        else:
            texto = f"<b>En uso:</b> {DATA_DIR}"
            if str(configurada) != str(DATA_DIR):
                texto += (
                    f"<br><span style='color:#C0392B'><b>Aviso:</b> la carpeta "
                    f"configurada ({configurada}) no está disponible.</span>"
                )
        self.lbl_carpeta_datos.setText(texto)

    def _cambiar_carpeta_datos(self):
        carpeta = QFileDialog.getExistingDirectory(
            self, "Elige la carpeta donde guardar los datos", str(DATA_DIR)
        )
        if not carpeta:
            return
        config.guardar_ruta_datos(carpeta)
        self._refrescar_carpeta_datos()
        QMessageBox.information(
            self, "Carpeta cambiada",
            "La nueva carpeta se usará al reiniciar el programa.\n\n"
            f"Nueva carpeta:\n{carpeta}\n\n"
            "Si ya tenías datos, copia el contenido de la carpeta anterior "
            "a la nueva antes de volver a abrir el programa:\n"
            f"{DATA_DIR}",
        )

    def _restaurar_carpeta_datos(self):
        ans = QMessageBox.question(
            self, "Carpeta del programa",
            "¿Volver a guardar los datos en la carpeta 'data' del programa?\n"
            "El cambio se aplicará al reiniciar.",
        )
        if ans == QMessageBox.StandardButton.Yes:
            config.guardar_ruta_datos(None)
            self._refrescar_carpeta_datos()

    def _abrir_carpeta_datos(self):
        from PyQt6.QtCore import QUrl
        from PyQt6.QtGui import QDesktopServices
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(DATA_DIR)))

    def _group(self, title: str, fields: list[tuple[str, str]]) -> QGroupBox:
        box = QGroupBox(title)
        form = QFormLayout(box)
        for key, label in fields:
            inp = QLineEdit()
            form.addRow(label, inp)
            self._inputs[key] = inp
        return box

    def refresh(self):
        for key, inp in self._inputs.items():
            inp.setText(get_setting(key) or "")
        self._refrescar_carpeta_datos()
        self._refrescar_ia()

    def _save(self):
        for key, inp in self._inputs.items():
            set_setting(key, inp.text().strip())
        self._guardar_ia()
        QMessageBox.information(self, "Guardado", "Ajustes guardados correctamente.")

    def _reset(self):
        ans = QMessageBox.question(
            self, "Restablecer", "¿Restablecer los ajustes por defecto?"
        )
        if ans == QMessageBox.StandardButton.Yes:
            for key, default in DEFAULT_SETTINGS.items():
                set_setting(key, default)
            self.refresh()
