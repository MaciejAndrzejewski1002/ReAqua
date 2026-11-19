"""Reflectance scaling, spectral indices, masks and drought classification."""

import numpy as np

from .models import NODATA_CLASS

SCL_INVALID = (0, 1, 3, 8, 9, 10, 11)
SCL_WATER = 6


def to_reflectance(arr: np.ndarray, sensor: str = "sentinel", s2_offset: bool = True) -> np.ndarray:
    """Convert digital numbers to surface reflectance [0-1]; arrays already in 0-1 are kept."""
    sample = arr[::max(1, arr.shape[0] // 400), ::max(1, arr.shape[1] // 400)]
    valid = sample[np.isfinite(sample)]
    if valid.size == 0 or np.percentile(valid, 95) <= 2.0:
        return arr
    if sensor == "landsat":
        out = arr * 2.75e-5 - 0.2
    else:
        out = (arr - (1000.0 if s2_offset else 0.0)) / 10_000.0
    return np.clip(out, 0.0, 1.5).astype(np.float32)


def _normalized_difference(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    with np.errstate(invalid="ignore", divide="ignore"):
        denom = a + b
        return np.where(np.abs(denom) > 1e-6, (a - b) / denom, np.nan).astype(np.float32)


def ndvi(red, nir):
    return _normalized_difference(nir, red)


def ndmi(nir, swir):
    return _normalized_difference(nir, swir)


def ndbi(nir, swir):
    return _normalized_difference(swir, nir)


def mndwi(green, swir):
    return _normalized_difference(green, swir)


def invalid_mask(scl: np.ndarray = None, sensor: str = "sentinel") -> np.ndarray:
    """Cloud / shadow / snow / saturated pixels from the Sentinel-2 scene classification layer."""
    if scl is None or sensor != "sentinel":
        return None
    codes = np.nan_to_num(scl, nan=0).astype(np.uint8)
    return np.isin(codes, SCL_INVALID)


def water_mask(green=None, swir=None, scl=None, threshold: float = 0.05, sensor: str = "sentinel") -> np.ndarray:
    mask = None
    if green is not None and swir is not None:
        with np.errstate(invalid="ignore"):
            mask = mndwi(green, swir) > threshold
    if scl is not None and sensor == "sentinel":
        scl_water = np.nan_to_num(scl, nan=0).astype(np.uint8) == SCL_WATER
        mask = scl_water if mask is None else (mask | scl_water)
    return mask


def classify(ndvi_arr, ndmi_arr, p: dict, exclude: np.ndarray = None, ndbi_arr=None) -> np.ndarray:
    """Drought classes: 0 none, 1 light, 2 moderate, 3 severe, 255 invalid / masked.

    Severe drought requires NDVI <= ndvi_s together with NDMI < ndmi.
    The optional NDBI filter is disabled by default because NDBI == -NDMI for NIR/SWIR bands.
    """
    out = np.zeros(ndvi_arr.shape, dtype=np.uint8)
    keep = np.ones(ndvi_arr.shape, dtype=bool)
    if p.get("use_ndbi_filter") and ndbi_arr is not None:
        keep &= ndbi_arr <= p["ndbi"]
    out[keep & (ndvi_arr <= p["ndvi_l"]) & (ndvi_arr > p["ndvi_m"])] = 1
    out[keep & (ndvi_arr <= p["ndvi_m"]) & (ndvi_arr > p["ndvi_s"])] = 2
    out[keep & (ndvi_arr <= p["ndvi_s"]) & (ndmi_arr < p["ndmi"])] = 3
    bad = np.isnan(ndvi_arr) | np.isnan(ndmi_arr)
    if exclude is not None:
        bad |= exclude
    out[bad] = NODATA_CLASS
    return out
