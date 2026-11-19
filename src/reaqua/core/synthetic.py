"""Synthetic Sentinel-2-like scene used by the demo, the sample data and the tests."""

import os

import numpy as np
from scipy.ndimage import gaussian_filter

from . import io
from .models import Grid


def epsg_wkt(epsg: int) -> str:
    if io.BACKEND == "gdal":
        srs = io.osr.SpatialReference()
        srs.ImportFromEPSG(epsg)
        return srs.ExportToWkt()
    from pyproj import CRS

    return CRS.from_epsg(epsg).to_wkt()


def _blob(shape, cx, cy, sx, sy):
    yy, xx = np.mgrid[0:shape[0], 0:shape[1]]
    return np.exp(-(((xx - cx) / sx) ** 2 + ((yy - cy) / sy) ** 2))


def make_arrays(size: int = 600, seed: int = 1) -> dict:
    """Return reflectance arrays (green, red, nir, swir) and the arable-land mask."""
    rng = np.random.default_rng(seed)
    shape = (size, size)
    noise = gaussian_filter(rng.normal(size=shape), 6)
    noise = noise / (np.abs(noise).max() + 1e-9)
    stress = np.zeros(shape)
    for cx, cy, sx, sy, amp in ((0.25, 0.30, 0.10, 0.14, 1.0), (0.70, 0.25, 0.12, 0.08, 0.75),
                                (0.55, 0.72, 0.16, 0.11, 0.95), (0.20, 0.80, 0.07, 0.07, 0.55)):
        stress += amp * _blob(shape, cx * size, cy * size, sx * size, sy * size)
    stress = np.clip(stress + 0.08 * noise, 0.0, 1.0)

    ndvi_t = np.clip(0.65 - 0.55 * stress + 0.03 * noise, -0.2, 0.9)
    ndmi_t = np.clip(0.25 - 0.55 * stress + 0.02 * noise, -0.5, 0.6)
    nir = np.full(shape, 0.40) + 0.02 * noise
    red = nir * (1 - ndvi_t) / (1 + ndvi_t)
    swir = nir * (1 - ndmi_t) / (1 + ndmi_t)
    green = 0.08 + 0.01 * noise

    arable = np.ones(shape, dtype=np.uint8)
    yy, xx = np.mgrid[0:size, 0:size]
    town = (np.abs(xx - 0.85 * size) < 0.07 * size) & (np.abs(yy - 0.55 * size) < 0.06 * size)
    red[town], nir[town], swir[town], green[town] = 0.22, 0.26, 0.34, 0.18
    arable[town] = 0
    lake = np.hypot(xx - 0.45 * size, yy - 0.50 * size) < 0.04 * size
    red[lake], nir[lake], swir[lake], green[lake] = 0.04, 0.02, 0.01, 0.06
    arable[lake] = 0
    return {"green": green, "red": red, "nir": nir, "swir": swir, "arable": arable}


def to_dn(refl: np.ndarray) -> np.ndarray:
    return np.clip(refl * 10_000.0 + 1000.0, 0, 65535).astype(np.uint16)


def write_scene(out_dir: str, size: int = 600, px: float = 10.0, seed: int = 1, epsg: int = 32633,
                origin: tuple = (620_000.0, 5_810_000.0)) -> dict:
    os.makedirs(out_dir, exist_ok=True)
    arrays = make_arrays(size, seed)
    grid = Grid((origin[0], px, 0.0, origin[1], 0.0, -px), epsg_wkt(epsg), size, size)
    paths = {}
    for role, code in (("green", "B03"), ("red", "B04"), ("nir", "B08"), ("swir", "B11")):
        paths[role] = io.write_raster(os.path.join(out_dir, f"T33UXU_20260421T100031_{code}_10m.tif"),
                                      to_dn(arrays[role]), grid, nodata=0)
    paths["mask"] = io.write_raster(os.path.join(out_dir, "arable_mask.tif"), arrays["arable"], grid, nodata=255)
    return paths
