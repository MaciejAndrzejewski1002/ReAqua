import numpy as np

from reaqua.core import costs, scout
from reaqua.core.models import NODATA_CLASS


def test_allocate_quotas_budget_and_proportion():
    quotas = scout.allocate_quotas({1: 100.0, 2: 300.0, 3: 600.0}, 10)
    assert sum(quotas.values()) == 10
    assert all(v >= 1 for v in quotas.values())
    assert quotas[3] > quotas[2] > quotas[1]


def test_allocate_quotas_more_zones_than_budget():
    quotas = scout.allocate_quotas({i: float(i) for i in range(1, 8)}, 3)
    assert sorted(quotas) == [5, 6, 7]
    assert scout.allocate_quotas({}, 5) == {}


def test_select_points_respects_distance_and_budget():
    rng = np.random.default_rng(2)
    density = rng.random((60, 60)).astype(np.float32)
    qualifying = np.ones_like(density, dtype=bool)
    zone_of = (np.arange(60)[:, None] // 20) * 3 + (np.arange(60)[None, :] // 20)
    weights = {int(z): 1.0 for z in np.unique(zone_of)}
    picks = scout.select_points(density, qualifying, weights, zone_of, 12, 8.0)
    assert len(picks) == 12
    pts = np.array([(r, c) for r, c, _d, _z in picks], dtype=float)
    dist = np.hypot(pts[:, None, 0] - pts[None, :, 0], pts[:, None, 1] - pts[None, :, 1])
    assert dist[np.triu_indices(len(pts), 1)].min() >= 8.0


def test_run_scout_points_follow_drought(drought, grid):
    out = scout.run_scout(drought, grid, {"min_distance_m": 300.0, "max_points": 12, "n_zones": 4})
    res = out["reservoirs"]
    assert 0 < len(res) <= 12
    assert [r.priority for r in res] == list(range(1, len(res) + 1))
    assert [r.density for r in res] == sorted((r.density for r in res), reverse=True)
    for r in res:
        row, col = grid.rowcol(r.x, r.y)
        window = drought[max(0, row - 30):row + 31, max(0, col - 30):col + 31]
        assert ((window >= 1) & (window <= 3)).any()
        assert r.lon is not None and 16 < r.lon < 19


def test_run_scout_costs_match_cost_model(drought, grid):
    res = scout.run_scout(drought, grid, {"reservoir_area_ha": 2.0})["reservoirs"][0]
    cost = costs.reservoir_cost(2.0)
    assert res.cost_min_pln == cost["min"] and res.cost_max_pln == cost["max"]
    assert res.volume_m3 == 2.0 * 10_000 * 2.0


def test_proportional_size_is_clipped(drought, grid):
    res = scout.run_scout(drought, grid, {"size_mode": "proportional", "area_min_ha": 1.0, "area_max_ha": 3.0})["reservoirs"]
    assert all(1.0 <= r.area_ha <= 3.0 for r in res)


def test_no_drought_gives_message(grid):
    empty = np.zeros((grid.nrows, grid.ncols), dtype=np.uint8)
    out = scout.run_scout(empty, grid)
    assert out["reservoirs"] == [] and out["message"]


def test_drought_statistics(grid):
    arr = np.zeros((grid.nrows, grid.ncols), dtype=np.uint8)
    arr[:10] = 2
    arr[10:20] = NODATA_CLASS
    stats = scout.drought_statistics(arr, grid)
    px_ha = grid.px_area_m2 / 10_000
    assert abs(stats["class2_ha"] - 10 * grid.ncols * px_ha) < 1e-6
    assert abs(stats["valid_ha"] - 290 * grid.ncols * px_ha) < 1e-6


def test_mask_removes_town_and_lake(scene_paths, grid):
    from reaqua.core import pipeline
    from reaqua.core.params import merge

    p = merge({})
    with_mask, _ = pipeline.load_scene(scene_paths, "sentinel", p)
    without = {k: v for k, v in with_mask.items() if k != "mask"}
    masked = scout.build_drought_map(with_mask, grid, p)
    unmasked = scout.build_drought_map(without, grid, p)
    assert (masked == NODATA_CLASS).sum() > (unmasked == NODATA_CLASS).sum()
