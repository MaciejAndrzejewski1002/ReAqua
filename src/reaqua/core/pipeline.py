"""End-to-end analysis (Scout -> Kriging -> Report) shared by the QGIS plugin and the CLI."""

import json
import os

import numpy as np

from . import hydrology, io, kriging, report, schema, scout
from .models import NODATA_CLASS, Grid
from .params import merge

OUTPUT_NAMES = {
    "drought": "susza.tif",
    "mitigation": "mitygacja_suszy.tif",
    "kriging": "kriging_wplyw.tif",
    "residual": "ryzyko_resztkowe.tif",
    "geojson": "zbiorniki.geojson",
    "csv": "zbiorniki.csv",
    "report": "raport_regionalny.html",
    "metrics": "metryki.json",
    "db": "reaqua.gpkg",
}
STEPS = ("scout", "kriging", "report")


def _progress(cb, value: float, message: str):
    if cb:
        cb(value, message)


def load_scene(paths: dict, sensor: str, p: dict) -> tuple:
    """Read bands from file paths and align them to the red-band grid -> (bands, Grid)."""
    missing = [k for k in ("red", "nir", "swir") if not paths.get(k)]
    if missing:
        raise ValueError(f"Brak pasm: {', '.join(missing)}")
    red, grid = io.read_float(paths["red"])
    bands = {"red": red}
    for role in ("nir", "swir", "green", "scl"):
        if paths.get(role):
            method = "nearest" if role == "scl" else "bilinear"
            bands[role] = io.read_aligned(paths[role], grid, method)
    if paths.get("mask"):
        bands["mask"] = io.read_aligned(paths["mask"], grid, "nearest")
    return bands, grid


def run_scout_step(bands: dict, grid: Grid, p: dict, sensor: str, out_dir: str) -> dict:
    drought = scout.build_drought_map(bands, grid, p, sensor)
    path = io.write_raster(os.path.join(out_dir, OUTPUT_NAMES["drought"]), drought, grid, nodata=NODATA_CLASS)
    found = scout.run_scout(drought, grid, p)
    return {"drought": drought, "drought_path": path, "reservoirs": found["reservoirs"],
            "message": found["message"], "stats": scout.drought_statistics(drought, grid)}


def run_kriging_step(grid: Grid, drought: np.ndarray, reservoirs: list, p: dict, out_dir: str) -> dict:
    res = kriging.run_kriging(grid, drought, reservoirs, p)
    res["paths"] = {
        "mitigation": io.write_raster(os.path.join(out_dir, OUTPUT_NAMES["mitigation"]), res["mitigation"], grid,
                                      nodata=-9999.0),
        "kriging": io.write_raster(os.path.join(out_dir, OUTPUT_NAMES["kriging"]), res["kriging"], grid,
                                   nodata=-9999.0),
        "residual": io.write_raster(os.path.join(out_dir, OUTPUT_NAMES["residual"]), res["residual"], grid,
                                    nodata=-9999.0),
    }
    return res


def run_report_step(grid: Grid, drought: np.ndarray, reservoirs: list, mitigation, p: dict, out_dir: str,
                    mitigation_source: str = None) -> dict:
    result = hydrology.compute_regional(reservoirs, grid, drought, mitigation, p, mitigation_source)
    path = report.write_html(os.path.join(out_dir, OUTPUT_NAMES["report"]), result, p["region_label"], p)
    metrics = os.path.join(out_dir, OUTPUT_NAMES["metrics"])
    with open(metrics, "w", encoding="utf-8") as fh:
        json.dump(result, fh, ensure_ascii=False, indent=2, default=str)
    return {"result": result, "report_path": path, "metrics_path": metrics}


def save_outputs(reservoirs: list, result: dict, p: dict, out_dir: str, sensor: str, db_path: str = None) -> dict:
    paths = {
        "geojson": schema.write_geojson(os.path.join(out_dir, OUTPUT_NAMES["geojson"]), reservoirs),
        "csv": schema.write_csv(os.path.join(out_dir, OUTPUT_NAMES["csv"]), reservoirs),
    }
    from ..db import geopackage

    db_file = db_path or os.path.join(out_dir, OUTPUT_NAMES["db"])
    conn = geopackage.connect(db_file)
    try:
        run_id = geopackage.save_run(conn, reservoirs, result, p, p["region_label"], sensor)
    finally:
        conn.close()
    paths["db"] = db_file
    paths["run_id"] = run_id
    return paths


def run_pipeline(paths: dict, out_dir: str, params: dict = None, sensor: str = "sentinel", steps=STEPS,
                 db_path: str = None, progress=None) -> dict:
    """Run the selected steps on band files; returns paths, arrays and statistics."""
    p = merge(params)
    os.makedirs(out_dir, exist_ok=True)
    out = {"paths": {}, "steps": list(steps)}

    _progress(progress, 0.05, "Wczytywanie i dopasowanie pasm")
    bands, grid = load_scene(paths, sensor, p)
    out["grid"] = grid

    _progress(progress, 0.25, "Klasyfikacja suszy i wybór lokalizacji (Scout)")
    sc = run_scout_step(bands, grid, p, sensor, out_dir)
    out.update({"drought": sc["drought"], "reservoirs": sc["reservoirs"], "drought_stats": sc["stats"],
                "message": sc["message"]})
    out["paths"]["drought"] = sc["drought_path"]
    if not sc["reservoirs"]:
        return out

    mitigation, source = None, None
    if "kriging" in steps:
        _progress(progress, 0.55, "Kriging anizotropowy")
        kr = run_kriging_step(grid, sc["drought"], sc["reservoirs"], p, out_dir)
        out["kriging"] = {"stats": kr["stats"], "notes": kr["notes"]}
        out["paths"].update(kr["paths"])
        mitigation, source = kr["mitigation"], f"kriging ({kr['stats']['kriging_type']})"

    result = {"n_reservoirs": len(sc["reservoirs"])}
    if "report" in steps:
        _progress(progress, 0.8, "Raport regionalny")
        rp = run_report_step(grid, sc["drought"], sc["reservoirs"], mitigation, p, out_dir, source)
        result = rp["result"]
        out["result"] = result
        out["paths"].update({"report": rp["report_path"], "metrics": rp["metrics_path"]})
    out["paths"].update(save_outputs(sc["reservoirs"], result, p, out_dir, sensor, db_path))
    _progress(progress, 1.0, "Zakończono")
    return out
