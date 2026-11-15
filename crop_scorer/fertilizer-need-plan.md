# Plan: Düngebedarf (Stickstoff) einer Fruchtfolge, danach Zwischenfrüchte

## Top-Level Overview

**Ziel:** Für eine Fruchtfolge gibt es ein weiteres, mit Wasser und Temperaturrisiko vergleichbares Kriterium: den **N-Düngebedarf** (kg N pro ha und Jahr der Fruchtfolge, kleiner ist besser). Im zweiten Schritt kommen **Zwischenfrüchte** dazu. Sie ändern die Brache und damit Auswaschung, Erosion und Bodengesundheit.

**Festgelegt (Entscheidung des Teams):**
- Zuerst nur **Stickstoff**. Phosphor und Kalium kommen später.
- **Referenzerträge** pro Kultur aus **USDA NASS Quick Stats, Kansas gesamt, unbewässert, Mittel 1991–2025**. Kein wetterabhängiger Ertrag. Der Wasserstress-Ertrag (ETa/ETc) bleibt eine mögliche spätere Erweiterung.
- **Soja-Gutschrift für die Folgefrucht netto aus Daten:** Fixierung minus N im abgefahrenen Korn, dazu Reste-N (Option B). Alle Eingangswerte stammen aus `Combined_crop_data.csv`.
- **Zitierpflicht:** Jeder Wert im Modell wird mit Quelle belegt (siehe Abschnitt "Zitierpflicht"). Es gibt keinen Wert ohne Herkunft.
- Zwischenfrüchte erst, wenn der Basis-N-Score steht.
- Vom Wasser-Teil (`crop_scorer/water_usage/`) wird nur **übernommen, was ohne großen Aufwand geht**. Sonst weglassen.
- Die Brache muss im N-Modell vorkommen, weil Zwischenfrüchte genau sie verändern.
- Bewässerung: Das Feld gilt wie in `water_usage` als **unbewässert** (`irrigated: null` in `field_profile.json`).
- Neuer Branch von `feat/crop-scorer` aus: `feat/fertilizer-need`.

**Ausgangslage (im Code geprüft):**
- [`water_usage.py`](water_usage/water_usage.py) ist ein Skript mit `main()` und einem `if __name__ == "__main__"`-Block. Die Funktionen `build_timeline`, `simulate`, `load_weather` und `load_crop_params` sind aber sauber getrennt und importierbar.
- `build_timeline` ist laut [`rotation-scoring-plan.md`](rotation-scoring-plan.md) die Quelle der Wahrheit für Saisons. Brachephasen sind dort die Lücken zwischen Ernte und nächster Aussaat.
- Die Wasserbilanz in `soil_water_balance` kennt Regen, der über Feldkapazität hinausgeht ("rain above field capacity percolates", Zeile 212). Dieses **Sickerwasser wird heute nicht ausgegeben**. Es ist die Grundlage für N-Auswaschung.
- [`Combined_crop_data.csv`](../data/base-data/dryad/Combined_crop_data.csv) enthält N/P/K-Gehalte (`N_pc_fresh`, `HI`) und für Leguminosen `Fixed_N_kg_N_metric_t_fresh_crop_product` (z. B. Erbse 32, Ackerbohne 23, Wicke 21, Lupine 18 und **Soja 45 kg N pro t Korn**, Quelle IFA 2020 / IPNI).
- Bodendaten: `organic_matter` aus `soil_ssurgo_long.csv` (`soil_ssurgo_long.csv`: 1,5 % in 0–23 cm, 0,7 % in 23–69 cm, 0,3 % in 69–200 cm. `field_profile.json` nennt 1,31 %, wie dieser Wert gemittelt ist, steht dort nicht. Niedrig in jedem Fall), `Ntot_…` und `CNrat_d-2_N` aus [`soil_layers_merged.csv`](../data/base-data/soil/soil_layers_merged.md) (nur 2017er Profile).
- Es gibt **keine** Erträge, keine Düngegaben, keinen Boden-P und keine Zwischenfrucht-Daten im Repo.

**Ansatz (einfache N-Bilanz pro Saison, ohne Neuerfindung der Saisons):**

```
Düngebedarf = max(0, (Entzug − Nachlieferung − Gutschriften) / Ausnutzung + Verluste)
```

- **Entzug** = Referenzertrag × N-Gehalt (Korn und, wo relevant, Reste).
- **Nachlieferung** = Mineralisierung aus der organischen Bodensubstanz über die Saisontage.
- **Gutschriften** = Vorfruchtwirkung von Leguminosen (Fixierung, netto) und später Zwischenfrüchte.
- **Verluste** = Auswaschung in Phasen mit Sickerwasser, besonders auf Brache.
- **Ausnutzung** = Anteil des gedüngten N, den die Pflanze aufnimmt.

## Zitierpflicht

Jeder Koeffizient steht in der Koeffizienten-Tabelle (Sub-Task 1) mit diesen Feldern:

| Feld | Inhalt |
|---|---|
| `value`, `unit` | Wert und Einheit |
| `source` | Autor/Herausgeber, Titel, Jahr |
| `locator` | Tabelle, Seite oder Abfrageparameter, so genau, dass man den Wert nachschlagen kann |
| `url_or_doi` | Link oder DOI |
| `retrieved` | Abrufdatum (bei Web-Quellen wie NASS Quick Stats) |
| `kind` | `data` (aus einer Quelle übernommen), `derived` (aus Quellwerten gerechnet, Formel angeben) oder `assumption` (keine Quelle, begründen) |

- Werte aus `Combined_crop_data.csv` werden mit den Spalten `reference_where_data_were_collated` und `primary_reference_of_dataset` der gewählten Zeile zitiert. Dazu kommt die Datei selbst: Dryad, DOI 10.5061/dryad.n2z34tn0x (steht schon in [`max_sources.md`](../data/base-data/max_sources.md)).
- Alle neuen Quellen werden zusätzlich in einer Quellen-Datei unter `data/base-data/` geführt, im Stil der vorhandenen `*_sources.md`.
- `assumption` ist erlaubt, soll aber selten sein und wird in der README als Grenze genannt.

## Datenlage und Lücken

| Baustein | Vorhanden | Lücke |
|---|---|---|
| N-Gehalt Korn/Reste für Weizen, Mais, Hirse, Soja, Sonnenblume | `Combined_crop_data.csv` (Zeilen noch auszuwählen) | Welche Zeile/Region gilt, muss festgelegt werden |
| Referenzertrag | nein | NASS Quick Stats (entschieden), muss abgerufen werden |
| Fixierung Leguminosen | Soja (45), Erbse, Ackerbohne, Wicke, Lupine in `Combined_crop_data.csv` | Brutto-Fixierung. Netto wird gerechnet (siehe Sub-Task 3) |
| Boden-N, organische Substanz | SSURGO und NCSS (ein Feld) | Mineralisierungsrate ist Literaturwert (Annahme) |
| Sickerwasser | berechnet, aber nicht ausgegeben | kleine Ergänzung in `water_usage.py` |
| Zwischenfrüchte (Roggen, Hafer, Wicke, Klee, Senf, Rettich) | nein | Arten, Fenster, Frosttoleranz, N-Aufnahme, C/N: alles extern |
| Boden-P, Boden-K verfügbar | nein / unvollständig | spätere Phase (P und K) |
| Düngegaben der Vergangenheit | nein | nicht nötig für den Bedarf |

## Quellen

**Schon im Repo** (`Combined_crop_data.csv`, Weltwerte, IFA 2020, im Repo geprüft). Der Entzug pro Tonne Korn folgt aus `N_pc_fresh` × 10:

| Kultur | N im Korn (% Frischmasse) | Entzug pro t Korn | Weitere Zeilen in der Datei |
|---|---|---|---|
| Weizen | 1,9 (IPNI) | 19 kg N | Stroh 0,43 bis 0,6 |
| Mais | 1,2 (IPNI) | 12 kg N | Reste 0,6 bis 1,1 |
| Hirse | 1,3 (IPNI) | 13 kg N | Reste 0,4 bis 1,1 |
| Sonnenblume | 2,7 (IPNI) | 27 kg N | Reste 1,8 |
| Soja | 5,5 (IPNI) | 55 kg N | Reste 0,8 bis 1,8, HI USA 0,42 bis 0,46, Fixierung **45 kg N/t Korn** |
| Wicke | 2,1 | 21 kg N | Fixierung 21 kg N/t |

- Die Datei hat pro Kultur mehrere Zeilen (Regionen, Quellen). Je Kultur wird eine Zeile gewählt, bevorzugt USA oder North America, sonst World. Die Wahl steht in der Tabelle.
- Erträge stehen nicht in der Datei. Die Ertragszeilen sind australisch (Unkovich et al. 2010) und taugen nicht für Kansas.
- Roggen, Hafer und Senf stehen nur als Körnerfrucht in der Datei, nicht als Zwischenfrucht.

**Noch zu beschaffen** (nicht im Repo). Die Quellen sind Vorschläge aus allgemeinem Wissen. Sie wurden bei der Planung **nicht** geöffnet oder geprüft und müssen beim Eintragen belegt werden:

| Benötigt | Vorschlag | Wo |
|---|---|---|
| Referenzerträge Kansas | USDA NASS Quick Stats, Kansas gesamt, unbewässert (Parameter "production practice"), Mittel 1991–2025 | `quickstats.nass.usda.gov`. Passt zur bestehenden NASS-Quelle (Handbook 628 im Kalender). |
| Umrechnung bu/acre in t/ha | Standard-Kornmasse je Kultur und Feuchte | Quelle benennen, z. B. USDA oder NASS. Wichtig für den Bezug auf `N_pc_fresh` (Frischmasse). |
| Mineralisierung, N-Ausnutzung | Pauschalwerte | Düngeempfehlungen K-State Research and Extension, dort prüfen |
| Zwischenfrüchte: N-Aufnahme, C/N, Fixierung, Fenster | SARE "Managing Cover Crops Profitably" | frei verfügbar, Tabellen je Art |
| Zwischenfrüchte: Kansas | USDA-NRCS Conservation Practice Standard 340 (Cover Crop), K-State Extension | vom Team gegenprüfen |
| Boden-P (später) | NCSS Lab Data Mart, Tabelle `Phosphorus` ist für Kearny leer | spätere Phase |

## Entscheidungen

| Thema | Festlegung | Status |
|---|---|---|
| Nährstoff | Nur N | entschieden |
| Ertrag | NASS Quick Stats, Kansas gesamt, unbewässert, Mittel 1991–2025 | entschieden |
| Soja-Gutschrift | Netto aus Daten (Fixierung − Korn-N, dazu Reste-N) | entschieden |
| Belege | Jeder Wert zitiert (Zitierpflicht) | entschieden |
| Saisons | `water_usage.build_timeline` | entschieden |
| Wasser | Nur Regen und Sickerwasser aus der vorhandenen Bilanz. ET0-Score, ETc und `irrigation_need` fließen nicht ein. | entschieden |
| Bewässerung | Unbewässert | entschieden |
| Brache | Eigene Phasen im N-Modell mit Mineralisierung und Auswaschung, kein Entzug | entschieden |
| Zwischenfrucht | Zweiter Schritt, ändert die Brache-Phasen | entschieden |
| Mineralisierung | Feste Rate aus organischer Substanz (SSURGO 0–23 cm, 1,5 %, `derived`); Rate zitiert, Quelle offen | Bodenwert entschieden, Rate offen |
| Auswaschung | Aus `drainage`, Mischungsmodell (N-Pool × Sickerwasser ÷ Bodenwasservolumen); Quelle offen | entschieden, Beleg offen |
| Soja-Fixierung | 45 kg N/t als Korn-Wert, Netto-Gutschrift ≤ 0 auf 0 begrenzt | entschieden |
| Harvest-Index | Prince et al. (2001), Johnson et al. (2006) als Spanne in der README | entschieden |
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
- **Status:** `[x] done` (Branch `feat/fertilizer-need` existiert; Plan noch nicht committet)

### 1. Datenbasis: N-Koeffizienten je Kultur (mit Quellen)

- **Intent:** Alle N-Eingangswerte stehen an einer Stelle, mit Quelle, und sind prüfbar.
- **Expected Outcomes:**
  - Eine Tabelle (CSV oder Python-Datei, wie `config.py` im Risk-Score) mit je Kultur: Referenzertrag, N-Gehalt Korn, N-Gehalt Reste, Harvest-Index, N-Fixierung (Leguminosen). Jeder Wert trägt die Felder der Zitierpflicht (`source`, `locator`, `url_or_doi`, `retrieved`, `kind`).
  - Referenzerträge aus NASS Quick Stats: Kansas gesamt, unbewässert, Mittel über die Jahre 1991–2025. Die Abfrageparameter und das Abrufdatum stehen in der Tabelle, das Rohergebnis wird als Datei unter `data/base-data/nass/` abgelegt, damit der Wert nachprüfbar bleibt.
  - Jede NASS-Zahl nennt die Anzahl der Jahre, über die gemittelt wurde. Fehlen Jahre oder eine Kultur (z. B. Sonnenblume unbewässert), wird das festgehalten und mit dem Team entschieden. Rückfall wäre dann ein anderer belegter Wert, nicht ein geschätzter.
  - Umrechnung von bu/acre in t/ha mit belegter Kornmasse und Feuchte. Der Bezug zu `N_pc_fresh` (Frischmasse) wird geprüft.
  - Auswahl der Zeilen aus `Combined_crop_data.csv` (Region USA oder World, Variablen `N_pc_fresh`, `N_pc`, `HI`, Fixierung). Die Wahl wird begründet.
- **Todo List:**
  1. Für die 5 Kulturen aus `FAO_ROWS` die passenden Zeilen in `Combined_crop_data.csv` finden (Namen wie `Wheat`, `Maize`, `Sorghum`, `Soybeans`, `Sunflower seed`). Die Zeile je Wert mit `reference_where_data_were_collated` und `primary_reference_of_dataset` festhalten.
  2. NASS Quick Stats abrufen und Rohdaten speichern. Die Umrechnungsfaktoren belegen.
  3. Koeffizienten-Tabelle und Quellen-Datei schreiben, kurz im README beschreiben.
  4. Kontrolle: Entzug pro Kultur in kg N/ha ist in realistischer Größe (Größenordnung gegen eine belegte Quelle prüfen).
- **Relevant Context:** [`Combined_crop_data.csv`](../data/base-data/dryad/Combined_crop_data.csv) (Spalten `original_crop`, `crop_component`, `variable`, `value`, `reference_where_data_were_collated`, `primary_reference_of_dataset`, `original_region`). [`kansas_crop_calendar_long.csv`](../data/base-data/nass/kansas_crop_calendar_long.csv) und [`felix_sources.md`](../data/base-data/felix_sources.md) als Vorbild für NASS-Quellen. [`risk_score/config.py`](risk_score/config.py) als Vorbild für eine Konfig-Tabelle.
- **Status:** `[x] done mit Abweichung` — Koeffizienten stehen in [`data/fertilizer_n_coefficients.csv`](../data/fertilizer_n_coefficients.csv) (Team, alle Kandidaten mit `selected`-Flag) und gespiegelt in [`fertilizer_need/config.py`](fertilizer_need/config.py); `run.py` prüft, dass beide übereinstimmen. Erträge: **nicht** wie geplant Kansas gesamt unbewässert 1991–2025 (diese Datei fehlt, API-Key nötig), sondern die NASS-Daten von `origin/main` (`data/base-data/nass_quickstats/`): Distrikt Südwest unbewässert für Mais (9 Jahre) und Weizen (10 Jahre); **Sorghum, Soja, Sonnenblume: Kansas alle Anbauweisen (16 Jahre)**, weil dafür keine unbewässerte Distriktreihe existiert (Teamentscheidung). Das überschätzt den Ertrag eines unbewässerten Feldes. Umrechnung bu/acre → t/ha über [`crop_unit_conversion.csv`](../data/crop_unit_conversion.csv).

### 2. Sickerwasser aus der Wasserbilanz verfügbar machen

- **Intent:** Auswaschung braucht Sickerwasser pro Tag. Es entsteht schon in `soil_water_balance`, wird aber verworfen.
- **Expected Outcomes:**
  - `soil_water_balance` liefert zusätzlich eine Spalte `drainage` (mm/Tag, Regen über Feldkapazität).
  - Alle bisherigen Ergebnisse von `water_usage` bleiben identisch (Vergleich von `data/processed/water_usage/irrigation_need_daily_long.csv` vor und nach der Änderung).
  - Die Änderung war nicht invasiv (eine Zeile); die frühere Rückfalloption (Auswaschung grob über Niederschlag) entfällt.
- **Todo List:**
  1. Prüfen, ob `water_usage` importierbar ist (`rotation-scoring-plan.md`, Sub-Task 1, behandelt dieselbe Frage).
  2. Eine Zeile Sickerwasser in `soil_water_balance` ergänzen, ohne die Rechenlogik zu verändern.
  3. Vorher und nachher `main()` laufen lassen und die Ausgabedatei vergleichen.
- **Relevant Context:** [`water_usage.py`](water_usage/water_usage.py): `soil_water_balance` (Zeilen 198–219, Regenzeile 212), `simulate`.
- **Status:** `[x] done` — Spalte `drainage` ergänzt, `irrigation_need_daily_long.csv` und Konsolenausgabe von `main()` bleiben byte-identisch. **Befund:** Sickerwasser ist selten. Bei der Testfruchtfolge (Winterweizen, Mais, Sorghum) tritt es nur in 9 von 34 Startjahren auf (99 Tage, 682 mm gesamt, v. a. 1996, 2007, 2019; max. 23,1 mm/Tag). Auswaschung als "Anteil des N-Pools an Sickertagen" wäre meist ≈ 0. **Entschieden:** Auswaschung wird aus `drainage` gerechnet (Mischungsmodell, siehe Sub-Task 3). Dass in Kansas bei ca. 490 mm Jahresniederschlag kaum etwas ausgewaschen wird, ist ein Befund, kein Fehler. Das 90. Perzentil über die Startjahre erfasst die nassen Jahre. Die Rückfalloption "grob aus dem Niederschlag" entfällt.

### 3. N-Bilanz entlang der Fruchtfolge (ohne Zwischenfrucht)

- **Intent:** Für jede Saison und jede Brachephase einer Fruchtfolge den N-Bedarf rechnen.
- **Expected Outcomes:**
  - Eine Funktion nimmt die Saisonliste von `build_timeline` und liefert pro Saison: Entzug, Nachlieferung, Gutschrift (Vorfrucht), Düngebedarf; pro Brachephase: Mineralisierung und Auswaschung.
  - Auswaschung aus Brache wird der **nachfolgenden** Kultur angelastet (sie muss das verlorene N ersetzen) und separat ausgewiesen. So ist der Effekt später gegen die Zwischenfrucht vergleichbar.
  - **Soja-Gutschrift netto:** Fixierung (45 kg N/t Korn) minus N im abgefahrenen Korn (55 kg N/t Korn). Das ergibt −10 kg N/t Korn, also keinen Gewinn. Der Reste-N-Anteil kommt aus `HI` und `N_pc` der Reste. Wie Reste-N korrekt eingeht, wird im Code belegt und in der README erklärt. Vor der Umsetzung ist in der Quelle (IFA 2020 / IPNI) zu prüfen, ob die 45 kg/t nur das fixierte N im Korn oder in der ganzen Pflanze meint, weil davon das Ergebnis abhängt.
  - Dass die Gutschrift klein oder null ausfällt, ist ein **Ergebnis**, kein Fehler. Es wird in der README so erklärt. Eine Ertragswirkung der Fruchtfolge (Vorfruchtwert über N hinaus) ist nicht Teil des Modells.
  - Tagestabelle oder Saisontabelle im Long-Format wie bei `water_usage`, zusätzlich eine Saisondatei.
  - Bezug pro Jahr der Fruchtfolge (kg N/ha/Jahr), Mittel und 90. Perzentil über Startjahre.
- **Todo List:**
  1. Neues Paket `crop_scorer/fertilizer_need/` mit kleinen Dateien (z. B. `config.py`, `balance.py`, `run.py`), im Stil von `risk_score/`.
  2. Mineralisierung als einfache Rate aus organischer Substanz und Saison-/Brachetagen. Organische Substanz aus `soil_ssurgo_long.csv`, aktive obere Schicht 0–23 cm (1,5 %), `kind="derived"`; die 1,31 % aus `field_profile.json` werden nicht genutzt, weil nicht nachvollziehbar ist, wie sie gemittelt wurden. Die Rate braucht eine zitierte Quelle (Offene Frage 7) und kommt mit Sensitivität (niedrig, mittel, hoch) in die Koeffizienten-Tabelle (`kind` ehrlich setzen).
  3. Auswaschung aus `drainage` (Sub-Task 2) als Mischungsmodell: Verlust = N-Pool × Sickerwasser ÷ Bodenwasservolumen. Das Modell ist **nicht gegen eine Quelle geprüft**, die Quelle wird vor dem Einbau gesucht (Offene Frage 6). Kein Pauschalansatz aus dem Niederschlag, weil das eine zusätzliche Annahme wäre und dem Wassermodell widerspräche.
  4. Wiederholungen von Kulturen und Brache vor der ersten Saison eines Laufs behandeln, wie in `rotation_irrigation_need` (Läufe mit zu wenigen Saisons auslassen).
  5. Plausibilität: Testfolge Winterweizen, Mais, Hirse liefert Werte in realistischer Größe. Eine Fruchtfolge mit Soja wird gegen die Netto-Rechnung geprüft.
  6. Brache-Dauer aus `erosion.rotation_timeline` gegenprüfen (gleiche Phasen).
- **Relevant Context:** Sub-Task 1 und 2. `water_usage.build_timeline`, `erosion.py` (Brache-Berechnung), `risk_score/run.py` (Aufbau und `sanity_checks`).
- **Status:** `[x] done mit Abweichungen` — [`inputs.py`](fertilizer_need/inputs.py), [`balance.py`](fertilizer_need/balance.py), [`run.py`](fertilizer_need/run.py). Auswaschung nach SWAT+ (Frage 6 belegt, exakte Exponentialform statt linearer Näherung), Mineralisierung nach K-State (Frage 7 belegt). Abweichungen vom Plan: (a) Soja deckt einen Teil seines Entzugs durch Eigenfixierung (45 kg N/t Korn), sonst käme Soja auf ca. 200 kg N/ha; (b) der Entzug wird durch `fe` = 0,55 geteilt (K-State-Struktur), sonst hätte die Bilanz keinen Verlustfaktor; (c) Mineralisierung als Jahreswert pro Tag gerechnet, in der Brache mit der Warmseason-Rate (Annahme); (d) kein Tageslauf, sondern eine Zeile je Saison. **Befund:** Auswaschung ≈ 0,03 kg N/ha/Jahr, die Sensitivität θe 0,2/0,8 ändert sie nur auf 0,02–0,08. Der Düngebedarf hängt dagegen stark von der Mineralisierungsstufe ab (24/36/45 kg N/ha/Jahr). K-State-Formel als Gegenprobe liegt bei 62,5 gegen 36,2 der Bilanz.

### 4. Als Kriterium einhängen und dokumentieren

- **Intent:** Der N-Bedarf wird neben Wasser und Temperaturrisiko als Kriterium nutzbar.
- **Expected Outcomes:**
  - Eintrag im Kriterien-Register aus `rotation-scoring-plan.md`, Sub-Task 4 (Name, Einheit kg N/ha/Jahr, Richtung kleiner ist besser).
  - README mit Datenfluss, Spalten, Annahmen, Grenzen und der vollständigen Quellenliste. Die Grenzen nennen ausdrücklich: Referenzertrag statt Wetterertrag, nur N, ein Feld, unbewässert, Kansas-Mittel statt Standortwert, Mineralisierung als Annahme.
  - Falls `rotation-scoring-plan.md` bis dahin nicht umgesetzt ist: Ausgabe zunächst als eigene Datei unter `data/processed/fertilizer_need/` im Long-Format.
- **Todo List:**
  1. Ausgabedatei(en) und Spaltenbeschreibung (Muster: `data/processed/water_usage/README.md`).
  2. Anbindung an das Register, sobald es existiert.
- **Relevant Context:** [`rotation-scoring-plan.md`](rotation-scoring-plan.md) Sub-Tasks 4 und 5. [`data/processed/water_usage/README.md`](../data/processed/water_usage/README.md).
- **Status:** `[-] teilweise` — README und Ausgabe unter [`data/processed/fertilizer_need/`](../data/processed/fertilizer_need/README.md) (Long-Format, Mittel und 90. Perzentil). Offen: Eintrag im Kriterien-Register (`rotation-scoring-plan.md` ist nicht umgesetzt). Das 90. Perzentil ist kaum vom Mittel verschieden, weil Erträge fest sind und die Startjahre nur die Wetter-Historie der Brache ändern.

### 5. Zwischenfrüchte (zweiter Schritt, startet erst nach Sub-Task 4)

- **Intent:** Brachephasen können mit einer Zwischenfrucht gefüllt werden. Das verändert N-Auswaschung, N-Nachlieferung, Erosion (Bare Days) und die Bodengesundheit.
- **Expected Outcomes:**
  - Eine Zwischenfrucht-Tabelle: Art, Aussaat- und Umbruchfenster, Frosttoleranz, N-Aufnahme, ob Leguminose (Fixierung), C/N-Verhältnis, Wasserverbrauch. **Alle Werte extern und zitiert** (Zitierpflicht).
  - Regel, wann eine Zwischenfrucht in eine Lücke passt: Die Lücke muss das Aussaat- und Umbruchfenster abdecken. Das lässt sich aus der Brache-Lücke in `build_timeline` ableiten.
  - Änderungen in der N-Bilanz: weniger Auswaschung auf der Zwischenfrucht-Fläche, Gutschrift bei Leguminosen (ebenfalls netto), Immobilisierung bei hohem C/N (Roggen), Rückgabe an die Folgefrucht.
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
- **Status:** `[-] teilweise` — Arten: Winterroggen, Zottelwicke, Futterrettich (Teamauswahl; Sunn Hemp ohne belegte Daten ausgelassen). Umgesetzt: Lückenregel (Aussaatfenster aus `cover_crops.csv`, ≥ 28 Tage, Beendigung 35 Tage vor Saat, winterkillende Arten beim mittleren ersten Frost), Rückhalt und N-Effekt in der Bilanz, Vergleich mit und ohne (Testfolge: ohne 36,2, Roggen 59,3, Wicke 9,0, Rettich 36,2 kg N/ha/Jahr). **Nicht umgesetzt:** Wasserverbrauch der Zwischenfrucht (`water_usage`), Erosion (`erosion.py`, Bare Days), Bodengesundheits-Indikator (Frage 4). Rettich hat in SARE keine Netto-N-Zahl und bleibt bei 0.

## Offene Fragen

1. **NASS-Abdeckung (beantwortet, teilweise):** Mit den Daten von `origin/main` fehlt für Sorghum, Soja und Sonnenblume eine unbewässerte Distriktreihe; Rückfall siehe Sub-Task 1. Ursprüngliche Frage: Gibt es für alle 5 Kulturen (vor allem Sonnenblume) unbewässerte Kansas-Erträge in Quick Stats für 1991–2025? Das zeigt sich erst beim Abruf in Sub-Task 1. Dann entscheidet das Team über einen Rückfall.
2. **Bedeutung der 45 kg N/t bei Soja:** Meint der IFA/IPNI-Wert die ganze Pflanze oder nur das Korn? Das Dryad-Feld heißt `Fixed_N_kg_N_metric_t_fresh_crop_product`, was aufs Korn hindeutet. Das Team hat das so akzeptiert (nicht in der IFA-Quelle geprüft).
3. **Negative Netto-Gutschrift:** Entschieden: ausweisen und für den Düngebedarf auf 0 begrenzen.
4. **Zwischenfrucht-Indikator für Bodengesundheit:** Welche Größe (Bare Days, organische Substanz)?
5. **Mineralisierung und Temperatur:** Reicht eine feste Rate pro Tag, oder soll Temperatur/Feuchte eingehen? Erst bei Bedarf. Die Rate braucht eine Quelle.
6. **Quelle für das Mischungsmodell der Auswaschung (beantwortet):** SWAT+ Theoretical Documentation, Nitrate Movement, Gl. 4:2.1.2 und 4:2.1.8 (siehe `data/fertilizer_model_references.csv`). Offen bleibt θe (`ANION_EXCL`): die SWAT+-Seite nennt keinen Standardwert, 0,5 ist eine Annahme mit Sensitivität 0,2/0,8. Ursprünglich: Verlust = N-Pool × Sickerwasser ÷ Bodenwasservolumen. Das ist Allgemeinwissen und **nicht gegen eine Quelle geprüft**. Eine Quelle suchen (z. B. Extension-Literatur oder Lehrbuch zu Nitratauswaschung), bevor die Formel eingebaut wird. Ohne Beleg wird sie als `kind="assumption"` geführt.
7. **Quelle für die Mineralisierungsrate (beantwortet):** K-State MF2586 p. 3–5 (20 lb N/ac je 1 % OM warm season, 10 cool season) mit UNL 14/28 als Spanne. Es ist eine Gutschrift der Düngeempfehlung, keine gemessene Rate, und gilt für 6 in. Ursprünglich: Zu suchen ist eine zitierte Faustzahl aus der Extension-Literatur (z. B. K-State). Als **unverifizierte Erinnerung** ohne Beleg: etwa 20 lb N/acre pro 1 % organischer Substanz und Jahr. Diese Zahl darf erst in `config.py`, wenn die Quelle gefunden und geprüft ist. Zusätzlich eine Sensitivität (niedrig, mittel, hoch) rechnen und in der README zeigen.
8. **Harvest-Index:** Prince et al. (2001) ist gewählt. Johnson et al. (2006) wird in der README als Spanne dokumentiert, gerechnet wird mit Prince.

## Nicht Teil dieses Plans

- P und K.
- Wetterabhängiger Ertrag (ETa/ETc).
- Ein Bodenstickstoff-Modell wie DSSAT oder APSIM.
- Düngetechnik, Aufteilung der Gaben, Düngerarten.
- Visualisierung.
- Zukunftsklima.
