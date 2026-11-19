"""Flask dashboard and REST API over the ReAqua results database."""

import csv
import io
import json
import os

from flask import Flask, Response, abort, jsonify, render_template, request

from .. import __authors__, __version__
from .. import inbox
from ..core import charts
from ..core import params as P
from ..db import geopackage
from .scenes import register_scene_routes

DEFAULT_DB = os.environ.get("REAQUA_DB", "/data/reaqua.gpkg")
DEFAULT_INBOX = os.environ.get("REAQUA_INBOX", "/data/inbox")
DEFAULT_OUTPUT = os.environ.get("REAQUA_OUTPUT", "/data/output")
MAX_UPLOAD_MB = int(os.environ.get("REAQUA_MAX_UPLOAD_MB", "500"))


def _figures(rows: list) -> dict:
    top = rows[:15]
    max_area = max((r["pow_zb_ha"] for r in rows), default=1) or 1
    return {
        "map": charts.point_map([(r["lon"], r["lat"], r["priorytet"], r["pow_zb_ha"] / max_area) for r in rows],
                                "Rozmieszczenie zbiorników"),
        "cost": charts.bar_chart([f"P{r['priorytet']}" for r in top], [r["koszt_sr_pln"] for r in top],
                                 "Koszt średni według priorytetu", "zł"),
        "volume": charts.bar_chart([f"P{r['priorytet']}" for r in top], [r["obj_m3"] for r in top],
                                   "Pojemność według priorytetu", "m³", color=charts.PALETTE["bar2"]),
    }


def _summary(rows: list) -> dict:
    return {
        "n": len(rows),
        "area_ha": sum(r["pow_zb_ha"] for r in rows),
        "volume_m3": sum(r["obj_m3"] for r in rows),
        "cost_min": sum(r["koszt_min_pln"] for r in rows),
        "cost_max": sum(r["koszt_max_pln"] for r in rows),
        "mean_density": sum(r["gestosc"] for r in rows) / max(len(rows), 1),
    }


def _upload_form_options() -> dict:
    return {"wind": P.WIND_CHOICES, "soil": P.SOIL_CHOICES, "crops": tuple((c[0], c[1]) for c in P.CROPS),
            "sensors": P.SENSORS}


def create_app(db_path: str = None, inbox_dir: str = None, output_dir: str = None) -> Flask:
    app = Flask(__name__)
    app.config["DB_PATH"] = db_path or DEFAULT_DB
    app.config["INBOX_DIR"] = inbox_dir or DEFAULT_INBOX
    app.config["OUTPUT_DIR"] = output_dir or DEFAULT_OUTPUT
    app.config["UPLOAD_TOKEN"] = os.environ.get("REAQUA_UPLOAD_TOKEN", "")
    app.config["MAX_CONTENT_LENGTH"] = MAX_UPLOAD_MB * 1024 * 1024

    @app.context_processor
    def inject_footer():
        return {"version": __version__, "authors": __authors__}

    def conn():
        return geopackage.connect(app.config["DB_PATH"])

    def resolve_run(db, run_id):
        run_id = run_id or request.args.get("run_id", type=int) or geopackage.latest_run_id(db)
        if run_id is None:
            abort(404, "Brak zapisanych analiz. Uruchom: python -m reaqua demo")
        return run_id

    @app.get("/health")
    def health():
        return jsonify(status="ok", version=__version__)

    @app.get("/")
    def dashboard():
        db = conn()
        try:
            run_id = request.args.get("run_id", type=int) or geopackage.latest_run_id(db)
            run = geopackage.get_run(db, run_id) if run_id else None
            rows = geopackage.get_reservoirs(db, run_id) if run else []
            runs = geopackage.list_runs(db)
        finally:
            db.close()
        context = {"run": run, "rows": rows, "runs": runs,
                   "scenes": inbox.list_scenes(app.config["INBOX_DIR"])[:8], "form": _upload_form_options(),
                   "token_required": bool(app.config["UPLOAD_TOKEN"]), "max_upload_mb": MAX_UPLOAD_MB}
        if run:
            context.update(figures=_figures(rows), stats=_summary(rows))
        return render_template("index.html", **context)

    @app.get("/api/runs")
    def api_runs():
        db = conn()
        try:
            return jsonify(geopackage.list_runs(db))
        finally:
            db.close()

    @app.get("/api/runs/<int:run_id>")
    def api_run(run_id):
        db = conn()
        try:
            run = geopackage.get_run(db, run_id)
        finally:
            db.close()
        if run is None:
            abort(404)
        return jsonify(run)

    @app.get("/api/stats")
    def api_stats():
        db = conn()
        try:
            run_id = resolve_run(db, None)
            return jsonify(run_id=run_id, metrics=geopackage.get_metrics(db, run_id))
        finally:
            db.close()

    @app.get("/api/reservoirs")
    def api_reservoirs():
        fmt = request.args.get("format", "json").lower()
        min_priority = request.args.get("max_priority", type=int)
        db = conn()
        try:
            run_id = resolve_run(db, None)
            rows = geopackage.get_reservoirs(db, run_id)
        finally:
            db.close()
        if min_priority:
            rows = [r for r in rows if r["priorytet"] <= min_priority]
        if fmt == "geojson":
            body = json.dumps(geopackage.rows_to_geojson(rows), ensure_ascii=False)
            return Response(body, mimetype="application/geo+json",
                            headers={"Content-Disposition": "attachment; filename=zbiorniki.geojson"})
        if fmt == "csv":
            buf = io.StringIO()
            if rows:
                writer = csv.DictWriter(buf, fieldnames=list(rows[0].keys()))
                writer.writeheader()
                writer.writerows(rows)
            return Response(buf.getvalue(), mimetype="text/csv",
                            headers={"Content-Disposition": "attachment; filename=zbiorniki.csv"})
        if fmt != "json":
            abort(400, "format musi mieć wartość: json, geojson lub csv")
        return jsonify(run_id=run_id, count=len(rows), reservoirs=rows)

    register_scene_routes(app)
    return app
