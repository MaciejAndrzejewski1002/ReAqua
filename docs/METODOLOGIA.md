# Metodologia

Szczegółowe stałe i ich status (założenie robocze / wymaga weryfikacji) są w `ANALIZA_MERYTORYCZNA.md`, sekcja 4.

## 1. Klasyfikacja suszy

Wskaźniki: NDVI = (NIR − RED)/(NIR + RED), NDMI = (NIR − SWIR)/(NIR + SWIR). Odbicie: Sentinel-2 (DN − 1000)/10000, Landsat C2 DN·2,75e-5 − 0,2.

Klasy (progi domyślne z prezentacji CASSINI): lekka NDVI ≤ 0,50, umiarkowana NDVI ≤ 0,30, silna NDVI ≤ 0,15 i NDMI < −0,20. Wartość 255 oznacza brak danych (woda, chmury, poza maską gruntów ornych, NaN). Dostępny jest też preset konserwatywny (0,35 / 0,20 / 0,05 / 0,00).

## 2. Lokalizacja zbiorników

1. Gęstość suszy: wagi klas (1, 2, 3) wygładzone filtrem gaussowskim (sigma 500 m) na rastrze o komórce 50 m.
2. Podział obszaru na strefy Z×Z (domyślnie 8×8); kwoty punktów proporcjonalne do ważonej powierzchni suszy, minimum jeden punkt na strefę.
3. Wybór zachłanny po malejącej gęstości z globalną odległością minimalną (domyślnie 1000 m); niewykorzystane kwoty trafiają do innych stref.
4. Wielkość zbiornika: stała (2 ha) lub proporcjonalna do suszy w oknie 500 m, z ograniczeniem min/max. Objętość = powierzchnia × głębokość (2 m). Koszt: roboty ziemne, uszczelnienie, budowle hydrotechniczne, dokumentacja; dla 2 ha 1,29–3,0 mln zł.

## 3. Zasięg oddziaływania

Promienie: wilgoć 80·√ha, mikroklimat 130·√ha·(1 + 0,4·v), mnożone przez współczynnik gleby. Model analityczny: kowariancja Gaussa C(h) = (1 − nugget)·exp(−3h²) z geometryczną anizotropią (oś główna zgodna z kierunkiem wiatru), waga = waga objętości × współczynnik klasy suszy.

Kriging: obserwacje to zbiorniki i stacje tła o wartości 0 poza zasięgiem. Wariant prosty (domyślny) lub zwyczajny, rozwiązanie LU na siatce zgrubnej (maks. 200 komórek) i interpolacja dwuliniowa do rozdzielczości rastra. Łączenie z modelem analitycznym: maksimum, średnia lub pojedyncze źródło. Ryzyko resztkowe = (klasa suszy / 3) × (1 − mitygacja), wartości 0–1.

Układ współrzędnych rastra musi być metryczny; dla układu geograficznego obliczenia są odrzucane z komunikatem.

## 4. Raport regionalny

- MCI: odsetek obszaru suszy w sumie buforów wilgoci. MEI: średnia mitygacja na obszarze suszy. HSRI = 1 − exp(−2,5·MCI/100). `retention_mm`: objętość zbiorników na powierzchnię regionu.
- Bilans wodny: magazyn (pojemność × liczba napełnień) − parowanie (kc · ET0 · powierzchnia) − przesiąkanie (współczynnik gleby); bez dopływu ze zlewni.
- Roślinność, bioróżnorodność, węgiel: trzy scenariusze (0,5×, 1×, 1,5×) współczynników roboczych.
- Ocena syntetyczna: cztery kryteria (MCI ≥ 25%, MEI ≥ 15%, ≥ 10 zbiorników, ≥ 500 tys. m³), neutralne sformułowanie, progi robocze.
- Opcjonalnie zwrot z pomocy suszowej: roczna oszczędność = pomoc × powierzchnia suszy w buforach wilgoci × częstość lat suszowych; okres zwrotu = koszt/oszczędność.
