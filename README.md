# ReAqua

[![CI](https://github.com/MaciejAndrzejewski1002/ReAqua/actions/workflows/ci.yml/badge.svg)](https://github.com/MaciejAndrzejewski1002/ReAqua/actions)

Mała retencja przeciw suszy rolniczej: wtyczka QGIS, narzędzie wiersza poleceń i panel WWW w jednym repozytorium.

ReAqua łączy trzy wcześniejsze wtyczki (Retention Scout, Retention Kriging, Retention Summary) w jedną wtyczkę z menu kontekstowym warstw. Projekt zespołu Hydronauts, rozwinięty z rozwiązania z 11. CASSINI Hackathon, realizowany w ramach przedmiotu Projekt Geoinformatyczny (Politechnika Wrocławska).

## Spis treści według checklisty weryfikacji repozytorium

| Punkt checklisty | Sekcja |
|------------------|--------|
| 1.1 Konfiguracja podstawowa i plik README | [1.1](#11-konfiguracja-podstawowa-i-plik-readme) |
| 1.2 Organizacja plików w repozytorium | [1.2](#12-organizacja-plików-w-repozytorium) |
| 2.1 Organizacja pracy na GitHubie | [2.1](#21-organizacja-pracy-na-githubie) |
| 2.2 Prawidłowe korzystanie z systemu Git | [2.2](#22-prawidłowe-korzystanie-z-systemu-git) |
| 3.1 Czytelność i struktura kodu | [3.1](#31-czytelność-i-struktura-kodu) |
| 3.2 Komentarze i obsługa błędów | [3.2](#32-komentarze-i-obsługa-błędów) |
| 4.1 Konfiguracja środowiska (Docker) | [4.1](#41-konfiguracja-środowiska) |
| 5.1 Testy automatyczne i workflows | [5.1](#51-testy-automatyczne-i-workflows) |
| 6 Prezentacja końcowa | [6](#6-prezentacja-końcowa) |

Pełne mapowanie z oceną każdego podpunktu: [docs/CHECKLISTA.md](docs/CHECKLISTA.md). Instrukcja wdrożenia na GitHub krok po kroku: [docs/INSTRUKCJA_GITHUB.md](docs/INSTRUKCJA_GITHUB.md).

## 1. Struktura repozytorium i dokumentacja

### 1.1 Konfiguracja podstawowa i plik README

- **Nazwa repozytorium:** `ReAqua`.
- **Uprawnienia dostępu:** wszyscy członkowie zespołu dodani jako współpracownicy (Settings, Collaborators): Maciej Andrzejewski, Weronika Zator, Kacper Mikołajczyk, Tomasz Szulski.
- **Opis projektu:** ten plik. Cel, problem badawczy i wymogi uruchomieniowe poniżej.

#### Cel i problem badawczy

Susza rolnicza zmniejsza plony, a rozproszona retencja (małe zbiorniki o powierzchni ok. 2 ha) może łagodzić jej skutki lokalnie. ReAqua odpowiada na pytania:

1. Gdzie jest susza? Klasyfikacja NDVI i NDMI ze scen Sentinel-2 L2A lub Landsat 8/9.
2. Gdzie zlokalizować zbiorniki? Rozmieszczenie proporcjonalne do powierzchni suszy w strefach, z odległością minimalną.
3. Jaki zasięg ma ich oddziaływanie? Anizotropowy kriging z uwzględnieniem wiatru i gleby oraz ryzyko resztkowe.
4. Ile to kosztuje i co daje? Bilans wodny, scenariusze (niski, bazowy, wysoki) dla roślinności, bioróżnorodności i węgla, przedział kosztów.

Nieścisłości znalezione w oryginalnych wtyczkach i ich poprawki: [docs/ANALIZA_MERYTORYCZNA.md](docs/ANALIZA_MERYTORYCZNA.md). Wyniki liczbowe różnią się od wartości z prezentacji hackathonowej, ponieważ poprawiono błędy metodyczne.

#### Zastosowanie

ReAqua ma dwie ścieżki użycia:
1. **Wtyczka QGIS** dla analityka: analiza sceny, edycja parametrów i wyników bezpośrednio w projekcie GIS.
2. **Usługa w Dockerze** dla osób bez QGIS (urząd gminy, spółka wodna, doradca rolniczy): wgranie pasm satelitarnych przez stronę WWW, analiza na serwerze w tle, pobranie wyników (rastry GeoTIFF, raport HTML, zbiorniki w GeoJSON/CSV). Ten sam kod i te same wersje bibliotek zapewniają powtarzalność wyników.

Wynik odpowiada na pytanie decyzyjne: gdzie zlokalizować zbiorniki małej retencji, żeby łagodzić skutki suszy rolniczej, i ile to będzie kosztować.

#### Wymogi uruchomieniowe

- QGIS 3.22 lub nowszy (wtyczka); w QGIS używany jest wbudowany GDAL.
- Python 3.12+ (wiersz poleceń, panel WWW, testy); zależności w `requirements.txt` z zafiksowanymi wersjami.
- Docker i Docker Compose (opcjonalnie, do uruchomienia bez instalacji bibliotek).

#### Instalacja wtyczki w QGIS

1. Zbuduj paczkę: `python scripts/build_plugin.py` (powstaje `dist/reaqua.zip`) lub pobierz artefakt `reaqua-plugin` z zakładki Actions.
2. W QGIS: Wtyczki, Zarządzaj wtyczkami, Zainstaluj z pliku ZIP, wskaż `reaqua.zip`.
3. W menu pojawi się pozycja ReAqua, a przycisk na pasku narzędzi uruchomi pełną analizę.

#### Użycie w QGIS

Menu kontekstowe warstwy (prawy przycisk myszy, podmenu ReAqua):

| Warstwa | Polecenie |
|---------|-----------|
| Raster | Pełna analiza ReAqua z tej sceny |
| Raster | Scout: wykryj suszę i zaproponuj zbiorniki |
| Raster | Kriging: użyj jako raster suszy |
| Raster | Raport: użyj jako raster suszy |
| Wektor punktowy | Kriging: użyj jako zbiorniki |
| Wektor punktowy | Raport: użyj jako zbiorniki |

Okno dialogowe wypełnia się danymi z klikniętej warstwy. Obliczenia działają w tle, a wyniki trafiają do projektu jako warstwy: raster suszy, mitygacji, ryzyka resztkowego i punkty zbiorników. Raport HTML otwiera przycisk na pasku komunikatów. Te same polecenia są w menu ReAqua.

Wejście: pasma B03 (opcjonalnie), B04, B08, B11, opcjonalnie SCL i maska gruntów ornych, w jednym metrycznym układzie współrzędnych (np. EPSG:32633). Dla Landsata analogiczne pasma Collection 2 Level 2. Dane przykładowe: `data/sample/`.

#### Wiersz poleceń

```
pip install -r requirements.txt
export PYTHONPATH=src
python -m reaqua demo --out output --db output/reaqua.gpkg
python -m reaqua run --folder dane/scena --steps scout,kriging,report --out output
python -m reaqua serve --db output/reaqua.gpkg
python -m reaqua submit --folder dane/scena --inbox inbox --label "Gmina X"
python -m reaqua worker --inbox inbox --output output --db output/reaqua.gpkg --once
python -m reaqua export --db output/reaqua.gpkg --format geojson --output zbiorniki.geojson
python -m reaqua params
```

Parametry zmienia się opcją `--set klucz=wartość` (lista: `python -m reaqua params`).

### 1.2 Organizacja plików w repozytorium

- **Przejrzysta struktura katalogów:**

```
ReAqua/
  src/reaqua/          kod wtyczki, rdzeń obliczeniowy, baza danych, panel WWW, CLI
    core/              algorytmy niezależne od QGIS (numpy, scipy)
    db/                zapis wyników do GeoPackage
    web/               Flask: panel i API
    gui/               część QGIS: okna, zadania w tle, menu kontekstowe
  data/sample/         syntetyczna scena demonstracyjna (840 KB)
  tests/               testy pytest
  docs/                analiza, metodologia, architektura, Docker, harmonogram, checklista
  scripts/             budowa paczki wtyczki, generator danych i ikony
  .github/workflows/   CI (GitHub Actions)
  Dockerfile
  docker-compose.yml
  requirements.txt
  README.md
```

- **Brak niepotrzebnych plików:** `.gitignore` wyklucza `.vscode/`, `.idea/`, `output/`, `dist/`, `*.gpkg`, `*.zip` i `data/raw/` (duże dane własne). W repozytorium są tylko dane przykładowe.

## 2. Zarządzanie pracą i historia zmian (Git i GitHub)

### 2.1 Organizacja pracy na GitHubie

- **Tablica Kanban (GitHub Projects):** kolumny Todo, In Progress, Done; lista zadań do wprowadzenia w [docs/HARMONOGRAM.md](docs/HARMONOGRAM.md).
- **Przypisanie zadań (Assignees):** wykonawcy w tabeli zadań w `docs/HARMONOGRAM.md`.
- **Aktualność harmonogramu:** zadania przesuwane na tablicy w miarę postępu prac.
- **Harmonogram projektu (wykres Gantta):** `docs/HARMONOGRAM.md`, sekcja 1 (diagram Mermaid renderowany przez GitHub) oraz arkusz Excel `docs/ReAqua_monitoring_postepu.xlsx` (zadania, checklista do odhaczania, wykresy postępu, Gantt).

### 2.2 Prawidłowe korzystanie z systemu Git

- **Regularność commitów:** praca w małych commitach przez cały semestr.
- **Opisowe wiadomości commitów:** w formie zdania w trybie rozkazującym, np. `Add anisotropic simple and ordinary kriging variants`; przykłady w `docs/HARMONOGRAM.md`, sekcja 3.
- **Zrównoważony wkład zespołu:** podział zadań w `docs/HARMONOGRAM.md`; historia commitów powinna odzwierciedlać udział każdej osoby.

## 3. Jakość kodu i dobra praktyka (Clean Code)

### 3.1 Czytelność i struktura kodu

- **Znaczące nazwy:** nazwy opisują przeznaczenie (`reservoir_cost`, `background_stations`, `classify`).
- **Jednolity standard nazewnictwa:** `snake_case` dla funkcji i zmiennych, `CamelCase` dla klas (PEP 8); kontrola `flake8` w CI.
- **Zasada pojedynczej odpowiedzialności:** funkcje wykonują jedną operację (`core/spectral.py`, `core/costs.py`, `core/physics.py`). Kilka funkcji orkiestrujących (`compute_regional`, `run_kriging`, `run_scout`) jest dłuższych i składa wyniki mniejszych funkcji.
- **Modularność:** rdzeń `core/`, baza `db/`, WWW `web/`, QGIS `gui/`; parametry w jednym miejscu (`core/params.py`).

### 3.2 Komentarze i obsługa błędów

- **Wartościowe komentarze:** docstringi opisują intencję i nietrywialną logikę (np. dlaczego NDBI jest domyślnie wyłączony); brak komentarzy opisujących oczywiste linie.
- **Brak „martwego” kodu:** brak zakomentowanych fragmentów; `print` tylko w `cli.py` jako wyjście poleceń.
- Błędy danych wejściowych kończą się czytelnym komunikatem (`ValueError`) pokazywanym w oknie QGIS lub w konsoli.

## 4. Konteneryzacja i środowisko (Docker)

### 4.1 Konfiguracja środowiska

- **`requirements.txt`:** kompletna lista bibliotek z wersjami; `requirements-dev.txt` dodaje narzędzia testowe.
- **`Dockerfile`** (katalog główny): obraz bazowy `python:3.13-slim`, katalog roboczy `/app`, kopiowanie plików, komenda startowa `gunicorn`.
- **`docker-compose.yml`** (katalog główny): usługi `seed` (dane demonstracyjne), `worker` (analiza scen w tle) i `web` (panel, API, wgrywanie scen), port 8000, wspólny wolumen `reaqua-data` utrwalający bazę, kolejkę i wyniki.

#### Jak działa Docker

Docker buduje z `Dockerfile` obraz (środowisko z Pythonem i bibliotekami), a `docker-compose.yml` uruchamia z niego trzy kontenery. `seed` wypełnia bazę danymi demonstracyjnymi i się zatrzymuje. `web` przyjmuje wgrane sceny i pokazuje wyniki pod http://localhost:8000. `worker` odbiera sceny z kolejki na wspólnym wolumenie, liczy analizę (Scout, Kriging, Raport) i zapisuje wyniki do bazy. Wtyczka QGIS nie działa w kontenerze; Docker uruchamia ten sam silnik jako usługę.

```
docker compose up --build
```

W panelu, sekcja "Nowa analiza": wgraj pasma (do wypróbowania pliki z `data/sample/`), odczekaj kilka sekund i pobierz wyniki. Po pracy: `docker compose down` (dodaj `-v`, by usunąć dane). Szczegółowy opis architektury, konfiguracji (token wgrywania, limit rozmiaru), API i rozwiązywania problemów: [docs/DOCKER.md](docs/DOCKER.md).

## 5. Testowanie i CI/CD (GitHub Actions)

### 5.1 Testy automatyczne i workflows

- **Workflow CI/CD** (`.github/workflows/ci.yml`): przy każdym `push` na `main` i każdym `pull_request` uruchamia `flake8`, `pytest` (Python 3.12 i 3.13), budowę obrazu Docker z testem uruchomienia oraz budowę paczki wtyczki.
- **Status pipeline'u:** znaczek na górze README i zakładka Actions.

Uruchomienie lokalnie:

```
pip install -r requirements-dev.txt
export PYTHONPATH=src
pytest --cov=reaqua
flake8 src tests scripts
```

Testy interfejsu sprawdzają rejestrację poleceń na atrapach modułów QGIS; pełny test okna wymaga ręcznego uruchomienia w QGIS.

## 6. Prezentacja końcowa

- **Baza danych:** plik OGC GeoPackage (SQLite, rozszerzenie przestrzenne) `reaqua.gpkg` z tabelami `runs`, `reservoirs` (punkty w EPSG:4326, współrzędne projekcyjne w `x_proj`, `y_proj`) i `metrics`. Wypełniana poleceniem `python -m reaqua demo`, usługą `seed` lub analizą wgranej sceny (`worker`) w Dockerze; otwiera się bezpośrednio w QGIS.
- **Wizualizacja danych:** panel WWW pod `/` (statystyki, wykres rozmieszczenia, tabela zbiorników) oraz raport HTML z wykresami.
- **Pobieranie danych:** API w formatach JSON, GeoJSON i CSV:

| Adres | Odpowiedź |
|-------|-----------|
| `/health` | stan usługi i wersja |
| `/api/runs` | lista przebiegów |
| `/api/runs/<id>` | szczegóły przebiegu |
| `/api/stats` | metryki ostatniego przebiegu |
| `/api/reservoirs?format=json`, `geojson` lub `csv`, opcjonalnie `max_priority=N` | zbiorniki do pobrania |
| `POST /api/scenes` | wgranie scen (pola `red`, `nir`, `swir`, opcjonalnie `green`, `scl`, `mask`, `label`, `param_*`), odpowiedź 202 z identyfikatorem |
| `/api/scenes`, `/api/scenes/<id>` | lista i stan przetwarzania scen |
| `/scenes/<id>/files/<plik>` | pobranie wyniku sceny (GeoTIFF, raport HTML, GeoJSON, CSV) |

## Ograniczenia

Współczynniki wpływu zbiorników, scenariusze roślinności i progi oceny są założeniami roboczymi, niekalibrowanymi pomiarami terenowymi. Pełna lista w [docs/ANALIZA_MERYTORYCZNA.md](docs/ANALIZA_MERYTORYCZNA.md), sekcje 4 i 6.

## Autorzy

Zespół Hydronauts: Maciej Andrzejewski (lider), Weronika Zator, Kacper Mikołajczyk, Tomasz Szulski.

Licencja: MIT (plik `LICENSE`).
