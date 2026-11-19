"""Scout: area-weighted siting of small retention reservoirs from a drought map."""

import numpy as np
from scipy.ndimage import gaussian_filter

from . import costs, io, physics
from .models import NODATA_CLASS, Grid, Reservoir
from .params import merge
from . import spectral

CLASS_WEIGHTS = {1: 1.0, 2: 2.0, 3: 3.0}


def build_drought_map(bands: dict, grid: Grid, p: dict, sensor: str = "sentinel") -> np.ndarray:
    """Classify drought from aligned reflectance bands (red, nir, swir[, green, scl])."""
    red = spectral.to_reflectance(bands["red"], sensor, p["s2_offset"])
    nir = spectral.to_reflectance(bands["nir"], sensor, p["s2_offset"])
    swir = spectral.to_reflectance(bands["swir"], sensor, p["s2_offset"])
    green = bands.get("green")
    if green is not None:
        green = spectral.to_reflectance(green, sensor, p["s2_offset"])
    scl = bands.get("scl")
    exclude = spectral.invalid_mask(scl, sensor)
    water = spectral.water_mask(green, swir, scl, p["mndwi"], sensor)
    if water is not None:
        exclude = water if exclude is None else (exclude | water)
    user_mask = bands.get("mask")
    if user_mask is not None:
        outside = np.nan_to_num(user_mask, nan=0.0) <= 0
        exclude = outside if exclude is None else (exclude | outside)
    ndbi_arr = spectral.ndbi(nir, swir) if p.get("use_ndbi_filter") else None
    return spectral.classify(spectral.ndvi(red, nir), spectral.ndmi(nir, swir), p, exclude, ndbi_arr)


def block_mean(arr: np.ndarray, factor: int) -> np.ndarray:
    if factor <= 1:
        return arr.astype(np.float32)
    nr = (arr.shape[0] // factor) * factor
    nc = (arr.shape[1] // factor) * factor
    view = arr[:nr, :nc].reshape(nr // factor, factor, nc // factor, factor)
    return view.mean(axis=(1, 3), dtype=np.float32)


def allocate_quotas(weights: dict, budget: int) -> dict:
    """Split a point budget across zones proportionally to weight, at least one per zone when possible."""
    if budget <= 0 or not weights:
        return {}
    ids = sorted(weights, key=lambda z: -weights[z])
    if len(ids) >= budget:
        return {z: 1 for z in ids[:budget]}
    total = float(sum(weights.values()))
    remaining = budget - len(ids)
    raw = {z: (weights[z] / total * remaining if total > 0 else 0.0) for z in ids}
    quotas = {z: 1 + int(np.floor(raw[z])) for z in ids}
    leftover = budget - sum(quotas.values())
    for z in sorted(ids, key=lambda k: -(raw[k] - np.floor(raw[k])))[:max(leftover, 0)]:
        quotas[z] += 1
    return quotas


def _disk(radius_cells: float):
    r = int(np.ceil(radius_cells))
    yy, xx = np.mgrid[-r:r + 1, -r:r + 1]
    return r, (np.hypot(yy, xx) < radius_cells)


def select_points(density: np.ndarray, qualifying: np.ndarray, zone_weights: dict, zone_of: np.ndarray,
                  max_points: int, min_dist_cells: float) -> list:
    """Greedy selection by descending density with per-zone quotas and a global minimum distance.

    Returns a list of (row, col, density, zone) in selection order. Unused quota is redistributed
    to zones that still have free candidate cells.
    """
    rows, cols = np.nonzero(qualifying)
    if rows.size == 0:
        return []
    dens = density[rows, cols]
    order = np.argsort(-dens, kind="stable")
    rows, cols, dens = rows[order], cols[order], dens[order]
    zones = zone_of[rows, cols]
    blocked = np.zeros(density.shape, dtype=bool)
    radius, disk = _disk(max(min_dist_cells, 1.0))
    taken = {}
    selected = []
    available = dict(zone_weights)
    target = {}
    for _ in range(4):
        left = max_points - len(selected)
        if left <= 0 or not available:
            break
        extra = allocate_quotas(available, left)
        for z, k in extra.items():
            target[z] = taken.get(z, 0) + k
        progress = 0
        for i in range(rows.size):
            if len(selected) >= max_points:
                break
            r, c, z = int(rows[i]), int(cols[i]), int(zones[i])
            if blocked[r, c] or taken.get(z, 0) >= target.get(z, 0):
                continue
            selected.append((r, c, float(dens[i]), z))
            taken[z] = taken.get(z, 0) + 1
            progress += 1
            r0, r1 = max(0, r - radius), min(density.shape[0], r + radius + 1)
            c0, c1 = max(0, c - radius), min(density.shape[1], c + radius + 1)
            blocked[r0:r1, c0:c1] |= disk[r0 - r + radius:r1 - r + radius, c0 - c + radius:c1 - c + radius]
        free = {int(z) for z in np.unique(zones[~blocked[rows, cols]])}
        available = {z: w for z, w in zone_weights.items() if z in free}
        if progress == 0:
            break
    return selected


def _dominant_class(block: np.ndarray) -> int:
    vals = block[(block >= 1) & (block <= 3)]
    if vals.size == 0:
        return 0
    return int(np.bincount(vals, minlength=4)[1:].argmax() + 1)


def size_reservoir(drought_window_km2: float, p: dict) -> tuple:
    if p["size_mode"] == "proportional":
        area = float(np.clip(p["area_fraction"] * drought_window_km2 * 100.0, p["area_min_ha"], p["area_max_ha"]))
    else:
        area = float(p["reservoir_area_ha"])
    return area, area * 10_000.0 * p["depth_m"]


def run_scout(drought: np.ndarray, grid: Grid, params: dict = None) -> dict:
    """Select reservoir candidates from a drought-class raster.

    Returns {"reservoirs": [Reservoir], "density": coarse density, "message": str | None}.
    """
    p = merge(params)
    factor = max(1, int(round(p["analysis_cell_m"] / grid.px_w)))
    cell_m = factor * grid.px_w
    cell_km2 = (factor * grid.px_w) * (factor * grid.px_h) / 1e6

    lut = np.zeros(256, dtype=np.float32)
    for cls, weight in CLASS_WEIGHTS.items():
        if cls >= p["min_class"]:
            lut[cls] = weight
    weighted = block_mean(lut[drought], factor)
    in_drought = ((drought >= p["min_class"]) & (drought <= 3)).astype(np.float32)
    frac = block_mean(in_drought, factor)

    density = gaussian_filter(weighted, sigma=max(1.0, p["sigma_m"] / cell_m))
    peak = float(density.max())
    if peak <= 0:
        return {"reservoirs": [], "density": density, "message": "Brak pikseli suszy spełniających kryteria."}
    density = (density / peak).astype(np.float32)

    nr, nc = density.shape
    n_zones = int(p["n_zones"])
    zone_of = (np.minimum(np.arange(nr) * n_zones // nr, n_zones - 1)[:, None] * n_zones
               + np.minimum(np.arange(nc) * n_zones // nc, n_zones - 1)[None, :])
    qualifying = (weighted > 0) & (density >= p["min_density"])
    if not qualifying.any():
        return {"reservoirs": [], "density": density,
                "message": "Żadna komórka nie spełnia progu gęstości. Obniż minimalną gęstość lub klasę suszy."}
    zone_weights = {}
    for z in np.unique(zone_of[qualifying]):
        sel = qualifying & (zone_of == z)
        zone_weights[int(z)] = float(weighted[sel].sum() * cell_km2 * 1e6)

    picks = select_points(density, qualifying, zone_weights, zone_of, int(p["max_points"]),
                          p["min_distance_m"] / cell_m)
    if not picks:
        return {"reservoirs": [], "density": density,
                "message": "Kandydaci zostali odrzuceni przez minimalną odległość między punktami."}

    picks.sort(key=lambda t: -t[2])
    half = max(1, int(round(p["window_radius_m"] / cell_m)))
    reservoirs = []
    for priority, (r, c, dens, zone) in enumerate(picks, start=1):
        r0, r1 = max(0, r - half), min(nr, r + half + 1)
        c0, c1 = max(0, c - half), min(nc, c + half + 1)
        window_km2 = float(frac[r0:r1, c0:c1].sum() * cell_km2)
        block = drought[r * factor:(r + 1) * factor, c * factor:(c + 1) * factor]
        x, y = grid.xy(r * factor + factor / 2.0 - 0.5, c * factor + factor / 2.0 - 0.5)
        area_ha, volume = size_reservoir(window_km2, p)
        cost = costs.reservoir_cost(area_ha, p["waterproofing"], p["lining_factor"])
        radii = physics.influence_radii(area_ha, p["wind_speed_ms"], p["soil_type"], p["k_moist"], p["k_micro"])
        reservoirs.append(Reservoir(
            x=x, y=y, priority=priority, drought_class=_dominant_class(block), density=round(dens, 4),
            drought_area_km2=round(window_km2, 4), area_ha=area_ha, volume_m3=volume, zone=zone,
            cost_min_pln=cost["min"], cost_mid_pln=cost["mid"], cost_max_pln=cost["max"],
            r_moist_m=radii["r_moist_m"], r_micro_m=radii["r_micro_m"],
        ))
    if io.BACKEND is not None and grid.wkt:
        lon, lat = io.to_wgs84([r.x for r in reservoirs], [r.y for r in reservoirs], grid.wkt)
        for res, lo, la in zip(reservoirs, lon, lat):
            res.lon, res.lat = float(lo), float(la)
    return {"reservoirs": reservoirs, "density": density, "message": None}


def drought_statistics(drought: np.ndarray, grid: Grid) -> dict:
    valid = drought != NODATA_CLASS
    px_ha = grid.px_area_m2 / 10_000.0
    stats = {"valid_ha": float(valid.sum() * px_ha)}
    for cls in (0, 1, 2, 3):
        stats[f"class{cls}_ha"] = float((drought == cls).sum() * px_ha)
    stats["drought_ha"] = sum(stats[f"class{c}_ha"] for c in (1, 2, 3))
    stats["drought_share_pct"] = 100.0 * stats["drought_ha"] / max(stats["valid_ha"], 1e-9)
    return stats
