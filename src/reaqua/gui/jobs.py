"""Job preparation (GUI thread) and execution (background thread) for the plugin."""

import os

import numpy as np

from ..core import io, pipeline, schema
from ..core.models import NODATA_CLASS
from ..core.params import merge


def layer_to_reservoirs(layer, wkt: str, depth_m: float, area_ha: float) -> list:
    """Convert a QGIS point layer into Reservoir objects in the raster CRS (GUI thread only)."""
    from qgis.core import QgsCoordinateReferenceSystem, QgsCoordinateTransform, QgsPointXY, QgsProject

    names = [f.name() for f in layer.fields()]
    dest = QgsCoordinateReferenceSystem()
    dest.createFromWkt(wkt)
    transform = QgsCoordinateTransform(layer.crs(), dest, QgsProject.instance())
    out = []
    for feat in layer.getFeatures():
        geom = feat.geometry()
        if geom is None or geom.isEmpty():
            continue
        props = {name: feat[name] for name in names}
        try:
            x, y = float(props["x_proj"]), float(props["y_proj"])
        except (KeyError, TypeError, ValueError):
            point = geom.asMultiPoint()[0] if geom.isMultipart() else geom.asPoint()
            moved = transform.transform(QgsPointXY(point))
            x, y = moved.x(), moved.y()
        out.append(schema.from_props(props, x, y, depth_m, area_ha))
    if out:
        lon, lat = io.to_wgs84([r.x for r in out], [r.y for r in out], wkt)
        for res, lo, la in zip(out, lon, lat):
            res.lon, res.lat = float(lo), float(la)
    return out


def default_out_dir(job: dict) -> str:
    ref = job["scene"].get("red") or job.get("drought_path") or os.path.expanduser("~")
    return os.path.join(os.path.dirname(os.path.abspath(ref)), "reaqua_wyniki")


def execute(task, job: dict) -> dict:
    """Run the selected steps; called by QgsTask in a worker thread (no GUI calls here)."""
    p = merge(job["params"])
    steps = tuple(job["steps"])
    out_dir = job["out_dir"]
    os.makedirs(out_dir, exist_ok=True)

    def progress(value, message):
        task.setProgress(100.0 * value)

    if "scout" in steps:
        return pipeline.run_pipeline(job["scene"], out_dir, p, job["sensor"], steps, progress=progress)

    arr, _nodata, grid = io.read_raster(job["drought_path"])
    drought = arr.astype(np.uint8)
    drought[drought > 3] = NODATA_CLASS
    reservoirs = job["reservoirs"]
    out = {"paths": {}, "reservoirs": reservoirs, "grid": grid, "drought": drought, "steps": list(steps)}

    mitigation, source = None, None
    if "kriging" in steps:
        progress(0.2, "Kriging anizotropowy")
        kr = pipeline.run_kriging_step(grid, drought, reservoirs, p, out_dir)
        out["kriging"] = {"stats": kr["stats"], "notes": kr["notes"]}
        out["paths"].update(kr["paths"])
        mitigation, source = kr["mitigation"], f"kriging ({kr['stats']['kriging_type']})"
    elif job.get("mitigation_path"):
        raw = io.read_aligned(job["mitigation_path"], grid, "bilinear")
        mitigation = np.clip(np.nan_to_num(raw, nan=0.0), 0.0, 1.0).astype(np.float32)
        source = "wczytany raster mitygacji"

    if "report" in steps:
        progress(0.7, "Raport regionalny")
        rp = pipeline.run_report_step(grid, drought, reservoirs, mitigation, p, out_dir, source)
        out["result"] = rp["result"]
        out["paths"].update({"report": rp["report_path"], "metrics": rp["metrics_path"]})
        out["paths"].update(pipeline.save_outputs(reservoirs, rp["result"], p, out_dir, job["sensor"]))
    progress(1.0, "Zakończono")
    return out
