import numpy as np
import pytest

from reaqua.core import pipeline, scout, synthetic
from reaqua.core.models import Grid
from reaqua.core.params import merge


@pytest.fixture(scope="session")
def utm_wkt():
    return synthetic.epsg_wkt(32633)


@pytest.fixture(scope="session")
def scene_paths(tmp_path_factory):
    return synthetic.write_scene(str(tmp_path_factory.mktemp("scene")), size=300, seed=3)


@pytest.fixture(scope="session")
def grid(utm_wkt):
    return Grid((620_000.0, 10.0, 0.0, 5_810_000.0, 0.0, -10.0), utm_wkt, 300, 300)


@pytest.fixture(scope="session")
def drought(grid):
    arrays = synthetic.make_arrays(300, seed=3)
    params = merge({"s2_offset": True})
    bands = {k: synthetic.to_dn(arrays[k]).astype(np.float32) for k in ("red", "nir", "swir", "green")}
    bands["mask"] = arrays["arable"].astype(np.float32)
    return scout.build_drought_map(bands, grid, params)


@pytest.fixture(scope="session")
def pipeline_out(scene_paths, tmp_path_factory):
    out = tmp_path_factory.mktemp("out")
    result = pipeline.run_pipeline(scene_paths, str(out), {"min_distance_m": 400.0, "max_points": 15, "n_zones": 5})
    result["out_dir"] = str(out)
    return result
