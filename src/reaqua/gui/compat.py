"""QGIS 3.x / 4.x (Qt5 / Qt6) compatibility helpers."""

from qgis.core import Qgis, QgsMapLayer

try:
    from qgis.core import QgsMapLayerType

    RASTER = QgsMapLayerType.RasterLayer
    VECTOR = QgsMapLayerType.VectorLayer
except ImportError:
    RASTER = QgsMapLayer.RasterLayer
    VECTOR = QgsMapLayer.VectorLayer

try:
    POINT_GEOMETRY = Qgis.GeometryType.Point
except AttributeError:
    from qgis.core import QgsWkbTypes

    POINT_GEOMETRY = QgsWkbTypes.PointGeometry

try:
    LEVEL_SUCCESS = Qgis.MessageLevel.Success
    LEVEL_WARNING = Qgis.MessageLevel.Warning
    LEVEL_CRITICAL = Qgis.MessageLevel.Critical
except AttributeError:
    LEVEL_SUCCESS = Qgis.Success
    LEVEL_WARNING = Qgis.Warning
    LEVEL_CRITICAL = Qgis.Critical


def is_raster(layer) -> bool:
    return layer is not None and layer.type() == RASTER


def is_point_layer(layer) -> bool:
    return layer is not None and layer.type() == VECTOR and layer.geometryType() == POINT_GEOMETRY
