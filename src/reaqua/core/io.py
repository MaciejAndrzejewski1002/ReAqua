"""Raster / CRS helpers with two interchangeable backends.

Inside QGIS the GDAL Python bindings (osgeo) are used; in Docker / CI / CLI the
rasterio + pyproj stack is used. Both expose the same functions.
"""

import os
import re

import numpy as np

from .models import Grid

IMPORT_ERRORS = []

try:
    from osgeo import gdal, osr

    gdal.UseExceptions()
    BACKEND = "gdal"
except ImportError as exc_gdal:
    IMPORT_ERRORS.append(f"osgeo: {exc_gdal}")
    gdal = osr = None
    try:
        import rasterio
        from rasterio.crs import CRS
        from rasterio.transform import Affine
        from rasterio.warp import Resampling, reproject

        BACKEND = "rasterio"
    except ImportError as exc_rasterio:
        IMPORT_ERRORS.append(f"rasterio: {exc_rasterio}")
        BACKEND = None

_BAND_RULES = {
    "sentinel": {"red": ("b04",), "nir": ("b08", "b8a"), "swir": ("b11",), "green": ("b03",), "scl": ("scl",)},
    "landsat": {"red": ("b4",), "nir": ("b5",), "swir": ("b6",), "green": ("b3",), "scl": ("qa_pixel",)},
}
_RASTER_EXT = (".tif", ".tiff", ".img", ".jp2")
_RES_RANK = {"10m": 0, "20m": 1, "60m": 2}


def require_backend():
    if BACKEND is None:
        raise RuntimeError(
            "Brak biblioteki rastrowej: zainstaluj rasterio (poza QGIS) lub użyj Pythona z QGIS. "
            "Szczegóły: " + "; ".join(IMPORT_ERRORS)
        )


def read_raster(path: str) -> tuple:
    """Read band 1 -> (array, nodata, Grid)."""
    require_backend()
    if not os.path.isfile(path):
        raise FileNotFoundError(path)
    if BACKEND == "gdal":
        ds = gdal.Open(path)
        band = ds.GetRasterBand(1)
        arr = band.ReadAsArray()
        nodata = band.GetNoDataValue()
        gt = ds.GetGeoTransform()
        grid = Grid(tuple(gt), ds.GetProjection() or "", ds.RasterYSize, ds.RasterXSize)
        ds = None
    else:
        with rasterio.open(path) as src:
            arr = src.read(1)
            nodata = src.nodata
            gt = src.transform.to_gdal()
            wkt = src.crs.to_wkt() if src.crs else ""
            grid = Grid(tuple(gt), wkt, src.height, src.width)
    if abs(grid.gt[2]) > 1e-12 or abs(grid.gt[4]) > 1e-12:
        raise ValueError(f"Obrócone rastry nie są obsługiwane: {path}")
    return arr, nodata, grid


def read_grid(path: str) -> Grid:
    """Raster header only (no pixel data)."""
    require_backend()
    if BACKEND == "gdal":
        ds = gdal.Open(path)
        grid = Grid(tuple(ds.GetGeoTransform()), ds.GetProjection() or "", ds.RasterYSize, ds.RasterXSize)
        ds = None
        return grid
    with rasterio.open(path) as src:
        return Grid(tuple(src.transform.to_gdal()), src.crs.to_wkt() if src.crs else "", src.height, src.width)


def read_float(path: str) -> tuple:
    """Band 1 as float32 with nodata replaced by NaN -> (array, Grid)."""
    arr, nodata, grid = read_raster(path)
    out = arr.astype(np.float32)
    if nodata is not None:
        out[arr == nodata] = np.nan
    return out, grid


def read_aligned(path: str, ref: Grid, resampling: str = "bilinear") -> np.ndarray:
    """Read a raster resampled onto the reference grid (float32, NaN outside)."""
    require_backend()
    arr, grid = read_float(path)
    if grid.same_as(ref) and grid.wkt == ref.wkt:
        return arr
    if BACKEND == "gdal":
        src = gdal.Open(path)
        dst = gdal.GetDriverByName("MEM").Create("", ref.ncols, ref.nrows, 1, gdal.GDT_Float32)
        dst.SetGeoTransform(ref.gt)
        dst.SetProjection(ref.wkt)
        dst.GetRasterBand(1).SetNoDataValue(float("nan"))
        dst.GetRasterBand(1).Fill(float("nan"))
        method = gdal.GRA_NearestNeighbour if resampling == "nearest" else gdal.GRA_Bilinear
        gdal.ReprojectImage(src, dst, None, None, method)
        out = dst.GetRasterBand(1).ReadAsArray().astype(np.float32)
        src = dst = None
        return out
    dst_arr = np.full((ref.nrows, ref.ncols), np.nan, dtype=np.float32)
    method = Resampling.nearest if resampling == "nearest" else Resampling.bilinear
    with rasterio.open(path) as src:
        reproject(
            source=rasterio.band(src, 1),
            destination=dst_arr,
            dst_transform=Affine.from_gdal(*ref.gt),
            dst_crs=CRS.from_wkt(ref.wkt) if ref.wkt else None,
            resampling=method,
            src_nodata=src.nodata,
            dst_nodata=np.nan,
        )
    return dst_arr


_GDAL_TYPES = {"uint8": "GDT_Byte", "uint16": "GDT_UInt16", "float32": "GDT_Float32"}


def write_raster(path: str, arr: np.ndarray, grid: Grid, nodata=None) -> str:
    require_backend()
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    dtype = str(arr.dtype)
    if dtype not in _GDAL_TYPES:
        raise ValueError(f"Nieobsługiwany typ rastra: {dtype}")
    if BACKEND == "gdal":
        ds = gdal.GetDriverByName("GTiff").Create(
            path, grid.ncols, grid.nrows, 1, getattr(gdal, _GDAL_TYPES[dtype]), ["COMPRESS=LZW"]
        )
        ds.SetGeoTransform(grid.gt)
        if grid.wkt:
            ds.SetProjection(grid.wkt)
        band = ds.GetRasterBand(1)
        if nodata is not None:
            band.SetNoDataValue(float(nodata))
        band.WriteArray(arr)
        band.FlushCache()
        ds = None
    else:
        with rasterio.open(
            path, "w", driver="GTiff", height=grid.nrows, width=grid.ncols, count=1, dtype=dtype,
            crs=CRS.from_wkt(grid.wkt) if grid.wkt else None,
            transform=Affine.from_gdal(*grid.gt), nodata=nodata, compress="lzw",
        ) as dst:
            dst.write(arr, 1)
    return path


def is_projected(wkt: str) -> bool:
    if not wkt:
        return False
    head = wkt.lstrip().upper()
    return head.startswith(("PROJCS", "PROJCRS", "PROJECTEDCRS")) or "PROJCS[" in head or "PROJCRS[" in head


def to_wgs84(xs, ys, wkt: str) -> tuple:
    """Transform coordinates from the CRS given as WKT to lon/lat (EPSG:4326)."""
    xs = np.atleast_1d(np.asarray(xs, dtype=float))
    ys = np.atleast_1d(np.asarray(ys, dtype=float))
    if not wkt:
        raise ValueError("Brak definicji układu współrzędnych (CRS) rastra.")
    if BACKEND == "gdal":
        src = osr.SpatialReference()
        src.ImportFromWkt(wkt)
        dst = osr.SpatialReference()
        dst.ImportFromEPSG(4326)
        for srs in (src, dst):
            if hasattr(srs, "SetAxisMappingStrategy"):
                srs.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
        tr = osr.CoordinateTransformation(src, dst)
        pts = [tr.TransformPoint(float(x), float(y))[:2] for x, y in zip(xs, ys)]
        arr = np.array(pts, dtype=float).reshape(-1, 2)
        return arr[:, 0], arr[:, 1]
    from pyproj import CRS as PCRS
    from pyproj import Transformer

    tr = Transformer.from_crs(PCRS.from_wkt(wkt), "EPSG:4326", always_xy=True)
    lon, lat = tr.transform(xs, ys)
    return np.asarray(lon), np.asarray(lat)


def find_bands(folder: str, sensor: str = "sentinel") -> dict:
    """Search a scene folder recursively; prefer the finest resolution for each role."""
    rules = _BAND_RULES.get(sensor, _BAND_RULES["sentinel"])
    best = {}
    for root, _dirs, files in os.walk(folder):
        for name in files:
            if not name.lower().endswith(_RASTER_EXT):
                continue
            stem = os.path.splitext(name)[0].lower()
            for role, codes in rules.items():
                for code in codes:
                    if re.search(r"(?<![a-z0-9])" + re.escape(code) + r"(?![a-z0-9])", stem):
                        rank = min((r for token, r in _RES_RANK.items() if token in stem), default=3)
                        key = (rank, codes.index(code))
                        if role not in best or key < best[role][0]:
                            best[role] = (key, os.path.join(root, name))
    return {role: item[1] for role, item in best.items()}
