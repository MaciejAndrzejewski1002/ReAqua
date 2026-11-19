import numpy as np
import pytest

from reaqua.core import kriging, physics
from reaqua.core.models import Grid, Reservoir
from reaqua.core.params import merge

GEOGRAPHIC_WKT = 'GEOGCS["WGS 84",DATUM["WGS_1984",SPHEROID["WGS 84",6378137,298.257223563]],PRIMEM["Greenwich",0],UNIT["degree",0.0174532925199433]]'


def _res(grid, col, row, area=2.0, cls=2):
    x, y = grid.xy(row, col)
    r = Reservoir(x=x, y=y, area_ha=area, volume_m3=area * 20_000, drought_class=cls)
    radii = physics.influence_radii(area, 3.0)
    r.r_moist_m, r.r_micro_m = radii["r_moist_m"], radii["r_micro_m"]
    return r


def test_analytic_field_peak_decay_and_downwind(grid):
    p = merge({"wind_direction": "W", "wind_speed_ms": 4.0})
    res = _res(grid, 150, 150)
    field = kriging.analytic_field(grid, [res], p)
    radii = physics.influence_radii(res.area_ha, 4.0)
    peak = kriging._weight(res) * (1 - physics.soil("loam")["nugget"])
    assert abs(field[150, 150] - peak) < 0.02
    assert field.max() <= 1.0 and field.min() >= 0.0
    step = int(0.5 * radii["r_micro_m"] / 10)
    east, north = field[150, 150 + step], field[150 - step, 150]
    assert east > north
    far = int(3 * radii["r_micro_m"] / 10)
    assert field[150, min(299, 150 + far)] < 0.01


def test_wind_direction_flips_plume(grid):
    res = _res(grid, 150, 150)
    west = kriging.analytic_field(grid, [res], merge({"wind_direction": "W", "wind_speed_ms": 6.0}))
    east = kriging.analytic_field(grid, [res], merge({"wind_direction": "E", "wind_speed_ms": 6.0}))
    step = 20
    assert west[150, 150 + step] > 0 and abs(west[150, 150 + step] - east[150, 150 + step]) < 1e-6
    north = kriging.analytic_field(grid, [res], merge({"wind_direction": "N", "wind_speed_ms": 6.0}))
    assert north[150 - step, 150] > north[150, 150 + step]


def test_krige_interpolates_observations():
    xy = np.array([[0.0, 0.0], [500.0, 0.0], [0.0, 500.0], [800.0, 800.0]])
    val = np.array([1.0, 0.5, 0.2, 0.0])
    for kind in ("ordinary", "simple"):
        pred = kriging.krige(xy, val, xy[:, 0], xy[:, 1], 90.0, 600.0, 400.0, 0.01, kind)
        assert np.allclose(pred, val, atol=0.08), kind


def test_simple_kriging_decays_ordinary_reverts_to_mean():
    xy = np.array([[0.0, 0.0], [5000.0, 5000.0]])
    val = np.array([1.0, 0.6])
    far_x, far_y = np.array([2500.0]), np.array([-4000.0])
    sk = kriging.krige(xy, val, far_x, far_y, 90.0, 400.0, 200.0, 0.1, "simple")
    ok = kriging.krige(xy, val, far_x, far_y, 90.0, 400.0, 200.0, 0.1, "ordinary")
    assert sk[0] < 0.01
    assert ok[0] > 0.5


def test_run_kriging_outputs(grid, drought):
    reservoirs = [_res(grid, 80, 80, cls=3), _res(grid, 200, 220, cls=2)]
    out = kriging.run_kriging(grid, drought, reservoirs, {"combine": "max"})
    shape = (grid.nrows, grid.ncols)
    for key in ("analytic", "kriging", "mitigation", "residual"):
        assert out[key].shape == shape
    assert out["mitigation"].min() >= 0 and out["mitigation"].max() <= 1
    assert np.all(out["mitigation"] >= out["analytic"] - 1e-6)
    assert np.all(out["mitigation"] >= out["kriging"] - 1e-6)
    valid = out["residual"] != -9999.0
    assert out["residual"][valid].max() <= 1.0
    assert 0 <= out["stats"]["coverage_pct"] <= 100


def test_combine_modes(grid, drought):
    reservoirs = [_res(grid, 80, 80)]
    a = kriging.run_kriging(grid, drought, reservoirs, {"combine": "analytic"})
    k = kriging.run_kriging(grid, drought, reservoirs, {"combine": "kriging"})
    m = kriging.run_kriging(grid, drought, reservoirs, {"combine": "mean"})
    assert np.allclose(a["mitigation"], a["analytic"])
    assert np.allclose(k["mitigation"], k["kriging"])
    assert np.allclose(m["mitigation"], (m["analytic"] + m["kriging"]) / 2, atol=1e-6)


def test_geographic_crs_is_rejected(drought):
    geo = Grid((17.0, 0.0001, 0.0, 52.0, 0.0, -0.0001), GEOGRAPHIC_WKT, 300, 300)
    with pytest.raises(ValueError, match="metrach"):
        kriging.run_kriging(geo, drought, [Reservoir(x=17.01, y=51.99)])


def test_no_reservoirs_rejected(grid, drought):
    with pytest.raises(ValueError):
        kriging.run_kriging(grid, drought, [])


def test_background_stations_outside_reach(grid):
    res = [_res(grid, 150, 150)]
    p = merge({"n_stations": 100, "seed": 5})
    stations = kriging.background_stations(grid, res, p, (400.0, 110.0))
    az = physics.downwind_azimuth(p["wind_direction"])
    h = physics.aniso_distance(stations[:, 0] - res[0].x, stations[:, 1] - res[0].y, az, 400.0, 110.0)
    assert len(stations) > 0 and h.min() >= 1.3


def test_seed_changes_stations_and_is_reproducible(grid):
    res = [_res(grid, 150, 150)]
    a = kriging.background_stations(grid, res, merge({"seed": 1}), (400.0, 110.0))
    b = kriging.background_stations(grid, res, merge({"seed": 1}), (400.0, 110.0))
    c = kriging.background_stations(grid, res, merge({"seed": 2}), (400.0, 110.0))
    assert np.array_equal(a, b) and not np.array_equal(a, c)
