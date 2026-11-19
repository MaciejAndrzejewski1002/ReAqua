"""File-based job queue shared by the web panel and the background worker.

Each scene is a directory ``<inbox>/<scene_id>/`` holding the uploaded bands, ``request.json`` and
``status.json``. Keeping the queue on the shared volume lets the web container accept uploads while
the worker container does the heavy computation.
"""

import json
import os
import re
import shutil
import time
import uuid
from datetime import datetime, timezone

from .core import pipeline
from .core.params import merge

ROLES = ("red", "nir", "swir", "green", "scl", "mask")
REQUIRED_ROLES = ("red", "nir", "swir")
SCENE_ID = re.compile(r"^\d{8}T\d{6}-[0-9a-f]{6}$")
TIFF_MAGIC = (b"II*\x00", b"MM\x00*", b"II+\x00", b"MM\x00+")
QUEUED, RUNNING, DONE, ERROR = "queued", "running", "done", "error"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _write_json(path: str, data: dict) -> None:
    tmp = f"{path}.{uuid.uuid4().hex[:6]}.tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


def _read_json(path: str) -> dict:
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def scene_dir(inbox: str, scene_id: str) -> str:
    if not SCENE_ID.match(scene_id):
        raise ValueError("Niepoprawny identyfikator sceny")
    return os.path.join(inbox, scene_id)


def looks_like_tiff(path: str) -> bool:
    with open(path, "rb") as fh:
        return fh.read(4) in TIFF_MAGIC


def write_status(inbox: str, scene_id: str, **fields) -> dict:
    path = os.path.join(scene_dir(inbox, scene_id), "status.json")
    status = _read_json(path) if os.path.exists(path) else {"id": scene_id}
    status.update(fields)
    _write_json(path, status)
    return status


def read_status(inbox: str, scene_id: str):
    path = os.path.join(scene_dir(inbox, scene_id), "status.json")
    return _read_json(path) if os.path.exists(path) else None


def list_scenes(inbox: str) -> list:
    if not os.path.isdir(inbox):
        return []
    scenes = []
    for name in sorted(os.listdir(inbox), reverse=True):
        if SCENE_ID.match(name):
            status = read_status(inbox, name)
            if status:
                scenes.append(status)
    return scenes


def create_scene(inbox: str, sources: dict, sensor: str = "sentinel", params: dict = None, label: str = "") -> str:
    """Store the bands (file paths or uploaded files with ``save``) and queue the scene; returns its id."""
    missing = [r for r in REQUIRED_ROLES if not sources.get(r)]
    if missing:
        raise ValueError(f"Brak wymaganych pasm: {', '.join(missing)}")
    if sensor not in ("sentinel", "landsat"):
        raise ValueError("Czujnik musi mieć wartość sentinel lub landsat")
    scene_id = f"{datetime.now(timezone.utc):%Y%m%dT%H%M%S}-{uuid.uuid4().hex[:6]}"
    target = scene_dir(inbox, scene_id)
    os.makedirs(target)
    try:
        for role in ROLES:
            source = sources.get(role)
            if not source:
                continue
            dest = os.path.join(target, f"{role}.tif")
            if hasattr(source, "save"):
                source.save(dest)
            else:
                shutil.copyfile(source, dest)
            if not looks_like_tiff(dest):
                raise ValueError(f"Plik dla pasma {role} nie jest rastrem GeoTIFF")
        request = {"sensor": sensor, "params": params or {}, "label": label}
        _write_json(os.path.join(target, "request.json"), request)
        write_status(inbox, scene_id, state=QUEUED, label=label, sensor=sensor, created_at=_now(),
                     message="Oczekuje na przetworzenie")
    except Exception:
        shutil.rmtree(target, ignore_errors=True)
        raise
    return scene_id


def recover(inbox: str) -> int:
    """Re-queue scenes left in the running state by a crashed worker."""
    count = 0
    for status in list_scenes(inbox):
        if status.get("state") == RUNNING:
            lock = os.path.join(scene_dir(inbox, status["id"]), ".lock")
            shutil.rmtree(lock, ignore_errors=True)
            write_status(inbox, status["id"], state=QUEUED, message="Wznowiono po restarcie workera")
            count += 1
    return count


def process_scene(inbox: str, output: str, scene_id: str, db_path: str) -> dict:
    target = scene_dir(inbox, scene_id)
    try:
        os.mkdir(os.path.join(target, ".lock"))
    except FileExistsError:
        return read_status(inbox, scene_id)
    write_status(inbox, scene_id, state=RUNNING, started_at=_now(), message="Trwa analiza")
    try:
        request = _read_json(os.path.join(target, "request.json"))
        params = merge(request.get("params"))
        if request.get("label"):
            params["region_label"] = request["label"]
        paths = {role: os.path.join(target, f"{role}.tif") for role in ROLES
                 if os.path.exists(os.path.join(target, f"{role}.tif"))}
        out_dir = os.path.join(output, scene_id)
        result = pipeline.run_pipeline(paths, out_dir, params, request["sensor"], db_path=db_path)
        run_id = result["paths"].get("run_id")
        message = result.get("message") or ("Analiza zakończona" if run_id else "Nie znaleziono lokalizacji zbiorników")
        files = sorted(os.path.basename(p) for p in result["paths"].values() if isinstance(p, str) and os.path.dirname(p) == out_dir)
        return write_status(inbox, scene_id, state=DONE, finished_at=_now(), run_id=run_id,
                            n_reservoirs=len(result.get("reservoirs", [])), message=message, files=files)
    except Exception as exc:
        return write_status(inbox, scene_id, state=ERROR, finished_at=_now(), message=str(exc))
    finally:
        shutil.rmtree(os.path.join(target, ".lock"), ignore_errors=True)


def process_pending(inbox: str, output: str, db_path: str) -> list:
    """Process every queued scene, oldest first; returns the resulting statuses."""
    results = []
    for status in reversed(list_scenes(inbox)):
        if status.get("state") == QUEUED:
            results.append(process_scene(inbox, output, status["id"], db_path))
    return results


def watch(inbox: str, output: str, db_path: str, interval: float = 5.0, once: bool = False, log=print) -> None:
    os.makedirs(inbox, exist_ok=True)
    os.makedirs(output, exist_ok=True)
    recovered = recover(inbox)
    if recovered:
        log(f"Wznowiono scen: {recovered}")
    while True:
        for status in process_pending(inbox, output, db_path):
            log(f"{status['id']}: {status['state']} - {status['message']}")
        if once:
            return
        time.sleep(interval)
