# Instrukcja krok po kroku: od paczki do repozytorium spełniającego checklistę

Dokument prowadzi przez wszystko, co zespół musi wykonać, żeby zaliczyć każdy punkt checklisty weryfikacji repozytorium. Kolejność kroków jest celowa: najpierw przygotowanie, potem repozytorium, potem praca zespołu, na końcu kontrola.

Oznaczenia w nawiasach (np. 1.1, 2.2) odpowiadają numeracji z checklisty. Szczegółowy stan każdego punktu: `CHECKLISTA.md` i arkusz `ReAqua_monitoring_postepu.xlsx`.

## Kto robi co

| Osoba | Zakres w tej instrukcji |
|-------|-------------------------|
| Maciej Andrzejewski | Kroki 1 do 7: założenie repozytorium, pierwsze commity, zaproszenia |
| Tomasz Szulski | Krok 8 (Kanban), krok 10 (Actions), test Dockera |
| Weronika Zator | Krok 9 (harmonogram), krok 11 (test w QGIS), weryfikacja literatury |
| Kacper Mikołajczyk | Krok 10 (Docker), weryfikacja współczynników |
| Wszyscy | Krok 12: własne commity i pull requesty |

Podział to propozycja; zmieńcie go, jeśli ktoś ma inne możliwości.

## Krok 0. Przygotowanie komputera (każdy)

1. Załóż konto na https://github.com, jeśli go nie masz.
2. Zainstaluj Git: https://git-scm.com/downloads. Na Windows zostaw domyślne opcje (zawiera Git Bash i Git Credential Manager, który loguje do GitHuba przez przeglądarkę, bez wpisywania hasła w terminalu).
3. Ustaw swoje dane. Muszą być Twoje, bo na ich podstawie GitHub przypisuje commity do Twojego konta w Insights, Contributors (2.2 Zrównoważony wkład):

```
git config --global user.name "Imię Nazwisko"
git config --global user.email "adres-użyty-na-GitHubie@example.com"
git config --global core.autocrlf true
```

Ostatnia linia dotyczy Windows i zapobiega ostrzeżeniom o końcach linii. Adres e-mail musi być dodany w GitHub, Settings, Emails (może być adres prywatny `...@users.noreply.github.com`).

4. Zainstaluj Docker Desktop (https://www.docker.com/products/docker-desktop) i uruchom go. Na Windows może poprosić o włączenie WSL 2: zgódź się i zrestartuj komputer.
5. Zainstaluj QGIS 3.22 lub nowszy (https://qgis.org). Zainstaluj Python 3.12+ i edytor (np. VS Code), jeśli ich nie masz.

## Krok 1. Rozpakowanie paczki (Maciej)

1. Rozpakuj `ReAqua_repozytorium.zip`. Powstanie folder `ReAqua`.
2. Jeśli w folderze jest ukryty podfolder `.git`, usuń go (to pusty, niepotrzebny zalążek repozytorium z wcześniejszego etapu):
   - Windows PowerShell: `Remove-Item -Recurse -Force ReAqua\.git`
   - Linux/macOS: `rm -rf ReAqua/.git`
3. Sprawdź, że widzisz katalog `.github` (jest ukryty przez kropkę). W Eksploratorze Windows włącz Widok, Pokaż, Ukryte elementy. Ten folder musi trafić do repozytorium, bo zawiera workflow CI (5.1).

## Krok 2. Utworzenie repozytorium na GitHubie (Maciej) — punkt 1.1 Nazwa repozytorium

1. GitHub, ikona plusa w prawym górnym rogu, New repository.
2. Repository name: `ReAqua`. Nazwa jest krótka, jednoznaczna i nawiązuje do tematu (retencja wodna, susza).
3. Description: `Mała retencja przeciw suszy: wtyczka QGIS, CLI i panel WWW`.
4. Widoczność: Public (najprościej) lub Private. Przy Private dodaj prowadzącą jako współpracownika w kroku 3.
5. **Nie zaznaczaj** Add a README file, .gitignore ani license. Te pliki są już w paczce, a zaznaczenie ich spowoduje konflikt przy pierwszym wypchnięciu.
6. Create repository. Zapamiętaj adres w formacie `https://github.com/NAZWA-KONTA/ReAqua.git`.

Jeśli repozytorium ma należeć do organizacji, utwórz je w jej ramach (lista Owner przy tworzeniu).

## Krok 3. Współpracownicy (Maciej) — punkt 1.1 Uprawnienia dostępu

1. W repozytorium: Settings, w lewym menu Collaborators.
2. Add people. Wpisz nazwę użytkownika lub e-mail i wybierz osobę: Weronika Zator, Kacper Mikołajczyk, Tomasz Szulski oraz prowadząca (mgr inż. Michalina Kotyla).
3. Każda osoba dostaje e-mail z zaproszeniem i musi je zaakceptować (link w e-mailu lub https://github.com/NAZWA-KONTA/ReAqua/invitations).
4. Kontrola: w Settings, Collaborators wszyscy mają mieć status aktywny, bez dopisku Pending invite.

## Krok 4. Podmiana miejsc zastępczych (Maciej)

W plikach są wartości do zastąpienia: `ZASTAP-ORGANIZACJA` (nazwa konta lub organizacji GitHub) i `reaqua@example.com` (e-mail kontaktowy).

1. Otwórz folder `ReAqua` w VS Code (File, Open Folder).
2. Ctrl+Shift+H (wyszukiwanie i zamiana w plikach). Wpisz `ZASTAP-ORGANIZACJA`, w polu zamiany Twoją nazwę konta (np. `maciej-andrzejewski`), kliknij Replace All.
3. To samo dla `reaqua@example.com` na właściwy adres.
4. Zmiany obejmują `README.md` (znaczek CI w pierwszej linii) i `src/reaqua/metadata.txt` (linki wtyczki). Wzmianki w `docs/CHECKLISTA.md` mogą zostać, są opisem tej czynności.
5. Nie używaj PowerShell `Set-Content` do tej operacji: dopisuje on znacznik BOM, który może zepsuć odczyt `metadata.txt` w QGIS.

## Krok 5. Test lokalny przed wysłaniem (Maciej)

W terminalu w folderze `ReAqua`:

```
python -m venv .venv
.venv\Scripts\activate          (Linux/macOS: source .venv/bin/activate)
pip install -r requirements-dev.txt
pytest
flake8 src tests scripts
```

Oczekiwany wynik: `67 passed` i brak komunikatów flake8. Jeśli coś się nie powiedzie (np. brak biblioteki `rasterio` na starszym Pythonie), skopiuj komunikat i napisz do mnie.

Opcjonalnie zainstaluj projekt, żeby mieć polecenie `reaqua`: `pip install -e .`, potem `reaqua demo --out output --db output/reaqua.gpkg`.

## Krok 6. Pierwsze commity z historią (Maciej) — punkty 2.2 Regularność i Opisowe komunikaty

Zasada: commit to jedna logiczna zmiana z komunikatem w trybie rozkazującym, który mówi co się zmieniło (np. `Add ...`, `Fix ...`), nigdy `update` ani `poprawki`.

1. Zainicjuj repozytorium:

```
git init -b main
git remote add origin https://github.com/NAZWA-KONTA/ReAqua.git
```

2. Wykonuj po kolei poniższe commity. Każdy blok to `git add ...` i `git commit -m ...`:

```
git add .gitignore LICENSE AUTHORS .flake8 requirements.txt requirements-dev.txt pyproject.toml
git commit -m "Add project configuration, license and pinned dependencies"

git add src/reaqua/__init__.py src/reaqua/core/__init__.py src/reaqua/core/models.py src/reaqua/core/params.py src/reaqua/core/physics.py src/reaqua/core/io.py src/reaqua/core/spectral.py
git commit -m "Add raster I/O and NDVI/NDMI drought classification with reflectance scaling"

git add src/reaqua/core/scout.py src/reaqua/core/synthetic.py scripts/make_sample_data.py data
git commit -m "Add reservoir siting with zone quotas, minimum distance and sample data"

git add src/reaqua/core/kriging.py
git commit -m "Add anisotropic simple and ordinary kriging of reservoir influence"

git add src/reaqua/core/costs.py src/reaqua/core/hydrology.py src/reaqua/core/report.py src/reaqua/core/charts.py src/reaqua/core/schema.py src/reaqua/core/pipeline.py
git commit -m "Add regional water balance, indices, scenarios, costs and HTML report"

git add src/reaqua/db
git commit -m "Add GeoPackage writer for runs, reservoirs and metrics"

git add src/reaqua/__main__.py src/reaqua/cli.py src/reaqua/inbox.py
git commit -m "Add command line interface and file-based scene queue"

git add src/reaqua/web
git commit -m "Add Flask dashboard, REST API and scene upload"

git add src/reaqua/gui src/reaqua/metadata.txt src/reaqua/icon.png scripts/make_icon.py scripts/build_plugin.py
git commit -m "Add QGIS plugin with layer context menu and background tasks"

git add tests
git commit -m "Add pytest suite for core, database, web and plugin registration"

git add Dockerfile docker-compose.yml .dockerignore
git commit -m "Add Dockerfile and docker-compose with seed, worker and web services"

git add .github
git commit -m "Add GitHub Actions workflow running flake8, pytest and Docker build"

git add README.md docs
git commit -m "Add README and project documentation"
```

3. Kontrola: `git status` ma pokazać `nothing to commit, working tree clean`, a `git log --oneline` 13 commitów. Jeśli `git status` pokazuje pliki niedodane, dodaj je osobnym commitem z opisem.
4. Wysłanie: `git push -u origin main`. Przy pierwszym wysłaniu otworzy się okno logowania przez przeglądarkę.

Uwaga o uczciwości historii: te commity powstaną jednego dnia i jedną osobą. Checklista wymaga pracy rozłożonej na semestr i udziału wszystkich, więc nie wystarczą one same. Nie zmieniaj dat commitów ani autorstwa, żeby to ukryć: kolejne kroki dają realną pracę dla każdego z autorów.

## Krok 7. Kontrola po wysłaniu (Maciej) — punkty 1.2, 5.1

Odśwież stronę repozytorium na GitHubie i sprawdź:
1. Widać foldery `.github`, `src`, `data`, `tests`, `docs`, `scripts` oraz pliki `README.md`, `Dockerfile`, `docker-compose.yml`, `requirements.txt` (1.2 Przejrzysta struktura).
2. Nie ma `.vscode/`, `.idea/`, `.venv/`, `output/`, `dist/` ani plików `*.zip` (1.2 Brak niepotrzebnych plików). Jeśli któryś się pojawił: `git rm -r --cached nazwa`, commit `Remove tracked local files`, push.
3. README wyświetla się na stronie głównej z numerowanymi sekcjami 1.1 do 6 (1.1 Opis projektu).
4. Zakładka Actions: workflow `CI` uruchomił się automatycznie po wysłaniu. Poczekaj kilka minut; trzy zadania (`test`, `docker`, `plugin`) mają być zielone (5.1 Workflow i Status pipeline'u). Przy czerwonym wyniku otwórz zadanie, skopiuj komunikat błędu i napisz do mnie.

## Krok 8. Tablica Kanban i przypisanie zadań (Tomasz) — punkty 2.1

1. W repozytorium: zakładka Projects, New project.
2. Szablon Board, nazwa `ReAqua - zadania`, Create. Kolumny mają nazywać się dokładnie Todo, In Progress, Done (tak jest w szablonie). W razie potrzeby zmień nazwy przez menu kolumny.
3. Utwórz zgłoszenia (Issues): zakładka Issues, New issue, szablon Zadanie. Jedno zgłoszenie na każdy wiersz z arkusza `ReAqua_monitoring_postepu.xlsx`, arkusz Zadania (30 pozycji). Tytuł to treść z kolumny Zadanie, opis to kolumna Uwagi i termin.
4. Dodaj zgłoszenia do projektu: w projekcie przycisk Add item, wpisz `#` i wybierz zgłoszenia (można zaznaczyć wiele). Alternatywnie w zgłoszeniu: panel Projects po prawej, wybierz projekt.
5. Ustaw status każdego zadania zgodnie z arkuszem: ukończone przenieś do Done (zamknij zgłoszenie), pozostałe zostają w Todo.
6. **Przypisanie zadań:** w każdym zgłoszeniu po prawej Assignees, wybierz osobę (wymaga zaakceptowanego zaproszenia z kroku 3). Podział jest w kolumnie Wykonawca arkusza. W widoku tablicy włącz wyświetlanie pola Assignees (ikona ustawień widoku, Fields). Zadania "Cały zespół" rozbij na zgłoszenia dla poszczególnych osób, bo checklista wymaga przypisanych wykonawców.
7. **Aktualność harmonogramu:** w projekcie Settings, Workflows włącz `Item closed` ustawiający status Done. Od tej pory zamknięcie zgłoszenia (np. przez `Closes #12` w pull requeście) samo przenosi kartę do Done. Pozostałe przesunięcia (do In Progress) wykonuj ręcznie, gdy zaczynasz pracę.
8. Kontrola: żadne zadanie na tablicy nie ma pustego pola Assignees, a kolumny In Progress i Done się zmieniają w czasie.

## Krok 9. Harmonogram Gantta (Weronika) — punkt 2.1

Są dwie wersje i obie spełniają wymaganie:
1. `docs/HARMONOGRAM.md` zawiera diagram Mermaid, który GitHub rysuje automatycznie po otwarciu pliku.
2. Arkusz `docs/ReAqua_monitoring_postepu.xlsx`, arkusz Gantt rysuje się sam z dat w arkuszu Zadania.

Co zrobić:
1. Zmień daty zadań na faktyczne terminy przedmiotu (w arkuszu kolumny Start i Termin, w `HARMONOGRAM.md` linie diagramu).
2. W Panelu arkusza ustaw właściwy termin oddania projektu (pole C5).
3. Co tydzień aktualizuj statusy i daty ukończenia, zatwierdzaj plik commitem `Update progress tracker for week of 16 Nov`.
4. Opcjonalnie: w projekcie GitHub dodaj widok Roadmap (przycisk New view, Roadmap) i pola dat. Jest mniej intuicyjny od arkusza, ale jest na tablicy.

## Krok 10. Docker i status pipeline'u (Kacper, Tomasz) — punkty 4.1, 5.1

Docker (Kacper). To jedyny element pliku, którego nie mogłem sprawdzić samodzielnie:
1. W folderze repozytorium: `docker compose up --build`.
2. Poczekaj, aż w logach zobaczysz zakończenie `seed` i start `web`. Pierwsze budowanie trwa kilka minut.
3. Otwórz http://localhost:8000. Ma być panel z wynikami demonstracyjnymi (statystyki, mapa punktów, wykresy, tabela).
4. Wgraj scenę: sekcja "Nowa analiza", pliki B04, B08, B11 z `data/sample/`. Po kilku sekundach na stronie sceny pojawią się linki do wyników; pobierz `susza.tif` i otwórz go w QGIS.
5. Zatrzymaj: Ctrl+C i `docker compose down`.
6. Jeśli wystąpi błąd, zapisz komunikat z `docker compose logs`. Zrób zrzut ekranu działającego panelu do README (np. `docs/img/panel.png`) i prezentacji.
7. Po sukcesie odhacz w arkuszu Checklista punkty Plik Dockerfile i Plik docker-compose.yml.

Status pipeline'u (Tomasz): po każdym wypchnięciu sprawdzaj w Actions, że CI jest zielony. Dodaj do README znaczek statusu (jest już w pierwszej linii, po podmianie z kroku 4 powinien pokazywać pass).

## Krok 11. Test wtyczki w QGIS (Weronika) — jakość i wymagania projektu

Wtyczki nie uruchamiałem w prawdziwym QGIS, więc ten test jest obowiązkowy.
1. Zbuduj paczkę: `python scripts/build_plugin.py` (powstaje `dist/reaqua.zip`) albo pobierz artefakt `reaqua-plugin` z Actions (kliknij ukończone uruchomienie CI, sekcja Artifacts).
2. QGIS: Wtyczki, Zarządzaj wtyczkami i instaluj, Zainstaluj z pliku ZIP, wskaż `reaqua.zip`, Zainstaluj.
3. W menu głównym ma pojawić się pozycja ReAqua oraz przycisk na pasku narzędzi.
4. Wczytaj `data/sample/*B04*.tif` (Warstwa, Dodaj warstwę, Dodaj warstwę rastrową). Kliknij warstwę prawym przyciskiem: ma być podmenu ReAqua z poleceniami dla rastra.
5. Wybierz "Pełna analiza ReAqua z tej sceny". W oknie sprawdź pole folderu sceny, kliknij Uruchom. Po zakończeniu w projekcie mają pojawić się warstwy (susza, mitygacja, ryzyko resztkowe, zbiorniki), a na pasku komunikatów przycisk otwierający raport.
6. Wczytaj warstwę zbiorników (wynik) i sprawdź polecenia dla warstwy punktowej (Kriging, Raport).
7. Sprawdź także w najnowszym wydaniu QGIS, jeśli różni się od zainstalowanego.
8. Zapisz wynik testu w pliku `docs/TEST_QGIS.md` (wersja QGIS, co działało, co nie, zrzuty ekranu). Jeśli coś nie zadziała, wyślij mi treść błędu z panelu Komunikaty dziennika (Widok, Panele, Komunikaty dziennika).

## Krok 12. Praca zespołu: gałęzie i pull requesty (wszyscy) — punkty 2.2

Ten krok rozwiązuje wymagania Regularność commitów i Zrównoważony wkład. Każdy autor wykonuje własną, realną pracę pod własnym kontem. Poniżej propozycje zadań; każde jest faktycznie do zrobienia w projekcie.

| Osoba | Gałąź | Zadanie |
|-------|-------|---------|
| Weronika Zator | `docs/literature-check` | Zweryfikować w źródłach cytowania i współczynniki z `docs/ANALIZA_MERYTORYCZNA.md` (sekcja 4) oraz `REFERENCES` w `core/report.py`; poprawić opisy |
| Weronika Zator | `docs/qgis-test` | Test z kroku 11, `docs/TEST_QGIS.md`, zrzuty ekranu |
| Kacper Mikołajczyk | `fix/docker-verification` | Poprawki z testu z kroku 10, zrzut panelu |
| Kacper Mikołajczyk | `refactor/kriging-split` | Podzielić `run_kriging` w `core/kriging.py` na mniejsze funkcje (1 odpowiedzialność) |
| Tomasz Szulski | `refactor/web-routes` | Rozbić `create_app` w `web/app.py` (trasy w osobne funkcje lub plik) |
| Tomasz Szulski | `test/real-scene` | Test na prawdziwej scenie Sentinel-2 (patrz sekcja sugestii) |
| Maciej Andrzejewski | `refactor/hydrology-scout` | Podzielić `compute_regional` i `run_scout` |
| Maciej Andrzejewski | `feature/release-workflow` | Automatyczne wydanie paczki wtyczki na GitHub Releases |

Procedura pracy nad zadaniem (dotyczy każdego):

```
git clone https://github.com/NAZWA-KONTA/ReAqua.git        (tylko za pierwszym razem)
cd ReAqua
git switch main
git pull
git switch -c docs/literature-check
```

Wprowadź zmiany, po każdej logicznej części:

```
git add docs/ANALIZA_MERYTORYCZNA.md
git commit -m "Verify Allen et al. 1998 coefficients and fix reference description"
```

Gdy skończysz:

```
git push -u origin docs/literature-check
```

Na GitHubie pojawi się baner "Compare & pull request". Kliknij go, w opisie wpisz co zmieniono i `Closes #NUMER` (numer zgłoszenia z tablicy), w Reviewers wybierz inną osobę z zespołu. Reviewer sprawdza zmiany (zakładka Files changed), zatwierdza (Review changes, Approve) i klika Merge. Zamknięcie zgłoszenia przesunie kartę do Done (krok 8).

Zasady, które spełniają punkty checklisty:
- Commitujcie często, małymi porcjami, przez cały semestr (2.2 Regularność).
- Komunikaty po angielsku w trybie rozkazującym lub po polsku opisowo; nigdy `update`, `fix`, `zmiany` bez dopowiedzenia, czego dotyczą (2.2 Opisowe wiadomości).
- Każdy autor ma commity w historii; kontrola: GitHub, Insights, Contributors (2.2 Zrównoważony wkład). Rozkład powinien być zbliżony.
- Jeśli pracujecie razem nad jedną zmianą, dopisz w komunikacie commita linię `Co-authored-by: Imię Nazwisko <adres@github>`, żeby oboje byli uwzględnieni.

Opcjonalnie zabezpiecz gałąź `main` (Settings, Branches, Add branch protection rule dla `main`): wymagaj pull requesta i przejścia CI przed scaleniem. Pokazuje to dojrzałość procesu.

## Krok 13. Kontrola końcowa wg checklisty (wszyscy, przed oddaniem)

Przejdźcie po punktach i odhaczcie je w arkuszu (arkusz Checklista). Dla każdego punktu poniżej jest sposób pokazania spełnienia.

| Punkt | Jak sprawdzić |
|-------|----------------|
| 1.1 Nazwa repozytorium | Nazwa `ReAqua` widoczna na stronie głównej |
| 1.1 Uprawnienia dostępu | Settings, Collaborators: wszyscy aktywni |
| 1.1 Opis projektu w README.md | README zawiera cel, problem, wymogi uruchomieniowe, instalację i użycie |
| 1.2 Struktura katalogów | `src/`, `data/`, `tests/`, `docs/` na stronie głównej |
| 1.2 Brak zbędnych plików | Brak `.vscode/`, `.idea/`, `.venv/`, dużych danych |
| 2.1 Kanban | Zakładka Projects, kolumny Todo, In Progress, Done z kartami |
| 2.1 Przypisanie zadań | Każda karta ma Assignees |
| 2.1 Aktualność harmonogramu | Karty przesuwane w miarę postępu, data ostatniej zmiany niedawna |
| 2.1 Gantt | `docs/HARMONOGRAM.md` i arkusz Gantt |
| 2.2 Regularność commitów | Insights, Commits: aktywność w wielu tygodniach, nie jeden dzień |
| 2.2 Opisowe komunikaty | `git log --oneline`: czytelne zdania |
| 2.2 Zrównoważony wkład | Insights, Contributors: wszyscy czterej, zbliżone liczby |
| 3.1 Nazwy, nazewnictwo | `flake8` zielony; brak nazw typu `a1`, `x` |
| 3.1 Jedna odpowiedzialność | Po refaktoryzacji z kroku 12 brak funkcji powyżej ok. 50 linii (sprawdź: `python - <<EOF ... ` lub przegląd kodu) |
| 3.1 Modularność | `core/`, `db/`, `web/`, `gui/` |
| 3.2 Komentarze, martwy kod | Przegląd: docstringi zamiast komentarzy, brak zakomentowanego kodu i `print` poza `cli.py` |
| 4.1 requirements.txt | Plik z wersjami w katalogu głównym |
| 4.1 Dockerfile, docker-compose | `docker compose up --build` działa (krok 10) |
| 5.1 Workflow, status | Actions: zielone `CI` |
| 6 Baza danych | `reaqua.gpkg` w QGIS lub panel; tabele `runs`, `reservoirs`, `metrics` |
| 6 Wizualizacja | Panel: wykresy i statystyki |
| 6 Pobieranie danych | Panel: linki GeoJSON, CSV, JSON; API |

Plan prezentacji (ok. 6 minut, sekcja 6 checklisty):
1. Problem w jednym zdaniu: gdzie zbudować małe zbiorniki, żeby łagodzić suszę rolniczą (30 s).
2. QGIS: prawy przycisk na rastrze, ReAqua, Pełna analiza, wynik na mapie (2 min).
3. Docker: `docker compose up`, panel WWW, wgranie sceny, pobranie GeoJSON (2 min).
4. Baza: pokazać `reaqua.gpkg` w QGIS lub tabele w panelu (30 s).
5. Proces: tablica Kanban, historia commitów, zielone Actions (1 min).

## Sugestie dopracowania

### Najważniejsze przed oddaniem

1. **Test na prawdziwych danych.** Dotychczas wszystko sprawdzono na scenie syntetycznej. Pobierz fragment sceny Sentinel-2 L2A (Copernicus Browser, https://browser.dataspace.copernicus.eu, bezpłatna rejestracja) dla obszaru z suszą, np. okolice Trzemeszna latem. Pasma B04, B08 (10 m), B11 (20 m) oraz SCL; przytnij do kilku kilometrów i pozostaw w układzie metrycznym (EPSG:32633 lub 2180). Uruchom analizę i sprawdź, czy wyniki są sensowne. To najlepszy dowód użyteczności, a ujawni problemy, których syntetyka nie pokaże.
2. **Weryfikacja źródeł i współczynników.** Cytowania w raporcie są oznaczone "do weryfikacji", a współczynniki (promienie wpływu, biomasa, obniżenie temperatury, węgiel) są założeniami roboczymi. Sprawdźcie je w literaturze albo napiszcie wprost w raporcie, że są założeniami. Nie przedstawiajcie ich jako wyników pomiarów.
3. **Refaktoryzacja długich funkcji** (3.1). Siedem funkcji ma ponad 50 linii; podział jest w kroku 12 i jest tani, a pomaga w ocenie.
4. **Realna historia pracy** (2.2). Najważniejszy element do poprawy; wymaga czasu, dlatego zacznijcie od razu.

### Dopracowanie techniczne

- **Wydania na GitHubie.** Workflow, który po otagowaniu wersji (`git tag v3.0.0`, `git push --tags`) dołącza `reaqua.zip` do GitHub Releases. Prowadząca i użytkownicy pobierają gotową wtyczkę jednym kliknięciem.
- **Pokrycie testów w README.** Znaczek pokrycia (np. Codecov). Większość modułów rdzenia ma pokrycie powyżej 90%, ale interfejs QGIS jest testowany tylko na atrapach, a gałąź GDAL w `core/io.py` nie jest w ogóle uruchamiana poza QGIS.
- **Testy GUI w prawdziwym QGIS na CI.** Obraz `qgis/qgis` pozwala uruchomić `pytest` z prawdziwym QGIS w workflow. Zamyka to największą lukę testową.
- **Dependabot** (`.github/dependabot.yml`) do aktualizacji zależności i `pre-commit` z `flake8`, żeby błędy stylu nie trafiały do repozytorium.
- **Typowanie** (`mypy`) w rdzeniu; zwiększa czytelność i bezpieczeństwo zmian.
- **Baza PostGIS jako osobna usługa** w `docker-compose.yml` zamiast pliku GeoPackage. Spełnia checklistę ("usługi, np. baza danych") dosłownie i pokazuje typowe wdrożenie. Kosztuje przepisanie warstwy `db/`; GeoPackage jest prostszy i też jest poprawną bazą, więc to opcja, nie wymóg.
- **Mapa w panelu** z podkładem (Leaflet) zamiast statycznego wykresu punktów. Wymaga zewnętrznych bibliotek lub kafli, więc rozważcie pracę offline.
- **Logowanie do panelu i HTTPS** (serwer pośredniczący, np. Caddy lub nginx), jeśli usługa miałaby być wystawiona publicznie. Obecnie jest tylko token wgrywania.
- **Podgląd wyniku w QGIS bez dodatkowych kroków:** zapis stylów warstw (`.qml`) do wyników i ich automatyczne stosowanie.

### Dopracowanie merytoryczne

- **Szereg czasowy** zamiast jednej sceny: kilka terminów w sezonie i wskaźnik anomalii (np. standaryzowany NDVI), co ogranicza błędy wynikające z fenologii i zbiorów.
- **Ograniczenia lokalizacji:** model terenu (nachylenie, zlewnia), własność działek, obszary chronione, odległość od cieków. Dziś lokalizacja wynika tylko z gęstości suszy.
- **Kalibracja promieni wpływu** na danych obserwacyjnych (np. wilgotność gleby z satelitów) zamiast stałych `k_moist` i `k_micro`.
- **Dopływ do zbiorników** (model zlewni), bo bilans wodny obejmuje dziś tylko magazyn, parowanie i przesiąkanie.
- **Niepewność:** zamiast trzech scenariuszy mnożnikowych zakresy wynikające z rozrzutu parametrów (analiza wrażliwości).
- **Walidacja** na istniejących zbiorniki retencyjnych w wybranym regionie: czy model wskazałby podobne miejsca.
- **Porównanie z wynikami hackathonu:** krótka tabela, jak zmieniły się liczby po poprawkach metodycznych i dlaczego (dobre uzasadnienie dla prowadzącej).

### Dokumentacja

- Zrzuty ekranu panelu i okna QGIS w README (`docs/img/`).
- `CONTRIBUTING.md` z zasadami nazewnictwa gałęzi i commitów, uzupełnione o opis procesu pull requestów.
- Krótki film lub animowany GIF demonstracyjny do README.

## Częste problemy z Gitem i GitHubem

| Objaw | Rozwiązanie |
|-------|-------------|
| `remote: Permission denied` przy push | Nie jesteś współpracownikiem lub zaproszenie nie zostało zaakceptowane (krok 3) |
| `fatal: not a git repository` | Jesteś poza folderem `ReAqua`; wykonaj `cd ReAqua` |
| `rejected ... fetch first` | Ktoś wypchnął zmiany: `git pull --rebase`, potem `git push` |
| Konflikt przy scalaniu | Otwórz oznaczony plik w VS Code, wybierz właściwą wersję (Accept), `git add plik`, `git commit` |
| `git push` prosi o hasło | GitHub nie akceptuje haseł; użyj Git Credential Manager (logowanie przez przeglądarkę) lub personal access token |
| Brak folderu `.github` w repozytorium | Folder był ukryty; włącz widoczność ukrytych plików, dodaj `git add .github`, commit, push |
| Actions czerwone | Otwórz zadanie, skopiuj komunikat błędu; typowo brakująca zależność lub błąd stylu `flake8` |
| Ostrzeżenie `LF will be replaced by CRLF` | Nieszkodliwe; ustawiono `core.autocrlf true` w kroku 0 |
