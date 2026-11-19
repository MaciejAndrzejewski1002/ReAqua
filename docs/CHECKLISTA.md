# Checklista weryfikacji repozytorium GitHub

Numeracja i nazwy punktów odpowiadają oryginalnej checkliście (Projekt Geoinformatyczny, semestr zimowy 2025/2026).

Legenda statusu:
- ZROBIONE: spełnione w plikach repozytorium, nic nie trzeba robić.
- DO ZROBIENIA: wymaga działania zespołu (GitHub, komputer z Dockerem lub QGIS); kroki podane poniżej.
- CZĘŚCIOWO: spełnione w większości, opisano, co zostało.

Do odhaczania i monitorowania postępu służy arkusz `docs/ReAqua_monitoring_postepu.xlsx` (arkusze Panel, Zadania, Checklista, Gantt).

## Podsumowanie

| Punkt | Status |
|-------|--------|
| 1.1 Nazwa repozytorium | DO ZROBIENIA |
| 1.1 Uprawnienia dostępu | DO ZROBIENIA |
| 1.1 Opis projektu w README.md | ZROBIONE |
| 1.2 Przejrzysta struktura katalogów | ZROBIONE |
| 1.2 Brak niepotrzebnych plików | ZROBIONE |
| 2.1 Tablica Kanban | DO ZROBIENIA |
| 2.1 Przypisanie zadań | DO ZROBIENIA |
| 2.1 Aktualność harmonogramu | DO ZROBIENIA |
| 2.1 Harmonogram projektu (Gantt) | ZROBIONE (daty do sprawdzenia) |
| 2.2 Regularność commitów | DO ZROBIENIA |
| 2.2 Opisowe wiadomości commitów | DO ZROBIENIA |
| 2.2 Zrównoważony wkład zespołu | DO ZROBIENIA |
| 3.1 Znaczące nazwy | ZROBIONE |
| 3.1 Jednolity standard nazewnictwa | ZROBIONE |
| 3.1 Zasada pojedynczej odpowiedzialności | CZĘŚCIOWO |
| 3.1 Modularność kodu | ZROBIONE |
| 3.2 Wartościowe komentarze | ZROBIONE |
| 3.2 Brak "martwego" kodu | ZROBIONE |
| 4.1 requirements.txt | ZROBIONE |
| 4.1 Dockerfile | ZROBIONE (do sprawdzenia uruchomieniem) |
| 4.1 docker-compose.yml | ZROBIONE (do sprawdzenia uruchomieniem) |
| 5.1 Workflow CI/CD | ZROBIONE |
| 5.1 Status pipeline'u | DO ZROBIENIA |
| 6 Baza danych | ZROBIONE |
| 6 Wizualizacja danych | ZROBIONE |
| 6 Pobieranie danych | ZROBIONE |

Przed wykonaniem kroków z sekcji 1 i 2 wykonaj krok zerowy.

## Krok zerowy: podmiana miejsc zastępczych

W repozytorium są trzy miejsca zastępcze: `ZASTAP-ORGANIZACJA` (nazwa konta lub organizacji na GitHubie) i `reaqua@example.com` (e-mail kontaktowy). Po utworzeniu repozytorium podmień je w głównym katalogu projektu (przykład dla konta `hydronauts`):

```
grep -rl "ZASTAP-ORGANIZACJA" . | xargs sed -i 's/ZASTAP-ORGANIZACJA/hydronauts/g'
sed -i 's/reaqua@example.com/twoj.adres@mail.pl/' src/reaqua/metadata.txt
```

Dotyczy plików: `README.md`, `src/reaqua/metadata.txt`.

## 1. Struktura repozytorium i dokumentacja

### 1.1 Konfiguracja podstawowa i plik README

**Nazwa repozytorium: DO ZROBIENIA.** Proponowana nazwa: `ReAqua`.
1. GitHub, ikona plusa w prawym górnym rogu, New repository.
2. Repository name: `ReAqua`. Description: `Mała retencja przeciw suszy: wtyczka QGIS, CLI i panel WWW`.
3. Widoczność Public lub Private (jeśli prowadząca ma mieć dostęp, patrz następny punkt).
4. Nie zaznaczaj Add README, .gitignore ani License (są już w paczce). Kliknij Create repository.

**Uprawnienia dostępu: DO ZROBIENIA.**
1. W repozytorium: Settings, Collaborators (lub Collaborators and teams), Add people.
2. Dodaj po nazwie użytkownika lub e-mailu: Weronika Zator, Kacper Mikołajczyk, Tomasz Szulski oraz prowadzącą (mgr inż. Michalina Kotyla).
3. Każda z osób musi zaakceptować zaproszenie (przychodzi e-mailem). Sprawdź, że w Collaborators wszyscy mają status aktywny, a nie "Pending invite".

**Opis projektu w README.md: ZROBIONE.** `README.md`, sekcja 1.1: cel, problem badawczy, wymogi uruchomieniowe, instalacja, użycie.

### 1.2 Organizacja plików w repozytorium

**Przejrzysta struktura katalogów: ZROBIONE.** `src/`, `data/`, `tests/`, `docs/`, `scripts/`; drzewo w README, sekcja 1.2.

**Brak niepotrzebnych plików: ZROBIONE.** `.gitignore` wyklucza `.vscode/`, `.idea/`, `output/`, `dist/`, `*.gpkg`, `*.zip`, `data/raw/`. Dane przykładowe zajmują 840 KB. Przed pierwszym `git add` uruchom `git status` i sprawdź, że nie pojawiają się pliki IDE ani duże dane.

## 2. Zarządzanie pracą i historia zmian (Git i GitHub)

### 2.1 Organizacja pracy na GitHubie

**Tablica Kanban (GitHub Projects): DO ZROBIENIA.**
1. W repozytorium: zakładka Projects, New project, szablon Board, nazwa `ReAqua - zadania`.
2. Sprawdź, że kolumny to dokładnie Todo, In Progress, Done (szablon Board je tworzy; w razie potrzeby zmień nazwy).
3. Zakładka Issues, New issue: utwórz po jednym zgłoszeniu na każde zadanie z `docs/HARMONOGRAM.md`, sekcja 2 (15 zadań). Dostępne są szablony Zadanie i Błąd.
4. W zgłoszeniu: Projects, wybierz `ReAqua - zadania`. Zadania oznaczone w tabeli jako Done przenieś do kolumny Done, In Progress do In Progress, reszta zostaje w Todo.

**Przypisanie zadań (Assignees): DO ZROBIENIA.**
1. Przypisanie działa tylko dla osób dodanych jako współpracownicy (punkt 1.1), więc najpierw one muszą zaakceptować zaproszenia.
2. W każdym zgłoszeniu: Assignees po prawej stronie, wybierz osobę. Podział w `docs/HARMONOGRAM.md` jest propozycją; ustalcie go w zespole i zmieńcie, jeśli ktoś robi coś innego.
3. W widoku tablicy włącz pole Assignees (ikona ustawień widoku, Fields), żeby było widać wykonawców.
4. Sprawdź, że żadne zgłoszenie na tablicy nie ma pustego pola Assignees.

**Aktualność harmonogramu: DO ZROBIENIA.** Wymaga stałej pracy do końca semestru: po rozpoczęciu zadania przeciągnij je do In Progress, po zakończeniu do Done. Najprościej zamykać zgłoszenie komunikatem w commicie (`Fixes #12`), a w ustawieniach projektu (Workflows) włączyć automatyczne przenoszenie zamkniętych zgłoszeń do Done.

**Harmonogram projektu (wykres Gantta): ZROBIONE.** `docs/HARMONOGRAM.md`, sekcja 1; GitHub wyświetla diagram automatycznie. Do zrobienia po Waszej stronie: zmienić daty w diagramie na faktyczne terminy przedmiotu (linie `:done, a1, 2026-10-05, 14d` itd.) i oznaczać `done` ukończone etapy. Alternatywa dopuszczona w checkliście: Gantt w Excelu, wgrany do `docs/`.

### 2.2 Prawidłowe korzystanie z systemu Git

**Regularność commitów: DO ZROBIENIA.** Nie wgrywaj całego projektu jednym commitem. Przykład zaczynający historię (w katalogu projektu):

```
git init -b main
git add .gitignore LICENSE AUTHORS requirements.txt requirements-dev.txt pyproject.toml .flake8
git commit -m "Add project configuration and dependency lists"
git add src/reaqua/core/spectral.py src/reaqua/core/models.py src/reaqua/core/io.py src/reaqua/core/params.py src/reaqua/core/physics.py src/reaqua/__init__.py src/reaqua/core/__init__.py
git commit -m "Add NDVI/NDMI drought classification with reflectance scaling"
```

Kolejne commity wg listy w `docs/HARMONOGRAM.md`, sekcja 3, w miarę dodawania kolejnych modułów. Potem:

```
git remote add origin https://github.com/NAZWA-KONTA/ReAqua.git
git push -u origin main
```

Dalszą pracę (poprawki, nowe funkcje, dokumentacja) commitujcie na bieżąco do końca semestru, najlepiej przez gałęzie i pull requesty.

**Opisowe wiadomości commitów: DO ZROBIENIA.** Gotowe propozycje w `docs/HARMONOGRAM.md`, sekcja 3. Zasada: zdanie w trybie rozkazującym opisujące zmianę (`Fix reservoir area taken from drought window area`), nigdy `update` ani `poprawki`.

**Zrównoważony wkład zespołu: DO ZROBIENIA.** Tego nie da się zapisać w plikach, a wygenerowanie sztucznej historii nie byłoby uczciwe. Każda z czterech osób powinna wykonać własne commity pod własnym kontem:
1. Każdy klonuje repozytorium: `git clone https://github.com/NAZWA-KONTA/ReAqua.git`.
2. Każdy ustawia własne dane: `git config user.name "Imię Nazwisko"` i `git config user.email "adres-z-konta-GitHub"`.
3. Każdy pracuje nad zadaniami przypisanymi na tablicy (np. Tomasz Szulski: baza, API, testy; Weronika Zator: raport i dokumentacja; Kacper Mikołajczyk: kriging i Docker; Maciej Andrzejewski: wtyczka QGIS) i wgrywa zmiany przez pull request.
4. Kontrola: GitHub, zakładka Insights, Contributors pokazuje udział każdej osoby.

## 3. Jakość kodu i dobra praktyka (Clean Code)

### 3.1 Czytelność i struktura kodu

**Znaczące nazwy: ZROBIONE.** Nazwy opisują przeznaczenie (`reservoir_cost`, `background_stations`); brak `a1`, `temp`, `x`.

**Jednolity standard nazewnictwa: ZROBIONE.** `snake_case` dla funkcji i zmiennych, `CamelCase` dla klas; kontrola `flake8` w CI.

**Zasada pojedynczej odpowiedzialności: CZĘŚCIOWO.** Większość funkcji jest krótka. Siedem ma ponad 50 linii: `generate_html` (szablon raportu), `compute_regional`, `create_app` (rejestracja tras), `run_kriging`, `run_scout`, `_build` i `_tab_data` (okno QGIS). Co zrobić: podzielić je na mniejsze funkcje. Mogę to wykonać na Waszą prośbę; wymaga to ponownego uruchomienia testów.

**Modularność kodu: ZROBIONE.** `core/`, `db/`, `web/`, `gui/`; parametry w jednym miejscu (`core/params.py`).

### 3.2 Komentarze i obsługa błędów

**Wartościowe komentarze: ZROBIONE.** Docstringi opisują intencję i nietrywialną logikę (np. dlaczego filtr NDBI jest domyślnie wyłączony).

**Brak "martwego" kodu: ZROBIONE.** Brak zakomentowanego kodu; `print` występuje tylko w `cli.py` jako wyjście poleceń konsolowych.

## 4. Konteneryzacja i środowisko (Docker)

### 4.1 Konfiguracja środowiska

**Plik `requirements.txt`: ZROBIONE.** Kompletna lista bibliotek z wersjami (`requirements.txt`, `requirements-dev.txt`); wersje zgodne z przetestowanymi.

**Plik `Dockerfile`: ZROBIONE, DO SPRAWDZENIA URUCHOMIENIEM.** Obraz bazowy `python:3.13-slim`, katalog roboczy `/app`, kopiowanie plików, komenda startowa `gunicorn`. Nie budowałem obrazu (brak Dockera w moim środowisku). Co zrobić: zainstalować Docker Desktop i wykonać w katalogu głównym `docker build -t reaqua .`; oczekiwany wynik: obraz zbudowany bez błędów.

**Plik `docker-compose.yml`: ZROBIONE, DO SPRAWDZENIA URUCHOMIENIEM.** Usługi `seed`, `worker` i `web`, port 8000, wspólny wolumen `reaqua-data`. Co zrobić: `docker compose up --build`, poczekać na zakończenie usługi `seed` i otworzyć http://localhost:8000; oczekiwany wynik: panel ze statystykami i tabelą zbiorników. Jeśli coś nie działa, wyślij mi komunikat błędu (`docker compose logs`). Opis działania: `docs/DOCKER.md`.

## 5. Testowanie i CI/CD (GitHub Actions)

### 5.1 Testy automatyczne i workflows

**Workflow CI/CD (`.github/workflows/`): ZROBIONE.** `ci.yml` przy każdym `push` na `main` i każdym `pull_request` uruchamia `flake8` i 53 testy `pytest` (Python 3.12 i 3.13), buduje obraz Docker i paczkę wtyczki. Plik musi trafić do repozytorium z zachowaniem ścieżki `.github/workflows/ci.yml` (katalog z kropką łatwo pominąć przy ręcznym wgrywaniu).

**Status pipeline'u: DO ZROBIENIA.**
1. Po pierwszym `git push` otwórz zakładkę Actions i sprawdź, że workflow `CI` zakończył się zielonym znacznikiem dla wszystkich trzech zadań (`test`, `docker`, `plugin`).
2. Jeśli zadanie jest czerwone, otwórz je, skopiuj komunikat błędu i wyślij mi; naprawię.
3. Wykonaj krok zerowy, żeby znaczek statusu na górze README wskazywał właściwe repozytorium.

## 6. Prezentacja końcowa

**Baza danych: ZROBIONE.** GeoPackage `reaqua.gpkg` (SQLite, rozszerzenie przestrzenne) z tabelami `runs`, `reservoirs`, `metrics`. Wypełniana poleceniem `python -m reaqua demo` lub usługą `seed` w Dockerze. Na prezentacji pokaż plik otwarty w QGIS lub panel WWW.

**Wizualizacja danych: ZROBIONE.** Panel WWW pod `/` (statystyki i wykres rozmieszczenia) oraz raport HTML z wykresami.

**Pobieranie danych: ZROBIONE.** `/api/reservoirs?format=json`, `geojson` lub `csv`; polecenie `python -m reaqua export`.

## Test ręczny przed oddaniem

1. `docker compose up --build`, otworzyć http://localhost:8000.
2. Zainstalować `dist/reaqua.zip` w QGIS (Wtyczki, Zainstaluj z pliku ZIP), wczytać `data/sample/*.tif`, kliknąć prawym przyciskiem raster B04 i wybrać ReAqua, Pełna analiza.
3. Sprawdzić, że po zakończeniu pojawia się grupa warstw i przycisk raportu. Interfejs QGIS nie był przeze mnie uruchamiany w prawdziwym QGIS.
4. Sprawdzić zielony status w Actions i listę współpracowników w Insights, Contributors.
