# Harmonogram i lista zadań

Daty są propozycją i wymagają dostosowania do terminów przedmiotu. Wersja do bieżącego uzupełniania z wykresami: `ReAqua_monitoring_postepu.xlsx`.

## 1. Wykres Gantta

```mermaid
gantt
    title Projekt ReAqua
    dateFormat  YYYY-MM-DD
    axisFormat  %d.%m
    section Analiza
    Analiza wtyczek i wymagań            :done, a1, 2026-10-05, 14d
    Poprawki metodyczne                  :done, a2, after a1, 14d
    section Implementacja
    Rdzeń obliczeniowy                   :done, b1, 2026-10-19, 21d
    Wtyczka QGIS i menu kontekstowe      :b2, 2026-11-02, 14d
    Baza GeoPackage, API, panel WWW      :b3, 2026-11-02, 14d
    section Jakość
    Testy i CI                           :c1, 2026-11-09, 14d
    Docker i dokumentacja                :c2, 2026-11-16, 14d
    section Oddanie
    Test w QGIS i poprawki               :d1, 2026-11-30, 10d
    Prezentacja końcowa                  :d2, 2026-12-10, 7d
```

## 2. Zadania do tablicy Kanban (GitHub Projects)

Kolumny: Todo, In Progress, Done. Wykonawcy są propozycją, do potwierdzenia przez zespół.

| Zadanie | Wykonawca | Kolumna |
|---------|-----------|---------|
| Analiza merytoryczna trzech wtyczek | Maciej Andrzejewski | Done |
| Rdzeń: klasyfikacja suszy i wybór lokalizacji | Maciej Andrzejewski | Done |
| Rdzeń: kriging i zasięg oddziaływania | Kacper Mikołajczyk | Done |
| Rdzeń: hydrologia, koszty, raport | Weronika Zator | Done |
| Baza GeoPackage | Tomasz Szulski | Done |
| API i panel WWW | Tomasz Szulski | Done |
| Wtyczka QGIS i menu kontekstowe | Maciej Andrzejewski | In Progress |
| Test wtyczki w QGIS 3.22 i najnowszym LTR | Weronika Zator | Todo |
| Weryfikacja źródeł literaturowych i współczynników | Kacper Mikołajczyk | Todo |
| Testy jednostkowe i integracyjne | Tomasz Szulski | Done |
| GitHub Actions | Tomasz Szulski | In Progress |
| Dockerfile i docker-compose | Kacper Mikołajczyk | In Progress |
| README i dokumentacja | Weronika Zator | In Progress |
| Test `docker compose up` | Tomasz Szulski | Todo |
| Prezentacja końcowa | Cały zespół | Todo |

## 3. Propozycje komunikatów commitów

```
Add NDVI/NDMI drought classification with reflectance scaling
Fix reservoir area taken from drought window area
Add anisotropic simple and ordinary kriging variants
Add GeoPackage writer for runs, reservoirs and metrics
Add Flask API with GeoJSON and CSV export
Add layer context menu entries to QGIS plugin
Add pytest suite for spectral, scout and kriging modules
Add scene upload queue and worker service to docker-compose
Add GitHub Actions workflow running flake8 and pytest
Document methodology and checklist mapping
```
