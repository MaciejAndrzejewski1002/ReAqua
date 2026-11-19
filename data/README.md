# Dane

`sample/` zawiera syntetyczną scenę 600 x 600 pikseli (10 m, EPSG:32633) z pasmami B03, B04, B08, B11 i maską gruntów ornych. Scena nie pochodzi z satelity; służy do testów i demonstracji. Odtworzenie: `python scripts/make_sample_data.py`.

Własne dane (Sentinel-2 L2A, Landsat 8/9 Collection 2 Level 2) należy trzymać poza repozytorium, np. w `data/raw/` (wykluczone w `.gitignore`).
