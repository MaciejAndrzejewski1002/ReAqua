import json
import os

import pytest

from reaqua import cli, inbox
from reaqua.core import params as P
from reaqua.db import geopackage
from reaqua.web.app import create_app

BAND_ROLES = ("red", "nir", "swir", "green", "scl", "mask")


@pytest.fixture()
def dirs(tmp_path):
    return {"inbox": str(tmp_path / "inbox"), "out": str(tmp_path / "out"), "db": str(tmp_path / "r.gpkg")}


@pytest.fixture()
def client(dirs):
    app = create_app(dirs["db"], dirs["inbox"], dirs["out"])
    return app.test_client()


def _sources(scene_paths):
    return {role: scene_paths[role] for role in BAND_ROLES if scene_paths.get(role)}


def _upload_files(scene_paths, roles=None):
    return {role: (open(path, "rb"), f"{role}.tif") for role, path in _sources(scene_paths).items()
            if roles is None or role in roles}


def test_params_coerce_validates_type_range_and_choice():
    assert P.coerce("max_points", "12") == 12
    assert P.coerce("wind_speed_ms", "4.5") == 4.5
    assert P.coerce("waterproofing", "on") is True
    assert P.coerce("soil_type", "clay") == "clay"
    for key, raw in (("nieistnieje", "1"), ("max_points", "abc"), ("max_points", "100000"), ("soil_type", "kamien")):
        with pytest.raises(ValueError):
            P.coerce(key, raw)


def test_create_scene_validation(dirs, scene_paths, tmp_path):
    with pytest.raises(ValueError, match="Brak wymaganych"):
        inbox.create_scene(dirs["inbox"], {"red": scene_paths["red"]})
    with pytest.raises(ValueError, match="Czujnik"):
        inbox.create_scene(dirs["inbox"], _sources(scene_paths), sensor="modis")
    fake = tmp_path / "fake.tif"
    fake.write_text("to nie jest raster")
    bad = dict(_sources(scene_paths), nir=str(fake))
    with pytest.raises(ValueError, match="GeoTIFF"):
        inbox.create_scene(dirs["inbox"], bad)
    assert inbox.list_scenes(dirs["inbox"]) == []
    assert not [d for d in os.listdir(dirs["inbox"])]


def test_scene_id_rejects_path_traversal(dirs):
    for value in ("../etc", "..", "abc", "20261102T195209-zzzzzz"):
        with pytest.raises(ValueError):
            inbox.scene_dir(dirs["inbox"], value)


def test_worker_processes_scene_into_database(dirs, scene_paths):
    scene_id = inbox.create_scene(dirs["inbox"], _sources(scene_paths), "sentinel",
                                  {"max_points": 8, "min_distance_m": 400.0, "n_zones": 5}, "Obszar testowy")
    assert inbox.read_status(dirs["inbox"], scene_id)["state"] == inbox.QUEUED
    results = inbox.process_pending(dirs["inbox"], dirs["out"], dirs["db"])
    status = results[0]
    assert status["state"] == inbox.DONE and status["run_id"] == 1 and 0 < status["n_reservoirs"] <= 8
    assert "raport_regionalny.html" in status["files"] and "susza.tif" in status["files"]
    assert inbox.process_pending(dirs["inbox"], dirs["out"], dirs["db"]) == []
    conn = geopackage.connect(dirs["db"])
    try:
        assert geopackage.get_run(conn, 1)["region"] == "Obszar testowy"
    finally:
        conn.close()


def test_worker_reports_error_for_unreadable_raster(dirs, scene_paths, tmp_path):
    broken = tmp_path / "broken.tif"
    broken.write_bytes(b"II*\x00" + b"\x00" * 64)
    sources = dict(_sources(scene_paths), red=str(broken))
    scene_id = inbox.create_scene(dirs["inbox"], sources)
    status = inbox.process_scene(dirs["inbox"], dirs["out"], scene_id, dirs["db"])
    assert status["state"] == inbox.ERROR and status["message"]


def test_recover_requeues_interrupted_scene(dirs, scene_paths):
    scene_id = inbox.create_scene(dirs["inbox"], _sources(scene_paths))
    inbox.write_status(dirs["inbox"], scene_id, state=inbox.RUNNING)
    os.mkdir(os.path.join(inbox.scene_dir(dirs["inbox"], scene_id), ".lock"))
    assert inbox.recover(dirs["inbox"]) == 1
    assert inbox.read_status(dirs["inbox"], scene_id)["state"] == inbox.QUEUED


def test_locked_scene_is_not_processed_twice(dirs, scene_paths):
    scene_id = inbox.create_scene(dirs["inbox"], _sources(scene_paths))
    os.mkdir(os.path.join(inbox.scene_dir(dirs["inbox"], scene_id), ".lock"))
    status = inbox.process_scene(dirs["inbox"], dirs["out"], scene_id, dirs["db"])
    assert status["state"] == inbox.QUEUED


def test_web_upload_worker_and_download(client, dirs, scene_paths):
    data = _upload_files(scene_paths)
    data.update({"label": "Gmina <test>", "sensor": "sentinel", "param_max_points": "6", "param_min_distance_m": "400"})
    response = client.post("/api/scenes", data=data, content_type="multipart/form-data")
    assert response.status_code == 202
    scene_id = response.json["id"]
    assert client.get(response.json["status_url"]).json["state"] == "queued"
    assert client.get("/api/scenes").json[0]["id"] == scene_id
    assert b"queued" in client.get(f"/scenes/{scene_id}").data
    inbox.process_pending(dirs["inbox"], dirs["out"], dirs["db"])
    status = client.get(f"/api/scenes/{scene_id}").json
    assert status["state"] == "done" and status["n_reservoirs"] <= 6
    page = client.get(f"/scenes/{scene_id}")
    body = page.data.decode()
    assert "Panel wyników tej analizy" in body and "Gmina &lt;test&gt;" in body
    raster = client.get(f"/scenes/{scene_id}/files/susza.tif")
    assert raster.status_code == 200 and raster.data[:4] in inbox.TIFF_MAGIC
    report = client.get(f"/scenes/{scene_id}/files/raport_regionalny.html")
    assert "default-src 'none'" in report.headers["Content-Security-Policy"]
    assert client.get(f"/?run_id={status['run_id']}").status_code == 200
    assert scene_id.encode() in client.get("/").data


def test_web_upload_rejections(client, scene_paths):
    missing = ("red", "nir")
    assert client.post("/api/scenes", data=_upload_files(scene_paths, missing),
                       content_type="multipart/form-data").status_code == 400
    fake = _upload_files(scene_paths)
    import io as _io
    fake["swir"] = (_io.BytesIO(b"nie raster"), "swir.tif")
    assert client.post("/api/scenes", data=fake, content_type="multipart/form-data").status_code == 400
    bad_param = _upload_files(scene_paths)
    bad_param["param_max_points"] = "-5"
    answer = client.post("/api/scenes", data=bad_param, content_type="multipart/form-data")
    assert answer.status_code == 400 and "max_points" in answer.json["error"]
    html = client.post("/upload", data=_upload_files(scene_paths, missing), content_type="multipart/form-data")
    assert html.status_code == 400 and "Nie przyjęto" in html.data.decode()
    assert client.get("/api/scenes").json == []


def test_web_routes_block_traversal_and_unknown_files(client, dirs, scene_paths):
    assert client.get("/api/scenes/nieistnieje").status_code == 404
    assert client.get("/scenes/20261102T195209-abcdef").status_code == 404
    scene_id = inbox.create_scene(dirs["inbox"], _sources(scene_paths))
    inbox.process_pending(dirs["inbox"], dirs["out"], dirs["db"])
    for name in ("reaqua.gpkg", "request.json", "..%2F..%2Fetc%2Fpasswd"):
        assert client.get(f"/scenes/{scene_id}/files/{name}").status_code == 404


def test_upload_token_is_enforced(dirs, scene_paths, monkeypatch):
    monkeypatch.setenv("REAQUA_UPLOAD_TOKEN", "sekret")
    client = create_app(dirs["db"], dirs["inbox"], dirs["out"]).test_client()
    assert client.post("/api/scenes", data=_upload_files(scene_paths), content_type="multipart/form-data").status_code == 403
    data = _upload_files(scene_paths)
    data["token"] = "zly"
    assert client.post("/api/scenes", data=data, content_type="multipart/form-data").status_code == 403
    ok = _upload_files(scene_paths)
    ok["token"] = "sekret"
    assert client.post("/api/scenes", data=ok, content_type="multipart/form-data").status_code == 202
    header = client.post("/api/scenes", data=_upload_files(scene_paths), headers={"X-Token": "sekret"},
                         content_type="multipart/form-data")
    assert header.status_code == 202


def test_cli_submit_and_worker_once(dirs, capsys):
    folder = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "sample")
    assert cli.main(["submit", "--folder", folder, "--inbox", dirs["inbox"], "--label", "CLI",
                     "--set", "max_points=5"]) == 0
    assert cli.main(["worker", "--inbox", dirs["inbox"], "--output", dirs["out"], "--db", dirs["db"], "--once"]) == 0
    out = capsys.readouterr().out
    assert "done" in out
    scene = inbox.list_scenes(dirs["inbox"])[0]
    assert scene["state"] == "done" and scene["label"] == "CLI"
    with open(os.path.join(dirs["out"], scene["id"], "metryki.json"), encoding="utf-8") as fh:
        assert json.load(fh)["n_reservoirs"] <= 5


def test_cli_submit_requires_bands(dirs, tmp_path):
    with pytest.raises(SystemExit):
        cli.main(["submit", "--folder", str(tmp_path), "--inbox", dirs["inbox"]])


def test_demo_if_empty_does_not_duplicate_runs(dirs, capsys):
    args = ["demo", "--out", dirs["out"], "--db", dirs["db"], "--size", "300", "--if-empty"]
    assert cli.main(args) == 0
    assert cli.main(args) == 0
    assert "pomijam" in capsys.readouterr().out
    conn = geopackage.connect(dirs["db"])
    try:
        assert len(geopackage.list_runs(conn)) == 1
    finally:
        conn.close()
