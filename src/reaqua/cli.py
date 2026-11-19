"""Command line interface: python -m reaqua {demo,run,serve,submit,worker,export,params}."""

import argparse
import json
import os
import sys

from . import __version__, inbox
from .core import io, params as P, pipeline, synthetic
from .db import geopackage

DEFAULT_DB = os.environ.get("REAQUA_DB", "reaqua.gpkg")
DEFAULT_INBOX = os.environ.get("REAQUA_INBOX", "inbox")
DEFAULT_OUTPUT = os.environ.get("REAQUA_OUTPUT", "output")


def _add_param_overrides(parser: argparse.ArgumentParser):
    parser.add_argument("--set", action="append", default=[], metavar="KLUCZ=WARTOŚĆ",
                        help="nadpisanie parametru, np. --set max_points=30 (lista: python -m reaqua params)")


def _parse_overrides(pairs) -> dict:
    out = {}
    for pair in pairs:
        if "=" not in pair:
            raise SystemExit(f"Niepoprawny parametr: {pair}")
        key, raw = pair.split("=", 1)
        try:
            out[key] = P.coerce(key, raw)
        except ValueError as exc:
            raise SystemExit(str(exc)) from None
    return out


def _print_summary(out: dict):
    stats = out.get("drought_stats", {})
    print(f"Obszar suszy: {stats.get('drought_ha', 0):.1f} ha ({stats.get('drought_share_pct', 0):.1f}% analizowanego obszaru)")
    if out.get("message"):
        print(out["message"])
    res = out.get("result")
    print(f"Zbiorniki: {len(out.get('reservoirs', []))}")
    if res:
        print(f"MCI {res['mci']}%  MEI {res['mei']}%  koszt {res['cost']['min'] / 1e6:.1f}-{res['cost']['max'] / 1e6:.1f} mln zł")
    for name, path in out.get("paths", {}).items():
        print(f"  {name}: {path}")


def cmd_demo(args) -> int:
    if args.if_empty and os.path.exists(args.db):
        conn = geopackage.connect(args.db)
        try:
            has_runs = geopackage.latest_run_id(conn) is not None
        finally:
            conn.close()
        if has_runs:
            print("Baza zawiera już analizy, pomijam generowanie danych demonstracyjnych.")
            return 0
    scene_dir = os.path.join(args.out, "scena")
    paths = synthetic.write_scene(scene_dir, size=args.size)
    overrides = {"max_points": 20, "min_distance_m": 600.0, "n_zones": 6, "region_label": "Scena syntetyczna (demo)"}
    overrides.update(_parse_overrides(args.set))
    out = pipeline.run_pipeline(paths, args.out, overrides, db_path=args.db)
    _print_summary(out)
    return 0


def cmd_run(args) -> int:
    paths = {"red": args.red, "nir": args.nir, "swir": args.swir, "green": args.green, "scl": args.scl,
             "mask": args.mask}
    if args.folder:
        found = io.find_bands(args.folder, args.sensor)
        for key, value in found.items():
            paths.setdefault(key, None)
            paths[key] = paths[key] or value
    steps = tuple(s for s in args.steps.split(",") if s)
    out = pipeline.run_pipeline(paths, args.out, _parse_overrides(args.set), args.sensor, steps, args.db)
    _print_summary(out)
    return 0 if out.get("reservoirs") else 2


def cmd_serve(args) -> int:
    from .web.app import create_app

    create_app(args.db).run(host=args.host, port=args.port)
    return 0


def cmd_submit(args) -> int:
    found = io.find_bands(args.folder, args.sensor)
    try:
        scene_id = inbox.create_scene(args.inbox, found, args.sensor, _parse_overrides(args.set), args.label)
    except ValueError as exc:
        raise SystemExit(str(exc)) from None
    print(f"Dodano scenę do kolejki: {scene_id}")
    return 0


def cmd_worker(args) -> int:
    inbox.watch(args.inbox, args.output, args.db, args.interval, args.once)
    return 0


def cmd_export(args) -> int:
    conn = geopackage.connect(args.db)
    try:
        run_id = args.run or geopackage.latest_run_id(conn)
        if run_id is None:
            raise SystemExit("Baza nie zawiera analiz.")
        rows = geopackage.get_reservoirs(conn, run_id)
    finally:
        conn.close()
    if args.format == "geojson":
        body = json.dumps(geopackage.rows_to_geojson(rows), ensure_ascii=False, indent=2)
    elif args.format == "json":
        body = json.dumps(rows, ensure_ascii=False, indent=2)
    else:
        import csv
        import io as _io

        buf = _io.StringIO()
        if rows:
            writer = csv.DictWriter(buf, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)
        body = buf.getvalue()
    if args.output:
        with open(args.output, "w", encoding="utf-8", newline="") as fh:
            fh.write(body)
    else:
        sys.stdout.write(body)
    return 0


def cmd_params(_args) -> int:
    for p in P.ALL_PARAMS:
        print(f"{p.key:22} {p.kind:7} domyślnie={p.default!s:12} {p.label}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="reaqua", description="ReAqua - lokalizacja małej retencji i mitygacja suszy")
    parser.add_argument("--version", action="version", version=f"reaqua {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    demo = sub.add_parser("demo", help="scena syntetyczna -> pełna analiza -> baza danych")
    demo.add_argument("--out", default="output")
    demo.add_argument("--db", default=DEFAULT_DB)
    demo.add_argument("--size", type=int, default=600)
    demo.add_argument("--if-empty", action="store_true", help="pomiń, jeśli baza zawiera już analizy")
    _add_param_overrides(demo)
    demo.set_defaults(func=cmd_demo)

    run = sub.add_parser("run", help="analiza na własnych pasmach")
    run.add_argument("--folder")
    run.add_argument("--red")
    run.add_argument("--nir")
    run.add_argument("--swir")
    run.add_argument("--green")
    run.add_argument("--scl")
    run.add_argument("--mask")
    run.add_argument("--sensor", choices=("sentinel", "landsat"), default="sentinel")
    run.add_argument("--steps", default="scout,kriging,report")
    run.add_argument("--out", default="output")
    run.add_argument("--db", default=None)
    _add_param_overrides(run)
    run.set_defaults(func=cmd_run)

    serve = sub.add_parser("serve", help="panel WWW i API")
    serve.add_argument("--db", default=DEFAULT_DB)
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8000)
    serve.set_defaults(func=cmd_serve)

    submit = sub.add_parser("submit", help="dodaj scenę (folder z pasmami) do kolejki workera")
    submit.add_argument("--folder", required=True)
    submit.add_argument("--inbox", default=DEFAULT_INBOX)
    submit.add_argument("--sensor", choices=("sentinel", "landsat"), default="sentinel")
    submit.add_argument("--label", default="")
    _add_param_overrides(submit)
    submit.set_defaults(func=cmd_submit)

    worker = sub.add_parser("worker", help="przetwarzaj sceny z kolejki w tle")
    worker.add_argument("--inbox", default=DEFAULT_INBOX)
    worker.add_argument("--output", default=DEFAULT_OUTPUT)
    worker.add_argument("--db", default=DEFAULT_DB)
    worker.add_argument("--interval", type=float, default=5.0)
    worker.add_argument("--once", action="store_true", help="przetwórz oczekujące sceny i zakończ")
    worker.set_defaults(func=cmd_worker)

    export = sub.add_parser("export", help="eksport zbiorników z bazy")
    export.add_argument("--db", default=DEFAULT_DB)
    export.add_argument("--run", type=int)
    export.add_argument("--format", choices=("geojson", "json", "csv"), default="geojson")
    export.add_argument("--output")
    export.set_defaults(func=cmd_export)

    par = sub.add_parser("params", help="lista parametrów")
    par.set_defaults(func=cmd_params)
    return parser


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
