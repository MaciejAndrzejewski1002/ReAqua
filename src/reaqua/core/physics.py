"""Shared physical constants and influence-radius model used by every module.

The coefficients are working assumptions of the team (see docs/ANALIZA_MERYTORYCZNA.md);
they are exposed as parameters and are not calibrated against field measurements.
"""

import math

import numpy as np

SOILS = {
    "sand": {"label": "Piasek (wysoka przepuszczalność)", "nugget": 0.30, "range_scale": 0.70, "infiltration": 0.45},
    "loamy_sand": {"label": "Piasek gliniasty", "nugget": 0.22, "range_scale": 0.80, "infiltration": 0.38},
    "sandy_loam": {"label": "Glina piaszczysta", "nugget": 0.18, "range_scale": 0.90, "infiltration": 0.30},
    "loam": {"label": "Glina średnia", "nugget": 0.12, "range_scale": 1.00, "infiltration": 0.22},
    "clay_loam": {"label": "Glina zwięzła", "nugget": 0.08, "range_scale": 1.15, "infiltration": 0.14},
    "clay": {"label": "Glina ciężka (niska przepuszczalność)", "nugget": 0.05, "range_scale": 1.30, "infiltration": 0.08},
}

WIND_FROM_AZIMUTH = {"N": 0, "NE": 45, "E": 90, "SE": 135, "S": 180, "SW": 225, "W": 270, "NW": 315}
WIND_LABELS = {
    "W": "Zachodni (dominujący w Polsce)",
    "SW": "Południowo-zachodni",
    "NW": "Północno-zachodni",
    "N": "Północny",
    "NE": "Północno-wschodni",
    "E": "Wschodni",
    "SE": "Południowo-wschodni",
    "S": "Południowy",
}

K_MOIST_DEFAULT = 80.0
K_MICRO_DEFAULT = 130.0


def downwind_azimuth(direction_from: str) -> float:
    """Meteorological convention (direction wind blows FROM) to azimuth it blows TO."""
    return (WIND_FROM_AZIMUTH.get(direction_from.upper(), 270) + 180) % 360


def soil(key: str) -> dict:
    return SOILS.get(key, SOILS["loam"])


def influence_radii(
    area_ha: float,
    wind_speed_ms: float,
    soil_key: str = "loam",
    k_moist: float = K_MOIST_DEFAULT,
    k_micro: float = K_MICRO_DEFAULT,
) -> dict:
    """Moisture and microclimate influence radii [m] scaling with sqrt(area)."""
    scale = soil(soil_key)["range_scale"]
    wind_factor = 1.0 + 0.4 * min(max(wind_speed_ms, 0.0), 8.0)
    root = math.sqrt(max(area_ha, 0.01))
    return {
        "r_moist_m": k_moist * root * scale,
        "r_micro_m": k_micro * root * scale * wind_factor,
    }


def volume_weight(volume_m3: float) -> float:
    return float(min(1.0, 0.3 + 0.1 * math.log10(max(volume_m3, 100.0))))


def class_factor(drought_class: int) -> float:
    return 1.0 + 0.25 * (max(int(drought_class), 1) - 1)


def aniso_distance(dx, dy, azimuth_deg: float, range_major: float, range_minor: float):
    """Normalised geometric-anisotropy distance; major axis points along azimuth (0 = north, clockwise)."""
    theta = math.radians(azimuth_deg)
    along = dx * math.sin(theta) + dy * math.cos(theta)
    across = -dx * math.cos(theta) + dy * math.sin(theta)
    eps = 1e-9
    return np.sqrt((along / (range_major + eps)) ** 2 + (across / (range_minor + eps)) ** 2)


def gaussian_cov(h, nugget: float = 0.0):
    return (1.0 - nugget) * np.exp(-3.0 * np.square(h))
