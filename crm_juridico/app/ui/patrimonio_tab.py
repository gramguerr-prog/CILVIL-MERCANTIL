"""Pestañas de situación familiar y de patrimonio del cliente."""
from datetime import date

from PyQt6.QtCore import QDate, Qt
from PyQt6.QtWidgets import (
    QCheckBox, QComboBox, QDateEdit, QDialog, QDialogButtonBox,
    QDoubleSpinBox, QFormLayout, QGroupBox, QHBoxLayout, QLabel,
    QLineEdit, QMessageBox, QPlainTextEdit, QPushButton, QTabWidget,
    QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

from app.models import clients as m_clients
from app.models import patrimonio as m_patrimonio
from app.models.patrimonio import CATEGORIAS
from app.ui.widgets.common import (
    DangerButton, PrimaryButton, autofit_columns, configure_table, fmt_eur,
)

ESTADOS_CIVILES = [
    "", "soltero/a", "casado/a", "pareja de hecho", "separado/a",
    "divorciado/a", "viudo/a",
]

REGIMENES = [
    "", "gananciales", "separación de bienes", "participación", "no aplica",
]

# Fecha centinela para "sin fecha" en los QDateEdit.
_SIN_FECHA = QDate(1900, 1, 1)


def _edad(fecha_nacimiento: str | None) -> str:
    if not fecha_nacimiento:
        return ""
    try:
        y, m, d = (int(p) for p in fecha_nacimiento.split("-"))
        nac = date(y, m, d)
    except (ValueError, TypeError):
        return ""
    hoy = date.today()
    años = hoy.year - nac.year - ((hoy.month, hoy.day) < (nac.month, nac.day))
    if años < 0:
        return ""
    return f"{años} años" + (" (menor)" if años < 18 else "")


class AssetDialog(QDialog):
    """Alta / edición de un elemento patrimonial."""

    def __init__(self, parent, client_id: int, categoria: str,
                 asset_id: int | None = None):
        super().__init__(parent)
        self.client_id = client_id
        self.categoria = categoria
        self.asset_id = asset_id
        _etiqueta, lbl_ident, lbl_entidad, lbl_valor = CATEGORIAS[categoria]
        self.setWindowTitle(m_patrimonio.SINGULAR.get(categoria, "Registro"))
        self.setMinimumWidth(480)

        lay = QVBoxLayout(self)
        form = QFormLayout()
        self.in_desc = QLineEdit()
        self.in_ident = QLineEdit()
        self.in_entidad = QLineEdit()
        self.in_valor = QDoubleSpinBox()
        self.in_valor.setRange(0, 1_000_000_000)
        self.in_valor.setDecimals(2)
        self.in_valor.setSuffix(" €")
        self.in_fecha = QDateEdit(calendarPopup=True)
        self.in_fecha.setMinimumDate(_SIN_FECHA)
        self.in_fecha.setSpecialValueText("(sin fecha)")
        self.in_fecha.setDate(_SIN_FECHA)
        self.in_notas = QPlainTextEdit()
        self.in_notas.setFixedHeight(70)

        form.addRow("Descripción*", self.in_desc)
        form.addRow(lbl_ident, self.in_ident)
        form.addRow(lbl_entidad, self.in_entidad)
        form.addRow(lbl_valor, self.in_valor)
        form.addRow("Fecha", self.in_fecha)
        form.addRow("Notas", self.in_notas)
        lay.addLayout(form)

        bb = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save
            | QDialogButtonBox.StandardButton.Cancel
        )
        bb.accepted.connect(self._save)
        bb.rejected.connect(self.reject)
        lay.addWidget(bb)

        if asset_id:
            self._load()

    def _load(self):
        a = m_patrimonio.get_asset(self.asset_id)
        if a is None:
            return
        self.in_desc.setText(a["descripcion"] or "")
        self.in_ident.setText(a["identificador"] or "")
        self.in_entidad.setText(a["entidad"] or "")
        self.in_valor.setValue(float(a["valor"] or 0))
        if a["fecha"]:
            self.in_fecha.setDate(QDate.fromString(a["fecha"], "yyyy-MM-dd"))
        self.in_notas.setPlainText(a["notas"] or "")

    def _save(self):
        if not self.in_desc.text().strip():
            QMessageBox.warning(self, "Descripción",
                                "La descripción es obligatoria.")
            return
        fecha = self.in_fecha.date()
        data = {
            "client_id": self.client_id,
            "categoria": self.categoria,
            "descripcion": self.in_desc.text().strip(),
            "identificador": self.in_ident.text().strip() or None,
            "entidad": self.in_entidad.text().strip() or None,
            "valor": float(self.in_valor.value()),
            "fecha": None if fecha == _SIN_FECHA else fecha.toString("yyyy-MM-dd"),
            "notas": self.in_notas.toPlainText().strip() or None,
        }
        if self.asset_id:
            m_patrimonio.update_asset(self.asset_id, data)
        else:
            m_patrimonio.create_asset(data)
        self.accept()


class AssetTable(QWidget):
    """Tabla con alta/edición/baja para una categoría patrimonial."""

    def __init__(self, parent, client_id: int, categoria: str, on_change=None):
        super().__init__(parent)
        self.client_id = client_id
        self.categoria = categoria
        self.on_change = on_change
        self._ids: list[int] = []
        _, lbl_ident, lbl_entidad, lbl_valor = CATEGORIAS[categoria]

        lay = QVBoxLayout(self)
        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(
            ["Descripción", lbl_ident, lbl_entidad, lbl_valor, "Fecha", "Notas"]
        )
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows
        )
        configure_table(self.table, elastic=0)
        self.table.doubleClicked.connect(self._edit)
        lay.addWidget(self.table, 1)

        row = QHBoxLayout()
        b_add = PrimaryButton("+ Añadir")
        b_add.clicked.connect(self._add)
        b_edit = QPushButton("Editar")
        b_edit.clicked.connect(self._edit)
        b_del = DangerButton("Eliminar")
        b_del.clicked.connect(self._delete)
        row.addWidget(b_add)
        row.addWidget(b_edit)
        row.addStretch(1)
        self.lbl_total = QLabel()
        row.addWidget(self.lbl_total)
        row.addWidget(b_del)
        lay.addLayout(row)

        self.reload()

    def reload(self):
        rows = m_patrimonio.list_assets(self.client_id, self.categoria)
        self.table.setRowCount(len(rows))
        self._ids = []
        total = 0.0
        for i, r in enumerate(rows):
            self._ids.append(r["id"])
            self.table.setItem(i, 0, QTableWidgetItem(r["descripcion"] or ""))
            self.table.setItem(i, 1, QTableWidgetItem(r["identificador"] or ""))
            self.table.setItem(i, 2, QTableWidgetItem(r["entidad"] or ""))
            valor = QTableWidgetItem(fmt_eur(r["valor"]))
            valor.setTextAlignment(
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
            )
            self.table.setItem(i, 3, valor)
            self.table.setItem(i, 4, QTableWidgetItem(r["fecha"] or ""))
            self.table.setItem(i, 5, QTableWidgetItem(r["notas"] or ""))
            total += float(r["valor"] or 0)
        autofit_columns(self.table)
        self.lbl_total.setText(f"<b>Total: {fmt_eur(total)}</b>")

    def _selected_id(self) -> int | None:
        row = self.table.currentRow()
        if row < 0 or row >= len(self._ids):
            return None
        return self._ids[row]

    def _notify(self):
        self.reload()
        if self.on_change:
            self.on_change()

    def _add(self):
        dlg = AssetDialog(self, self.client_id, self.categoria)
        if dlg.exec():
            self._notify()

    def _edit(self):
        aid = self._selected_id()
        if aid is None:
            return
        dlg = AssetDialog(self, self.client_id, self.categoria, asset_id=aid)
        if dlg.exec():
            self._notify()

    def _delete(self):
        aid = self._selected_id()
        if aid is None:
            return
        if QMessageBox.question(self, "Eliminar", "¿Eliminar este registro?") \
                == QMessageBox.StandardButton.Yes:
            m_patrimonio.delete_asset(aid)
            self._notify()


class ChildDialog(QDialog):
    def __init__(self, parent, client_id: int, child_id: int | None = None):
        super().__init__(parent)
        self.client_id = client_id
        self.child_id = child_id
        self.setWindowTitle("Hijo/a")
        self.setMinimumWidth(420)

        lay = QVBoxLayout(self)
        form = QFormLayout()
        self.in_nombre = QLineEdit()
        self.in_fecha = QDateEdit(calendarPopup=True)
        self.in_fecha.setMinimumDate(_SIN_FECHA)
        self.in_fecha.setSpecialValueText("(sin fecha)")
        self.in_fecha.setDate(_SIN_FECHA)
        self.in_notas = QPlainTextEdit()
        self.in_notas.setFixedHeight(70)
        form.addRow("Nombre*", self.in_nombre)
        form.addRow("Fecha nacimiento", self.in_fecha)
        form.addRow("Notas", self.in_notas)
        lay.addLayout(form)

        bb = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save
            | QDialogButtonBox.StandardButton.Cancel
        )
        bb.accepted.connect(self._save)
        bb.rejected.connect(self.reject)
        lay.addWidget(bb)

        if child_id:
            self._load()

    def _load(self):
        c = m_patrimonio.get_child(self.child_id)
        if c is None:
            return
        self.in_nombre.setText(c["nombre"] or "")
        if c["fecha_nacimiento"]:
            self.in_fecha.setDate(
                QDate.fromString(c["fecha_nacimiento"], "yyyy-MM-dd")
            )
        self.in_notas.setPlainText(c["notas"] or "")

    def _save(self):
        nombre = self.in_nombre.text().strip()
        if not nombre:
            QMessageBox.warning(self, "Nombre", "El nombre es obligatorio.")
            return
        fecha = self.in_fecha.date()
        fecha_str = None if fecha == _SIN_FECHA else fecha.toString("yyyy-MM-dd")
        notas = self.in_notas.toPlainText().strip()
        if self.child_id:
            m_patrimonio.update_child(self.child_id, nombre, fecha_str, notas)
        else:
            m_patrimonio.create_child(self.client_id, nombre, fecha_str, notas)
        self.accept()


class FamiliaTab(QWidget):
    """Situación familiar: estado civil, régimen económico e hijos."""

    def __init__(self, parent, client_id: int):
        super().__init__(parent)
        self.client_id = client_id
        self._child_ids: list[int] = []
        self._loading = False
        self._build()
        self.reload()

    def _build(self):
        lay = QVBoxLayout(self)

        datos = QGroupBox("Datos familiares")
        form = QFormLayout(datos)
        self.cmb_estado_civil = QComboBox()
        self.cmb_estado_civil.setEditable(True)
        self.cmb_estado_civil.addItems(ESTADOS_CIVILES)
        self.cmb_estado_civil.currentTextChanged.connect(self._save_fields)
        self.cmb_regimen = QComboBox()
        self.cmb_regimen.setEditable(True)
        self.cmb_regimen.addItems(REGIMENES)
        self.cmb_regimen.currentTextChanged.connect(self._save_fields)
        self.chk_hijos = QCheckBox("Tiene hijos")
        self.chk_hijos.toggled.connect(self._on_toggle_hijos)
        form.addRow("Estado civil", self.cmb_estado_civil)
        form.addRow("Régimen económico", self.cmb_regimen)
        form.addRow("", self.chk_hijos)
        lay.addWidget(datos)

        hijos = QGroupBox("Hijos")
        hijos_lay = QVBoxLayout(hijos)
        botones = QHBoxLayout()
        botones.addStretch(1)
        b_add = PrimaryButton("+ Añadir hijo/a")
        b_add.clicked.connect(self._add_child)
        b_edit = QPushButton("Editar")
        b_edit.clicked.connect(self._edit_child)
        b_del = DangerButton("Eliminar")
        b_del.clicked.connect(self._delete_child)
        botones.addWidget(b_add)
        botones.addWidget(b_edit)
        botones.addWidget(b_del)
        hijos_lay.addLayout(botones)

        self.tbl_hijos = QTableWidget(0, 4)
        self.tbl_hijos.setHorizontalHeaderLabels(
            ["Nombre", "Fecha nacimiento", "Edad", "Notas"]
        )
        self.tbl_hijos.verticalHeader().setVisible(False)
        self.tbl_hijos.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tbl_hijos.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows
        )
        configure_table(self.tbl_hijos, elastic=3)
        self.tbl_hijos.doubleClicked.connect(self._edit_child)
        hijos_lay.addWidget(self.tbl_hijos, 1)
        lay.addWidget(hijos, 1)

    def reload(self):
        c = m_clients.get_client(self.client_id)
        if c is None:
            return
        self._loading = True
        self.cmb_estado_civil.setCurrentText(c["estado_civil"] or "")
        self.cmb_regimen.setCurrentText(c["regimen_economico"] or "")
        self.chk_hijos.setChecked(bool(c["tiene_hijos"]))
        self._loading = False
        self._reload_children()

    def _save_fields(self, *_args):
        if self._loading:
            return
        m_clients.update_client_fields(self.client_id, {
            "estado_civil": self.cmb_estado_civil.currentText().strip() or None,
            "regimen_economico": self.cmb_regimen.currentText().strip() or None,
        })

    def _on_toggle_hijos(self, checked: bool):
        if self._loading:
            return
        m_clients.update_client_fields(
            self.client_id, {"tiene_hijos": 1 if checked else 0}
        )

    def _reload_children(self):
        rows = m_patrimonio.list_children(self.client_id)
        self.tbl_hijos.setRowCount(len(rows))
        self._child_ids = []
        for i, r in enumerate(rows):
            self._child_ids.append(r["id"])
            self.tbl_hijos.setItem(i, 0, QTableWidgetItem(r["nombre"] or ""))
            self.tbl_hijos.setItem(
                i, 1, QTableWidgetItem(r["fecha_nacimiento"] or "")
            )
            self.tbl_hijos.setItem(
                i, 2, QTableWidgetItem(_edad(r["fecha_nacimiento"]))
            )
            self.tbl_hijos.setItem(i, 3, QTableWidgetItem(r["notas"] or ""))
        autofit_columns(self.tbl_hijos)
        # Añadir un hijo marca la casilla en la BD; lo reflejamos aquí.
        c = m_clients.get_client(self.client_id)
        if c is not None:
            self._loading = True
            self.chk_hijos.setChecked(bool(c["tiene_hijos"]))
            self._loading = False

    def _selected_child_id(self) -> int | None:
        row = self.tbl_hijos.currentRow()
        if row < 0 or row >= len(self._child_ids):
            return None
        return self._child_ids[row]

    def _add_child(self):
        dlg = ChildDialog(self, self.client_id)
        if dlg.exec():
            self.reload()

    def _edit_child(self):
        cid = self._selected_child_id()
        if cid is None:
            return
        dlg = ChildDialog(self, self.client_id, child_id=cid)
        if dlg.exec():
            self.reload()

    def _delete_child(self):
        cid = self._selected_child_id()
        if cid is None:
            return
        if QMessageBox.question(self, "Eliminar", "¿Eliminar este registro?") \
                == QMessageBox.StandardButton.Yes:
            m_patrimonio.delete_child(cid)
            self.reload()


class PatrimonioTab(QWidget):
    """Patrimonio y cargas: vehículos, cuentas, hipotecas, propiedades, deudas."""

    def __init__(self, parent, client_id: int):
        super().__init__(parent)
        self.client_id = client_id
        self._loading = False
        self._build()
        self.reload()

    def _build(self):
        lay = QVBoxLayout(self)

        # Casillas rápidas: se marcan solas al añadir un registro, pero también
        # pueden marcarse a mano cuando aún no hay detalle.
        flags_row = QHBoxLayout()
        flags_row.addWidget(QLabel("Tiene:"))
        self.flag_checks: dict[str, QCheckBox] = {}
        for categoria, columna in m_patrimonio.FLAG_BY_CATEGORIA.items():
            etiqueta = CATEGORIAS[categoria][0]
            chk = QCheckBox(etiqueta)
            chk.toggled.connect(
                lambda checked, col=columna: self._on_toggle_flag(col, checked)
            )
            self.flag_checks[categoria] = chk
            flags_row.addWidget(chk)
        flags_row.addStretch(1)
        lay.addLayout(flags_row)

        self.tabs = QTabWidget()
        self.asset_tables: dict[str, AssetTable] = {}
        for categoria, (etiqueta, *_rest) in CATEGORIAS.items():
            tabla = AssetTable(
                self, self.client_id, categoria, on_change=self._reload_summary
            )
            self.asset_tables[categoria] = tabla
            self.tabs.addTab(tabla, etiqueta)
        lay.addWidget(self.tabs, 1)

        self.lbl_resumen = QLabel()
        self.lbl_resumen.setStyleSheet(
            "background: #ECF0F1; padding: 8px; border-radius: 4px;"
        )
        lay.addWidget(self.lbl_resumen)

    def reload(self):
        c = m_clients.get_client(self.client_id)
        if c is None:
            return
        self._loading = True
        for categoria, chk in self.flag_checks.items():
            columna = m_patrimonio.FLAG_BY_CATEGORIA[categoria]
            chk.setChecked(bool(c[columna]))
        self._loading = False
        for tabla in self.asset_tables.values():
            tabla.reload()
        self._reload_summary()

    def _on_toggle_flag(self, columna: str, checked: bool):
        if self._loading:
            return
        m_clients.update_client_fields(
            self.client_id, {columna: 1 if checked else 0}
        )

    def _reload_summary(self):
        # Añadir un registro marca su casilla automáticamente en la BD:
        # reflejamos aquí ese cambio sin disparar el guardado.
        c = m_clients.get_client(self.client_id)
        if c is not None:
            self._loading = True
            for categoria, chk in self.flag_checks.items():
                chk.setChecked(bool(c[m_patrimonio.FLAG_BY_CATEGORIA[categoria]]))
            self._loading = False

        s = m_patrimonio.patrimonio_summary(self.client_id)
        self.lbl_resumen.setText(
            f"<b>Activo estimado:</b> {fmt_eur(s['activo'])} &nbsp;·&nbsp; "
            f"<b>Cargas y deudas:</b> {fmt_eur(s['pasivo'])} &nbsp;·&nbsp; "
            f"<b style='color:{'#C0392B' if s['neto'] < 0 else '#27AE60'}'>"
            f"Patrimonio neto: {fmt_eur(s['neto'])}</b>"
        )
