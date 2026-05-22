from PyQt6.QtWidgets import (
    QFormLayout, QGroupBox, QHBoxLayout, QLineEdit, QMessageBox, QPushButton,
    QVBoxLayout, QWidget,
)

from app.config import DEFAULT_SETTINGS
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
