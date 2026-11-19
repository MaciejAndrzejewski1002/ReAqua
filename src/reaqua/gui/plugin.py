"""ReAqua QGIS plugin: one menu, one toolbar button and a layer context menu."""

import datetime
import os

from qgis.core import QgsApplication, QgsTask
from qgis.PyQt.QtCore import QUrl
from qgis.PyQt.QtGui import QDesktopServices, QIcon
from qgis.PyQt.QtWidgets import QAction, QMessageBox, QPushButton

from .. import __authors__, __team_lead__, __version__
from ..core import io
from . import compat, jobs, layers
from .dialog import ReAquaDialog

ALL_STEPS = ("scout", "kriging", "report")
MENU = "&ReAqua"
CONTEXT_MENU = "ReAqua"


class ReAquaPlugin:
    def __init__(self, iface):
        self.iface = iface
        self.actions = []
        self.context_actions = []
        self._tasks = []
        self._dialogs = []

    def initGui(self):
        icon_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "icon.png")
        icon = QIcon(icon_path) if os.path.exists(icon_path) else QIcon()
        window = self.iface.mainWindow()

        entries = (
            ("Pełna analiza (Scout + Kriging + Raport)...", lambda: self.open_dialog(ALL_STEPS)),
            ("Scout - susza i lokalizacja zbiorników...", lambda: self.open_dialog(("scout",))),
            ("Kriging - zasięg mitygacji...", lambda: self.open_dialog(("kriging",))),
            ("Raport regionalny...", lambda: self.open_dialog(("report",))),
        )
        for index, (text, callback) in enumerate(entries):
            action = QAction(icon, text, window)
            action.triggered.connect(lambda _checked=False, cb=callback: cb())
            self.iface.addPluginToMenu(MENU, action)
            if index == 0:
                self.iface.addToolBarIcon(action)
            self.actions.append(action)
        about = QAction("O wtyczce ReAqua", window)
        about.triggered.connect(lambda _checked=False: self.show_about())
        self.iface.addPluginToMenu(MENU, about)
        self.actions.append(about)

        context = (
            (compat.RASTER, "Pełna analiza ReAqua z tej sceny...", ALL_STEPS, "scene"),
            (compat.RASTER, "Scout: wykryj suszę i zaproponuj zbiorniki...", ("scout",), "scene"),
            (compat.RASTER, "Kriging: użyj jako raster suszy...", ("kriging",), "drought"),
            (compat.RASTER, "Raport: użyj jako raster suszy...", ("report",), "drought"),
            (compat.VECTOR, "Kriging: użyj jako zbiorniki...", ("kriging",), "reservoirs"),
            (compat.VECTOR, "Raport: użyj jako zbiorniki...", ("report",), "reservoirs"),
        )
        for layer_type, text, steps, role in context:
            action = QAction(icon, text, window)
            action.triggered.connect(
                lambda _checked=False, s=steps, r=role: self.open_dialog(s, self._preset_from_current(r)))
            self.iface.addCustomActionForLayerType(action, CONTEXT_MENU, layer_type, True)
            self.context_actions.append(action)

    def unload(self):
        for action in self.actions:
            self.iface.removePluginMenu(MENU, action)
            self.iface.removeToolBarIcon(action)
        for action in self.context_actions:
            self.iface.removeCustomActionForLayerType(action)
        self.actions, self.context_actions = [], []

    def _preset_from_current(self, role: str) -> dict:
        layer = self.iface.layerTreeView().currentLayer() or self.iface.activeLayer()
        if layer is None:
            return {}
        if role == "reservoirs":
            if not compat.is_point_layer(layer):
                self.iface.messageBar().pushMessage("ReAqua", "Wybrana warstwa nie jest warstwą punktową.",
                                                    level=compat.LEVEL_WARNING, duration=6)
                return {}
            return {"reservoir_layer_id": layer.id()}
        if not compat.is_raster(layer):
            return {}
        source = layer.source().split("|")[0]
        if role == "drought":
            return {"drought_raster": source}
        return {"scene_folder": os.path.dirname(source)}

    def open_dialog(self, steps, preset=None):
        dlg = ReAquaDialog(self.iface.mainWindow(), steps, preset)
        dlg.run_btn.clicked.connect(lambda: self._start(dlg))
        self._dialogs.append(dlg)
        dlg.exec()
        self._dialogs.remove(dlg)

    def _start(self, dlg: ReAquaDialog):
        try:
            job = dlg.collect_job()
        except (ValueError, FileNotFoundError, RuntimeError) as exc:
            QMessageBox.warning(dlg, "ReAqua - brak danych", str(exc))
            return
        dlg.set_busy(True)
        dlg.append_log("Start analizy: " + ", ".join(job["steps"]))
        label = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        task = QgsTask.fromFunction(
            "ReAqua - analiza", jobs.execute, job,
            on_finished=lambda exception, result=None: self._finished(dlg, label, exception, result),
        )
        task.progressChanged.connect(dlg.set_progress)
        self._tasks.append(task)
        QgsApplication.taskManager().addTask(task)

    def _finished(self, dlg: ReAquaDialog, label: str, exception, result):
        self._tasks = [t for t in self._tasks if t.isActive()]
        dlg.set_busy(False)
        if exception is not None or result is None:
            message = str(exception) if exception else "Analiza zakończyła się bez wyniku."
            dlg.append_log("Błąd: " + message)
            QMessageBox.critical(dlg, "ReAqua - błąd analizy", message)
            return
        if not result.get("reservoirs"):
            dlg.append_log(result.get("message") or "Nie znaleziono lokalizacji zbiorników.")
            QMessageBox.warning(dlg, "ReAqua - brak wyników", result.get("message") or "Nie znaleziono lokalizacji.")
            return
        added = layers.add_results(result, label)
        dlg.set_progress(100)
        dlg.append_log(self._summary(result, len(added)))
        self._push_report_button(result.get("paths", {}).get("report"))

    @staticmethod
    def _summary(result: dict, n_layers: int) -> str:
        lines = [f"Zbiorniki: {len(result['reservoirs'])}", f"Dodano warstw: {n_layers}"]
        stats = result.get("drought_stats")
        if stats:
            lines.append(f"Obszar suszy: {stats['drought_ha']:.1f} ha ({stats['drought_share_pct']:.1f}%)")
        kr = result.get("kriging", {})
        for note in kr.get("notes", []):
            lines.append(note)
        res = result.get("result")
        if res:
            lines.append(f"MCI {res['mci']}%, MEI {res['mei']}%, koszt {res['cost']['min'] / 1e6:.1f}-"
                         f"{res['cost']['max'] / 1e6:.1f} mln zł")
        return "\n".join(lines)

    def _push_report_button(self, report_path):
        if not report_path:
            return
        bar = self.iface.messageBar()
        widget = bar.createMessage("ReAqua", "Analiza zakończona.")
        button = QPushButton("Otwórz raport")
        button.clicked.connect(lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(report_path)))
        widget.layout().addWidget(button)
        bar.pushWidget(widget, compat.LEVEL_SUCCESS, 0)

    def show_about(self):
        QMessageBox.information(
            self.iface.mainWindow(), "O wtyczce ReAqua",
            f"ReAqua {__version__}\n\nWspólna wtyczka: Scout, Kriging i Raport regionalny.\n"
            f"Backend rastrowy: {io.BACKEND}\n\nZespół Hydronauts (11. CASSINI Hackathon):\n"
            + "\n".join(f"  {a}{' (lider)' if a == __team_lead__ else ''}" for a in __authors__),
        )
