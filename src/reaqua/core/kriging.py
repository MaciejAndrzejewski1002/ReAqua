"""Kriging: reservoir mitigation footprint (anisotropic) and residual drought risk.

The field is a scenario model: reservoirs act as sources with value = mitigation weight,
background stations away from every reservoir carry value 0. Ordinary kriging (OK) or simple
kriging (SK, known mean 0) with an anisotropic Gaussian covariance interpolates between them.
"""

import numpy as np
from scipy.interpolate import RectBivariateSpline
from scipy.linalg import lu_factor, lu_solve

from . import io, physics
from .models import NODATA_CLASS, Grid, Reservoir
from .params import merge


def _weight(res: Reservoir) -> float:
    return min(1.0, physics.volume_weight(res.volume_m3) * physics.class_factor(res.drought_class))


def _radii(res: Reservoir, p: dict) -> dict:
    return physics.influence_radii(res.area_ha, p["wind_speed_ms"], p["soil_type"], p["k_moist"], p["k_micro"])


def analytic_field(grid: Grid, reservoirs: list, p: dict) -> np.ndarray:
    """Max-envelope of anisotropic Gaussian footprints, computed in a window around each reservoir."""
    az = physics.downwind_azimuth(p["wind_direction"])
    nugget = physics.soil(p["soil_type"])["nugget"]
    out = np.zeros((grid.nrows, grid.ncols), dtype=np.float32)
    for res in reservoirs:
        radii = _radii(res, p)
        reach = 1.6 * max(radii["r_micro_m"], radii["r_moist_m"])
        row, col = grid.rowcol(res.x, res.y)
        hr = int(np.ceil(reach / grid.px_h))
        hc = int(np.ceil(reach / grid.px_w))
        r0, r1 = max(0, row - hr), min(grid.nrows, row + hr + 1)
        c0, c1 = max(0, col - hc), min(grid.ncols, col + hc + 1)
        if r0 >= r1 or c0 >= c1:
            continue
        xs = grid.gt[0] + (np.arange(c0, c1) + 0.5) * grid.gt[1]
        ys = grid.gt[3] + (np.arange(r0, r1) + 0.5) * grid.gt[5]
        h = physics.aniso_distance(xs[None, :] - res.x, ys[:, None] - res.y, az,
                                   radii["r_micro_m"], radii["r_moist_m"])
        contrib = (_weight(res) * physics.gaussian_cov(h, nugget)).astype(np.float32)
        out[r0:r1, c0:c1] = np.maximum(out[r0:r1, c0:c1], contrib)
    return np.clip(out, 0.0, 1.0)


def background_stations(grid: Grid, reservoirs: list, p: dict, ranges: tuple) -> np.ndarray:
    """Jittered regular grid of zero-valued stations outside the reach of every reservoir."""
    n = int(p["n_stations"])
    if n <= 0:
        return np.empty((0, 2))
    rng = np.random.default_rng(int(p["seed"]))
    xmin, ymin, xmax, ymax = grid.extent
    k = int(np.ceil(np.sqrt(n)))
    gx = xmin + (np.arange(k) + 0.5) / k * (xmax - xmin)
    gy = ymin + (np.arange(k) + 0.5) / k * (ymax - ymin)
    xx, yy = np.meshgrid(gx, gy)
    xx = xx.ravel() + rng.uniform(-0.4, 0.4, xx.size) * (xmax - xmin) / k
    yy = yy.ravel() + rng.uniform(-0.4, 0.4, yy.size) * (ymax - ymin) / k
    az = physics.downwind_azimuth(p["wind_direction"])
    keep = np.ones(xx.size, dtype=bool)
    for res in reservoirs:
        h = physics.aniso_distance(xx - res.x, yy - res.y, az, ranges[0], ranges[1])
        keep &= h >= 1.3
    return np.column_stack([xx[keep], yy[keep]])


def krige(obs_xy: np.ndarray, obs_val: np.ndarray, gx: np.ndarray, gy: np.ndarray, azimuth: float,
          range_major: float, range_minor: float, nugget: float, kind: str = "ordinary",
          chunk: int = 4000) -> np.ndarray:
    """Anisotropic kriging prediction at points (gx, gy); returns array of the shape of gx.

    OK solves [[K, 1], [1', 0]] [w; mu] = [c0; 1] and predicts w'y.
    SK (known mean 0) solves K w = c0.
    """
    n = len(obs_val)
    shape = gx.shape
    if n == 0:
        return np.zeros(shape)
    nug = max(nugget, 1e-8)
    dx = obs_xy[:, 0][:, None] - obs_xy[:, 0][None, :]
    dy = obs_xy[:, 1][:, None] - obs_xy[:, 1][None, :]
    k_mat = physics.gaussian_cov(physics.aniso_distance(dx, dy, azimuth, range_major, range_minor), nug)
    k_mat = k_mat + nug * np.eye(n)
    ordinary = kind == "ordinary"
    if ordinary:
        a = np.zeros((n + 1, n + 1))
        a[:n, :n] = k_mat
        a[:n, n] = 1.0
        a[n, :n] = 1.0
    else:
        a = k_mat
    lu = lu_factor(a)
    px, py = gx.ravel(), gy.ravel()
    out = np.empty(px.size)
    for start in range(0, px.size, chunk):
        end = min(start + chunk, px.size)
        h = physics.aniso_distance(px[start:end, None] - obs_xy[None, :, 0],
                                   py[start:end, None] - obs_xy[None, :, 1], azimuth, range_major, range_minor)
        c0 = physics.gaussian_cov(h, nug)
        rhs = np.hstack([c0, np.ones((c0.shape[0], 1))]) if ordinary else c0
        w = lu_solve(lu, rhs.T)
        out[start:end] = (w[:n] * obs_val[:, None]).sum(axis=0)
    return out.reshape(shape)


def _upsample(coarse: np.ndarray, rows: np.ndarray, cols: np.ndarray, nr: int, nc: int) -> np.ndarray:
    spline = RectBivariateSpline(rows, cols, coarse, kx=1, ky=1)
    full = spline(np.arange(nr), np.arange(nc))
    return np.clip(full, 0.0, 1.0).astype(np.float32)


def run_kriging(grid: Grid, drought: np.ndarray, reservoirs: list, params: dict = None) -> dict:
    """Compute analytic, kriged, combined mitigation and residual drought risk rasters."""
    p = merge(params)
    if not reservoirs:
        raise ValueError("Brak punktów zbiorników.")
    if not io.is_projected(grid.wkt):
        raise ValueError("Raster suszy musi mieć układ współrzędnych w metrach (np. EPSG:32633 lub EPSG:2180).")

    analytic = analytic_field(grid, reservoirs, p)

    areas = np.array([r.area_ha for r in reservoirs])
    radii = [_radii(r, p) for r in reservoirs]
    r_major = float(np.average([x["r_micro_m"] for x in radii], weights=areas))
    r_minor = float(np.average([x["r_moist_m"] for x in radii], weights=areas))
    az = physics.downwind_azimuth(p["wind_direction"])
    nugget = physics.soil(p["soil_type"])["nugget"]

    stations = background_stations(grid, reservoirs, p, (r_major, r_minor))
    kind = p["kriging_type"]
    notes = []
    if kind == "ordinary" and len(stations) == 0:
        kind = "simple"
        notes.append("Brak stacji tła poza zasięgiem zbiorników - użyto krigingu prostego (SK).")

    obs_xy = np.vstack([np.array([[r.x, r.y] for r in reservoirs]), stations])
    obs_val = np.concatenate([[_weight(r) for r in reservoirs], np.zeros(len(stations))])

    step = max(1, int(np.ceil(max(grid.nrows, grid.ncols) / p["max_grid"])))
    rows = np.unique(np.append(np.arange(0, grid.nrows, step), grid.nrows - 1))
    cols = np.unique(np.append(np.arange(0, grid.ncols, step), grid.ncols - 1))
    xs = grid.gt[0] + (cols + 0.5) * grid.gt[1]
    ys = grid.gt[3] + (rows + 0.5) * grid.gt[5]
    gx, gy = np.meshgrid(xs, ys)
    coarse = krige(obs_xy, obs_val, gx, gy, az, r_major, r_minor, nugget, kind)
    kriged = _upsample(coarse, rows, cols, grid.nrows, grid.ncols)

    mode = p["combine"]
    if mode == "analytic":
        mitigation = analytic
    elif mode == "kriging":
        mitigation = kriged
    elif mode == "mean":
        mitigation = (analytic + kriged) / 2.0
    else:
        mitigation = np.maximum(analytic, kriged)
    mitigation = mitigation.astype(np.float32)

    in_drought = (drought >= 1) & (drought <= 3)
    residual = np.full(drought.shape, -9999.0, dtype=np.float32)
    valid = drought != NODATA_CLASS
    residual[valid] = (drought[valid].clip(0, 3) / 3.0) * (1.0 - mitigation[valid])
    n_drought = int(in_drought.sum())
    coverage = float((mitigation[in_drought] > 0.20).sum() / n_drought * 100.0) if n_drought else 0.0
    mean_mit = float(mitigation[in_drought].mean()) if n_drought else 0.0

    return {
        "analytic": analytic,
        "kriging": kriged,
        "mitigation": mitigation,
        "residual": residual,
        "stats": {
            "n_reservoirs": len(reservoirs),
            "n_stations": int(len(stations)),
            "kriging_type": kind,
            "coverage_pct": round(coverage, 1),
            "mean_mitigation": round(mean_mit, 4),
            "range_major_m": round(r_major, 1),
            "range_minor_m": round(r_minor, 1),
            "wind_azimuth_to": az,
        },
        "notes": notes,
    }
