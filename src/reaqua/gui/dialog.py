"""Single tabbed dialog for the whole ReAqua workflow (Scout, Kriging, Report)."""

import os

from qgis.PyQt.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from .. import __version__
from ..core import io
from ..core import params as P
from . import jobs
from .widgets import FolderPicker, ParamForm, PathPicker, PointLayerPicker

STEP_LABELS = (
    ("scout", "Scout - klasyfikacja suszy i lokalizacja zbiorników"),
    ("kriging", "Kriging - zasięg mitygacji i ryzyko resztkowe"),
    ("report", "Raport - bilans, roślinność, koszty (HTML), zapis do bazy"),
)
BAND_ROLES = (
    ("red", "Pasmo RED (B04 / B4)", False),
    ("nir", "Pasmo NIR (B08 / B5)", False),
    ("swir", "Pasmo SWIR1 (B11 / B6)", False),
    ("green", "Pasmo zielone (B03 / B3) - opcjonalne, maska wody", True),
    ("scl", "Warstwa SCL Sentinel-2 - opcjonalna, maska chmur", True),
    ("mask", "Maska gruntów ornych (1 = uprawy) - opcjonalna", True),
)


class ReAquaDialog(QDialog):
    def __init__(self, parent=None, steps=("scout", "kriging", "report"), preset=None):
        super().__init__(parent)
        self.setWindowTitle(f"ReAqua {__version__} - małą retencją przeciw suszy")
        self.setMinimumWidth(760)
        self._build(steps)
        self.apply_preset(preset or {})
        self._sync()

    def _build(self, steps):
        root = QVBoxLayout(self)
        header = QLabel("<b>ReAqua</b> - lokalizacja zbiorników małej retencji, kriging zasięgu oddziaływania i raport regionalny")
        header.setWordWrap(True)
        root.addWidget(header)

        self.tabs = QTabWidget()
        root.addWidget(self.tabs)
        self.tabs.addTab(self._tab_data(steps), "Dane")

        self.form_drought = ParamForm(P.SCOUT_DROUGHT)
        drought = QWidget()
        lay = QVBoxLayout(drought)
        row = QHBoxLayout()
        row.addWidget(QLabel("Profil progów:"))
        self.preset_combo = QComboBox()
        for key, spec in P.THRESHOLD_PRESETS.items():
            self.preset_combo.addItem(spec["label"], key)
        self.preset_combo.currentIndexChanged.connect(self._apply_threshold_preset)
        row.addWidget(self.preset_combo, 1)
        lay.addLayout(row)
        lay.addWidget(self.form_drought)
        lay.addStretch()
        self.tabs.addTab(drought, "Susza")

        self.form_algo = ParamForm(P.SCOUT_ALGORITHM)
        self.form_reservoir = ParamForm(P.RESERVOIR_PARAMS)
        self.form_kriging = ParamForm(P.KRIGING_PARAMS)
        self.form_report = ParamForm(P.REPORT_PARAMS)
        self.tab_algo = self._wrap(self.form_algo)
        self.tab_reservoir = self._wrap(self.form_reservoir)
        self.tab_kriging = self._wrap(self.form_kriging)
        self.tab_report = self._wrap(self.form_report)
        self.tabs.addTab(self.tab_algo, "Lokalizacja")
        self.tabs.addTab(self.tab_reservoir, "Zbiorniki i koszty")
        self.tabs.addTab(self.tab_kriging, "Wiatr, gleba, kriging")
        self.tabs.addTab(self.tab_report, "Raport")

        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setMaximumHeight(110)
        root.addWidget(self.log)
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        root.addWidget(self.progress)
        buttons = QHBoxLayout()
        buttons.addStretch()
        self.run_btn = QPushButton("Uruchom analizę")
        self.close_btn = QPushButton("Zamknij")
        self.close_btn.clicked.connect(self.reject)
        buttons.addWidget(self.run_btn)
        buttons.addWidget(self.close_btn)
        root.addLayout(buttons)

    @staticmethod
    def _wrap(form):
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.addWidget(form)
        lay.addStretch()
        return w

    def _tab_data(self, steps):
        w = QWidget()
        lay = QVBoxLayout(w)

        box = QGroupBox("Etapy analizy")
        v = QVBoxLayout(box)
        self.step_boxes = {}
        for key, label in STEP_LABELS:
            cb = QCheckBox(label)
            cb.setChecked(key in steps)
            cb.toggled.connect(self._sync)
            self.step_boxes[key] = cb
            v.addWidget(cb)
        lay.addWidget(box)

        self.scene_box = QGroupBox("Scena satelitarna")
        form = QFormLayout(self.scene_box)
        self.sensor = QComboBox()
        for key, label in P.SENSORS:
            self.sensor.addItem(label, key)
        form.addRow("Sensor:", self.sensor)
        self.scene_folder = FolderPicker("Folder ze sceną")
        detect = QPushButton("Wykryj pasma w folderze")
        detect.clicked.connect(self._detect)
        row = QHBoxLayout()
        row.addWidget(self.scene_folder, 1)
        row.addWidget(detect)
        form.addRow("Folder sceny:", row)
        self.band_pickers = {}
        for role, label, optional in BAND_ROLES:
            picker = PathPicker(label, optional)
            self.band_pickers[role] = picker
            form.addRow(label + ":", picker)
        lay.addWidget(self.scene_box)

        self.prev_box = QGroupBox("Wyniki wcześniejszych etapów (gdy Scout wyłączony)")
        form2 = QFormLayout(self.prev_box)
        self.reservoir_picker = PointLayerPicker()
        self.drought_picker = PathPicker("Raster suszy")
        self.mitigation_picker = PathPicker("Raster mitygacji", optional=True)
        form2.addRow("Warstwa zbiorników (punkty):", self.reservoir_picker)
        form2.addRow("Raster suszy (klasy 0-3):", self.drought_picker)
        form2.addRow("Raster mitygacji (opcjonalnie):", self.mitigation_picker)
        lay.addWidget(self.prev_box)

        out_box = QGroupBox("Wyniki")
        form3 = QFormLayout(out_box)
        self.out_picker = FolderPicker("Folder wyników")
        form3.addRow("Folder wyników (puste = obok danych):", self.out_picker)
        lay.addWidget(out_box)
        lay.addStretch()
        return w

    def _sync(self, *_args):
        scout = self.step_boxes["scout"].isChecked()
        self.scene_box.setEnabled(scout)
        self.prev_box.setEnabled(not scout)
        self.tab_algo.setEnabled(scout)
        self.form_drought.setEnabled(scout)
        self.tab_kriging.setEnabled(self.step_boxes["kriging"].isChecked() or self.step_boxes["report"].isChecked())
        self.tab_report.setEnabled(self.step_boxes["report"].isChecked())

    def _apply_threshold_preset(self, _index=None):
        key = self.preset_combo.currentData()
        if key in P.THRESHOLD_PRESETS:
            self.form_drought.set_values(P.THRESHOLD_PRESETS[key]["values"])

    def _detect(self):
        folder = self.scene_folder.path()
        if not folder or not os.path.isdir(folder):
            self.append_log("Wskaż istniejący folder ze sceną.")
            return
        found = io.find_bands(folder, self.sensor.currentData())
        for role, picker in self.band_pickers.items():
            if role in found:
                picker.set_path(found[role])
        self.append_log("Wykryte pasma: " + (", ".join(sorted(found)) or "brak"))

    def apply_preset(self, preset: dict):
        if preset.get("scene_folder"):
            self.scene_folder.set_path(preset["scene_folder"])
            self._detect()
        if preset.get("drought_raster"):
            self.drought_picker.set_path(preset["drought_raster"])
        if preset.get("reservoir_layer_id"):
            self.reservoir_picker.set_layer_id(preset["reservoir_layer_id"])

    def append_log(self, text: str):
        self.log.appendPlainText(text)

    def set_progress(self, value: float):
        self.progress.setValue(int(value))

    def set_busy(self, busy: bool):
        self.run_btn.setEnabled(not busy)
        if busy:
            self.progress.setValue(0)

    def collect_job(self) -> dict:
        steps = [key for key, cb in self.step_boxes.items() if cb.isChecked()]
        if not steps:
            raise ValueError("Wybierz co najmniej jeden etap analizy.")
        values = {}
        for form in (self.form_drought, self.form_algo, self.form_reservoir, self.form_kriging, self.form_report):
            values.update(form.values())
        job = {"steps": steps, "sensor": self.sensor.currentData(), "params": values, "scene": {},
               "drought_path": None, "mitigation_path": None, "reservoirs": None}
        if "scout" in steps:
            scene = {role: picker.path() for role, picker in self.band_pickers.items()}
            for role in ("red", "nir", "swir"):
                if not scene[role] or not os.path.isfile(scene[role]):
                    raise ValueError(f"Brak poprawnego pliku dla pasma {role.upper()}.")
            job["scene"] = {k: v for k, v in scene.items() if v}
        else:
            drought_path = self.drought_picker.path()
            if not drought_path or not os.path.isfile(drought_path):
                raise ValueError("Kriging i raport wymagają rastra suszy (klasy 0-3).")
            layer = self.reservoir_picker.layer()
            if layer is None:
                raise ValueError("Wybierz warstwę punktów zbiorników.")
            grid = io.read_grid(drought_path)
            if not io.is_projected(grid.wkt):
                raise ValueError("Raster suszy musi mieć układ współrzędnych w metrach.")
            reservoirs = jobs.layer_to_reservoirs(layer, grid.wkt, values["depth_m"], values["reservoir_area_ha"])
            if not reservoirs:
                raise ValueError("Wybrana warstwa nie zawiera punktów.")
            job.update({"drought_path": drought_path, "reservoirs": reservoirs,
                        "mitigation_path": self.mitigation_picker.path() or None})
        job["out_dir"] = self.out_picker.path() or jobs.default_out_dir(job)
        return job
