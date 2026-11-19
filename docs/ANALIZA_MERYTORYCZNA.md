# Analiza merytoryczna projektu ReAqua

Dokument opisuje, co zostało sprawdzone w trzech wcześniejszych wtyczkach (Retention Scout v2, Retention Kriging v1, Retention Summary v2) i prezentacji z 11. CASSINI Hackathon, jakie nieścisłości znaleziono, jak je poprawiono w wersji 3.0.0 oraz które założenia pozostają niezweryfikowane.

## 1. Zakres

Wejście analizy: pasma Sentinel-2 L2A (B03, B04, B08, B11, opcjonalnie SCL) lub Landsat 8/9 Collection 2 Level 2, opcjonalna maska gruntów ornych. Łańcuch przetwarzania:

1. Scout: klasyfikacja suszy rolniczej (NDVI, NDMI), wybór lokalizacji zbiorników małej retencji.
2. Kriging: zasięg oddziaływania zbiorników i ryzyko resztkowe.
3. Raport: wskaźniki regionalne, bilans wodny, scenariusze roślinności, koszty, ocena syntetyczna.
4. Zapis wyników do bazy GeoPackage i udostępnienie w panelu WWW / API.

Trzy wtyczki wymieniały dane przez pliki i ręczne przepisywanie parametrów. W ReAqua mają wspólny rdzeń (`src/reaqua/core`), wspólną specyfikację parametrów (`core/params.py`) i jedno menu kontekstowe warstw.

## 2. Ustalenia i poprawki

Każde ustalenie zostało sprawdzone w kodzie oryginalnych wtyczek (`algorithm.py`, `kriging_engine.py`, `hydro_engine.py`, `report_generator.py`).

| Nr | Ustalenie w oryginale | Skutek | Poprawka w 3.0.0 |
|----|-----------------------|--------|------------------|
| 1 | NDBI liczone z NIR i SWIR jest równe −NDMI (`ndbi = (swir − nir)/(swir + nir)`). Scout stosuje filtr NDBI ≤ próg razem z warunkiem NDMI < próg. Przy progach z prezentacji (NDMI < −0,2, NDBI ≤ 0,2) warunki wykluczają się. | Klasa silnej suszy nigdy nie występuje; kolejne moduły dostają zaniżoną powierzchnię suszy. | Filtr NDBI domyślnie wyłączony i opisany w interfejsie. Zabudowę wyklucza maska gruntów ornych i SCL. Test: `test_ndbi_filter_makes_severe_class_impossible`. |
| 2 | Kriging odczytuje atrybut `pow_km2` ze Scouta (powierzchnia obszaru suszy w oknie) i przelicza go na `area_ha` zbiornika (`pow_km2 * 100`). | Mieszanie pojęć: powierzchnia suszy w oknie ≠ powierzchnia lustra wody. Promienie wpływu, objętość i koszty zależą od niewłaściwej wielkości. | Zbiornik ma własną powierzchnię (`area_ha`, domyślnie 2 ha, tryb stały lub proporcjonalny do suszy w oknie, z ograniczeniem min/max). Susza w oknie jest osobnym atrybutem `pow_susz_km2`. |
| 3 | Kriging zwyczajny (z mnożnikiem Lagrange'a) interpoluje wynik scenariuszowy z ok. 45 punktów. Poza zasięgiem zbiorników estymator wraca do średniej oszacowanej z tych punktów. | Mitygacja jest zawyżona z dala od zbiorników. Na scenie testowej OK dał MEI 29,9% wobec 9,1% dla krigingu prostego (ok. 3,4 raza więcej). | Zaimplementowano oba warianty (anizotropowa kowariancja Gaussa, rozwiązanie układu LU). Domyślny jest kriging prosty (średnia 0), który wygasa z odległością. Wybór jest widoczny w interfejsie. |
| 4 | Stacje tła losowane z dowolnych pikseli suszy (`drought >= min_class`), także w zasięgu zbiorników; wartość 0–0,05; ziarno zawsze 42. | Sprzeczne dane wejściowe krigingu i brak możliwości powtórzenia z innym losowaniem. | Stacje losowane poza zasięgiem anizotropowym (h ≥ 1,3), wartość 0, ziarno jako parametr. Testy: `test_background_stations_outside_reach`, `test_seed_changes_stations_and_is_reproducible`. |
| 5 | Scout zamienia NaN na klasę 0 („brak suszy”) i nie ma maski wody, chmur ani zabudowy. | Obszary bez danych, jeziora i miasta są traktowane jak teren bez suszy lub błędnie klasyfikowane. | Kod 255 jako brak danych; maska wody (MNDWI lub SCL=6), chmury i cienie (SCL), opcjonalna maska gruntów ornych. Powierzchnie liczone tylko z pikseli ważnych. |
| 6 | Wybór lokalizacji: kwoty stref proporcjonalne do suszy, ale najlepsze piksele wybierane w strefie bez uwzględnienia odległości; filtr odległości minimalnej działa dopiero po wyborze. | Po filtrze liczba punktów jest mniejsza niż przydział, a kwota strefy nie jest odtwarzana. | Wybór zachłanny z globalną odległością minimalną w trakcie wyboru i redystrybucją niewykorzystanych kwot. Obliczenia na rastrze zgrubnym (domyślnie 50 m). |
| 7 | Skalowanie odbicia: wyłącznie przeskalowanie 0–10000 → 0–1; brak offsetu radiometrycznego Sentinel-2 (baseline ≥ 04.00) i skali Landsat Collection 2. | Zniekształcone NDVI/NDMI dla nowszych scen i dla Landsata. | Sentinel: (DN − 1000)/10000 (przełącznik); Landsat: DN·2,75e-5 − 0,2. Dane już w odbiciu nie są skalowane ponownie. |
| 8 | Wskaźnik ARI (m² zbiorników na km² regionu) jest porównywany w ocenie syntetycznej z progami 2,0 i 5,0 bez uzasadnienia. | Kryterium zależy od jednostek i wielkości regionu; progi nie mają źródła. | ARI usunięty z oceny. Raport podaje `retention_mm` (objętość / powierzchnia regionu) w mm. Ocena ma 4 jawne kryteria z adnotacją, że progi są robocze. |
| 9 | Raport liczy powierzchnię suszy jako liczbę pikseli × (powierzchnia regionu wpisana ręcznie / liczba pikseli); bez rastra suszy przyjmuje 60% regionu jako suszę, 25% jako silną i 50% jako umiarkowaną. | Wynik zależy od ręcznie wpisanej powierzchni; bez rastra raport używa liczb zmyślonych. | Powierzchnia z geometrii rastra (rozmiar piksela), ręczna wartość tylko jako jawne nadpisanie. Brak rastra suszy = błąd, nie wartości domyślne. |
| 10 | Wskaźniki roślinności, bioróżnorodności i węgla podawane jako pojedyncze liczby. | Pozorna precyzja przy niekalibrowanych współczynnikach. | Trzy scenariusze (0,5×, 1×, 1,5×). Dla trwałych użytków cena plonu = 0, więc korzyść produkcyjna = 0. |
| 11 | Raport HTML importuje czcionki z `fonts.googleapis.com`; wartości tekstowe nie są escapowane. | Raport nie działa offline; ryzyko wstrzyknięcia HTML przez nazwę regionu. | Samodzielny HTML z wbudowanymi wykresami SVG, escapowanie wszystkich wartości. Test: `test_report_is_self_contained_and_escaped`. |
| 12 | Obliczenia uruchamiane w wątku interfejsu (`dlg.exec_()`), bez zadań w tle. | Zawieszanie QGIS przy większych scenach. | Zadania w tle (`QgsTask`), pasek postępu i dziennik w oknie dialogowym. |

Bilans wodny w oryginale (magazyn − parowanie − przesiąkanie) był poprawny koncepcyjnie. W ReAqua dodano liczbę napełnień w roku i jawną adnotację, że dopływ ze zlewni nie jest modelowany.

## 3. Dodane elementy

- Jedna wtyczka z menu kontekstowym warstw: dla rastra „Pełna analiza”, „Scout”, „Kriging jako raster suszy”, „Raport jako raster suszy”; dla warstwy punktowej „Kriging jako zbiorniki”, „Raport jako zbiorniki”. Te same polecenia są w menu „ReAqua” i na pasku narzędzi.
- Rdzeń niezależny od QGIS (numpy/scipy), z dwoma backendami rastrowymi: `osgeo.gdal` w QGIS, `rasterio` + `pyproj` w CLI, Dockerze i CI.
- Baza wyników GeoPackage (OGC) z tabelami `runs`, `reservoirs`, `metrics`; plik czytany przez GDAL i QGIS.
- Panel WWW (Flask) i API REST: `/health`, `/api/runs`, `/api/stats`, `/api/reservoirs?format=json|geojson|csv`.
- CLI: `python -m reaqua demo | run | serve | export | params`.
- Generator scen syntetycznych oraz przykładowe dane w `data/sample` (840 KB).
- Pakiet testów (53 testy), Dockerfile, docker-compose, GitHub Actions, dokumentacja.

## 4. Założenia niezweryfikowane

Poniższe stałe są **roboczymi założeniami zespołu**, nie wynikami kalibracji ani cytowaniem normy. Są dostępne jako parametry tam, gdzie to możliwe, a raport zawiera ich listę.

| Założenie | Wartość | Uwagi |
|-----------|---------|-------|
| Promień wilgoci / mikroklimatu | 80 / 130 m na √ha, mnożniki gleby 0,70–1,30, wiatr 1 + 0,4·v (do 8 m/s) | Z prezentacji, bez kalibracji terenowej. |
| Waga objętości zbiornika | min(1; 0,3 + 0,1·log10 V) | Kształt arbitralny. |
| Współczynnik klasy suszy | 1 + 0,25·(klasa − 1) | Arbitralny. |
| ΔNDVI | 0,06 + 0,04·log10(V/10 000) + 0,015·min(MCI/25; 2) | Zakres 0,01–0,25. |
| Biomasa na 0,1 NDVI | 3,2 t/ha | Do weryfikacji. |
| Obniżenie temperatury | maks. 1,5 °C | Do weryfikacji w literaturze. |
| Węgiel | 2,5 (mokradło) / 0,15 (rolnictwo) t CO2/ha/rok | Do weryfikacji. |
| Kryteria oceny | MCI ≥ 25%, MEI ≥ 15%, ≥ 10 zbiorników, ≥ 500 tys. m³ | Progi robocze. |
| Ceny plonów | pszenica 800, kukurydza 750, rzepak 1800, ziemniaki 600 zł/t | Do aktualizacji przez użytkownika. |
| Koszty jednostkowe | roboty ziemne 15–30 zł/m², uszczelnienie 40–90 zł/m², budowle 150–500 tys. zł, dokumentacja 40–100 tys. zł | Z prezentacji; zbiornik 2 ha: 1,29–3,0 mln zł. |

Przywołane w raporcie pozycje literatury (Allen i in. 1998; Puma i Cook 2010; Hesslerová i in. 2013) są oznaczone „do weryfikacji”: odtworzone z pamięci, nie sprawdzone w źródłach. Przed złożeniem projektu należy sprawdzić ich zasadność i wartości liczbowe.

## 5. Weryfikacja

- Testy jednostkowe i integracyjne (pytest): indeksy i klasyfikacja, wybór lokalizacji, kriging, hydrologia i koszty, raport, baza, API, CLI, metadane i autorzy, rejestracja akcji w menu kontekstowym (na atrapach modułów QGIS).
- Baza GeoPackage ma poprawny `application_id`, nagłówki geometrii i jest odczytywana przez GDAL (`pyogrio.read_info`).
- Cały przebieg `demo` uruchomiony na scenie syntetycznej, API sprawdzone przez gunicorn.

Nie zweryfikowano: działania interfejsu graficznego w prawdziwym QGIS (brak QGIS w środowisku budowania), gałęzi `osgeo.gdal`, budowy obrazu Docker (brak demona). Wymaga to krótkiego testu ręcznego (patrz `docs/CHECKLISTA.md`).

## 6. Ograniczenia modelu

- Jedna scena, bez analizy wielookresowej; niski NDVI może wynikać z fenologii lub zbiorów.
- Kriging dotyczy pola scenariuszowego (zbiorniki = źródła, stacje tła = 0), nie pomiarów wilgotności gleby.
- Brak modelu zlewni i odpływu; brak uwzględnienia istniejących zbiorników i ograniczeń prawnych (własność, Natura 2000, nachylenie terenu).
- Wyniki liczbowe różnią się od wartości z prezentacji hackathonowej, ponieważ poprawiono błędy z tabeli powyżej.

## 7. Kierunki rozwoju

Seria czasowa NDVI/NDMI i wskaźniki standaryzowane, dane glebowe i NMT do ograniczeń lokalizacji, kalibracja promieni wpływu na danych SMAP/Sentinel-1, model zlewni i dopływu, walidacja na rzeczywistych zbiornikach.
