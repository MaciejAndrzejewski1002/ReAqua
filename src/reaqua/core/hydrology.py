"""Regional hydrological balance, drought mitigation indices, vegetation and cost estimates.

All vegetation, biodiversity and carbon coefficients are working assumptions; results are
reported as low / base / high scenarios and must not be read as measured effects.
"""

import math

import numpy as np

from . import costs, physics
from .kriging import analytic_field
from .models import NODATA_CLASS, Grid
from .params import crop_price, merge

BIOMASS_PER_NDVI_01 = 3.2
DELTA_TEMP_MAX = 1.5
ECOTONE_FACTOR = 1.8
CARBON_WETLAND = 2.5
CARBON_AGRO = 0.15
LAMBDA_HEAT = 2.5
SCENARIOS = {"low": 0.5, "base": 1.0, "high": 1.5}
MCI_LOW, MCI_MODERATE, MCI_GOOD = 10.0, 25.0, 45.0


def buffer_mask(grid: Grid, reservoirs: list, radius_of) -> np.ndarray:
    """Union of circles (radius_of(reservoir) in metres) as a boolean raster."""
    mask = np.zeros((grid.nrows, grid.ncols), dtype=bool)
    for res in reservoirs:
        radius = radius_of(res)
        row, col = grid.rowcol(res.x, res.y)
        hr = int(np.ceil(radius / grid.px_h))
        hc = int(np.ceil(radius / grid.px_w))
        r0, r1 = max(0, row - hr), min(grid.nrows, row + hr + 1)
        c0, c1 = max(0, col - hc), min(grid.ncols, col + hc + 1)
        if r0 >= r1 or c0 >= c1:
            continue
        xs = grid.gt[0] + (np.arange(c0, c1) + 0.5) * grid.gt[1]
        ys = grid.gt[3] + (np.arange(r0, r1) + 0.5) * grid.gt[5]
        dist = np.hypot(xs[None, :] - res.x, ys[:, None] - res.y)
        mask[r0:r1, c0:c1] |= dist <= radius
    return mask


def delta_ndvi(mean_volume_m3: float, mci: float, factor: float = 1.0) -> float:
    base = 0.06 + 0.04 * math.log10(max(mean_volume_m3, 1000.0) / 10_000.0)
    boost = 0.015 * min(mci / 25.0, 2.0)
    return float(max(0.01, min(0.25, (base + boost) * factor)))


def vegetation_scenarios(n: int, mean_volume_m3: float, moist_ha: float, micro_ha: float, asa_drought_ha: float,
                         mci: float, region_km2: float, crop_price_pln_t: float, crop_fraction: float) -> dict:
    region_ha = max(region_km2 * 100.0, 1.0)
    out = {}
    for name, factor in SCENARIOS.items():
        d = delta_ndvi(mean_volume_m3, mci, factor)
        coverage = min(1.0, moist_ha / region_ha)
        sbi = asa_drought_ha * (d / 0.1) * BIOMASS_PER_NDVI_01
        cbi_t = sbi * crop_fraction
        out[name] = {
            "delta_ndvi": round(d, 3),
            "vii_pct": round(d * coverage * 100.0, 2),
            "sbi_t_yr": round(sbi, 1),
            "cbi_t_yr": round(cbi_t, 1),
            "cbi_pln_yr": round(cbi_t * crop_price_pln_t),
            "mean_temp_reduction_c": round(min(1.0, micro_ha / region_ha) * DELTA_TEMP_MAX * factor, 3),
            "bsi": round(n * ECOTONE_FACTOR * (max(moist_ha, 1.0) / 10.0) ** 0.35, 1),
            "csi_t_co2_yr": round((moist_ha * CARBON_WETLAND + max(0.0, asa_drought_ha - moist_ha) * CARBON_AGRO)
                                  * factor, 1),
        }
    return out


def water_balance(reservoirs: list, p: dict) -> dict:
    """Annual storage / evaporation / seepage balance (no catchment inflow model)."""
    f_inf = physics.soil(p["soil_type"])["infiltration"]
    total_vol = sum(r.volume_m3 for r in reservoirs)
    total_area_m2 = sum(r.area_ha for r in reservoirs) * 10_000.0
    stored = total_vol * p["fill_cycles"]
    evaporation = p["kc_water"] * total_area_m2 * p["et0_mm"] / 1000.0
    seepage = stored * f_inf
    return {
        "stored_m3": round(stored),
        "evaporation_m3": round(evaporation),
        "seepage_m3": round(seepage),
        "net_usable_m3": round(stored - evaporation - seepage),
        "seepage_fraction": f_inf,
    }


def verdict(mci: float, mei: float, n: int, volume_m3: float) -> dict:
    checks = [
        (mci >= MCI_MODERATE, f"MCI = {mci:.1f}% (próg {MCI_MODERATE:.0f}%)"),
        (mei >= 15.0, f"MEI = {mei:.1f}% (próg 15%)"),
        (n >= 10, f"Liczba zbiorników = {n} (próg 10)"),
        (volume_m3 >= 500_000, f"Łączna pojemność = {volume_m3 / 1000:.0f} tys. m³ (próg 500 tys.)"),
    ]
    passed = sum(1 for ok, _ in checks if ok)
    return {
        "passed": passed,
        "total": len(checks),
        "criteria": [{"ok": ok, "text": text} for ok, text in checks],
        "note": "Progi są roboczymi wartościami zespołu, nie normą ani wytyczną.",
    }


def compute_regional(reservoirs: list, grid: Grid, drought: np.ndarray, mitigation: np.ndarray = None,
                     params: dict = None, mitigation_source: str = None) -> dict:
    p = merge(params)
    if not reservoirs:
        raise ValueError("Brak zbiorników.")
    n = len(reservoirs)
    valid = drought != NODATA_CLASS
    in_drought = (drought >= 1) & (drought <= 3)
    px_ha = grid.px_area_m2 / 10_000.0
    valid_ha = float(valid.sum() * px_ha)
    region_km2 = p["region_area_km2"] if p["region_area_km2"] > 0 else valid_ha / 100.0
    drought_ha = float(in_drought.sum() * px_ha)
    severe_ha = float((drought == 3).sum() * px_ha)
    mod_sev_ha = float(((drought >= 2) & (drought <= 3)).sum() * px_ha)

    if mitigation is None:
        mitigation = analytic_field(grid, reservoirs, p)
        mitigation_source = "model analityczny"
    else:
        mitigation_source = mitigation_source or "raster mitygacji"

    moist = buffer_mask(grid, reservoirs, lambda r: r.r_moist_m)
    micro = buffer_mask(grid, reservoirs, lambda r: r.r_micro_m)
    asa = buffer_mask(grid, reservoirs, lambda r: max(r.r_moist_m, 0.5 * r.r_micro_m))
    moist_ha = float(moist.sum() * px_ha)
    micro_ha = float(micro.sum() * px_ha)
    moist_in_drought_ha = float((moist & in_drought).sum() * px_ha)
    asa_drought_ha = float((asa & in_drought).sum() * px_ha)

    mci = min(100.0, moist_in_drought_ha / max(drought_ha, 1e-9) * 100.0) if drought_ha else 0.0
    hsri = (1.0 - math.exp(-LAMBDA_HEAT * mci / 100.0)) * 100.0
    total_area_ha = sum(r.area_ha for r in reservoirs)
    total_volume = sum(r.volume_m3 for r in reservoirs)
    ari = total_area_ha * 10_000.0 / max(region_km2, 1e-9)

    if drought_ha:
        mean_mit = float(mitigation[in_drought].mean())
        coverage = float((mitigation[in_drought] > 0.20).mean() * 100.0)
        cls = drought[in_drought].astype(np.float32)
        dr_before = float(cls.mean())
        dr_after = float((cls * (1.0 - mitigation[in_drought])).mean())
    else:
        mean_mit = coverage = dr_before = dr_after = 0.0
    mei = mean_mit * 100.0
    reduction = (dr_before - dr_after) / dr_before * 100.0 if dr_before > 0 else 0.0

    price = crop_price(p["crop"])
    veg = vegetation_scenarios(n, total_volume / n, moist_ha, micro_ha, asa_drought_ha, mci, region_km2,
                               price, p["crop_fraction"])
    balance = water_balance(reservoirs, p)

    total_cost = {k: sum(getattr(r, f"cost_{k}_pln") for r in reservoirs) for k in ("min", "mid", "max")}
    if total_cost["mid"] == 0:
        total_cost = costs.total_cost([r.area_ha for r in reservoirs], waterproofing=p["waterproofing"],
                                      lining_factor=p["lining_factor"])
    cost_per_ha = total_cost["mid"] / moist_in_drought_ha if moist_in_drought_ha > 0 else None
    savings = None
    if p["drought_aid_pln_ha"] > 0:
        annual = p["drought_aid_pln_ha"] * moist_in_drought_ha * p["drought_freq"]
        savings = {"annual_pln": round(annual),
                   "payback_years": round(total_cost["mid"] / annual, 1) if annual > 0 else None}

    per_reservoir = []
    for r in reservoirs:
        per_reservoir.append({
            "priority": r.priority, "drought_class": r.drought_class, "area_ha": round(r.area_ha, 2),
            "volume_m3": round(r.volume_m3), "r_moist_m": round(r.r_moist_m), "r_micro_m": round(r.r_micro_m),
            "evaporation_m3": round(p["kc_water"] * r.area_ha * 10_000.0 * p["et0_mm"] / 1000.0),
            "cost_mid_pln": round(r.cost_mid_pln), "lon": r.lon, "lat": r.lat,
        })

    return {
        "n_reservoirs": n,
        "region_km2": round(region_km2, 1),
        "total_area_ha": round(total_area_ha, 2),
        "total_volume_m3": round(total_volume),
        "ari": round(ari, 2),
        "retention_mm": round(total_volume / max(region_km2, 1e-9) / 1000.0, 2),
        "drought_ha": round(drought_ha, 1),
        "severe_ha": round(severe_ha, 1),
        "mod_sev_ha": round(mod_sev_ha, 1),
        "moist_ha": round(moist_ha, 1),
        "micro_ha": round(micro_ha, 1),
        "moist_in_drought_ha": round(moist_in_drought_ha, 1),
        "asa_drought_ha": round(asa_drought_ha, 1),
        "mci": round(mci, 1),
        "hsri": round(hsri, 1),
        "mei": round(mei, 1),
        "coverage_pct": round(coverage, 1),
        "dr_before": round(dr_before, 3),
        "dr_after": round(dr_after, 3),
        "dr_reduction_pct": round(reduction, 1),
        "mitigation_source": mitigation_source,
        "balance": balance,
        "vegetation": veg,
        "crop": p["crop"],
        "crop_price_pln_t": price,
        "cost": {k: round(v) for k, v in total_cost.items()},
        "cost_per_ha_pln": round(cost_per_ha) if cost_per_ha else None,
        "savings": savings,
        "per_reservoir": per_reservoir,
        "verdict": verdict(mci, mei, n, total_volume),
        "soil": p["soil_type"],
        "wind_speed_ms": p["wind_speed_ms"],
        "wind_direction": p["wind_direction"],
    }
