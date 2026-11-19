"""Reservoir cost model based on the unit-cost ranges from the CASSINI presentation."""

COST_RANGES = {
    "earthworks_pln_m2": (15.0, 30.0),
    "waterproofing_pln_m2": (40.0, 90.0),
    "hydraulic_pln": (150_000.0, 500_000.0),
    "documentation_pln": (40_000.0, 100_000.0),
}


def reservoir_cost(area_ha: float, waterproofing: bool = True, lining_factor: float = 1.0, ranges: dict = None) -> dict:
    """Return min / mid / max cost [PLN] and the itemised breakdown for one reservoir."""
    ranges = ranges or COST_RANGES
    area_m2 = area_ha * 10_000.0
    lined_m2 = area_m2 * lining_factor if waterproofing else 0.0
    items = {}
    for idx, label in enumerate(("min", "max")):
        items[label] = {
            "roboty_ziemne": area_m2 * ranges["earthworks_pln_m2"][idx],
            "uszczelnienie": lined_m2 * ranges["waterproofing_pln_m2"][idx],
            "budowle_hydrotechniczne": ranges["hydraulic_pln"][idx],
            "dokumentacja": ranges["documentation_pln"][idx],
        }
    low = sum(items["min"].values())
    high = sum(items["max"].values())
    return {"min": low, "mid": (low + high) / 2.0, "max": high, "items": items}


def total_cost(areas_ha, **kwargs) -> dict:
    parts = [reservoir_cost(a, **kwargs) for a in areas_ha]
    return {k: sum(p[k] for p in parts) for k in ("min", "mid", "max")}
