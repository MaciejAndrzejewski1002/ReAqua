import math

import numpy as np
import pytest

from reaqua.core import costs, hydrology, report
from reaqua.core.models import Reservoir
from reaqua.core.params import merge


def _reservoirs(grid, n=3):
    out = []
    for i in range(n):
        x, y = grid.xy(60 + 70 * i, 60 + 70 * i)
        r = Reservoir(x=x, y=y, priority=i + 1, drought_class=2, area_ha=2.0, volume_m3=40_000.0,
                      r_moist_m=113.0, r_micro_m=404.0, cost_min_pln=1.29e6, cost_mid_pln=2.145e6, cost_max_pln=3e6)
        out.append(r)
    return out


def test_cost_model_matches_presentation():
    c = costs.reservoir_cost(2.0)
    assert c["min"] == pytest.approx(1_290_000)
    assert c["max"] == pytest.approx(3_000_000)
    assert c["mid"] == pytest.approx((c["min"] + c["max"]) / 2)
    assert costs.reservoir_cost(2.0, waterproofing=False)["max"] == pytest.approx(3_000_000 - 20_000 * 90)
    assert costs.total_cost([1.0, 1.0])["mid"] == pytest.approx(2 * costs.reservoir_cost(1.0)["mid"])


def test_buffer_mask_area_matches_circle(grid):
    res = _reservoirs(grid, 1)
    mask = hydrology.buffer_mask(grid, res, lambda r: 300.0)
    area = mask.sum() * grid.px_area_m2
    assert area == pytest.approx(math.pi * 300**2, rel=0.05)


def test_regional_indices_are_consistent(grid, drought):
    out = hydrology.compute_regional(_reservoirs(grid), grid, drought, None, {})
    assert 0 <= out["mci"] <= 100
    assert out["moist_in_drought_ha"] <= out["drought_ha"]
    assert out["moist_in_drought_ha"] <= out["moist_ha"]
    assert out["dr_after"] <= out["dr_before"]
    assert out["mitigation_source"] == "model analityczny"
    assert out["total_volume_m3"] == 120_000
    low, base, high = (out["vegetation"][k] for k in ("low", "base", "high"))
    assert low["sbi_t_yr"] <= base["sbi_t_yr"] <= high["sbi_t_yr"]
    assert low["cbi_pln_yr"] <= base["cbi_pln_yr"] <= high["cbi_pln_yr"]
    assert out["verdict"]["total"] == len(out["verdict"]["criteria"])


def test_region_area_comes_from_raster_by_default(grid, drought):
    out = hydrology.compute_regional(_reservoirs(grid), grid, drought, None, {})
    valid_km2 = (drought != 255).sum() * grid.px_area_m2 / 1e6
    assert out["region_km2"] == pytest.approx(valid_km2, abs=0.1)
    override = hydrology.compute_regional(_reservoirs(grid), grid, drought, None, {"region_area_km2": 2500.0})
    assert override["region_km2"] == 2500.0


def test_meadow_gives_zero_crop_benefit(grid, drought):
    out = hydrology.compute_regional(_reservoirs(grid), grid, drought, None, {"crop": "meadow"})
    assert out["vegetation"]["base"]["cbi_pln_yr"] == 0
    wheat = hydrology.compute_regional(_reservoirs(grid), grid, drought, None, {"crop": "wheat"})
    assert wheat["vegetation"]["base"]["cbi_pln_yr"] > 0


def test_water_balance_arithmetic():
    res = [Reservoir(x=0, y=0, area_ha=2.0, volume_m3=40_000.0)]
    p = merge({"soil_type": "loam", "fill_cycles": 2.0, "et0_mm": 600.0, "kc_water": 1.0})
    bal = hydrology.water_balance(res, p)
    assert bal["stored_m3"] == 80_000
    assert bal["evaporation_m3"] == round(1.0 * 20_000 * 0.6)
    assert bal["seepage_m3"] == round(80_000 * 0.22)
    assert bal["net_usable_m3"] == bal["stored_m3"] - bal["evaporation_m3"] - bal["seepage_m3"]


def test_savings_only_when_aid_given(grid, drought):
    none = hydrology.compute_regional(_reservoirs(grid), grid, drought, None, {})
    some = hydrology.compute_regional(_reservoirs(grid), grid, drought, None,
                                      {"drought_aid_pln_ha": 1000.0, "drought_freq": 0.5})
    assert none["savings"] is None
    assert some["savings"]["annual_pln"] > 0 and some["savings"]["payback_years"] > 0


def test_empty_reservoirs_rejected(grid, drought):
    with pytest.raises(ValueError):
        hydrology.compute_regional([], grid, drought)


def test_report_is_self_contained_and_escaped(grid, drought):
    out = hydrology.compute_regional(_reservoirs(grid), grid, drought, None, {})
    html = report.generate_html(out, "<script>alert(1)</script>")
    assert "<script>alert(1)</script>" not in html
    assert "&lt;script&gt;" in html
    assert "googleapis" not in html and "http://" not in html.replace("http://www.w3.org", "")
    for section in ("Rozmieszczenie i koszty", "Bilans wodny", "Założenia i ograniczenia", "Koszty"):
        assert section in html
    for author in ("Maciej Andrzejewski", "Weronika Zator", "Kacper Mikołajczyk", "Tomasz Szulski"):
        assert author in html
    assert np.isfinite(out["mei"])
