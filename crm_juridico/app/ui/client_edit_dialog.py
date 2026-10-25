from __future__ import annotations

from PyQt6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFormLayout, QLineEdit,
    QMessageBox, QPlainTextEdit, QVBoxLayout,
)

from app.models import clients as m_clients


class ClientEditDialog(QDialog):
    def __init__(self, parent=None, client_id: int | None = None):
        super().__init__(parent)
        self.client_id = client_id
        self.setWindowTitle("Editar cliente" if client_id else "Nuevo cliente")
        self.setMinimumWidth(520)
        self._build()
        if client_id:
            self._load()

    def _build(self):
        lay = QVBoxLayout(self)
        form = QFormLayout()

        self.txt_nombre = QLineEdit()
        self.txt_apellidos = QLineEdit()
        self.txt_nif = QLineEdit()
        self.cmb_tipo = QComboBox()
        self.cmb_tipo.addItems(["particular", "empresa", "autonomo"])
        self.txt_email = QLineEdit()
        self.txt_tel = QLineEdit()
        self.txt_dir = QLineEdit()
        self.txt_ciudad = QLineEdit()
        self.txt_cp = QLineEdit()
        self.txt_pais = QLineEdit()
        self.txt_pais.setText("España")
        self.chk_irpf_nuevo = QCheckBox("Retención IRPF reducida (7 %, primeros 3 años)")
        self.chk_activo = QCheckBox("Activo")
        self.chk_activo.setChecked(True)
        self.txt_notas = QPlainTextEdit()
        self.txt_notas.setFixedHeight(80)

        form.addRow("Nombre*", self.txt_nombre)
        form.addRow("Apellidos", self.txt_apellidos)
        form.addRow("NIF / CIF", self.txt_nif)
        form.addRow("Tipo*", self.cmb_tipo)
        form.addRow("Email", self.txt_email)
        form.addRow("Teléfono", self.txt_tel)
        form.addRow("Dirección", self.txt_dir)
        form.addRow("Ciudad", self.txt_ciudad)
        form.addRow("Código postal", self.txt_cp)
        form.addRow("País", self.txt_pais)
        form.addRow("", self.chk_irpf_nuevo)
        form.addRow("", self.chk_activo)
        form.addRow("Notas internas", self.txt_notas)
        lay.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_save)
        buttons.rejected.connect(self.reject)
        lay.addWidget(buttons)

    def _load(self):
        c = m_clients.get_client(self.client_id)
        if c is None:
            return
        self.txt_nombre.setText(c["nombre"] or "")
        self.txt_apellidos.setText(c["apellidos"] or "")
        self.txt_nif.setText(c["nif"] or "")
        idx = self.cmb_tipo.findText(c["tipo"] or "particular")
        if idx >= 0:
            self.cmb_tipo.setCurrentIndex(idx)
        self.txt_email.setText(c["email"] or "")
        self.txt_tel.setText(c["telefono"] or "")
        self.txt_dir.setText(c["direccion"] or "")
        self.txt_ciudad.setText(c["ciudad"] or "")
        self.txt_cp.setText(c["codigo_postal"] or "")
        self.txt_pais.setText(c["pais"] or "España")
        self.chk_irpf_nuevo.setChecked(bool(c["irpf_nuevo"]))
        self.chk_activo.setChecked(bool(c["activo"]))
        self.txt_notas.setPlainText(c["notas"] or "")

    def _data(self) -> dict:
        return {
            "nombre": self.txt_nombre.text().strip(),
            "apellidos": self.txt_apellidos.text().strip() or None,
            "nif": self.txt_nif.text().strip() or None,
            "tipo": self.cmb_tipo.currentText(),
            "email": self.txt_email.text().strip() or None,
            "telefono": self.txt_tel.text().strip() or None,
            "direccion": self.txt_dir.text().strip() or None,
            "ciudad": self.txt_ciudad.text().strip() or None,
            "codigo_postal": self.txt_cp.text().strip() or None,
            "pais": self.txt_pais.text().strip() or None,
            "irpf_nuevo": 1 if self.chk_irpf_nuevo.isChecked() else 0,
            "activo": 1 if self.chk_activo.isChecked() else 0,
            "notas": self.txt_notas.toPlainText().strip() or None,
        }

    def _on_save(self):
        data = self._data()
        if not data["nombre"]:
            QMessageBox.warning(self, "Falta el nombre", "El nombre es obligatorio.")
            return
        try:
            if self.client_id:
                m_clients.update_client(self.client_id, data)
            else:
                self.client_id = m_clients.create_client(data)
        except Exception as e:
            QMessageBox.critical(self, "Error al guardar", str(e))
            return
        self.accept()
