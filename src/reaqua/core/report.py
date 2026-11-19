"""Self-contained HTML report (no external fonts, scripts or images)."""

import datetime
from html import escape

from .. import __authors__, __version__
from . import charts, physics

CSS = """
:root{--ink:#1b2a35;--muted:#5d6d7a;--line:#d7dee3;--accent:#1f6f8b;--bg:#f6f8fa;--warn:#a04000}
*{box-sizing:border-box}body{margin:0;font:15px/1.55 system-ui,-apple-system,"Segoe UI",Roboto,Arial,sans-serif;
color:var(--ink);background:var(--bg)}main{max-width:980px;margin:0 auto;padding:28px 20px 60px}
h1{font-size:26px;margin:0 0 4px}h2{font-size:19px;margin:34px 0 10px;padding-bottom:6px;
border-bottom:2px solid var(--accent)}h3{font-size:15px;margin:18px 0 6px}
.meta{color:var(--muted);font-size:13px}.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));
gap:10px;margin:16px 0}.card{background:#fff;border:1px solid var(--line);border-radius:6px;padding:12px}
.card b{display:block;font-size:21px}.card span{font-size:12px;color:var(--muted)}
table{width:100%;border-collapse:collapse;background:#fff;font-size:13.5px;margin:8px 0}
th,td{border:1px solid var(--line);padding:6px 9px;text-align:left}th{background:#eaf1f4}
td.n{text-align:right;font-variant-numeric:tabular-nums}.note{background:#fff7ec;border-left:4px solid var(--warn);
padding:10px 14px;margin:12px 0;font-size:13.5px}.ok{color:#1e7b34}.no{color:var(--warn)}
.charts{display:grid;grid-template-columns:repeat(auto-fit,minmax(320px,1fr));gap:14px}
svg.chart{width:100%;height:auto;background:#fff;border:1px solid var(--line);border-radius:6px;padding:6px}
footer{margin-top:40px;color:var(--muted);font-size:12.5px}@media print{body{background:#fff}.card{break-inside:avoid}}
"""

LIMITATIONS = (
    "Klasyfikacja suszy opiera się na jednej scenie satelitarnej; niski NDVI może wynikać także z fenologii, "
    "zbiorów lub odsłoniętej gleby. Wynik należy interpretować w sezonie wegetacyjnym i z maską gruntów ornych.",
    "Wpływ zbiorników (promienie wilgoci i mikroklimatu, wagi, ΔNDVI, biomasa, ceny) to założenia robocze, "
    "niekalibrowane pomiarami terenowymi. Wartości niskie i wysokie przedstawiają zakres niepewności, nie przedział ufności.",
    "Kriging dotyczy pola scenariuszowego (zbiorniki = źródła, stacje tła = 0), a nie pomiarów wilgotności gleby.",
    "Bilans wodny nie uwzględnia dopływu ze zlewni; podano pojemność, parowanie i przesiąkanie.",
    "Koszty wynikają z przedziałów jednostkowych z prezentacji CASSINI i nie zastępują kosztorysu inwestorskiego.",
    "Progi MCI, MEI, liczby zbiorników i pojemności w ocenie syntetycznej są wartościami roboczymi zespołu.",
)

REFERENCES = (
    "Allen R.G. i in. (1998), FAO Irrigation and Drainage Paper 56 - ET0 (do weryfikacji zastosowanych współczynników).",
    "Puma M.J., Cook B.I. (2010), wpływ nawadniania na klimat - ogólna podstawa efektu chłodzenia (do weryfikacji).",
    "Hesslerová P. i in. (2013), chłodzący wpływ obszarów wodno-błotnych - podstawa rzędu wielkości (do weryfikacji).",
    "Dane: Copernicus Sentinel-2 L2A; Landsat Collection 2 Level 2 (USGS).",
)


def _n(value, digits: int = 0) -> str:
    if value is None:
        return "-"
    return f"{value:,.{digits}f}".replace(",", " ")


def _row(label: str, value: str, unit: str = "") -> str:
    return f"<tr><th>{escape(label)}</th><td class='n'>{value} {escape(unit)}</td></tr>"


def _card(value: str, label: str) -> str:
    return f"<div class='card'><b>{value}</b><span>{escape(label)}</span></div>"


def _vegetation_table(veg: dict) -> str:
    rows = [
        ("Przyrost NDVI (ΔNDVI)", "delta_ndvi", 3, ""),
        ("Wskaźnik poprawy roślinności VII", "vii_pct", 2, "%"),
        ("Biomasa wspierana SBI", "sbi_t_yr", 0, "t/rok"),
        ("Korzyść produkcyjna CBI", "cbi_pln_yr", 0, "PLN/rok"),
        ("Średnie obniżenie temperatury", "mean_temp_reduction_c", 3, "°C"),
        ("Wskaźnik bioróżnorodności BSI", "bsi", 1, ""),
        ("Sekwestracja węgla CSI", "csi_t_co2_yr", 0, "t CO₂/rok"),
    ]
    head = "<tr><th>Wskaźnik</th><th>Niski</th><th>Bazowy</th><th>Wysoki</th><th>Jednostka</th></tr>"
    body = "".join(
        f"<tr><th>{escape(label)}</th>"
        + "".join(f"<td class='n'>{_n(veg[s][key], d)}</td>" for s in ("low", "base", "high"))
        + f"<td>{escape(unit)}</td></tr>"
        for label, key, d, unit in rows
    )
    return f"<table>{head}{body}</table>"


def generate_html(result: dict, region_label: str = "Obszar badań", params: dict = None) -> str:
    r = result
    bal, veg, cost = r["balance"], r["vegetation"], r["cost"]
    ver = r["verdict"]
    reservoirs = r["per_reservoir"]
    soil_label = physics.soil(r["soil"])["label"]
    wind_label = physics.WIND_LABELS.get(r["wind_direction"], r["wind_direction"])

    cards = "".join([
        _card(_n(r["n_reservoirs"]), "proponowane zbiorniki"),
        _card(_n(r["total_area_ha"], 1) + " ha", "łączna powierzchnia lustra"),
        _card(_n(r["total_volume_m3"] / 1000) + " tys. m³", "łączna pojemność"),
        _card(f"{r['mci']:.1f}%", "pokrycie suszy buforem wilgoci (MCI)"),
        _card(f"{r['mei']:.1f}%", "średnia mitygacja na obszarze suszy (MEI)"),
        _card(f"{cost['min'] / 1e6:.1f}-{cost['max'] / 1e6:.1f} mln zł", "szacunkowy koszt budowy"),
    ])

    top = reservoirs[:15]
    chart_cost = charts.bar_chart([f"P{x['priority']}" for x in top], [x["cost_mid_pln"] for x in top],
                                  "Koszt średni zbiornika według priorytetu", "zł")
    chart_vol = charts.bar_chart([f"P{x['priority']}" for x in top], [x["volume_m3"] for x in top],
                                 "Pojemność zbiornika według priorytetu", "m³", color=charts.PALETTE["bar2"])
    max_area = max((x["area_ha"] for x in reservoirs), default=1) or 1
    chart_map = charts.point_map([(x["lon"], x["lat"], x["priority"], x["area_ha"] / max_area)
                                  for x in reservoirs], "Rozmieszczenie zbiorników (WGS 84)")

    criteria = "".join(
        f"<li class='{'ok' if c['ok'] else 'no'}'>{'spełnione' if c['ok'] else 'niespełnione'}: {escape(c['text'])}</li>"
        for c in ver["criteria"]
    )
    table_rows = "".join(
        f"<tr><td class='n'>{x['priority']}</td><td class='n'>{x['drought_class']}</td><td class='n'>{x['area_ha']}</td>"
        f"<td class='n'>{_n(x['volume_m3'])}</td><td class='n'>{_n(x['r_moist_m'])}</td>"
        f"<td class='n'>{_n(x['r_micro_m'])}</td><td class='n'>{_n(x['evaporation_m3'])}</td>"
        f"<td class='n'>{_n(x['cost_mid_pln'])}</td></tr>"
        for x in reservoirs
    )
    savings = ""
    if r.get("savings"):
        s = r["savings"]
        savings = (_row("Roczna oszacowana oszczędność pomocy suszowej", _n(s["annual_pln"]), "PLN")
                   + _row("Prosty czas zwrotu", _n(s["payback_years"], 1) if s["payback_years"] else "-", "lat"))
    note_mit = f"Powierzchnia mitygacji pochodzi z: {escape(r['mitigation_source'])}."
    generated = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

    return f"""<!DOCTYPE html>
<html lang="pl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>ReAqua - raport regionalny: {escape(region_label)}</title><style>{CSS}</style></head><body><main>
<h1>ReAqua - raport regionalny</h1>
<div class="meta">{escape(region_label)} &middot; wygenerowano {generated} &middot; ReAqua {__version__}
&middot; powierzchnia analizy {_n(r['region_km2'], 1)} km² &middot; gleba: {escape(soil_label)}
&middot; wiatr: {escape(wind_label)}, {r['wind_speed_ms']} m/s</div>
<div class="cards">{cards}</div>
<div class="note">Wyniki są oszacowaniem scenariuszowym opartym na założeniach roboczych. {note_mit}
Szczegóły i ograniczenia opisano w sekcji końcowej.</div>

<h2>1. Rozmieszczenie i koszty</h2>
<div class="charts">{chart_map}{chart_cost}{chart_vol}</div>

<h2>2. Susza i zasięg oddziaływania</h2>
<table>
{_row("Obszar suszy (klasy 1-3)", _n(r["drought_ha"], 1), "ha")}
{_row("w tym umiarkowana i silna", _n(r["mod_sev_ha"], 1), "ha")}
{_row("w tym silna", _n(r["severe_ha"], 1), "ha")}
{_row("Bufor wilgoci (suma)", _n(r["moist_ha"], 1), "ha")}
{_row("Bufor mikroklimatu (suma)", _n(r["micro_ha"], 1), "ha")}
{_row("Bufor wilgoci na obszarze suszy", _n(r["moist_in_drought_ha"], 1), "ha")}
{_row("Obszar wspierany rolniczo na obszarze suszy (ASA)", _n(r["asa_drought_ha"], 1), "ha")}
{_row("Wskaźnik pokrycia suszy MCI", _n(r["mci"], 1), "%")}
{_row("Wskaźnik skuteczności mitygacji MEI", _n(r["mei"], 1), "%")}
{_row("Udział obszaru suszy z mitygacją > 20%", _n(r["coverage_pct"], 1), "%")}
{_row("Średnia klasa suszy przed / po", f"{r['dr_before']:.2f} / {r['dr_after']:.2f}")}
{_row("Redukcja klasy suszy", _n(r["dr_reduction_pct"], 1), "%")}
{_row("Powierzchnia lustra zbiorników na km² regionu (ARI)", _n(r["ari"], 0), "m²/km²")}
{_row("Pojemność retencyjna w przeliczeniu na warstwę wody", _n(r["retention_mm"], 2), "mm")}
{_row("Pomocniczy wskaźnik HSRI", _n(r["hsri"], 1), "%")}
</table>

<h2>3. Bilans wodny (roczny, bez dopływu ze zlewni)</h2>
<table>
{_row("Zmagazynowana woda", _n(bal["stored_m3"]), "m³")}
{_row("Parowanie z lustra", _n(bal["evaporation_m3"]), "m³")}
{_row("Przesiąkanie (udział " + f"{bal['seepage_fraction']:.2f})", _n(bal["seepage_m3"]), "m³")}
{_row("Woda netto do wykorzystania", _n(bal["net_usable_m3"]), "m³")}
</table>

<h2>4. Roślinność i korzyści środowiskowe (scenariusze)</h2>
<p>Uprawa dominująca: {escape(r['crop'])}, cena {_n(r['crop_price_pln_t'])} PLN/t. Zakres: niski = 0,5×, wysoki = 1,5× efekt bazowy.</p>
{_vegetation_table(veg)}

<h2>5. Koszty</h2>
<table>
{_row("Koszt minimalny", _n(cost["min"]), "PLN")}
{_row("Koszt średni", _n(cost["mid"]), "PLN")}
{_row("Koszt maksymalny", _n(cost["max"]), "PLN")}
{_row("Koszt średni na ha obszaru suszy objętego buforem wilgoci", _n(r["cost_per_ha_pln"]), "PLN/ha")}
{savings}
</table>

<h2>6. Zbiorniki</h2>
<table><tr><th>Priorytet</th><th>Klasa suszy</th><th>Powierzchnia [ha]</th><th>Pojemność [m³]</th>
<th>R wilgoci [m]</th><th>R mikroklimatu [m]</th><th>Parowanie [m³/rok]</th><th>Koszt średni [PLN]</th></tr>
{table_rows}</table>

<h2>7. Ocena syntetyczna</h2>
<p>Spełnione kryteria: <b>{ver['passed']} z {ver['total']}</b>.</p><ul>{criteria}</ul>
<p class="meta">{escape(ver['note'])}</p>

<h2>8. Założenia i ograniczenia</h2>
<ul>{''.join(f'<li>{escape(x)}</li>' for x in LIMITATIONS)}</ul>
<h3>Podstawy metodyczne (wymagają weryfikacji w źródłach)</h3>
<ul>{''.join(f'<li>{escape(x)}</li>' for x in REFERENCES)}</ul>

<footer>Autorzy: {escape(', '.join(__authors__))}. Projekt geoinformatyczny - ReAqua (CASSINI Hackathon, zespół Hydronauts).</footer>
</main></body></html>"""


def write_html(path: str, result: dict, region_label: str = "Obszar badań", params: dict = None) -> str:
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(generate_html(result, region_label, params))
    return path
