"""Single source of truth for every user-adjustable parameter (GUI, CLI and docs)."""

from dataclasses import dataclass
from typing import Any, Tuple

from .physics import SOILS, WIND_LABELS


@dataclass(frozen=True)
class Param:
    key: str
    label: str
    kind: str
    default: Any
    minimum: float = 0.0
    maximum: float = 1e9
    step: float = 1.0
    decimals: int = 2
    suffix: str = ""
    choices: Tuple = ()
    help: str = ""


THRESHOLD_PRESETS = {
    "cassini": {
        "label": "CASSINI Hackathon (progi z prezentacji)",
        "values": {"ndvi_l": 0.50, "ndvi_m": 0.30, "ndvi_s": 0.15, "ndmi": -0.20},
    },
    "conservative": {
        "label": "Konserwatywny (domyślne z Scout v2.1)",
        "values": {"ndvi_l": 0.35, "ndvi_m": 0.20, "ndvi_s": 0.05, "ndmi": 0.00},
    },
}

SENSORS = (("sentinel", "Sentinel-2 L2A"), ("landsat", "Landsat 8/9 C2 L2"))
SIZE_MODES = (("fixed", "Stała powierzchnia"), ("proportional", "Proporcjonalna do suszy w otoczeniu"))
KRIGING_TYPES = (("ordinary", "Kriging zwyczajny (OK)"), ("simple", "Kriging prosty (SK, średnia = 0)"))
COMBINE_MODES = (
    ("max", "Maksimum (model analityczny, kriging)"),
    ("mean", "Średnia (model analityczny, kriging)"),
    ("kriging", "Tylko kriging"),
    ("analytic", "Tylko model analityczny"),
)
CROPS = (
    ("wheat", "Pszenica", 800.0),
    ("corn", "Kukurydza", 750.0),
    ("rapeseed", "Rzepak", 1800.0),
    ("potato", "Ziemniaki", 600.0),
    ("meadow", "Łąka / trwałe użytki (bez korzyści produkcyjnej)", 0.0),
)

SOIL_CHOICES = tuple((k, v["label"]) for k, v in SOILS.items())
WIND_CHOICES = tuple(WIND_LABELS.items())

SCOUT_DROUGHT = (
    Param("ndvi_l", "NDVI – lekka susza (≤)", "float", 0.50, -1, 1, 0.01, 3),
    Param("ndvi_m", "NDVI – umiarkowana susza (≤)", "float", 0.30, -1, 1, 0.01, 3),
    Param("ndvi_s", "NDVI – silna susza (≤)", "float", 0.15, -1, 1, 0.01, 3),
    Param("ndmi", "NDMI – silna susza (<)", "float", -0.20, -1, 1, 0.01, 3,
          help="Silna susza wymaga NDVI ≤ próg oraz NDMI poniżej tego progu."),
    Param("s2_offset", "Offset radiometryczny Sentinel-2 (baseline ≥ 04.00)", "bool", True,
          help="Odejmuje 1000 DN przed skalowaniem; wyłącz dla scen sprzed 25.01.2022."),
    Param("use_ndbi_filter", "Filtr zabudowy NDBI", "bool", False,
          help="NDBI = −NDMI dla pasm NIR/SWIR, więc włączenie filtra wyklucza silną suszę przy progach z prezentacji."),
    Param("ndbi", "NDBI – próg zabudowy (≤)", "float", 0.20, -1, 1, 0.01, 3),
    Param("mndwi", "MNDWI – próg wody (>)", "float", 0.05, -1, 1, 0.01, 3,
          help="Stosowany tylko, gdy dostępne jest pasmo zielone (B03 / B3)."),
)

SCOUT_ALGORITHM = (
    Param("n_zones", "Liczba stref (Z×Z)", "int", 8, 2, 40),
    Param("sigma_m", "Sigma rozmycia gęstości", "float", 500.0, 50, 10_000, 50, 0, " m"),
    Param("analysis_cell_m", "Komórka analizy", "float", 50.0, 10, 500, 10, 0, " m",
          help="Rozdzielczość, na której liczona jest gęstość i wybór punktów."),
    Param("min_class", "Minimalna klasa suszy", "int", 1, 1, 3),
    Param("min_density", "Minimalny próg gęstości [0–1]", "float", 0.02, 0.001, 1.0, 0.005, 3),
    Param("min_distance_m", "Minimalna odległość między punktami", "float", 1000.0, 100, 50_000, 100, 0, " m"),
    Param("max_points", "Maksymalna liczba punktów", "int", 20, 1, 500),
    Param("window_radius_m", "Promień okna oceny suszy", "float", 500.0, 100, 5_000, 50, 0, " m"),
)

RESERVOIR_PARAMS = (
    Param("size_mode", "Tryb powierzchni zbiornika", "choice", "fixed", choices=SIZE_MODES),
    Param("reservoir_area_ha", "Powierzchnia zbiornika (tryb stały)", "float", 2.0, 0.1, 100, 0.5, 2, " ha"),
    Param("area_fraction", "Udział suszy w oknie (tryb proporcjonalny)", "float", 0.15, 0.01, 1.0, 0.01, 2),
    Param("area_min_ha", "Minimalna powierzchnia", "float", 0.5, 0.1, 100, 0.5, 2, " ha"),
    Param("area_max_ha", "Maksymalna powierzchnia", "float", 5.0, 0.1, 500, 0.5, 2, " ha"),
    Param("depth_m", "Średnia głębokość", "float", 2.0, 0.3, 10, 0.1, 1, " m"),
    Param("waterproofing", "Uwzględnij uszczelnienie niecki w kosztach", "bool", True),
    Param("lining_factor", "Powierzchnia uszczelnienia / powierzchnia lustra", "float", 1.0, 0.5, 3.0, 0.05, 2),
)

KRIGING_PARAMS = (
    Param("wind_direction", "Kierunek wiatru (skąd wieje)", "choice", "W", choices=WIND_CHOICES),
    Param("wind_speed_ms", "Prędkość wiatru", "float", 3.0, 0, 30, 0.5, 1, " m/s"),
    Param("soil_type", "Typ gleby", "choice", "loam", choices=SOIL_CHOICES),
    Param("kriging_type", "Typ krigingu", "choice", "simple", choices=KRIGING_TYPES,
          help="SK (średnia 0) gaśnie z odległością od zbiornika; OK wraca do średniej oszacowanej z danych."),
    Param("combine", "Łączenie powierzchni wpływu", "choice", "max", choices=COMBINE_MODES),
    Param("n_stations", "Liczba stacji tła (wartość 0)", "int", 40, 0, 2000),
    Param("seed", "Ziarno losowania stacji", "int", 42, 0, 1_000_000),
    Param("max_grid", "Maks. rozmiar siatki krigingu", "int", 200, 20, 1000),
    Param("k_moist", "Współczynnik promienia wilgoci", "float", 80.0, 10, 500, 5, 1, " m/√ha"),
    Param("k_micro", "Współczynnik promienia mikroklimatu", "float", 130.0, 10, 800, 5, 1, " m/√ha"),
)

REPORT_PARAMS = (
    Param("region_label", "Nazwa regionu", "text", "Obszar badań"),
    Param("region_area_km2", "Powierzchnia regionu (0 = z rastra)", "float", 0.0, 0, 1e6, 10, 1, " km²"),
    Param("crop", "Uprawa dominująca", "choice", "wheat", choices=tuple((c[0], c[1]) for c in CROPS)),
    Param("crop_fraction", "Udział areału z uprawą dominującą", "float", 0.6, 0.0, 1.0, 0.05, 2),
    Param("et0_mm", "Parowanie referencyjne ET0", "float", 600.0, 100, 1500, 10, 0, " mm/rok"),
    Param("kc_water", "Współczynnik parowania wody otwartej", "float", 1.05, 0.5, 1.5, 0.05, 2),
    Param("fill_cycles", "Liczba napełnień zbiorników w roku", "float", 1.0, 0.1, 10, 0.5, 1),
    Param("drought_aid_pln_ha", "Pomoc suszowa (0 = pomiń)", "float", 0.0, 0, 20_000, 100, 0, " PLN/ha"),
    Param("drought_freq", "Częstość lat suszowych", "float", 0.3, 0.0, 1.0, 0.05, 2),
)

ALL_PARAMS = (
    SCOUT_DROUGHT + SCOUT_ALGORITHM + RESERVOIR_PARAMS + KRIGING_PARAMS + REPORT_PARAMS
)


def defaults(*groups) -> dict:
    out = {}
    for group in groups or (ALL_PARAMS,):
        for p in group:
            out[p.key] = p.default
    return out


def crop_price(crop_key: str) -> float:
    for key, _label, price in CROPS:
        if key == crop_key:
            return price
    return 800.0


def coerce(key: str, raw: Any) -> Any:
    """Convert a text value to the type declared for parameter ``key``; ValueError for unknown or invalid input."""
    spec = next((p for p in ALL_PARAMS if p.key == key), None)
    if spec is None:
        raise ValueError(f"Nieznany parametr: {key}")
    try:
        if spec.kind == "int":
            value = int(raw)
        elif spec.kind == "float":
            value = float(raw)
        elif spec.kind == "bool":
            return str(raw).lower() in ("1", "true", "yes", "tak", "on")
        else:
            value = str(raw)
    except ValueError:
        raise ValueError(f"Niepoprawna wartość parametru {key}: {raw!r}") from None
    if spec.kind in ("int", "float") and not spec.minimum <= value <= spec.maximum:
        raise ValueError(f"Parametr {key} poza zakresem {spec.minimum}-{spec.maximum}: {value}")
    if spec.choices and value not in {c[0] for c in spec.choices}:
        raise ValueError(f"Parametr {key}: niedozwolona wartość {value!r}")
    return value


def merge(overrides: dict = None) -> dict:
    """Defaults for every module updated with user overrides (unknown keys are kept)."""
    out = defaults()
    out.update(overrides or {})
    return out
