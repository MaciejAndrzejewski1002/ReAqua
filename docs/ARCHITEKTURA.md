# Architektura

```
QGIS (gui/)  ──┐
CLI (cli.py) ──┼──> core/pipeline.py ──> core/{spectral,scout,kriging,hydrology,report}
Docker/CI    ──┘                    └──> db/geopackage.py ──> reaqua.gpkg ──> web/app.py (panel, API)
```

Zasady:

- `core/` nie importuje QGIS ani Flaska. Raster czytany przez `core/io.py`: `osgeo.gdal`, a gdy go brak, `rasterio` + `pyproj`.
- `core/params.py` jest jedynym źródłem parametrów (nazwa, etykieta, typ, wartość domyślna, zakres). Korzystają z niego okno QGIS, CLI (`--set`, `params`) i dokumentacja.
- `gui/` zawiera wyłącznie kod zależny od QGIS: `plugin.py` (menu, menu kontekstowe, zadania w tle), `dialog.py` i `widgets.py` (formularze generowane ze specyfikacji parametrów), `layers.py` (dodawanie wyników do projektu), `jobs.py` (wykonanie zadania), `compat.py` (QGIS 3.x/4.x, Qt5/Qt6).
- `db/geopackage.py` zapisuje GeoPackage biblioteką standardową (sqlite3), bez GDAL; zgodność z OGC sprawdzana w testach.
- `inbox.py`: kolejka scen oparta na plikach (`/data/inbox/<id>/`: pasma, `request.json`, `status.json`), wspólna dla panelu WWW i workera; blokada sceny i wznawianie po restarcie.
- `web/scenes.py`: wgrywanie scen, stan przetwarzania i pobieranie wyników; `web/app.py`: `create_app(db_path)`; produkcyjnie `gunicorn "reaqua.web.app:create_app()"`, ścieżka bazy z `REAQUA_DB`.

Przepływ w Dockerze: `web` zapisuje wgrane pasma do kolejki, `worker` (`python -m reaqua worker`) wykonuje `core/pipeline.py` i zapisuje wyniki do `reaqua.gpkg` oraz `/data/output/<id>/`.

Pliki wynikowe przebiegu: `susza.tif`, `mitygacja_suszy.tif`, `kriging_wplyw.tif`, `ryzyko_resztkowe.tif`, `zbiorniki.geojson`, `zbiorniki.csv`, `raport_regionalny.html`, `metryki.json`, `reaqua.gpkg`.

Schemat bazy: `runs` (przebieg, parametry JSON, wynik JSON), `reservoirs` (punkt WGS84, atrybuty po polsku zgodne z warstwą QGIS), `metrics` (klucz, wartość, jednostka).
