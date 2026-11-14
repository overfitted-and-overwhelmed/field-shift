# Plan: Düngebedarf (Stickstoff) einer Fruchtfolge, danach Zwischenfrüchte

## Top-Level Overview

**Ziel:** Für eine Fruchtfolge gibt es ein weiteres, mit Wasser und Temperaturrisiko vergleichbares Kriterium: den **N-Düngebedarf** (kg N pro ha und Jahr der Fruchtfolge, kleiner ist besser). Im zweiten Schritt kommen **Zwischenfrüchte** dazu. Sie ändern die Brache und damit Auswaschung, Erosion und Bodengesundheit.

**Festgelegt (Entscheidung des Teams):**
- Zuerst nur **Stickstoff**. Phosphor und Kalium kommen später.
- **Referenzerträge** pro Kultur, kein wetterabhängiger Ertrag. Der Wasserstress-Ertrag (ETa/ETc) bleibt eine mögliche spätere Erweiterung.
- Zwischenfrüchte erst, wenn der Basis-N-Score steht.
- Vom Wasser-Teil (`crop_scorer/water_usage/`) wird nur **übernommen, was ohne großen Aufwand geht**. Sonst weglassen.
- Die Brache muss im N-Modell vorkommen, weil Zwischenfrüchte genau sie verändern.
- Neuer Branch von `feat/crop-scorer` aus: `feat/fertilizer-need`.

**Ausgangslage (im Code geprüft):**
- [`water_usage.py`](water_usage/water_usage.py) ist ein Skript mit `main()` und einem `if __name__ == "__main__"`-Block. Die Funktionen `build_timeline`, `simulate`, `load_weather` und `load_crop_params` sind aber sauber getrennt und importierbar.
- `build_timeline` ist laut [`rotation-scoring-plan.md`](rotation-scoring-plan.md) die Quelle der Wahrheit für Saisons. Brachephasen sind dort die Lücken zwischen Ernte und nächster Aussaat.
- Die Wasserbilanz in `soil_water_balance` kennt Regen, der über Feldkapazität hinausgeht ("rain above field capacity percolates", Zeile 212). Dieses **Sickerwasser wird heute nicht ausgegeben**. Es ist die Grundlage für N-Auswaschung.
- [`Combined_crop_data.csv`](../data/base-data/dryad/Combined_crop_data.csv) enthält N/P/K-Gehalte (`N_pc_fresh`, `HI`) und für Leguminosen `Fixed_N_kg_N_metric_t_fresh_crop_product` (z. B. Erbse 32, Ackerbohne 23, Wicke 21, Lupine 18 und **Soja 45 kg N pro t Korn**, Quelle IFA 2020 / IPNI).
- Bodendaten: `organic_matter` aus `soil_ssurgo_long.csv` (Oberboden-Mittel in `field_profile.json`: 1,31 %, also niedrig, die Mineralisierung bleibt klein), `Ntot_…` und `CNrat_d-2_N` aus [`soil_layers_merged.csv`](../data/base-data/soil/soil_layers_merged.md) (nur 2017er Profile).
- Es gibt **keine** Erträge, keine Düngegaben, keinen Boden-P und keine Zwischenfrucht-Daten im Repo.

**Ansatz (einfache N-Bilanz pro Saison, ohne Neuerfindung der Saisons):**

```
Düngebedarf = max(0, (Entzug − Nachlieferung − Gutschriften) / Ausnutzung + Verluste)
```

- **Entzug** = Referenzertrag × N-Gehalt (Korn und, wo relevant, Reste).
- **Nachlieferung** = Mineralisierung aus der organischen Bodensubstanz über die Saisontage.
- **Gutschriften** = Vorfruchtwirkung von Leguminosen (Fixierung) und später Zwischenfrüchten.
- **Verluste** = Auswaschung in Phasen mit Sickerwasser, besonders auf Brache.
- **Ausnutzung** = Anteil des gedüngten N, den die Pflanze aufnimmt (Annahme, dokumentieren).

Alle Koeffizienten stehen in einer kleinen, kommentierten Tabelle mit Quelle. Jeder Wert ist eine **Annahme**, bis eine Quelle genannt ist. Es gibt keinen Wert ohne Herkunft.

## Datenlage und Lücken

| Baustein | Vorhanden | Lücke |
|---|---|---|
| N-Gehalt Korn/Reste für Weizen, Mais, Hirse, Soja, Sonnenblume | `Combined_crop_data.csv` (Zeilen noch auszuwählen) | Welche Zeile/Region gilt, muss festgelegt werden |
| Referenzertrag | nein | Quelle nötig (z. B. NASS Kansas, extern) oder dokumentierte Literaturwerte |
| Fixierung Leguminosen | Soja (45), Erbse, Ackerbohne, Wicke, Lupine in `Combined_crop_data.csv` | Brutto-Fixierung. Netto-Gutschrift für die Folgefrucht ist kleiner (siehe "Quellen") |
| Boden-N, organische Substanz | SSURGO und NCSS (ein Feld) | Mineralisierungsrate ist Literaturwert (Annahme) |
| Sickerwasser | berechnet, aber nicht ausgegeben | kleine Ergänzung in `water_usage.py` |
| Zwischenfrüchte (Roggen, Hafer, Wicke, Klee, Senf, Rettich) | nein | Arten, Fenster, Frosttoleranz, N-Aufnahme, C/N: alles extern |
| Boden-P, Boden-K verfügbar | nein / unvollständig | spätere Phase (P und K) |
| Düngegaben der Vergangenheit | nein | nicht nötig für den Bedarf |

## Quellen

**Schon im Repo** (`Combined_crop_data.csv`, Weltwerte, IFA 2020, in dieser Sitzung geprüft):

| Kultur | N im Korn (% Frischmasse) | Weitere Zeilen in der Datei |
|---|---|---|
| Weizen | 1,9 (IPNI) | Stroh 0,43 bis 0,6 |
| Mais | 1,2 (IPNI) | Reste 0,6 bis 1,1 |
| Hirse | 1,3 (IPNI) | Reste 0,4 bis 1,1 |
| Sonnenblume | 2,7 (IPNI) | Reste 1,8 |
| Soja | 5,5 (IPNI) | Reste 0,8 bis 1,8, HI USA 0,42 bis 0,46, Fixierung **45 kg N/t Korn** |
| Wicke | 2,1 | Fixierung 21 kg N/t |

- Die Datei hat pro Kultur mehrere Zeilen (Regionen, Quellen). Je Kultur wird eine Zeile gewählt, bevorzugt USA oder North America, sonst World. Die Wahl steht in der Tabelle.
- Fixierung ist **brutto** pro Tonne Korn. Soja entzieht im Korn etwa 55 kg N/t (5,5 % × 1000). Netto bleibt für die Folgefrucht deshalb nur, was in Wurzeln und Resten zurückbleibt. Ob brutto oder netto gerechnet wird, ist eine Entscheidung (siehe Offene Fragen).
- Roggen, Hafer und Senf stehen nur als Körnerfrucht in der Datei, nicht als Zwischenfrucht.

**Noch zu beschaffen** (nicht im Repo). Die Quellen sind meine Vorschläge aus allgemeinem Wissen. Ich habe sie in dieser Sitzung **nicht** geöffnet oder geprüft:

| Benötigt | Vorschlag | Wo |
|---|---|---|
| Referenzerträge Kansas | USDA NASS Quick Stats, Kearny County (FIPS 20093) oder ganz Kansas, Mittel 1991–2025, bewässert und unbewässert getrennt | `quickstats.nass.usda.gov`. Passt zur bestehenden NASS-Quelle (Handbook 628 im Kalender). |
| Mineralisierung, N-Ausnutzung | Pauschalwerte | Düngeempfehlungen K-State Research and Extension, dort prüfen |
| Zwischenfrüchte: N-Aufnahme, C/N, Fixierung, Fenster | SARE "Managing Cover Crops Profitably" | frei verfügbar, Tabellen je Art |
| Zwischenfrüchte: Kansas | USDA-NRCS Conservation Practice Standard 340 (Cover Crop), K-State Extension | vom Team gegenprüfen |
| Boden-P (später) | NCSS Lab Data Mart, Tabelle `Phosphorus` ist für Kearny leer | spätere Phase |

## Entscheidungen

| Thema | Festlegung | Status |
|---|---|---|
| Nährstoff | Nur N | entschieden |
| Ertrag | Referenzertrag pro Kultur, Tabelle mit Quelle | entschieden, Quelle offen |
| Saisons | `water_usage.build_timeline` | entschieden |
| Wasser | Nur Regen und Sickerwasser aus der vorhandenen Bilanz. ET0-Score, ETc und `irrigation_need` fließen nicht ein. | entschieden |
| Brache | Eigene Phasen im N-Modell mit Mineralisierung und Auswaschung, kein Entzug | entschieden |
| Zwischenfrucht | Zweiter Schritt, ändert die Brache-Phasen | entschieden |
| Richtung | Kleiner ist besser (weniger Dünger nötig) | wie bei den anderen Kriterien |
| Aggregation | Mittel und 90. Perzentil über Startjahre, pro Jahr der Fruchtfolge | wie in `rotation-scoring-plan.md` |
| Ort | Neues Paket `crop_scorer/fertilizer_need/` | Vorschlag |

## Sub-Tasks

### 0. Branch anlegen

- **Intent:** Die Arbeit liegt getrennt vom bisherigen Stand.
- **Expected Outcomes:** Branch `feat/fertilizer-need`, abgezweigt von `feat/crop-scorer`. Dieser Plan ist dort enthalten.
- **Todo List:**
  1. Auf `feat/crop-scorer` prüfen, dass der Arbeitsbaum sauber ist (zum Planungszeitpunkt war er es).
  2. `git switch -c feat/fertilizer-need`.
  3. Diesen Plan committen.
- **Relevant Context:** Aktueller Branch `feat/crop-scorer`. Branch-Namen im Repo: `feat/data`, `feat/explorer`, `feat/frontend`.
- **Status:** `[ ] pending`

### 1. Datenbasis: N-Koeffizienten je Kultur

- **Intent:** Alle N-Eingangswerte stehen an einer Stelle, mit Quelle, und sind prüfbar.
- **Expected Outcomes:**
  - Eine Tabelle (CSV oder Python-Datei, wie `config.py` im Risk-Score) mit je Kultur: Referenzertrag, N-Gehalt Korn, N-Gehalt Reste, Harvest-Index, ob Reste auf dem Feld bleiben, N-Fixierung (Leguminosen).
  - Jeder Wert hat Einheit und Quelle. Annahmen sind als solche markiert.
  - Entscheidung, welche Zeilen aus `Combined_crop_data.csv` gelten (Region USA oder World, Variable `N_pc_fresh` und `N_pc`). Die Wahl wird begründet.
  - Soja-Fixierung aus `Combined_crop_data.csv` (45 kg N/t Korn, IPNI). Brutto oder netto, siehe Offene Fragen.
- **Todo List:**
  1. Für die 5 Kulturen aus `FAO_ROWS` die passenden Zeilen in `Combined_crop_data.csv` finden (Namen wie `Wheat`, `Maize`, `Sorghum`, `Soya beans`, `Sunflower seed` sind noch zu bestätigen).
  2. Referenzerträge vom Team mit Quelle festlegen lassen. Das ist eine fachliche Entscheidung.
  3. Tabelle schreiben und kurz im README beschreiben.
  4. Kontrolle: Entzug pro Kultur in kg N/ha ist in realistischer Größe (Größenordnung gegen Literatur prüfen).
- **Relevant Context:** [`Combined_crop_data.csv`](../data/base-data/dryad/Combined_crop_data.csv) (Spalten `original_crop`, `crop_component`, `variable`, `value`, `reference_where_data_were_collated`, `original_region`). [`risk_score/config.py`](risk_score/config.py) als Vorbild für eine Konfig-Tabelle.
- **Status:** `[ ] pending`

### 2. Sickerwasser aus der Wasserbilanz verfügbar machen

- **Intent:** Auswaschung braucht Sickerwasser pro Tag. Es entsteht schon in `soil_water_balance`, wird aber verworfen.
- **Expected Outcomes:**
  - `soil_water_balance` liefert zusätzlich eine Spalte `drainage` (mm/Tag, Regen über Feldkapazität).
  - Alle bisherigen Ergebnisse von `water_usage` bleiben identisch (Vergleich von `data/processed/water_usage/irrigation_need_daily_long.csv` vor und nach der Änderung).
  - Falls die Änderung zu invasiv wäre: Sickerwasser wird in der neuen Datei nachgerechnet oder weggelassen (dann nur Auswaschung grob über Niederschlag). Das bleibt die Rückfalloption laut Auftrag "sonst weglassen".
- **Todo List:**
  1. Prüfen, ob `water_usage` importierbar ist (`rotation-scoring-plan.md`, Sub-Task 1, behandelt dieselbe Frage).
  2. Eine Zeile Sickerwasser in `soil_water_balance` ergänzen, ohne die Rechenlogik zu verändern.
  3. Vorher und nachher `main()` laufen lassen und die Ausgabedatei vergleichen.
- **Relevant Context:** [`water_usage.py`](water_usage/water_usage.py): `soil_water_balance` (Zeilen 198–219, Regenzeile 212), `simulate`.
- **Status:** `[ ] pending`

### 3. N-Bilanz entlang der Fruchtfolge (ohne Zwischenfrucht)

- **Intent:** Für jede Saison und jede Brachephase einer Fruchtfolge den N-Bedarf rechnen.
- **Expected Outcomes:**
  - Eine Funktion nimmt die Saisonliste von `build_timeline` und liefert pro Saison: Entzug, Nachlieferung, Gutschrift (Vorfrucht), Düngebedarf; pro Brachephase: Mineralisierung und Auswaschung.
  - Auswaschung aus Brache wird der **nachfolgenden** Kultur angelastet (sie muss das verlorene N ersetzen) und separat ausgewiesen. So ist der Effekt später gegen die Zwischenfrucht vergleichbar.
  - Vorfruchtwirkung: Eine Leguminose liefert der Folgekultur N. Sie braucht die Reihenfolge, die `build_timeline` schon liefert.
  - Tagestabelle oder Saisontabelle im Long-Format wie bei `water_usage`, zusätzlich eine Saisondatei.
  - Bezug pro Jahr der Fruchtfolge (kg N/ha/Jahr), Mittel und 90. Perzentil über Startjahre.
- **Todo List:**
  1. Neues Paket `crop_scorer/fertilizer_need/` mit kleinen Dateien (z. B. `config.py`, `balance.py`, `run.py`), im Stil von `risk_score/`.
  2. Mineralisierung als einfache Rate aus organischer Substanz (SSURGO) und Saison-/Brachetagen (Annahme dokumentieren, Temperatur- und Feuchteeinfluss nur wenn billig).
  3. Auswaschung als Anteil des mineralischen N-Pools an Tagen mit Sickerwasser.
  4. Wiederholungen von Kulturen und Brache vor der ersten Saison eines Laufs behandeln, wie in `rotation_irrigation_need` (Läufe mit zu wenigen Saisons auslassen).
  5. Plausibilität: Testfolge Winterweizen, Mais, Hirse liefert Werte in realistischer Größe; eine Fruchtfolge mit Soja zeigt eine Gutschrift für die Folgefrucht.
  6. Brache-Dauer aus `erosion.rotation_timeline` gegenprüfen (gleiche Phasen).
- **Relevant Context:** Sub-Task 1 und 2. `water_usage.build_timeline`, `erosion.py` (Brache-Berechnung), `risk_score/run.py` (Aufbau und `sanity_checks`).
- **Status:** `[ ] pending`

### 4. Als Kriterium einhängen und dokumentieren

- **Intent:** Der N-Bedarf wird neben Wasser und Temperaturrisiko als Kriterium nutzbar.
- **Expected Outcomes:**
  - Eintrag im Kriterien-Register aus `rotation-scoring-plan.md`, Sub-Task 4 (Name, Einheit kg N/ha/Jahr, Richtung kleiner ist besser).
  - README mit Datenfluss, Spalten, Annahmen, Grenzen. Die Grenzen nennen ausdrücklich: Referenzertrag statt Wetterertrag, nur N, ein Feld, Mineralisierung als Annahme.
  - Falls `rotation-scoring-plan.md` bis dahin nicht umgesetzt ist: Ausgabe zunächst als eigene Datei unter `data/processed/fertilizer_need/` im Long-Format.
- **Todo List:**
  1. Ausgabedatei(en) und Spaltenbeschreibung (Muster: `data/processed/water_usage/README.md`).
  2. Anbindung an das Register, sobald es existiert.
- **Relevant Context:** [`rotation-scoring-plan.md`](rotation-scoring-plan.md) Sub-Tasks 4 und 5. [`data/processed/water_usage/README.md`](../data/processed/water_usage/README.md).
- **Status:** `[ ] pending`

### 5. Zwischenfrüchte (zweiter Schritt, startet erst nach Sub-Task 4)

- **Intent:** Brachephasen können mit einer Zwischenfrucht gefüllt werden. Das verändert N-Auswaschung, N-Nachlieferung, Erosion (Bare Days) und die Bodengesundheit.
- **Expected Outcomes:**
  - Eine Zwischenfrucht-Tabelle: Art, Aussaat- und Umbruchfenster, Frosttoleranz, N-Aufnahme, ob Leguminose (Fixierung), C/N-Verhältnis, Wasserverbrauch. **Alle Werte extern**, Quelle je Wert.
  - Regel, wann eine Zwischenfrucht in eine Lücke passt: Die Lücke muss das Aussaat- und Umbruchfenster abdecken. Das lässt sich aus der Brache-Lücke in `build_timeline` ableiten.
  - Änderungen in der N-Bilanz: weniger Auswaschung auf der Zwischenfrucht-Fläche, Gutschrift bei Leguminosen, Immobilisierung bei hohem C/N (Roggen), Rückgabe an die Folgefrucht.
  - Neue Brache-Bilanz: Bare Days sinken. Soll `erosion.py` die Zwischenfrucht berücksichtigen, ist das eine kleine, getrennte Änderung.
  - **Bodengesundheit:** als einfacher Indikator, z. B. Eintrag organischer Substanz oder Bare Days, nicht als Modell. Der Indikator wird im Vorfeld mit dem Team festgelegt.
  - Wasser: Eine Zwischenfrucht verbraucht Wasser und leert den Bodenspeicher für die Folgefrucht. Wenn sich das mit `water_usage` ohne großen Aufwand abbilden lässt, wird es übernommen, sonst weggelassen und als Grenze dokumentiert.
- **Todo List:**
  1. Artenliste mit dem Team festlegen (Vorschlag: Roggen, Hafer, Wicke, Klee, Senf, Rettich). Das ist eine fachliche Entscheidung.
  2. Werte-Tabelle mit Quellen anlegen.
  3. Lückenregel in Code gießen. Wiederholungen und kurze Lücken (z. B. Weizen→Mais mit langem Winter) prüfen.
  4. N-Bilanz erweitern: Zwischenfrucht als optionaler Eintrag je Brachephase. Ohne Zwischenfrucht bleibt Sub-Task 3 unverändert.
  5. Vergleich Fruchtfolge mit und ohne Zwischenfrucht für die Testfolge.
  6. Entscheiden, ob und wie `erosion.py` und `water_usage` angepasst werden.
- **Relevant Context:** Sub-Tasks 1 bis 4. [`erosion.py`](erosion/erosion.py) (Hinweis "No cover crops" in Zeile 6). `ecocrop_selected_crops.csv` enthält Zwischenfrüchte heute nicht.
- **Status:** `[ ] pending`

## Offene Fragen

1. **Referenzerträge:** Das Repo enthält keine Kansas-Erträge. Optionen stehen in der Antwort im Chat und werden hier nach der Entscheidung eingetragen.
2. **Soja-Fixierung:** Wert vorhanden (45 kg N/t Korn). Offen: Gutschrift brutto, netto oder pauschal.
3. **Bewässerung:** Entschieden. `field_profile.json` hat `irrigated: null`, der Plan nimmt wie `water_usage` ein unbewässertes Feld an. Das ist in der README zu nennen.
4. **Zwischenfrucht-Indikator für Bodengesundheit:** Welche Größe (Bare Days, organische Substanz)?
5. **Mineralisierung und Temperatur:** Reicht eine feste Rate pro Tag, oder soll Temperatur/Feuchte eingehen? Erst bei Bedarf.

## Nicht Teil dieses Plans

- P und K.
- Wetterabhängiger Ertrag (ETa/ETc).
- Ein Bodenstickstoff-Modell wie DSSAT oder APSIM.
- Düngetechnik, Aufteilung der Gaben, Düngerarten.
- Visualisierung.
- Zukunftsklima.

---

Was schon in den vorhandenen Quellen steht
Alles in Combined_crop_data.csv (IFA 2020, Weltwerte). Der Entzug pro Tonne Korn folgt aus N_pc_fresh × 10:

Kultur	N im Korn	Entzug pro t Korn
Weizen	1,9 %	19 kg N
Mais	1,2 %	12 kg N
Hirse	1,3 %	13 kg N
Sonnenblume	2,7 %	27 kg N
Soja	5,5 %	55 kg N, Fixierung 45 kg N
Die Datei enthält auch Reste-N und Harvest-Index (HI) für USA und North America. Erträge stehen nicht darin. Die Ertragszeilen der Datei sind australisch (Unkovich) und taugen nicht für Kansas. Roggen, Hafer und Senf stehen nur als Körnerfrucht drin, nicht als Zwischenfrucht.

Was fehlt und wo es vermutlich herkommt
Diese Quellen sind meine Vorschläge aus allgemeinem Wissen. Ich habe sie nicht geöffnet oder geprüft.

Fehlt	Beste Quelle	Warum
Erträge	USDA NASS Quick Stats, Kansas	Dieselbe Behörde wie der bestehende Anbaukalender (Handbook 628). Frei verfügbar.
Mineralisierung, N-Ausnutzung	K-State Research and Extension (Düngeempfehlungen)	Pauschalwerte für Kansas, passend zum Standort.
Zwischenfrüchte (N-Aufnahme, C/N, Fixierung, Fenster)	SARE "Managing Cover Crops Profitably"	Frei verfügbar, Tabellen je Art.
Zwischenfrüchte für Kansas	USDA-NRCS Practice Standard 340 und K-State Extension	Regionale Aussaat- und Umbruchfenster.
Boden-P (später)	NCSS Lab Data Mart	Die Tabelle Phosphorus ist für Kearny leer.
Optionen zum Auswählen
Ertrag (Sub-Task 1):

Option	Daten	Realismus	Aufwand
A. NASS Kansas gesamt, unbewässert, Mittel 1991–2025	NASS Quick Stats	Gut. Passt zur Annahme "unbewässert".	Gering. Wenige Werte, eine Tabelle.
B. NASS Kearny County, unbewässert	NASS Quick Stats	Standortnäher, aber in kleinen Counties fehlen oft Jahre oder Werte.	Mittel. Lücken müssen abgefangen werden.
C. Pauschale Literaturwerte von K-State	Extension-Publikationen	Grob, nicht jahresbezogen.	Gering. Ich würde das nur als Rückfall nehmen.
Option A ist mein Vorschlag. Möglich ist auch A mit B als Gegenprobe. Realistisch ist Kearny County überwiegend bewässert (allgemeines Wissen, nicht geprüft). Die unbewässerten Erträge liegen deshalb niedriger als das, was dort real geerntet wird. Das gehört in die README-Grenzen.

Soja-Gutschrift für die Folgefrucht (Sub-Task 3):

Option	Beschreibung	Realismus
A. Pauschale Vorfrucht-Gutschrift	Fester Wert pro Leguminosen-Vorfrucht aus der Extension-Literatur.	Praxisnah und einfach.
B. Netto aus Daten	45 kg/t Fixierung abzüglich 55 kg/t im Korn, dazu Reste-N. Das Ergebnis liegt bei oder unter null.	Fachlich konsistent mit dem Repo, aber die Gutschrift fällt klein aus.
C. Brutto	Fixierung 45 kg/t ohne Abzug.	Überschätzt die Gutschrift. Nicht empfohlen.
Mein Vorschlag ist A, mit B als Plausibilitätsprüfung.

Mineralisierung (Sub-Task 3):

A. Feste Rate aus organischer Substanz (1,31 %), pro Tag und Phase. Das ist einfach und reicht für den Anfang.
B. Rate gewichtet mit Tagestemperatur und Bodenfeuchte. Die Daten haben wir, aber es ist mehr Aufwand und mehr Annahmen.
Mein Vorschlag ist A.

Bewässerung: entschieden, unbewässert.