"""Reusable form widgets generated from the declarative parameter specs."""

import os

from qgis.core import QgsProject
from qgis.PyQt.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QWidget,
)

from . import compat

RASTER_FILTER = "Rastry (*.tif *.tiff *.jp2 *.img);;Wszystkie pliki (*)"


class ParamForm(QWidget):
    """Form built from core.params.Param specs; values() returns {key: python value}."""

    def __init__(self, params, parent=None):
        super().__init__(parent)
        self._specs = {p.key: p for p in params}
        self.widgets = {}
        form = QFormLayout(self)
        for spec in params:
            widget = self._make(spec)
            if spec.help:
                widget.setToolTip(spec.help)
            self.widgets[spec.key] = widget
            form.addRow(spec.label + ":", widget)

    @staticmethod
    def _make(spec):
        if spec.kind == "int":
            w = QSpinBox()
            w.setRange(int(spec.minimum), int(min(spec.maximum, 2_000_000_000)))
            w.setSingleStep(max(1, int(spec.step)))
            w.setValue(int(spec.default))
        elif spec.kind == "float":
            w = QDoubleSpinBox()
            w.setDecimals(spec.decimals)
            w.setRange(spec.minimum, spec.maximum)
            w.setSingleStep(spec.step)
            w.setValue(float(spec.default))
        elif spec.kind == "bool":
            w = QCheckBox()
            w.setChecked(bool(spec.default))
            return w
        elif spec.kind == "choice":
            w = QComboBox()
            for key, label in spec.choices:
                w.addItem(label, key)
            w.setCurrentIndex(max(0, w.findData(spec.default)))
            return w
        else:
            w = QLineEdit(str(spec.default))
            return w
        if spec.suffix:
            w.setSuffix(spec.suffix)
        return w

    def values(self) -> dict:
        out = {}
        for key, w in self.widgets.items():
            kind = self._specs[key].kind
            if kind == "bool":
                out[key] = w.isChecked()
            elif kind == "choice":
                out[key] = w.currentData()
            elif kind == "text":
                out[key] = w.text().strip()
            else:
                out[key] = w.value()
        return out

    def set_values(self, values: dict):
        for key, value in values.items():
            w = self.widgets.get(key)
            if w is None:
                continue
            kind = self._specs[key].kind
            if kind == "bool":
                w.setChecked(bool(value))
            elif kind == "choice":
                w.setCurrentIndex(max(0, w.findData(value)))
            elif kind == "text":
                w.setText(str(value))
            else:
                w.setValue(value)


class PathPicker(QWidget):
    """Editable combo with the raster layers of the project plus a file browser."""

    def __init__(self, caption: str, optional: bool = False, file_filter: str = RASTER_FILTER, parent=None):
        super().__init__(parent)
        self._caption = caption
        self._filter = file_filter
        self._names = {}
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        self.combo = QComboBox()
        self.combo.setEditable(True)
        self.combo.setMinimumWidth(280)
        self.button = QPushButton("Przeglądaj...")
        self.button.clicked.connect(self._browse)
        lay.addWidget(self.combo, 1)
        lay.addWidget(self.button)
        self.optional = optional
        self.refresh()

    def refresh(self):
        current = self.path()
        self.combo.clear()
        self._names = {}
        self.combo.addItem("")
        for layer in QgsProject.instance().mapLayers().values():
            if compat.is_raster(layer) and os.path.isfile(layer.source().split("|")[0]):
                self._names[layer.name()] = layer.source().split("|")[0]
                self.combo.addItem(layer.name())
        if current:
            self.set_path(current)

    def _browse(self):
        path, _flt = QFileDialog.getOpenFileName(self, self._caption, "", self._filter)
        if path:
            self.set_path(path)

    def set_path(self, path: str):
        for name, source in self._names.items():
            if os.path.normpath(source) == os.path.normpath(path):
                self.combo.setCurrentIndex(self.combo.findText(name))
                return
        self.combo.setEditText(path)

    def path(self) -> str:
        text = self.combo.currentText().strip()
        return self._names.get(text, text)


class FolderPicker(QWidget):
    def __init__(self, caption: str, parent=None):
        super().__init__(parent)
        self._caption = caption
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        self.edit = QLineEdit()
        self.button = QPushButton("Przeglądaj...")
        self.button.clicked.connect(self._browse)
        lay.addWidget(self.edit, 1)
        lay.addWidget(self.button)

    def _browse(self):
        path = QFileDialog.getExistingDirectory(self, self._caption, self.edit.text())
        if path:
            self.edit.setText(path)

    def path(self) -> str:
        return self.edit.text().strip()

    def set_path(self, path: str):
        self.edit.setText(path)


class PointLayerPicker(QWidget):
    """Combo with the point vector layers of the project."""

    def __init__(self, parent=None):
        super().__init__(parent)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        self.combo = QComboBox()
        self.combo.setMinimumWidth(280)
        lay.addWidget(self.combo, 1)
        self.refresh()

    def refresh(self):
        current = self.layer_id()
        self.combo.clear()
        self.combo.addItem("", None)
        for layer in QgsProject.instance().mapLayers().values():
            if compat.is_point_layer(layer):
                self.combo.addItem(layer.name(), layer.id())
        if current:
            self.set_layer_id(current)

    def layer_id(self):
        return self.combo.currentData()

    def set_layer_id(self, layer_id):
        idx = self.combo.findData(layer_id)
        if idx >= 0:
            self.combo.setCurrentIndex(idx)

    def layer(self):
        layer_id = self.layer_id()
        return QgsProject.instance().mapLayer(layer_id) if layer_id else None
