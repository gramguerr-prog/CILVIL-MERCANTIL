from PyQt6.QtWidgets import (
    QFileDialog, QFormLayout, QGroupBox, QHBoxLayout, QLabel, QLineEdit,
    QMessageBox, QPushButton, QVBoxLayout, QWidget,
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
    ("ollama_model", "Modelo (ej: llama3.1)"),
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
        lay.addWidget(self._group("Agente IA local (Ollama)", AI_FIELDS))

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

    def _save(self):
        for key, inp in self._inputs.items():
            set_setting(key, inp.text().strip())
        QMessageBox.information(self, "Guardado", "Ajustes guardados correctamente.")

    def _reset(self):
        ans = QMessageBox.question(
            self, "Restablecer", "¿Restablecer los ajustes por defecto?"
        )
        if ans == QMessageBox.StandardButton.Yes:
            for key, default in DEFAULT_SETTINGS.items():
                set_setting(key, default)
            self.refresh()
