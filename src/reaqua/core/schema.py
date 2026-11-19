"""Attribute schema of reservoir layers, GeoPackage tables, GeoJSON and CSV exports."""

import csv
import io as _io
import json

from .models import DROUGHT_LABELS, Reservoir

RESERVOIR_FIELDS = (
    ("priorytet", "int", "priority"),
    ("kl_suszy", "int", "drought_class"),
    ("opis", "str", None),
    ("gestosc", "float", "density"),
    ("pow_susz_km2", "float", "drought_area_km2"),
    ("pow_zb_ha", "float", "area_ha"),
    ("obj_m3", "float", "volume_m3"),
    ("strefa", "int", "zone"),
    ("r_wilg_m", "float", "r_moist_m"),
    ("r_mikro_m", "float", "r_micro_m"),
    ("koszt_min_pln", "float", "cost_min_pln"),
    ("koszt_sr_pln", "float", "cost_mid_pln"),
    ("koszt_max_pln", "float", "cost_max_pln"),
)

DEFAULT_DEPTH_M = 2.0
DEFAULT_AREA_HA = 2.0


def to_props(res: Reservoir) -> dict:
    props = {}
    for name, _kind, attr in RESERVOIR_FIELDS:
        if attr is None:
            props[name] = DROUGHT_LABELS.get(res.drought_class, "")
        else:
            value = getattr(res, attr)
            props[name] = round(value, 4) if isinstance(value, float) else value
    return props


def _num(props: dict, names, default):
    for name in names:
        value = props.get(name)
        if value not in (None, "", "NULL"):
            try:
                return float(value)
            except (TypeError, ValueError):
                continue
    return default


def from_props(props: dict, x: float, y: float, depth_m: float = DEFAULT_DEPTH_M,
               area_ha: float = DEFAULT_AREA_HA) -> Reservoir:
    """Build a Reservoir from layer attributes; supports the legacy v2 names (priority, kl_suszy...)."""
    area = _num(props, ("pow_zb_ha", "area_ha"), area_ha)
    volume = _num(props, ("obj_m3", "volume_m3", "vol_m3"), 0.0)
    if volume <= 0:
        volume = area * 10_000.0 * depth_m
    return Reservoir(
        x=x, y=y,
        priority=int(_num(props, ("priorytet", "priority"), 1)),
        drought_class=int(_num(props, ("kl_suszy", "drought_cls"), 1)),
        density=_num(props, ("gestosc",), 0.5),
        drought_area_km2=_num(props, ("pow_susz_km2", "pow_km2"), 0.0),
        area_ha=area, volume_m3=volume, zone=int(_num(props, ("strefa",), 0)),
        r_moist_m=_num(props, ("r_wilg_m",), 0.0), r_micro_m=_num(props, ("r_mikro_m",), 0.0),
        cost_min_pln=_num(props, ("koszt_min_pln",), 0.0), cost_mid_pln=_num(props, ("koszt_sr_pln",), 0.0),
        cost_max_pln=_num(props, ("koszt_max_pln",), 0.0),
    )


def to_geojson(reservoirs: list, run_id: int = None) -> dict:
    features = []
    for res in reservoirs:
        if res.lon is None or res.lat is None:
            raise ValueError("Brak współrzędnych geograficznych zbiornika (lon/lat).")
        props = to_props(res)
        props.update({"x_proj": res.x, "y_proj": res.y})
        if run_id is not None:
            props["run_id"] = run_id
        features.append({"type": "Feature", "geometry": {"type": "Point", "coordinates": [res.lon, res.lat]},
                         "properties": props})
    return {"type": "FeatureCollection", "features": features}


def to_json_records(reservoirs: list) -> list:
    out = []
    for res in reservoirs:
        row = to_props(res)
        row.update({"lon": res.lon, "lat": res.lat, "x_proj": res.x, "y_proj": res.y})
        out.append(row)
    return out


def to_csv(reservoirs: list) -> str:
    rows = to_json_records(reservoirs)
    if not rows:
        return ""
    buf = _io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=list(rows[0].keys()))
    writer.writeheader()
    writer.writerows(rows)
    return buf.getvalue()


def write_geojson(path: str, reservoirs: list, run_id: int = None) -> str:
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(to_geojson(reservoirs, run_id), fh, ensure_ascii=False, indent=2)
    return path


def write_csv(path: str, reservoirs: list) -> str:
    with open(path, "w", encoding="utf-8", newline="") as fh:
        fh.write(to_csv(reservoirs))
    return path
