# Docker w projekcie ReAqua

## Po co Docker w tym projekcie

Wtyczka QGIS jest narzędziem analityka. Docker dodaje drugą ścieżkę użycia: usługę, z której korzystają osoby bez QGIS. Użytkownik otwiera stronę, wgrywa pasma satelitarne, a analiza wykonuje się na serwerze w tle. Wyniki (rastry GeoTIFF, raport HTML, punkty zbiorników w GeoJSON/CSV) pobiera z przeglądarki. Usługa wykonuje dokładnie ten sam kod co wtyczka, w tej samej wersji bibliotek, więc wyniki są powtarzalne.

## Architektura: trzy kontenery z jednego obrazu

```
przeglądarka ──> web ──(zapisuje scenę)──> /data/inbox ──(czyta)──> worker
                  │                                                   │
                  └──(czyta wyniki)──> /data/reaqua.gpkg <──(zapisuje)┘
                                        /data/output (rastry, raport)
```

| Usługa | Zadanie |
|--------|---------|
| `seed` | jednorazowo wypełnia bazę danymi demonstracyjnymi (`python -m reaqua demo --if-empty`), żeby panel nie był pusty; po zakończeniu się zatrzymuje |
| `web` | panel WWW i API: formularz wgrywania scen, status przetwarzania, pobieranie wyników; port 8000 |
| `worker` | w pętli sprawdza `/data/inbox`, analizuje nowe sceny (Scout, Kriging, Raport) i zapisuje wyniki do bazy i do `/data/output` |

Web przyjmuje pliki szybko i od razu odpowiada, a ciężkie obliczenia robi osobny kontener. Dzięki temu strona nie zawiesza się podczas analizy, a `worker` można zatrzymać lub zrestartować bez utraty kolejki: scena w stanie `running` po restarcie wraca do kolejki.

Wolumen `reaqua-data` jest wspólny dla wszystkich usług i przechowuje bazę, kolejkę scen i wyniki także po zatrzymaniu kontenerów.

## Gdzie to jest w repozytorium

Pliki Docker leżą w katalogu głównym, obok `README.md`:

| Plik | Rola |
|------|------|
| `Dockerfile` | przepis na obraz: system bazowy, katalog roboczy, kopiowanie plików, komenda startowa |
| `docker-compose.yml` | uruchamia usługi `seed`, `worker`, `web`, ustawia porty, zmienne i wolumen |
| `.dockerignore` | pliki, których nie kopiować do obrazu |
| `requirements.txt` | biblioteki instalowane w obrazie |

Kod kolejki to `src/reaqua/inbox.py`, trasy wgrywania to `src/reaqua/web/scenes.py`.

## Dockerfile

| Instrukcja | Znaczenie |
|------------|-----------|
| `FROM python:3.13-slim` | obraz bazowy: lekki Linux z Pythonem 3.13 |
| `ENV ...` | zmienne środowiskowe: ścieżki bazy (`REAQUA_DB`), kolejki (`REAQUA_INBOX`) i wyników (`REAQUA_OUTPUT`) |
| `WORKDIR /app` | katalog roboczy w kontenerze |
| `COPY requirements.txt .` i `RUN pip install ...` | instalacja bibliotek (osobna warstwa, więc przebudowa jest szybka) |
| `COPY src ./src`, `COPY data ./data` | kod i dane przykładowe |
| `USER reaqua` | działanie bez uprawnień administratora |
| `EXPOSE 8000` | port serwera WWW |
| `CMD [...]` | domyślna komenda: serwer `gunicorn` z aplikacją `reaqua.web.app:create_app()` |

## Jak uruchomić

1. Zainstaluj Docker Desktop (Windows, macOS) lub Docker Engine z Compose (Linux) i uruchom go.
2. W katalogu repozytorium wykonaj:

```
docker compose up --build
```

3. Poczekaj, aż `seed` zakończy pracę, i otwórz http://localhost:8000. Zobaczysz wyniki demonstracyjne.
4. Zatrzymanie: `Ctrl+C`, potem `docker compose down`. Usunięcie wszystkich danych: `docker compose down -v`.

## Jak przeanalizować własną scenę

W panelu, sekcja "Nowa analiza": wskaż pliki pasm (B04, B08, B11 wymagane; B03, SCL i maska opcjonalne), wpisz nazwę obszaru, wybierz parametry i kliknij "Uruchom analizę". Zostaniesz przeniesiony na stronę sceny, która odświeża się co 5 sekund. Po zakończeniu pojawią się linki do panelu wyników tej analizy oraz do plików do pobrania (`susza.tif`, `mitygacja_suszy.tif`, `ryzyko_resztkowe.tif`, `raport_regionalny.html`, `zbiorniki.geojson`, `zbiorniki.csv`). Rastry otwierają się w QGIS.

Do wypróbowania użyj plików z `data/sample/` (B04, B08, B11). Pasma muszą być w jednym metrycznym układzie współrzędnych (np. EPSG:32633).

Z linii poleceń to samo wykonuje API:

```
curl -F red=@B04.tif -F nir=@B08.tif -F swir=@B11.tif -F label="Gmina Trzemeszno" \
     -F param_max_points=15 http://localhost:8000/api/scenes
curl http://localhost:8000/api/scenes/<id>
```

Sceny można też dodać z folderu: `docker compose run --rm -v "$PWD/dane:/dane" web python -m reaqua submit --folder /dane --inbox /data/inbox`. Worker podejmie je automatycznie.

## Konfiguracja

| Zmienna | Znaczenie | Domyślnie |
|---------|-----------|-----------|
| `REAQUA_UPLOAD_TOKEN` | jeśli ustawiona, wgrywanie scen wymaga tego tokenu (pole formularza lub nagłówek `X-Token`) | brak |
| `REAQUA_MAX_UPLOAD_MB` | maksymalny rozmiar jednego wgrania | 500 |
| `REAQUA_DB`, `REAQUA_INBOX`, `REAQUA_OUTPUT` | ścieżki w kontenerze | `/data/...` |

Przykład z tokenem: `REAQUA_UPLOAD_TOKEN=haslo docker compose up --build`.

## Bezpieczeństwo i ograniczenia

- Panel nie ma logowania. Token chroni tylko wgrywanie. Nie wystawiaj usługi do internetu bez zabezpieczenia (serwer pośredniczący z HTTPS, ograniczenie dostępu).
- Wgrywane pliki są sprawdzane pod kątem formatu TIFF, identyfikatory scen są walidowane, a pobierać można tylko pliki z listy wyników.
- Jeden kontener `worker` przetwarza sceny po kolei. Uruchomienie kilku workerów na tym samym wolumenie jest zabezpieczone blokadą sceny, ale nie było testowane pod obciążeniem.
- Duże sceny (pełne kafle Sentinel-2) wymagają dużo pamięci; do testów używaj wycinków.

## Częste problemy

- `Cannot connect to the Docker daemon`: Docker nie jest uruchomiony.
- Port 8000 zajęty: zmień w `docker-compose.yml` `"8000:8000"` na np. `"8080:8000"`.
- Scena stale w stanie `queued`: sprawdź kontener worker (`docker compose logs worker`).
- Scena w stanie `error`: komunikat błędu jest na stronie sceny; typowe przyczyny to różne układy współrzędnych pasm lub układ geograficzny (stopnie) zamiast metrycznego.
