import json
import os
import sqlite3

import pytest

from reaqua import cli
from reaqua.core import io, pipeline, schema
from reaqua.db import geopackage
from reaqua.web.app import create_app


def test_pipeline_outputs(pipeline_out):
    paths = pipeline_out["paths"]
    for key in ("drought", "mitigation", "kriging", "residual", "report", "metrics", "geojson", "csv", "db"):
        assert os.path.exists(paths[key]), key
    assert len(pipeline_out["reservoirs"]) > 0
    assert pipeline_out["result"]["n_reservoirs"] == len(pipeline_out["reservoirs"])


def test_outputs_keep_crs_and_geometry(pipeline_out):
    grid = pipeline_out["grid"]
    for key in ("drought", "mitigation", "residual"):
        arr, _nodata, g = io.read_raster(pipeline_out["paths"][key])
        assert g.same_as(grid) and io.is_projected(g.wkt)
        assert arr.shape == (grid.nrows, grid.ncols)


def test_geojson_schema(pipeline_out):
    with open(pipeline_out["paths"]["geojson"], encoding="utf-8") as fh:
        data = json.load(fh)
    assert data["type"] == "FeatureCollection"
    props = data["features"][0]["properties"]
    for name, _kind, _attr in schema.RESERVOIR_FIELDS:
        assert name in props
    assert {"x_proj", "y_proj"} <= set(props)


def test_scout_only_still_saves_to_database(scene_paths, tmp_path):
    out = pipeline.run_pipeline(scene_paths, str(tmp_path), {"min_distance_m": 400.0, "n_zones": 5}, steps=("scout",))
    assert out["paths"]["run_id"] == 1 and os.path.exists(out["paths"]["db"])
    assert "result" not in out


def test_geopackage_structure(pipeline_out):
    conn = sqlite3.connect(pipeline_out["paths"]["db"])
    assert conn.execute("PRAGMA application_id").fetchone()[0] == 0x47504B47
    tables = {r[0] for r in conn.execute("SELECT table_name FROM gpkg_contents")}
    assert tables == {"runs", "metrics", "reservoirs"}
    blob = conn.execute("SELECT geom FROM reservoirs LIMIT 1").fetchone()[0]
    assert blob[:2] == b"GP" and len(blob) == 8 + 21
    conn.close()


def test_geopackage_readable_by_gdal(pipeline_out):
    pyogrio = pytest.importorskip("pyogrio")
    info = pyogrio.read_info(pipeline_out["paths"]["db"], layer="reservoirs")
    assert info["features"] == len(pipeline_out["reservoirs"])
    assert "4326" in info["crs"]


def test_database_roundtrip(pipeline_out):
    conn = geopackage.connect(pipeline_out["paths"]["db"])
    run_id = geopackage.latest_run_id(conn)
    rows = geopackage.get_reservoirs(conn, run_id)
    run = geopackage.get_run(conn, run_id)
    metrics = {m["key"] for m in geopackage.get_metrics(conn, run_id)}
    conn.close()
    assert len(rows) == len(pipeline_out["reservoirs"])
    assert rows[0]["priorytet"] == 1 and rows[0]["lon"] is not None
    assert run["result"]["n_reservoirs"] == len(rows)
    assert {"mci", "mei", "veg_cbi_pln_yr", "cost_min"} <= metrics


@pytest.fixture()
def client(pipeline_out):
    return create_app(pipeline_out["paths"]["db"]).test_client()


def test_web_endpoints(client):
    assert client.get("/health").json["status"] == "ok"
    page = client.get("/")
    assert page.status_code == 200 and b"Tomasz Szulski" in page.data and b"<svg" in page.data
    assert client.get("/api/runs").json[0]["id"] >= 1
    assert client.get("/api/stats").json["metrics"]
    data = client.get("/api/reservoirs").json
    assert data["count"] == len(data["reservoirs"]) > 0
    limited = client.get("/api/reservoirs?max_priority=2").json
    assert limited["count"] == 2


def test_web_downloads_and_errors(client):
    geo = client.get("/api/reservoirs?format=geojson")
    assert geo.mimetype == "application/geo+json" and json.loads(geo.data)["features"]
    csv_resp = client.get("/api/reservoirs?format=csv")
    assert csv_resp.data.decode().startswith("fid,run_id,priorytet")
    assert client.get("/api/reservoirs?format=xml").status_code == 400
    assert client.get("/api/runs/9999").status_code == 404


def test_empty_database_shows_upload_form(tmp_path):
    empty = create_app(str(tmp_path / "empty.gpkg"), str(tmp_path / "inbox"), str(tmp_path / "out")).test_client()
    page = empty.get("/")
    assert page.status_code == 200 and b"Baza nie zawiera" in page.data and b'action="/upload"' in page.data
    assert empty.get("/api/reservoirs").status_code == 404


def test_cli_demo_and_export(tmp_path, capsys):
    db = str(tmp_path / "demo.gpkg")
    assert cli.main(["demo", "--out", str(tmp_path / "o"), "--db", db, "--size", "300", "--set", "max_points=8"]) == 0
    capsys.readouterr()
    assert cli.main(["export", "--db", db, "--format", "json"]) == 0
    rows = json.loads(capsys.readouterr().out)
    assert 0 < len(rows) <= 8


def test_cli_rejects_unknown_parameter(tmp_path):
    with pytest.raises(SystemExit):
        cli.main(["demo", "--out", str(tmp_path), "--set", "nieistnieje=1"])
