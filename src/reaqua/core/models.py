from dataclasses import dataclass
from typing import Optional

import numpy as np


@dataclass(frozen=True)
class Grid:
    """Georeferenced north-up raster grid (GDAL geotransform + WKT CRS)."""

    gt: tuple
    wkt: str
    nrows: int
    ncols: int

    @property
    def px_w(self) -> float:
        return abs(self.gt[1])

    @property
    def px_h(self) -> float:
        return abs(self.gt[5])

    @property
    def px_area_m2(self) -> float:
        return self.px_w * self.px_h

    @property
    def extent(self) -> tuple:
        xmin = self.gt[0]
        ymax = self.gt[3]
        xmax = xmin + self.ncols * self.gt[1]
        ymin = ymax + self.nrows * self.gt[5]
        return min(xmin, xmax), min(ymin, ymax), max(xmin, xmax), max(ymin, ymax)

    @property
    def area_km2(self) -> float:
        return self.nrows * self.ncols * self.px_area_m2 / 1e6

    def xy(self, row: float, col: float) -> tuple:
        x = self.gt[0] + (col + 0.5) * self.gt[1]
        y = self.gt[3] + (row + 0.5) * self.gt[5]
        return x, y

    def rowcol(self, x: float, y: float) -> tuple:
        col = int(np.floor((x - self.gt[0]) / self.gt[1]))
        row = int(np.floor((y - self.gt[3]) / self.gt[5]))
        return row, col

    def coarsened(self, factor: int) -> "Grid":
        gt = (self.gt[0], self.gt[1] * factor, 0.0, self.gt[3], 0.0, self.gt[5] * factor)
        return Grid(gt, self.wkt, self.nrows // factor, self.ncols // factor)

    def same_as(self, other: "Grid", tol: float = 1e-6) -> bool:
        if (self.nrows, self.ncols) != (other.nrows, other.ncols):
            return False
        return all(abs(a - b) <= tol for a, b in zip(self.gt, other.gt))


@dataclass
class Reservoir:
    """Candidate small-retention reservoir (position in raster CRS)."""

    x: float
    y: float
    priority: int = 1
    drought_class: int = 1
    density: float = 0.0
    drought_area_km2: float = 0.0
    area_ha: float = 2.0
    volume_m3: float = 40_000.0
    zone: int = 0
    lon: Optional[float] = None
    lat: Optional[float] = None
    cost_min_pln: float = 0.0
    cost_mid_pln: float = 0.0
    cost_max_pln: float = 0.0
    r_moist_m: float = 0.0
    r_micro_m: float = 0.0


DROUGHT_LABELS = {
    0: "Brak suszy",
    1: "Lekka susza",
    2: "Umiarkowana susza",
    3: "Silna susza",
}
NODATA_CLASS = 255
