import numpy as np

from reaqua.core import spectral
from reaqua.core.models import NODATA_CLASS
from reaqua.core.params import THRESHOLD_PRESETS, merge


def test_ndbi_is_negative_ndmi():
    rng = np.random.default_rng(0)
    nir = rng.uniform(0.05, 0.6, (50, 50)).astype(np.float32)
    swir = rng.uniform(0.05, 0.6, (50, 50)).astype(np.float32)
    assert np.allclose(spectral.ndbi(nir, swir), -spectral.ndmi(nir, swir), atol=1e-6)


def test_reflectance_sentinel_with_offset():
    dn = np.full((10, 10), 3000.0, dtype=np.float32)
    assert np.allclose(spectral.to_reflectance(dn, "sentinel", True), 0.2)
    assert np.allclose(spectral.to_reflectance(dn, "sentinel", False), 0.3)


def test_reflectance_landsat_and_passthrough():
    dn = np.full((10, 10), 20_000.0, dtype=np.float32)
    assert np.allclose(spectral.to_reflectance(dn, "landsat"), 20_000 * 2.75e-5 - 0.2, atol=1e-6)
    refl = np.full((10, 10), 0.3, dtype=np.float32)
    assert spectral.to_reflectance(refl, "sentinel") is refl


def _params(**kw):
    return merge({**THRESHOLD_PRESETS["cassini"]["values"], **kw})


def test_classes_with_presentation_thresholds():
    p = _params()
    ndvi = np.array([[0.6, 0.4, 0.2, 0.1, 0.1]], dtype=np.float32)
    ndmi = np.array([[0.3, 0.1, 0.0, -0.3, 0.0]], dtype=np.float32)
    out = spectral.classify(ndvi, ndmi, p)
    assert out.tolist() == [[0, 1, 2, 3, 0]]


def test_ndbi_filter_makes_severe_class_impossible():
    p = _params(use_ndbi_filter=True)
    rng = np.random.default_rng(1)
    nir = rng.uniform(0.1, 0.5, (200, 200)).astype(np.float32)
    swir = rng.uniform(0.1, 0.7, (200, 200)).astype(np.float32)
    red = rng.uniform(0.02, 0.3, (200, 200)).astype(np.float32)
    ndvi, ndmi, ndbi = spectral.ndvi(red, nir), spectral.ndmi(nir, swir), spectral.ndbi(nir, swir)
    with_filter = spectral.classify(ndvi, ndmi, p, None, ndbi)
    without = spectral.classify(ndvi, ndmi, _params(use_ndbi_filter=False), None, ndbi)
    assert (with_filter == 3).sum() == 0
    assert (without == 3).sum() > 0


def test_masks_and_nan_become_nodata():
    p = _params()
    ndvi = np.array([[0.1, 0.1, np.nan]], dtype=np.float32)
    ndmi = np.array([[-0.3, -0.3, 0.0]], dtype=np.float32)
    out = spectral.classify(ndvi, ndmi, p, exclude=np.array([[False, True, False]]))
    assert out.tolist() == [[3, NODATA_CLASS, NODATA_CLASS]]


def test_water_and_cloud_masks():
    green = np.array([[0.10, 0.05]], dtype=np.float32)
    swir = np.array([[0.02, 0.30]], dtype=np.float32)
    water = spectral.water_mask(green=green, swir=swir, threshold=0.05)
    assert water.tolist() == [[True, False]]
    scl = np.array([[4, 9, 6]], dtype=np.float32)
    assert spectral.invalid_mask(scl).tolist() == [[False, True, False]]
    assert spectral.water_mask(scl=scl).tolist() == [[False, False, True]]
