"""Scene upload and job-status routes: the web side of the inbox queue."""

import hmac
import os

from flask import Flask, abort, jsonify, redirect, render_template, request, send_from_directory, url_for

from .. import inbox
from ..core import params as P
from ..core.pipeline import OUTPUT_NAMES

DOWNLOADABLE = {name for key, name in OUTPUT_NAMES.items() if key != "db"}
REPORT_CSP = "default-src 'none'; style-src 'unsafe-inline'; img-src data:"


def _check_token(app: Flask) -> None:
    expected = app.config["UPLOAD_TOKEN"]
    if not expected:
        return
    given = request.headers.get("X-Token") or request.form.get("token", "")
    if not hmac.compare_digest(given.encode(), expected.encode()):
        abort(403, "Brak poprawnego tokenu przesyłania")


def _parse_upload() -> dict:
    sources = {role: request.files[role] for role in inbox.ROLES if role in request.files and request.files[role].filename}
    overrides = {key[len("param_"):]: P.coerce(key[len("param_"):], value)
                 for key, value in request.form.items() if key.startswith("param_") and value != ""}
    return {"sources": sources, "sensor": request.form.get("sensor", "sentinel"),
            "label": request.form.get("label", "").strip()[:120], "params": overrides}


def _queue_upload(app: Flask) -> str:
    _check_token(app)
    return inbox.create_scene(app.config["INBOX_DIR"], **_parse_upload())


def register_scene_routes(app: Flask) -> None:
    def status_or_404(scene_id: str) -> dict:
        try:
            status = inbox.read_status(app.config["INBOX_DIR"], scene_id)
        except ValueError:
            status = None
        if status is None:
            abort(404, "Nie znaleziono sceny")
        return status

    @app.post("/api/scenes")
    def api_upload():
        try:
            scene_id = _queue_upload(app)
        except ValueError as exc:
            return jsonify(error=str(exc)), 400
        return jsonify(id=scene_id, status_url=url_for("api_scene", scene_id=scene_id)), 202

    @app.get("/api/scenes")
    def api_scenes():
        return jsonify(inbox.list_scenes(app.config["INBOX_DIR"]))

    @app.get("/api/scenes/<scene_id>")
    def api_scene(scene_id):
        return jsonify(status_or_404(scene_id))

    @app.post("/upload")
    def upload():
        try:
            scene_id = _queue_upload(app)
        except ValueError as exc:
            return render_template("scene.html", status=None, error=str(exc)), 400
        return redirect(url_for("scene_page", scene_id=scene_id), code=303)

    @app.get("/scenes/<scene_id>")
    def scene_page(scene_id):
        return render_template("scene.html", status=status_or_404(scene_id), error=None)

    @app.get("/scenes/<scene_id>/files/<name>")
    def scene_file(scene_id, name):
        status_or_404(scene_id)
        if name not in DOWNLOADABLE:
            abort(404)
        response = send_from_directory(os.path.join(app.config["OUTPUT_DIR"], scene_id), name)
        if name.endswith(".html"):
            response.headers["Content-Security-Policy"] = REPORT_CSP
        return response
