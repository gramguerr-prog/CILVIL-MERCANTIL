"""Cuadro de diálogo para dar de alta fichas de clientes desde un archivo."""

from __future__ import annotations

from PyQt6.QtWidgets import (
    QCheckBox, QDialog, QDialogButtonBox, QFileDialog, QHBoxLayout, QLabel,
    QLineEdit, QMessageBox, QPlainTextEdit, QPushButton, QVBoxLayout,
)

from app.services import importador
from app.ui.widgets.common import PrimaryButton, SectionTitle


class ImportClientsDialog(QDialog):
    """Elegir archivo → ver qué va a pasar → importar → leer el informe."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Importar fichas de clientes")
        self.resize(760, 560)
        self._clientes: list = []
        self._importado = False
        self._build()

    def _build(self):
        lay = QVBoxLayout(self)
        lay.addWidget(SectionTitle("Importar fichas de clientes"))
        lay.addWidget(QLabel(
            "Elige un archivo .json con las fichas preparadas. Antes de tocar "
            "nada verás aquí qué se va a crear y qué ya existe."
        ))

        fila = QHBoxLayout()
        self.ruta = QLineEdit()
        self.ruta.setPlaceholderText("Ningún archivo elegido")
        self.ruta.setReadOnly(True)
        btn_buscar = QPushButton("Elegir archivo...")
        btn_buscar.clicked.connect(self._elegir)
        fila.addWidget(self.ruta, 1)
        fila.addWidget(btn_buscar)
        lay.addLayout(fila)

        self.sobrescribir = QCheckBox(
            "Sobrescribir los datos que ya tenga la ficha "
            "(si no se marca, solo se rellenan los campos vacíos)"
        )
        lay.addWidget(self.sobrescribir)

        self.salida = QPlainTextEdit()
        self.salida.setReadOnly(True)
        self.salida.setPlaceholderText(
            "Aquí aparecerá la vista previa y, después, el resultado."
        )
        lay.addWidget(self.salida, 1)

        botones = QHBoxLayout()
        self.btn_importar = PrimaryButton("Importar")
        self.btn_importar.setEnabled(False)
        self.btn_importar.clicked.connect(self._importar)
        cerrar = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        cerrar.rejected.connect(self._cerrar)
        botones.addWidget(self.btn_importar)
        botones.addStretch(1)
        botones.addWidget(cerrar)
        lay.addLayout(botones)

    # --- Acciones ---

    def _elegir(self):
        ruta, _ = QFileDialog.getOpenFileName(
            self, "Archivo de fichas", "", "Fichas de clientes (*.json)"
        )
        if not ruta:
            return
        try:
            self._clientes = importador.leer(ruta)
        except importador.ImportError_ as e:
            self._clientes = []
            self.btn_importar.setEnabled(False)
            self.ruta.clear()
            self.salida.clear()
            QMessageBox.warning(self, "Archivo no válido", str(e))
            return

        self.ruta.setText(ruta)
        self._importado = False
        self.btn_importar.setEnabled(True)
        self.salida.setPlainText(
            f"Se van a revisar {len(self._clientes)} fichas:\n\n"
            + importador.resumen(self._clientes)
            + "\n\nPulsa «Importar» para grabarlas."
        )

    def _importar(self):
        if not self._clientes:
            return
        res = importador.importar(
            self._clientes, sobrescribir=self.sobrescribir.isChecked()
        )
        self._importado = True
        self.btn_importar.setEnabled(False)
        self.salida.setPlainText("RESULTADO DE LA IMPORTACIÓN\n\n" + res.como_texto())
        if res.avisos:
            QMessageBox.information(
                self, "Importación terminada",
                f"Se han revisado {res.total} fichas, con "
                f"{len(res.avisos)} avisos. Léelos en la ventana.",
            )

    def _cerrar(self):
        # accept() para que la lista de clientes se refresque al volver.
        self.accept() if self._importado else self.reject()
