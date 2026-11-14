# climate_data

Wetter- und Standortdaten für **ein** Feld: `ks-kearny-01`, Kearny County, Kansas (38,02511° N / -101,126084° E, 916 m).
Zeitraum **1991-01-01 bis 2025-12-31**, Tageswerte, keine Lücken in den Rohdaten.

| Datei | Inhalt | Zeilen |
|---|---|---|
| `power_daily_long.csv` | Tägliche Wetterdaten (NASA POWER), bereinigt | 127.840 |
| `features_daily_long.csv` | Abgeleitete Tages-Features (Verdunstung, Wasserbilanz, Gradtage, ...) | 204.544 |
| `features_annual_long.csv` | Agroklimatische Kennzahlen pro Jahr | 630 |
| `field_profile.json` | Statisches Feldprofil: Lage, Gelände, Boden, Randbedingungen | – |

**Format (Long):** eine Zeile = ein Wert. Spalten `lat, lon, date | year, parameter, value, unit`. Fehlend ist `NaN`.
Zum Pivotieren: `df.pivot(index="date", columns="parameter", values="value")`.

---

## `power_daily_long.csv` (Quelle: NASA POWER, Raster ca. 50 km)

| parameter | Einheit | Bedeutung |
|---|---|---|
| `air_temperature_max` / `_mean` / `_min` | °C | Tageshöchst-, Tagesmittel-, Tagestiefsttemperatur in 2 m |
| `precipitation` | mm/day | Niederschlag (korrigiert) |
| `relative_humidity` | % | relative Luftfeuchte in 2 m |
| `wind_speed` | m/s | Windgeschwindigkeit in 2 m |
| `solar_radiation` | MJ/m²/day | kurzwellige Einstrahlung an der Oberfläche (Wolken eingerechnet) |
| `soil_wetness_root_zone` | 0–1 | Bodenfeuchte Wurzelzone, 0 = trocken, 1 = gesättigt (Modellwert, grob aufgelöst) |
| `soil_wetness_surface` | 0–1 | Bodenfeuchte Oberfläche, gleiche Skala |
| `evapotranspiration` | MJ/m²/day (laut POWER) | Verdunstung aus POWER. **Einheit unsicher**, die Werte wirken wie mm/day. Besser `reference_evapotranspiration` nutzen. |

---

## `features_daily_long.csv` (abgeleitet aus POWER, Spalte `date`)

| parameter | Einheit | Bedeutung |
|---|---|---|
| `reference_evapotranspiration` | mm/day | Referenzverdunstung nach FAO-56 Penman-Monteith (Wasserbedarf einer Referenz-Grasfläche) |
| `water_balance` | mm/day | Niederschlag minus Referenzverdunstung (negativ = Defizit) |
| `air_temperature_range` | °C | Tmax minus Tmin |
| `vapor_pressure_deficit` | kPa | Dampfdruckdefizit, wie "durstig" die Luft ist |
| `growing_degree_days_base_10` | °C·Tag | Wachstumsgradtage, Basis 10 °C, Temperaturen auf 10–30 °C begrenzt |
| `growing_degree_days_base_0` | °C·Tag | Gradtage, Basis 0 °C (z. B. Winterweizen) |
| `growing_degree_days_base_10_cumulative` | °C·Tag | Summe der Gradtage (Basis 10) seit 1. Januar, setzt sich jedes Jahr zurück |
| `dry_spell_length` | Tage | aktuelle Länge der Trockenperiode (aufeinanderfolgende Tage mit < 1 mm) |
| `precipitation_sum_30d` / `_90d` | mm | Niederschlagssumme der letzten 30 / 90 Tage |
| `water_balance_sum_30d` / `_90d` | mm | Summe der Wasserbilanz der letzten 30 / 90 Tage |
| `heat_days_count_30d` | Tage | Anzahl Tage mit Tmax ≥ 35 °C in den letzten 30 Tagen |
| `air_temperature_mean_anomaly` | °C | Abweichung der Tagesmitteltemperatur vom Mittel 1991–2020 |
| `precipitation_sum_30d_anomaly` | mm | Abweichung der 30-Tage-Niederschlagssumme vom Mittel 1991–2020 |
| `water_balance_sum_90d_anomaly` | mm | Abweichung der 90-Tage-Wasserbilanz vom Mittel 1991–2020 |

Fenster-Features (`*_30d`, `*_90d`) sind in den ersten 29 bzw. 89 Tagen `NaN`. Anomalien beziehen sich auf eine geglättete Tages-Klimatologie 1991–2020 (±7 Tage).

---

## `features_annual_long.csv` (abgeleitet aus POWER, Spalte `year`)

| parameter | Einheit | Bedeutung |
|---|---|---|
| `air_temperature_mean_annual` | °C | Jahresmitteltemperatur |
| `air_temperature_mean_jun_aug` | °C | Sommermitteltemperatur (Juni–August) |
| `precipitation_total` | mm | Jahresniederschlag |
| `precipitation_apr_sep` | mm | Niederschlag in der Vegetationszeit (April–September) |
| `precipitation_max_1d` | mm | höchster Tagesniederschlag des Jahres |
| `wet_days_ge_1mm` | Tage | Tage mit ≥ 1 mm Niederschlag |
| `heavy_rain_days_ge_25mm` | Tage | Tage mit ≥ 25 mm Niederschlag (Starkregen) |
| `max_dry_spell_apr_sep` | Tage | längste Trockenperiode (< 1 mm) in April–September; die Periode kann schon vor April begonnen haben |
| `reference_evapotranspiration_apr_sep` | mm | Referenzverdunstung April–September |
| `water_balance_apr_sep` | mm | Niederschlag minus Referenzverdunstung, April–September |
| `aridity_index` | – | Jahresniederschlag / Referenzverdunstung (unter 0,5 = semiarid) |
| `growing_degree_days_base_10_apr_sep` | °C·Tag | Gradtage (Basis 10) April–September |
| `frost_days` | Tage | Tage mit Tmin < 0 °C |
| `last_spring_frost_doy` | Tag im Jahr | letzter Frost (Tmin < 0 °C) bis 30. Juni |
| `first_fall_frost_doy` | Tag im Jahr | erster Frost ab 1. Juli |
| `frost_free_days` | Tage | erster Herbstfrost minus letzter Frühjahrsfrost |
| `heat_days_ge_32` / `heat_days_ge_35` | Tage | Tage mit Tmax ≥ 32 °C / ≥ 35 °C |

---

## `field_profile.json` (Schema 0.2)

| Block | Inhalt |
|---|---|
| `field_id`, `location` | Feld-ID, Koordinaten, Bundesstaat, County (Kearny, FIPS 20093); `area_ha` ist `null` (unbekannt) |
| `terrain` | `elevation_m` (916), `slope_pct` (0,55) |
| `soil` | Boden aus USDA SSURGO: Textur (`silty clay loam`), `water_capacity_mm` (nutzbares Wasser 0–100 cm, 183), `organic_matter_pct`, `clay_pct`/`silt_pct`/`sand_pct`, `ph` (jeweils 0–30 cm gewichtet), `bulk_density_g_cm3`, hydrologische Gruppe, Drainage, Bewässerungs-Eignungsklassen |
| `constraints` | `irrigated` ist `null` (unbekannt), `excluded_crops` ist leer |
| `variables` | Beschreibung aller Zeitreihen-Variablen: Einheit, Takt, Quelle, Auflösung, Zeitraum, Datei |

---

## Hinweise

- **Räumliche Auflösung:** POWER-Werte gelten für ein ca. 50-km-Raster, nicht für das einzelne Feld.
- **Referenzverdunstung** ist berechnet (nicht gemessen) und nicht gegen eine Wetterstation geprüft.
- **Boden:** Die Werte stammen aus der SSURGO-Karteneinheit am Feldpunkt. Labormessungen in ca. 4 km Entfernung zeigen sandigeren Boden, die Bodenangaben sind also eine Schätzung.
- **Trends** (z. B. Hitzetage) sind einfache Auswertungen über 35 Jahre, ohne Signifikanztest.
- Erzeugt aus `data/base-data/z_processed/` mit `data/cleaning-scripts/build_datasets.py`. Diese README wird dabei nicht überschrieben.
