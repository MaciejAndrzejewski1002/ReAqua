"""Add and style result layers in the QGIS project."""

import os

from qgis.core import (
    QgsColorRampShader,
    QgsGraduatedSymbolRenderer,
    QgsMarkerSymbol,
    QgsPalLayerSettings,
    QgsProject,
    QgsRasterLayer,
    QgsRasterShader,
    QgsRendererRange,
    QgsSingleBandPseudoColorRenderer,
    QgsTextFormat,
    QgsVectorLayer,
    QgsVectorLayerSimpleLabeling,
)
from qgis.PyQt.QtGui import QColor

_DROUGHT_ITEMS = (
    (0, "#4caf50", "Brak suszy"),
    (1, "#f9e237", "Lekka susza"),
    (2, "#e86000", "Umiarkowana susza"),
    (3, "#7b0000", "Silna susza"),
)
_MITIGATION_ITEMS = (
    (0.00, "#c8d8c8", "Brak wpływu"), (0.10, "#a8c8a0", "Minimalny"), (0.25, "#70b8d0", "Niski"),
    (0.50, "#2090c8", "Umiarkowany"), (0.75, "#0060a0", "Wysoki"), (1.00, "#003070", "Pełny"),
)
_RESIDUAL_ITEMS = (
    (0.00, "#4caf50", "Brak ryzyka"), (0.20, "#a8d060", "Niskie"), (0.40, "#f9e237", "Umiarkowane"),
    (0.60, "#e86000", "Wysokie"), (0.80, "#bb1010", "Bardzo wysokie"), (1.00, "#5a0000", "Krytyczne"),
)
_PRIORITY_STYLE = (
    (1, 1, "#7b0000", 11.0, "Priorytet 1 (najwyższy)"),
    (2, 3, "#cc2200", 9.0, "Priorytet 2-3"),
    (4, 7, "#e86000", 7.5, "Priorytet 4-7"),
    (8, 9999, "#c8a000", 6.0, "Priorytet 8+"),
)


def _style_raster(layer, items, interpolated: bool):
    ramp = QgsColorRampShader()
    ramp.setColorRampType(QgsColorRampShader.Interpolated if interpolated else QgsColorRampShader.Exact)
    ramp.setColorRampItemList([QgsColorRampShader.ColorRampItem(v, QColor(c), label) for v, c, label in items])
    shader = QgsRasterShader()
    shader.setRasterShaderFunction(ramp)
    layer.setRenderer(QgsSingleBandPseudoColorRenderer(layer.dataProvider(), 1, shader))
    layer.triggerRepaint()


def _add(layer, group):
    QgsProject.instance().addMapLayer(layer, False)
    group.addLayer(layer)


def add_raster(path: str, name: str, kind: str, group):
    layer = QgsRasterLayer(path, name)
    if not layer.isValid():
        return None
    if kind == "drought":
        _style_raster(layer, _DROUGHT_ITEMS, False)
    elif kind == "residual":
        _style_raster(layer, _RESIDUAL_ITEMS, True)
    else:
        _style_raster(layer, _MITIGATION_ITEMS, True)
    _add(layer, group)
    return layer


def add_reservoirs(db_path: str, run_id: int, group):
    layer = QgsVectorLayer(f"{db_path}|layername=reservoirs", f"Zbiorniki (analiza {run_id})", "ogr")
    if not layer.isValid():
        return None
    layer.setSubsetString(f'"run_id" = {int(run_id)}')
    ranges = []
    for lo, hi, color, size, label in _PRIORITY_STYLE:
        symbol = QgsMarkerSymbol.createSimple({
            "name": "circle", "color": color, "size": str(size), "outline_color": "#222222", "outline_width": "0.4",
        })
        ranges.append(QgsRendererRange(lo, hi, symbol, label))
    layer.setRenderer(QgsGraduatedSymbolRenderer("priorytet", ranges))
    settings = QgsPalLayerSettings()
    settings.fieldName = "priorytet"
    settings.enabled = True
    fmt = QgsTextFormat()
    fmt.setSize(9)
    settings.setFormat(fmt)
    layer.setLabelsEnabled(True)
    layer.setLabeling(QgsVectorLayerSimpleLabeling(settings))
    _add(layer, group)
    return layer


def add_results(result: dict, label: str):
    """Add every produced layer into a new layer-tree group; returns the list of added layers."""
    root = QgsProject.instance().layerTreeRoot()
    group = root.insertGroup(0, f"ReAqua - {label}")
    paths = result.get("paths", {})
    added = []
    for key, name, kind in (("drought", "Mapa suszy", "drought"),
                            ("residual", "Ryzyko resztkowe suszy", "residual"),
                            ("mitigation", "Mitygacja suszy", "mitigation"),
                            ("kriging", "Kriging wpływu retencji", "mitigation")):
        if paths.get(key) and os.path.exists(paths[key]):
            layer = add_raster(paths[key], name, kind, group)
            if layer is not None:
                added.append(layer)
    if paths.get("db") and paths.get("run_id"):
        layer = add_reservoirs(paths["db"], paths["run_id"], group)
        if layer is not None:
            added.append(layer)
    return added
