"""Results database: an OGC GeoPackage (SQLite) written with the standard library only.

Tables
  runs       - one row per analysis (attributes table)
  reservoirs - proposed reservoirs, POINT geometry in EPSG:4326 (feature table)
  metrics    - flattened numeric indicators per run (attributes table)
The file opens directly in QGIS and can be queried with plain SQL.
"""

import datetime
import json
import sqlite3
import struct

from ..core import schema

SRS_WGS84 = (
    "WGS 84", 4326, "EPSG", 4326,
    'GEOGCS["WGS 84",DATUM["WGS_1984",SPHEROID["WGS 84",6378137,298.257223563,AUTHORITY["EPSG","7030"]],'
    'AUTHORITY["EPSG","6326"]],PRIMEM["Greenwich",0,AUTHORITY["EPSG","8901"]],'
    'UNIT["degree",0.0174532925199433,AUTHORITY["EPSG","9122"]],AUTHORITY["EPSG","4326"]]',
    "longitude/latitude coordinates in decimal degrees on the WGS 84 spheroid",
)

_DDL = """
CREATE TABLE IF NOT EXISTS gpkg_spatial_ref_sys (
  srs_name TEXT NOT NULL, srs_id INTEGER PRIMARY KEY, organization TEXT NOT NULL,
  organization_coordsys_id INTEGER NOT NULL, definition TEXT NOT NULL, description TEXT);
CREATE TABLE IF NOT EXISTS gpkg_contents (
  table_name TEXT NOT NULL PRIMARY KEY, data_type TEXT NOT NULL, identifier TEXT UNIQUE,
  description TEXT DEFAULT '', last_change DATETIME NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
  min_x DOUBLE, min_y DOUBLE, max_x DOUBLE, max_y DOUBLE, srs_id INTEGER,
  CONSTRAINT fk_gc_r_srs_id FOREIGN KEY (srs_id) REFERENCES gpkg_spatial_ref_sys(srs_id));
CREATE TABLE IF NOT EXISTS gpkg_geometry_columns (
  table_name TEXT NOT NULL, column_name TEXT NOT NULL, geometry_type_name TEXT NOT NULL,
  srs_id INTEGER NOT NULL, z TINYINT NOT NULL, m TINYINT NOT NULL,
  CONSTRAINT pk_geom_cols PRIMARY KEY (table_name, column_name),
  CONSTRAINT uk_gc_table_name UNIQUE (table_name),
  CONSTRAINT fk_gc_tn FOREIGN KEY (table_name) REFERENCES gpkg_contents(table_name),
  CONSTRAINT fk_gc_srs FOREIGN KEY (srs_id) REFERENCES gpkg_spatial_ref_sys (srs_id));
CREATE TABLE IF NOT EXISTS runs (
  id INTEGER PRIMARY KEY AUTOINCREMENT, created_at TEXT NOT NULL, region TEXT, sensor TEXT,
  mitigation_source TEXT, n_reservoirs INTEGER, region_km2 REAL, drought_ha REAL, mci REAL, mei REAL,
  total_volume_m3 REAL, cost_min_pln REAL, cost_max_pln REAL, params_json TEXT, result_json TEXT);
CREATE TABLE IF NOT EXISTS reservoirs (
  fid INTEGER PRIMARY KEY AUTOINCREMENT, geom BLOB, run_id INTEGER NOT NULL,
  priorytet INTEGER, kl_suszy INTEGER, opis TEXT, gestosc REAL, pow_susz_km2 REAL, pow_zb_ha REAL, obj_m3 REAL,
  strefa INTEGER, r_wilg_m REAL, r_mikro_m REAL, koszt_min_pln REAL, koszt_sr_pln REAL, koszt_max_pln REAL,
  lon REAL, lat REAL, x_proj REAL, y_proj REAL);
CREATE TABLE IF NOT EXISTS metrics (
  id INTEGER PRIMARY KEY AUTOINCREMENT, run_id INTEGER NOT NULL, key TEXT NOT NULL, value REAL, unit TEXT);
CREATE INDEX IF NOT EXISTS idx_reservoirs_run ON reservoirs(run_id);
CREATE INDEX IF NOT EXISTS idx_metrics_run ON metrics(run_id);
"""


def connect(path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(path, timeout=30)
    conn.row_factory = sqlite3.Row
    init_db(conn)
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    conn.execute("PRAGMA application_id = 1196444487")
    conn.execute("PRAGMA user_version = 10300")
    conn.executescript(_DDL)
    conn.execute("INSERT OR IGNORE INTO gpkg_spatial_ref_sys VALUES (?,?,?,?,?,?)", SRS_WGS84)
    conn.execute("INSERT OR IGNORE INTO gpkg_spatial_ref_sys VALUES "
                 "('Undefined Cartesian SRS',-1,'NONE',-1,'undefined','undefined Cartesian coordinate reference system')")
    conn.execute("INSERT OR IGNORE INTO gpkg_spatial_ref_sys VALUES "
                 "('Undefined geographic SRS',0,'NONE',0,'undefined','undefined geographic coordinate reference system')")
    for table, kind, srs in (("runs", "attributes", None), ("metrics", "attributes", None),
                             ("reservoirs", "features", 4326)):
        conn.execute("INSERT OR IGNORE INTO gpkg_contents (table_name, data_type, identifier, description, srs_id) "
                     "VALUES (?,?,?,?,?)", (table, kind, table, f"ReAqua: {table}", srs))
    conn.execute("INSERT OR IGNORE INTO gpkg_geometry_columns VALUES ('reservoirs','geom','POINT',4326,0,0)")
    conn.commit()


def point_blob(lon: float, lat: float) -> bytes:
    """GeoPackage binary geometry: 'GP' header (little endian, no envelope, EPSG:4326) + WKB point."""
    return b"GP" + bytes([0, 1]) + struct.pack("<i", 4326) + struct.pack("<BIdd", 1, 1, lon, lat)


def _flatten(result: dict) -> list:
    rows = []
    for key, value in result.items():
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            rows.append((key, float(value), ""))
    for group in ("balance", "cost"):
        for key, value in result.get(group, {}).items():
            if isinstance(value, (int, float)):
                rows.append((f"{group}_{key}", float(value), "PLN" if group == "cost" else ""))
    for key, value in result.get("vegetation", {}).get("base", {}).items():
        rows.append((f"veg_{key}", float(value), ""))
    return rows


def save_run(conn: sqlite3.Connection, reservoirs: list, result: dict, params: dict = None, region: str = "",
             sensor: str = "") -> int:
    now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    cost = result.get("cost", {})
    cur = conn.execute(
        "INSERT INTO runs (created_at, region, sensor, mitigation_source, n_reservoirs, region_km2, drought_ha, mci,"
        " mei, total_volume_m3, cost_min_pln, cost_max_pln, params_json, result_json) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (now, region, sensor, result.get("mitigation_source"), len(reservoirs), result.get("region_km2"),
         result.get("drought_ha"), result.get("mci"), result.get("mei"), result.get("total_volume_m3"),
         cost.get("min"), cost.get("max"), json.dumps(params or {}, ensure_ascii=False, default=str),
         json.dumps(result, ensure_ascii=False, default=str)),
    )
    run_id = cur.lastrowid
    names = [f[0] for f in schema.RESERVOIR_FIELDS]
    sql = (f"INSERT INTO reservoirs (geom, run_id, {', '.join(names)}, lon, lat, x_proj, y_proj) "
           f"VALUES ({', '.join(['?'] * (len(names) + 6))})")
    for res in reservoirs:
        props = schema.to_props(res)
        blob = point_blob(res.lon, res.lat) if res.lon is not None else None
        conn.execute(sql, [blob, run_id] + [props[n] for n in names] + [res.lon, res.lat, res.x, res.y])
    conn.executemany("INSERT INTO metrics (run_id, key, value, unit) VALUES (?,?,?,?)",
                     [(run_id, k, v, u) for k, v, u in _flatten(result)])
    lons = [r.lon for r in reservoirs if r.lon is not None]
    lats = [r.lat for r in reservoirs if r.lat is not None]
    if lons:
        conn.execute("UPDATE gpkg_contents SET min_x=?, min_y=?, max_x=?, max_y=?, "
                     "last_change=strftime('%Y-%m-%dT%H:%M:%fZ','now') WHERE table_name='reservoirs'",
                     (min(lons), min(lats), max(lons), max(lats)))
    conn.commit()
    return run_id


def list_runs(conn: sqlite3.Connection) -> list:
    rows = conn.execute("SELECT id, created_at, region, sensor, mitigation_source, n_reservoirs, region_km2, "
                        "drought_ha, mci, mei, total_volume_m3, cost_min_pln, cost_max_pln FROM runs "
                        "ORDER BY id DESC").fetchall()
    return [dict(r) for r in rows]


def latest_run_id(conn: sqlite3.Connection):
    row = conn.execute("SELECT MAX(id) AS id FROM runs").fetchone()
    return row["id"] if row else None


def get_run(conn: sqlite3.Connection, run_id: int):
    row = conn.execute("SELECT * FROM runs WHERE id = ?", (run_id,)).fetchone()
    if row is None:
        return None
    out = dict(row)
    out["params"] = json.loads(out.pop("params_json") or "{}")
    out["result"] = json.loads(out.pop("result_json") or "{}")
    return out


def get_reservoirs(conn: sqlite3.Connection, run_id: int) -> list:
    rows = conn.execute("SELECT * FROM reservoirs WHERE run_id = ? ORDER BY priorytet", (run_id,)).fetchall()
    out = []
    for row in rows:
        d = dict(row)
        d.pop("geom", None)
        out.append(d)
    return out


def get_metrics(conn: sqlite3.Connection, run_id: int) -> list:
    rows = conn.execute("SELECT key, value, unit FROM metrics WHERE run_id = ? ORDER BY key", (run_id,)).fetchall()
    return [dict(r) for r in rows]


def rows_to_geojson(rows: list) -> dict:
    features = []
    for d in rows:
        if d.get("lon") is None:
            continue
        props = {k: v for k, v in d.items() if k not in ("lon", "lat")}
        features.append({"type": "Feature", "geometry": {"type": "Point", "coordinates": [d["lon"], d["lat"]]},
                         "properties": props})
    return {"type": "FeatureCollection", "features": features}
