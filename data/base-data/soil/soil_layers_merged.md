# Bodendaten – `soil_layers_merged.csv`

Diese Datei beschreibt jede Spalte der zusammengeführten Bodentabelle `soil_layers_merged.csv`.

## Überblick

- **Quelle:** USDA-NRCS, National Cooperative Soil Survey (NCSS) – Soil Characterization Database, Kellogg Soil Survey Laboratory. Export über den NCSS Lab Data Mart (<https://ncsslabdatamart.sc.egov.usda.gov/>), Rohdaten in `data/raw/soil-data/`.
- **Inhalt:** 53 Bodenhorizonte aus 10 Profilen in Kearny County, Kansas (USA), ca. 38,0–38,2° N / 101,2–101,5° W.
  - 4 Profile von 1986 (`87P…`, Bodenserien *Ulysses* / *Buffalo Park*), 0–152 cm, 18 Horizonte – Laborsystem **CMS**.
  - 6 Profile von 2017 (`17N…`), 0–205 cm, 35 Horizonte – Laborsystem **SSL**.
- **Eine Zeile = ein Horizont** (Bodenschicht mit Ober- und Untergrenze). Profil- und Standortangaben wiederholen sich in jeder Zeile des Profils.
- **Leere Zelle = nicht gemessen.** Viele Messgrößen existieren doppelt – je eine Spalte für 1986 (CMS) und 2017 (SSL). Pro Zeile ist nur eine davon gefüllt.

## Entstehung

1. Alle 17 Messtabellen aus `data/raw/soil-data/` wurden über `layer_key` zusammengeführt; Standort (`site.csv`) und Profil (`pedon.csv`) wurden dazugespielt.
2. 44 Messspalten kamen in mehreren Tabellen vor (z. B. Ton in PSDA, Taxonomy und Andic). Ihre Werte waren überall identisch und wurden einmal übernommen.
3. 35 Horizonte der 2017er-Profile waren leere Duplikate (gleiche Tiefe und Probe, keine Messwerte) und wurden entfernt.
4. Leere Rohtabellen (Wassergehalt, Phosphor, Mineralogie, Spurenelemente u. a.) tragen nichts bei.

Spaltennamen der Messwerte sind die Original-Methodencodes des NCSS-Labors (z. B. `Clay_3A1a1a_Njj_193_SSL_0_0` = Analyt_Methode_Vorbereitung_…_Laborsystem). Alle Originalbeschreibungen (englisch) stehen in `soil_layers_merged_dict.csv`.

**Spalte „Labor“:** SSL (2017) = Werte für die Profile von 2017; CMS (1986) = Werte für die Profile von 1986. **„Gefüllt“** = Anzahl Zeilen mit Wert von 53.

## Standort (aus `site.csv`)

Gilt für alle Horizonte eines Profils.

| Spalte | Bedeutung | Einheit |
|---|---|---|
| `pedon_key` | Labor-ID des Bodenprofils (Pedon). Verknüpft alle Horizonte eines Profils. | – |
| `user_site_id` | ID des Probenahmestandorts. Präfix `S1986…` = Kampagne 1986, `I2017…` = Kampagne 2017. | – |
| `latitude_decimal_degrees` | Geografische Breite des Standorts (WGS84). | ° N |
| `longitude_decimal_degrees` | Geografische Länge des Standorts (WGS84, negativ = West). | ° E |
| `country` | Land (ISO-Code), hier immer `US`. | – |
| `state_admin_div` | Bundesstaat, hier immer `KS` (Kansas). | – |
| `county` | County-Code, hier `KS093` = Kearny County. | – |
| `ssa` | Soil Survey Area – Kartiergebiet der US-Bodenkartierung (nur 1986 gefüllt). | – |
| `mlra` | Major Land Resource Area – naturräumliche Großeinheit der USDA; `72` = Central High Tableland. | – |

## Profil (aus `pedon.csv`)

Gilt für das ganze Profil und wiederholt sich in jeder Horizontzeile. Für die Profile von 2017 sind diese Felder leer.

| Spalte | Bedeutung | Einheit |
|---|---|---|
| `user_pedon_id` | Profil-ID des Probennehmers (entspricht hier `user_site_id`). | – |
| `cntrl_depth_to_top` | Obergrenze der Kontrollsektion für die Korngrößenklasse (Particle-size control section) nach US Soil Taxonomy. | cm |
| `cntrl_depth_to_bot` | Untergrenze dieser Kontrollsektion. | cm |
| `sampled_taxon_name` | Bodenserie, als die das Profil bei der Probenahme angesprochen wurde (z. B. *Ulysses*, *Buffalo Park*). | – |
| `sampled_class_name` | Vollständige Klassifikation nach US Soil Taxonomy bei der Probenahme (Korngrößenklasse, Mineralogie, Temperaturregime, Subgruppe). | – |
| `correlated_taxon_name` | Bodenserie nach späterer Korrelation (offizielle Zuordnung). | – |
| `correlated_class_name` | Klassifikation nach späterer Korrelation. | – |
| `clyavg_d-1` | Gewichteter mittlerer Tongehalt in der Kontrollsektion. | Gew.-% |
| `wa0175_d-1_S` | Gewichteter Mittelwert des Anteils 0,1–75 mm in der Kontrollsektion (Unterscheidung „silty“ < 15 % vs. „loamy“ ≥ 15 %). | Gew.-% |
| `wacltot_d-1_S` | Gewichteter mittlerer Gesamt-Tongehalt in der Kontrollsektion. | Gew.-% |
| `wavfg2_d-1_S` | Gewichteter mittlerer Volumenanteil Grobboden (> 2 mm) in der Kontrollsektion. | Vol.-% |

## Horizont (Schicht)

Beschreibt die einzelne Bodenschicht, auf die sich die Messwerte der Zeile beziehen.

| Spalte | Bedeutung | Einheit |
|---|---|---|
| `layer_key` | Eindeutige Labor-ID des Horizonts – Primärschlüssel der Tabelle. | – |
| `layer_sequence` | Laufende Nummer des Horizonts in der Datenbank. | – |
| `layer_field_label_1` | Feldbezeichnung der Probe (Profil-ID + Horizontnummer). | – |
| `layer_field_label_2` | Zweite Probenbezeichnung (Labornummer der Probe, nur 2017). | – |
| `layer_field_label_3` | Dritte Probenbezeichnung (hier leer). | – |
| `hzn_top` | Obergrenze des Horizonts unter Geländeoberfläche. | cm |
| `hzn_bot` | Untergrenze des Horizonts. | cm |
| `hzn_desgn` | Horizontsymbol nach US-Nomenklatur: `A`/`Ap` Oberboden (p = gepflügt), `B`/`Bw` Unterboden mit Verwitterung, `Bk`/`Bky` mit Kalk- (k) bzw. Gipsanreicherung (y). | – |
| `texture_description` | Bodenart laut Feldansprache (Textbeschreibung). | – |

# Messwerte

## Korngrößen (< 2 mm Feinboden)

Anteile am Feinboden < 2 mm. USDA-Grenzen: Ton < 0,002 mm, Schluff 0,002–0,05 mm, Sand 0,05–2 mm. Für 1986 und 2017 gibt es jeweils eigene Spalten (gleiche Methode, anderes Laborsystem).

| Spalte | Bedeutung | Einheit | Labor | Gefüllt |
|---|---|---|---|---|
| `Textur_d-1_S` | Bodenart nach USDA, aus den Korngrößen berechnet (Kürzel, z. B. `sil` = silt loam / schluffiger Lehm). | – | CMS (1986) | 18/53 |
| `Textur_d-3_N` | Bodenart nach USDA (wie oben), Probenvorbereitung „N prep“. | – | SSL (2017) | 35/53 |
| `Clay_3A1a1a_Njj_193_SSL_0_0` | Gesamt-Ton (< 0,002 mm), inkl. Ton-Carbonat. | Gew.-% | SSL (2017) | 35/53 |
| `ClyT_p_3A1_Sjj_% wt_0_CMS_0_0` | Gesamt-Ton (< 0,002 mm), inkl. Ton-Carbonat. | Gew.-% | CMS (1986) | 18/53 |
| `ClyCO3_3A1a1a_Njj_193_SSL_0_0` | Carbonat-Ton: Anteil der Tonfraktion, der aus Carbonaten besteht. | Gew.-% | SSL (2017) | 32/53 |
| `ClyCO3_3A1_Sjj_% wt_0_CMS_0_0` | Carbonat-Ton: Anteil der Tonfraktion, der aus Carbonaten besteht. | Gew.-% | CMS (1986) | 12/53 |
| `Silt_d-3_N` | Gesamt-Schluff (0,002–0,05 mm). | Gew.-% | SSL (2017) | 35/53 |
| `Silt_d-1_S` | Gesamt-Schluff (0,002–0,05 mm). | Gew.-% | CMS (1986) | 18/53 |
| `SiltF_3A1a1a_Njj_193_SSL_0_0` | Feinschluff (0,002–0,02 mm). | Gew.-% | SSL (2017) | 35/53 |
| `SiltFp_3A1_Sjj_% wt_0_CMS_0_0` | Feinschluff (0,002–0,02 mm). | Gew.-% | CMS (1986) | 18/53 |
| `cSilt_d-3_N` | Grobschluff (0,02–0,05 mm). | Gew.-% | SSL (2017) | 35/53 |
| `CSilt_d-1_S` | Grobschluff (0,02–0,05 mm). | Gew.-% | CMS (1986) | 18/53 |
| `Sand_d-3_N` | Gesamt-Sand (0,05–2 mm). | Gew.-% | SSL (2017) | 35/53 |
| `Sand_d-1_S` | Gesamt-Sand (0,05–2 mm). | Gew.-% | CMS (1986) | 18/53 |
| `CoSiS_d-3_N` | Sand plus Grobschluff (0,02–2 mm). | Gew.-% | SSL (2017) | 35/53 |
| `SandVF_3A1a1a_Njj_193_SSL_0_0` | Sehr feiner Sand (0,05–0,1 mm). | Gew.-% | SSL (2017) | 35/53 |
| `SndVFp_3A1_Sjj_% wt_0_CMS_0_0` | Sehr feiner Sand (0,05–0,1 mm). | Gew.-% | CMS (1986) | 18/53 |
| `SandF_3A1a1a_Njj_193_SSL_0_0` | Feinsand (0,1–0,25 mm). | Gew.-% | SSL (2017) | 35/53 |
| `SndF_p_3A1_Sjj_% wt_0_CMS_0_0` | Feinsand (0,1–0,25 mm). | Gew.-% | CMS (1986) | 18/53 |
| `SandM_3A1a1a_Njj_193_SSL_0_0` | Mittelsand (0,25–0,5 mm). | Gew.-% | SSL (2017) | 35/53 |
| `SndM_p_3A1_Sjj_% wt_0_CMS_0_0` | Mittelsand (0,25–0,5 mm). | Gew.-% | CMS (1986) | 18/53 |
| `SandCo_3A1a1a_Njj_193_SSL_0_0` | Grobsand (0,5–1 mm). | Gew.-% | SSL (2017) | 35/53 |
| `SndC_p_3A1_Sjj_% wt_0_CMS_0_0` | Grobsand (0,5–1 mm). | Gew.-% | CMS (1986) | 18/53 |
| `SandVC_3A1a1a_Njj_193_SSL_0_0` | Sehr grober Sand (1–2 mm). | Gew.-% | SSL (2017) | 35/53 |
| `SndVCp_3A1_Sjj_% wt_0_CMS_0_0` | Sehr grober Sand (1–2 mm). | Gew.-% | CMS (1986) | 18/53 |

## Bodenwasser und Lagerungsdichte

Grundlage für die nutzbare Feldkapazität. 15 bar ≈ permanenter Welkepunkt; 1/3 bar ≈ Feldkapazität.

| Spalte | Bedeutung | Einheit | Labor | Gefüllt |
|---|---|---|---|---|
| `W15bar_3C2a1a_Njj_0_SSL_0_0` | Wassergehalt bei 15 bar Saugspannung (≈ Welkepunkt), gemessen an lufttrockener Probe < 2 mm. | Gew.-% | SSL (2017) | 35/53 |
| `W15L2_4B2a_Sjj_% wt_0_CMS_0_0` | Wassergehalt bei 15 bar (≈ Welkepunkt), lufttrockene Probe < 2 mm. | Gew.-% | CMS (1986) | 18/53 |
| `w15cly_d-1_S` | Verhältnis 15-bar-Wasser zu Ton (g/g). Typisch ~0,4; deutlich höhere Werte deuten auf amorphe Minerale oder viel organische Substanz. | – | CMS (1986) | 18/53 |
| `Db13bw_d-1_S` | Lagerungsdichte (Trockenrohdichte) des Gesamtbodens bei 1/3 bar (≈ Feldkapazität). | g/cm³ | CMS (1986) | 18/53 |
| `podr13_d-1_S` | Anteil der bei 1/3 bar entwässerten Poren (Luftkapazität / Grobporen) am Gesamtboden. | Vol.-% | CMS (1986) | 18/53 |
| `ADOD_3D1_Njj_0_SSL_0_0` | Verhältnis lufttrocken/ofentrocken (105 °C) – Umrechnungsfaktor, um lufttrocken gemessene Werte auf ofentrockene Basis zu beziehen. | – | SSL (2017) | 35/53 |
| `ADOD_4B5_Sjj_(NA)_0_CMS_0_0` | Verhältnis lufttrocken/ofentrocken (s. o.). | – | CMS (1986) | 18/53 |
| `ADOD_C_4E2a1a1a1_Njf_170_SSL_0_0` | Verhältnis lufttrocken/ofentrocken, für Gips korrigiert. | – | SSL (2017) | 7/53 |

## Kohlenstoff, Stickstoff, Schwefel, organische Substanz

| Spalte | Bedeutung | Einheit | Labor | Gefüllt |
|---|---|---|---|---|
| `Ctot_4H2a_Njf_8_SSL_0_0` | Gesamt-Kohlenstoff (organisch + anorganisch, inkl. Carbonat), Verbrennungsanalyse. | Gew.-% | SSL (2017) | 35/53 |
| `eoctotc_d-1_N` | Geschätzter organischer Kohlenstoff, abgeleitet aus Gesamt-C abzüglich Carbonat-C. | % | SSL (2017) | 35/53 |
| `OC_6A1c_Sjj_% wt_119_CMS_0_0` | Organischer Kohlenstoff (nasschemisch). | Gew.-% | CMS (1986) | 18/53 |
| `Ntot_4H2a_Njf_8_SSL_0_0` | Gesamt-Stickstoff. | Gew.-% | SSL (2017) | 35/53 |
| `Stot_4H2a_Njf_8_SSL_0_0` | Gesamt-Schwefel. | Gew.-% | SSL (2017) | 35/53 |
| `CNrat_d-2_N` | C/N-Verhältnis (Gesamt-C / Gesamt-N) – Hinweis auf Zersetzungsgrad der organischen Substanz. | – | SSL (2017) | 35/53 |
| `Minl2_5A_Njj_0_SSL_0_0` | Mineralgehalt nach Glühverlust bei 400 °C; 100 minus Wert ≈ organische Substanz. | Gew.-% | SSL (2017) | 35/53 |

## pH, Carbonat, Gips, Salz

| Spalte | Bedeutung | Einheit | Labor | Gefüllt |
|---|---|---|---|---|
| `pHh2o_4C1a2a1_Njj_73_SSL_0_0` | pH-Wert in Wasser (Boden:Wasser 1:1). | – | SSL (2017) | 35/53 |
| `pH_h2o_8C1f_Sjj_(NA)_123_CMS_0_0` | pH-Wert in Wasser (1:1). | – | CMS (1986) | 18/53 |
| `pHcacl_4C1a2a2_Njj_73_SSL_0_0` | pH-Wert in 0,01 M CaCl₂ (1:2); meist 0,3–0,6 niedriger als in Wasser, weniger salzabhängig. | – | SSL (2017) | 35/53 |
| `pHcacl_8C1f_Sjj_(NA)_123_CMS_0_0` | pH-Wert in 0,01 M CaCl₂ (1:2). | – | CMS (1986) | 18/53 |
| `CaCO3_4E1a1a1a1_Njf_193_SSL_0_0` | Carbonatgehalt (als CaCO₃-Äquivalent) im Feinboden. | Gew.-% | SSL (2017) | 35/53 |
| `CaCO3_6E1g_Sjj_% wt_118_CMS_0_0` | Carbonatgehalt (als CaCO₃-Äquivalent) im Feinboden. | Gew.-% | CMS (1986) | 16/53 |
| `c_Gyp_4E2a1a1a1_Njf_170_SSL_0_0` | Gipsgehalt im Feinboden (korrigiert). | Gew.-% | SSL (2017) | 11/53 |
| `EC_4F1a1a1_Njj_170_SSL_0_0` | Elektrische Leitfähigkeit (1:2-Extrakt, Schnelltest) – Indikator für Versalzung. Achtung: nicht identisch mit ECe (Sättigungsextrakt), die FAO/Ecocrop-Grenzen verwenden. | dS/m | SSL (2017) | 35/53 |

## Kationenaustausch und Basen

Austauschbare Kationen mit Ammoniumacetat bei pH 7. Es gibt zwei Datensätze („Set 182/16“ und „Set 194/20“) – verschiedene Analysechargen derselben Methode; pro Horizont ist meist nur einer gefüllt.

| Spalte | Bedeutung | Einheit | Labor | Gefüllt |
|---|---|---|---|---|
| `Ca_4B1a1b1_Njj_182_SSL_0_0` | Austauschbares Calcium (Charge 182). | cmol(+)/kg | SSL (2017) | 28/53 |
| `Ca_4B1a1b1_Njj_194_SSL_0_0` | Austauschbares Calcium (Charge 194). | cmol(+)/kg | SSL (2017) | 7/53 |
| `Mg_4B1a1b2_Njj_182_SSL_0_0` | Austauschbares Magnesium (Charge 182). | cmol(+)/kg | SSL (2017) | 28/53 |
| `Mg_4B1a1b2_Njj_194_SSL_0_0` | Austauschbares Magnesium (Charge 194). | cmol(+)/kg | SSL (2017) | 7/53 |
| `Na_4B1a1b4_Njj_182_SSL_0_0` | Austauschbares Natrium (Charge 182). | cmol(+)/kg | SSL (2017) | 28/53 |
| `Na_4B1a1b4_Njj_194_SSL_0_0` | Austauschbares Natrium (Charge 194). | cmol(+)/kg | SSL (2017) | 7/53 |
| `K_4B1a1b3_Njj_182_SSL_0_0` | Austauschbares Kalium (Charge 182). | cmol(+)/kg | SSL (2017) | 28/53 |
| `K_4B1a1b3_Njj_194_SSL_0_0` | Austauschbares Kalium (Charge 194). | cmol(+)/kg | SSL (2017) | 7/53 |
| `CEC_4B1a1a1a1_Njj_182_SSL_0_0` | Kationenaustauschkapazität (KAK) bei pH 7 (Charge 182). | cmol(+)/kg | SSL (2017) | 28/53 |
| `CEC_4B1a1a1a1_Njj_194_SSL_0_0` | Kationenaustauschkapazität (KAK) bei pH 7 (Charge 194). | cmol(+)/kg | SSL (2017) | 7/53 |
| `cecsb_d-19_N` | Summe der austauschbaren Basen Ca+Mg+Na+K (zu Charge 182). | meq/100 g | SSL (2017) | 28/53 |
| `cecsb_d-23_N` | Summe der austauschbaren Basen (zu Charge 194). | meq/100 g | SSL (2017) | 7/53 |
| `BSSBas_d-19_N` | Basensättigung = Basensumme / KAK × 100 (zu Charge 182). In Carbonatböden oft > 100 % gekappt, da Carbonate mitgelöst werden. | % | SSL (2017) | 28/53 |
| `BSSBas_d-23_N` | Basensättigung (zu Charge 194). | % | SSL (2017) | 7/53 |

## Grobboden und Gesamtboden (> 2 mm)

Steine und Kies. Bezugsbasis beachten: „Gesamtboden“, „< 75 mm“ oder Volumen bei 1/3 bar. Nur 1986 gemessen.

| Spalte | Bedeutung | Einheit | Labor | Gefüllt |
|---|---|---|---|---|
| `wpG2_d-1_S` | Gewichtsanteil > 2 mm am Gesamtboden. | Gew.-% | CMS (1986) | 18/53 |
| `wpL2w_d-1_S` | Gewichtsanteil < 2 mm (Feinboden) am Gesamtboden. | Gew.-% | CMS (1986) | 18/53 |
| `wp250u_d-1_S` | Gewichtsanteil ≥ 250 mm (Blöcke) am Gesamtboden. | Gew.-% | CMS (1986) | 18/53 |
| `wp2507_d-1_S` | Gewichtsanteil 75–250 mm (Steine) am Gesamtboden. | Gew.-% | CMS (1986) | 18/53 |
| `wp752_d-1_S` | Gewichtsanteil 2–75 mm (Kies) am Gesamtboden. | Gew.-% | CMS (1986) | 18/53 |
| `wp7520_d-1_S` | Gewichtsanteil 20–75 mm am Gesamtboden. | Gew.-% | CMS (1986) | 18/53 |
| `wp205_d-1_S` | Gewichtsanteil 5–20 mm am Gesamtboden. | Gew.-% | CMS (1986) | 18/53 |
| `wp52_d-1_S` | Gewichtsanteil 2–5 mm am Gesamtboden. | Gew.-% | CMS (1986) | 18/53 |
| `wp275_d-1_S` | Gewichtsanteil 2–75 mm, bezogen auf Material < 75 mm. | Gew.-% | CMS (1986) | 18/53 |
| `wpL2_d-1_S` | Gewichtsanteil < 2 mm, bezogen auf Material < 75 mm. | Gew.-% | CMS (1986) | 18/53 |
| `wp25_d-1_S` | Grobboden 2–5 mm, bezogen auf < 75 mm. | Gew.-% | CMS (1986) | 18/53 |
| `wp520_d-1_S` | Grobboden 5–20 mm, bezogen auf < 75 mm. | Gew.-% | CMS (1986) | 18/53 |
| `wp2075_d-1_S` | Grobboden 20–75 mm, bezogen auf < 75 mm. | Gew.-% | CMS (1986) | 18/53 |
| `wp0175_d-1_S` | Gewichtsanteil 0,1–75 mm, bezogen auf < 75 mm (Taxonomie: < 15 % = „silty“, ≥ 15 % = „loamy“). | Gew.-% | CMS (1986) | 18/53 |
| `vpG2_d-1_S` | Volumenanteil > 2 mm am Gesamtboden (bei 1/3 bar). | Vol.-% | CMS (1986) | 18/53 |
| `vpL2_d-1_S` | Volumenanteil < 2 mm am Gesamtboden. | Vol.-% | CMS (1986) | 18/53 |
| `vp250u_d-1_S` | Volumenanteil ≥ 250 mm. | Vol.-% | CMS (1986) | 18/53 |
| `vp2507_d-1_S` | Volumenanteil 75–250 mm. | Vol.-% | CMS (1986) | 18/53 |
| `vp752_d-1_S` | Volumenanteil 2–75 mm. | Vol.-% | CMS (1986) | 18/53 |
| `vp7520_d-1_S` | Volumenanteil 20–75 mm. | Vol.-% | CMS (1986) | 18/53 |
| `vp205_d-1_S` | Volumenanteil 5–20 mm. | Vol.-% | CMS (1986) | 18/53 |
| `vp52_d-1_S` | Volumenanteil 2–5 mm. | Vol.-% | CMS (1986) | 18/53 |
| `vpt205_d-1_S` | Volumenanteil Sand (0,05–2 mm) am Gesamtboden. | Vol.-% | CMS (1986) | 18/53 |
| `vp5002_d-1_S` | Volumenanteil Schluff (0,002–0,05 mm) am Gesamtboden. | Vol.-% | CMS (1986) | 18/53 |
| `vpL002_d-1_S` | Volumenanteil Ton (< 0,002 mm) am Gesamtboden. | Vol.-% | CMS (1986) | 18/53 |

## Siebdurchgang und Kornverteilungskurve (Ingenieurkennwerte)

Kumulative Kornverteilung bezogen auf Material < 75 mm (3 Zoll), wie in der Geotechnik üblich. Nur 1986.

| Spalte | Bedeutung | Einheit | Labor | Gefüllt |
|---|---|---|---|---|
| `pps2_d-1_S` | Siebdurchgang 2-Zoll-Sieb (50,8 mm). | Gew.-% | CMS (1986) | 18/53 |
| `pps32_d-1_S` | Siebdurchgang 1½-Zoll-Sieb (38,1 mm). | Gew.-% | CMS (1986) | 18/53 |
| `pps1_d-1_S` | Siebdurchgang 1-Zoll-Sieb (25,4 mm). | Gew.-% | CMS (1986) | 18/53 |
| `pps34_d-1_S` | Siebdurchgang ¾-Zoll-Sieb (19,1 mm). | Gew.-% | CMS (1986) | 18/53 |
| `pps38_d-1_S` | Siebdurchgang ⅜-Zoll-Sieb (9,5 mm). | Gew.-% | CMS (1986) | 18/53 |
| `pps4_d-1_S` | Siebdurchgang Sieb Nr. 4 (4,76 mm). | Gew.-% | CMS (1986) | 18/53 |
| `pps10_d-1_S` | Siebdurchgang Sieb Nr. 10 (2,0 mm). | Gew.-% | CMS (1986) | 18/53 |
| `pps40_d-1_S` | Siebdurchgang Sieb Nr. 40 (0,42 mm). | Gew.-% | CMS (1986) | 18/53 |
| `pps200_d-1_S` | Siebdurchgang Sieb Nr. 200 (0,074 mm) – Feinkornanteil. | Gew.-% | CMS (1986) | 18/53 |
| `pps20m_d-1_S` | Anteil < 20 µm. | Gew.-% | CMS (1986) | 18/53 |
| `pps5m_d-1_S` | Anteil < 5 µm. | Gew.-% | CMS (1986) | 18/53 |
| `pps2m_d-1_S` | Anteil < 2 µm (≈ Ton). | Gew.-% | CMS (1986) | 18/53 |
| `cc1_d-1_S` | Kumulativer Anteil < 1 mm. | Gew.-% | CMS (1986) | 18/53 |
| `cc5_d-1_S` | Kumulativer Anteil < 0,5 mm. | Gew.-% | CMS (1986) | 18/53 |
| `cc25_d-1_S` | Kumulativer Anteil < 0,25 mm. | Gew.-% | CMS (1986) | 18/53 |
| `cc10_d-1_S` | Kumulativer Anteil < 0,1 mm. | Gew.-% | CMS (1986) | 18/53 |
| `cc05_d-1_S` | Kumulativer Anteil < 0,05 mm. | Gew.-% | CMS (1986) | 18/53 |
| `cc60p_d-1_S` | Korndurchmesser d60 (60 % der Masse sind feiner). | mm | CMS (1986) | 18/53 |
| `cc50p_d-1_S` | Korndurchmesser d50 (Median). | mm | CMS (1986) | 18/53 |
| `cc10p_d-1_S` | Korndurchmesser d10 (10 % sind feiner). | mm | CMS (1986) | 18/53 |
| `gunfr_d-1_S` | Ungleichförmigkeitszahl Cu = d60/d10. | – | CMS (1986) | 18/53 |
| `gcurv_d-1_S` | Krümmungszahl Cc = d30² / (d10 · d60). | – | CMS (1986) | 18/53 |

## Tonfreie Kornverteilung

Kornfraktionen umgerechnet auf eine tonfreie Basis – wird u. a. zur Prüfung von Schichtwechseln (Lithologie) im Profil verwendet. Nur 1986.

| Spalte | Bedeutung | Einheit | Labor | Gefüllt |
|---|---|---|---|---|
| `cfsand_d-1_S` | Sand 0,05–2 mm, tonfreier Gesamtboden. | Gew.-% | CMS (1986) | 18/53 |
| `cffsi_d-1_S` | Schluff 0,002–0,05 mm, tonfreier Gesamtboden. | Gew.-% | CMS (1986) | 18/53 |
| `cfL002_d-1_S` | Ton < 0,002 mm, auf tonfreier Gesamtboden-Basis. | Gew.-% | CMS (1986) | 18/53 |
| `cfvcsa_d-1_S` | Sehr grober Sand 1–2 mm, tonfreier Feinboden. | Gew.-% | CMS (1986) | 1/53 |
| `cfcsnd_d-1_S` | Grobsand 0,5–1 mm, tonfreier Feinboden. | Gew.-% | CMS (1986) | 4/53 |
| `cfmsnd_d-1_S` | Mittelsand 0,25–0,5 mm, tonfreier Feinboden. | Gew.-% | CMS (1986) | 14/53 |
| `cffsnd_d-1_S` | Feinsand 0,1–0,25 mm, tonfreier Feinboden. | Gew.-% | CMS (1986) | 18/53 |
| `cfvfs_d-1_S` | Sehr feiner Sand 0,05–0,1 mm, tonfreier Feinboden. | Gew.-% | CMS (1986) | 18/53 |
| `cfcsi_d-1_S` | Grobschluff 0,02–0,05 mm, tonfreier Feinboden. | Gew.-% | CMS (1986) | 18/53 |
| `cfffsi_d-1_S` | Feinschluff 0,002–0,02 mm, tonfreier Feinboden. | Gew.-% | CMS (1986) | 18/53 |
| `cfcly_d-1_S` | Ton < 0,002 mm, auf tonfreier Feinboden-Basis. | Gew.-% | CMS (1986) | 18/53 |

## Hinweise für die Auswertung

- **Feldkapazität (1/3 bar) ist nicht direkt gemessen**, nur der Welkepunkt (15 bar). Für die nutzbare Feldkapazität muss sie geschätzt werden, z. B. per Pedotransferfunktion (Saxton & Rawls 2006) aus Ton, Sand und organischem Kohlenstoff.
- **Lagerungsdichte** (`Db13bw_d-1_S`) liegt nur für die Profile von 1986 vor.
- **Volumetrischer Wassergehalt** = gravimetrischer Wassergehalt (Gew.-%) × Lagerungsdichte (g/cm³).
- **Kohlenstoff:** 2017 wurde Gesamt-C gemessen (in Kalkhorizonten inkl. Carbonat-C!); organischer C steht dort in `eoctotc_d-1_N`. 1986 ist organischer C direkt gemessen (`OC_6A1c_…`).
- **EC** ist ein 1:2-Schnelltest und nicht direkt mit der ECe (Sättigungsextrakt) vergleichbar, auf die sich FAO- und ECOCROP-Salzgrenzen beziehen.
