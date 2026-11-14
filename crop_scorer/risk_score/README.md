# risk_score

Temperatur-Risikoscore für 5 Crops (Winterweizen, Mais, Hirse, Soja, Sonnenblume), Standort Kearny County, Kansas, 1991–2025. Nur Temperatur (NASA POWER Tmin/Tmax/Tmean), keine Niederschlags-, Boden- oder Lichtwerte.

## So funktioniert es

1. **Saison:** Jeder Saattag im NASS-Saatfenster (`planting_begin` bis `planting_end`) startet eine Saison bis `harvest_begin`. Winterweizen endet im Folgejahr. Nur Saisontage werden bewertet.
2. **Tageswert** (Grenzen aus Ecocrop):
   - Hitze: Tmax, 0 bei `temp_opt_max`, 1 bei `temp_abs_max`, darüber weiter steigend (kein Deckel, kein Hitze-Kill).
   - Frost: Tmin, 0 bei `temp_opt_min`, 1 bei `temp_abs_min`, dort gedeckelt.
   - Kälte-Kill: Tmin < `killing_temp_early_growth`, wenn Ecocrop ihn kennt (Winterweizen, Sonnenblume: 0 °C), sonst Annahme 0 °C (Mais, Hirse, Soja). Ein Kill-Tag zählt +100 und ersetzt den Stresswert.
   - Winterweizen, Ruhephase 1. Dez. bis 28. Feb.: kein Frost-Stress, Kill erst unter −20 °C.
3. **Saison-Score:** Mittel der Tageswerte über die Saison. Score 0 = kein Risiko, höher = riskanter.
4. **Hauptkennzahl** (`risk_score`, pro Crop und Saatjahr): Mittel der Saison-Scores im Hauptsaatfenster (`planting_most_active_*`). Zusätzlich `score_full_window`, `score_min`, `score_max` und Zähler für Frost-, Hitze- und Kill-Tage.

## Dateien

| Datei | Inhalt |
|---|---|
| `config.py` | `CropConfig` pro Crop (Ecocrop + NASS) und Parameter (Kill-Strafe 100, Kill-Fallback 0 °C, Ruhephase, −20 °C) |
| `loader.py` | `load_temperature_data()`: Tmin/Tmax/Tmean pro Tag, mit Prüfung auf Lücken und Ausreißer |
| `severity.py` | `compute_daily_risk()`: Tageswerte und Kill-Flags für einen Crop |
| `seasons.py` | `simulate_seasons()`, `aggregate_yearly()`, `check_season_lengths()` |

## Beispiel

```python
import pandas as pd
from crop_scorer.risk_score import (
    aggregate_yearly, load_crop_configs, load_temperature_data, simulate_seasons,
)

crops, temps = load_crop_configs(), load_temperature_data()
seasons = pd.concat([simulate_seasons(temps, c) for c in crops.values()], ignore_index=True)
print(aggregate_yearly(seasons))
```

Aufruf mit `uv run python ...` aus dem Repo-Root.

## Was es nicht kann / Grenzen

- Noch kein Einstiegspunkt und keine CSV-Ausgabe (geplant, siehe `risk-score-plan.md`).
- Ecocrop-Grenzen gelten für die Tagesmitteltemperatur, wir wenden sie auf Tmin/Tmax an (Näherung).
- Mais, Hirse, Soja: 0 °C als Kill-Grenze ist eine Annahme, Ecocrop hat keinen Wert.
- Winterruhe-Zeitraum ist eine Näherung (Parameter). Winterweizen bleibt trotzdem deutlich am höchsten, weil Tmin im Herbst und Frühjahr oft unter 0 °C liegt.
- NASS-Kalender ist für alle Jahre gleich, die Saatdaten variieren nicht pro Jahr.
- NASA POWER hat ca. 50 km Auflösung, die Werte sind nicht feldgenau.
- Winterweizen-Saatjahre nur 1991–2024 (Saison 2025/26 fehlt in den Daten).
