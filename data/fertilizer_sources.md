Quellen und Dateien fuer den Duengebedarf (Stickstoff), Plan: crop_scorer/fertilizer-need-plan.md

Dateien in data/
fertilizer_n_coefficients.csv        N-Gehalt Korn/Reste, Harvest-Index (Prince, Johnson als Spanne), Soja-Fixierung und Netto-Gutschrift (auf 0 begrenzt),
                                     Boden (org. Substanz 0-23 cm 1,5 %) und Mineralisierung (K-State 20 lb N/ac je 1 % OM, Spanne 14-28, Feld 21-42).
                                     Alle Kandidaten-Zeilen, die gewaehlte ist `selected`. Auswahl wie in crop_scorer/fertilizer_need/config.py (Team).
                                     Spalten nach Zitierpflicht: value, unit, source, locator, url_or_doi, retrieved, kind (data/derived/assumption), note.
                                     Erzeugt mit crop_scorer/fertilizer_need/build_coefficients.py
crop_unit_conversion.csv             bu/acre bzw. lb/acre in t/ha (Kornmasse und Feuchte je Kultur). Kornmassen aus origin/main (Team), Umrechnung abgeleitet.
ksu_mf2586_n_recommendations_long.csv        K-State Duengeformel mit Ausnutzung (ie), Boden-N-Gutschrift (SOM*20), Grenzen. Aus origin/main (Team).
ksu_mf2586_previous_crop_adjustments.csv     Vorfruchtkorrektur in lb N/acre je Vorfrucht. Aus origin/main (Team).
fertilizer_model_references.csv      Belege fuer die offenen Fragen 6 und 7 des Plans: SWAT+ Gleichungen fuer die Auswaschung (exakt + Naeherung des Plans),
                                     Mineralisierung (K-State, UNL, Schoenau als Plausibilitaet), Soja-Entscheidung. Skript: build_model_references.py
cover_crops.csv                      Zwischenfruechte: 14 Arten + Triticale (nicht bewertbar). Eigenschaften aus SARE, Winterverhalten am Standort,
                                     spaeteste Saat aus den lokalen Frostdaten, Empfehlung (recommended/conditional/not_recommended) mit Begruendung.
cover_crop_site_facts.csv            Standort: USDA-Winterhaertezone 6a, Frosttermine, Niederschlag, NRCS-Beendigungszone. Alles mit Quelle.
cover_crop_effects.csv               Literaturwerte fuer Bilanz: N-Mehrbedarf nach Getreide-Deckfrucht, Leguminosen-N, C:N, Bodenwasser-Kosten (K-State).
fertilizer_n_coefficients.csv        enthaelt jetzt auch Zeilen mit crop_part=cover_crop (N gesamt, Trockenmasse, C:N), Spalten value_low/value_high.
                                     Erzeugt mit crop_scorer/fertilizer_need/build_cover_crops.py
nass_yields_kansas_raw.csv           NOCH NICHT VORHANDEN: braucht NASS_API_KEY in .env. Skript: crop_scorer/fertilizer_need/fetch_nass_yields.py
nass_reference_yields.csv            NOCH NICHT VORHANDEN: Mittel je Kultur und Praxis (unbewaessert, bewaessert, alle), Jahre, t/ha, Abfrageparameter

Hinweis zur Pruefung: Die Werte in fertilizer_n_coefficients.csv stammen aus der Dryad-Sammlung (Combined_crop_data.csv). Die dort
genannten Originalquellen (IPNI, USDA, IFA) wurden hier nicht erneut geoeffnet. `source` nennt immer die Sammlung und die Originalquelle.

Combined_crop_data.csv (Datensammlung, Spalten reference_where_data_were_collated / primary_reference_of_dataset je Zeile)
Dryad, DOI 10.5061/dryad.n2z34tn0x  (steht auch in max_sources.md)

IPNI (2014) IPNI Estimates of Nutrient Uptake and Removal
http://www.ipni.net/ipniweb/portal.nsf/0/CBDC9962624CDFCD85257AC60050BBD2/$FILE/Metric%204_1%20&%204_5%200115.pdf
Als Kandidat in der Tabelle (pflanzenteil-genaue Zeilen, z. B. 'Corn stover'). Gewaehlt ist wie im Team-Config die IFA-Zeile (Korn) und die FAO-Zeile (Reste).

FAO (2020) FAOSTAT Domain Soil Nutrient Budget, Metadata (Primaerquelle IPNI-Rechner)
https://fenixservices.fao.org/faostat/static/documents/ESB/ESB_e.pdf
Gewaehlte Zeilen fuer N in Reststoffen (N_pc_fresh, World).

International Fertilizer Association (2020): N im Korn (N_pc_fresh) und Soja N-Fixierung 45 kg N/t Korn (brutto, Quelle dort IPNI)
https://api.ifastat.org/reports/download/12965
Gewaehlte Zeilen fuer N im Korn. Der Link antwortete am 2026-11-15 nicht, der Bericht selbst wurde nicht geoeffnet. Offen: Meint die 45 Korn oder ganze Pflanze?

USDA (2009) Chapter 6 Role of Plants in Waste Management, Agricultural Waste Management Field Handbook
https://directives.sc.egov.usda.gov/OpenNonWebContent.aspx?content=6621.wba
Nur Gegenprobe: N in Trockenmasse fuer USA (Kilmer 1982; Morrison 1956; Sanchez 1976; USDA 1985).

Unkovich et al. (2010) A review of biological yield and harvest index in Australian field crops, Advances in Agronomy
DOI 10.1016/S0065-2113(10)05005-4   https://www.sciencedirect.com/science/article/abs/pii/S0065211310050054
Harvest-Index, USA-Zeilen (primaer Prince et al. 2001 und Johnson et al. 2006). Der Review ist australisch, die USA-Werte sind darin zitiert.

K-State Research and Extension, MF2586 Soil Test Interpretations and Fertilizer Recommendations (Ruiz Diaz, Jan 2024)
https://bookstore.ksre.ksu.edu/pubs/soil-test-interpretations-and-fertilizer-recommendations_MF2586.pdf
Seitenzahl je Zeile in den ksu_*-Dateien (pdf_page). Mineralisierung als Boden-N-Gutschrift SOM*20 lb N/acre je 1 % organische Substanz.

USDA ERS, Agricultural Handbook 697: Weights, Measures and Conversion Factors for Agricultural Commodities
https://www.ers.usda.gov/publications/pub-details?pubid=41881
Kornmasse je Bushel (Mais/Hirse 56 lb, Weizen/Soja 60 lb). Feuchte-Bezug aus K-State MF2586 Tabelle 1.

USDA NASS Quick Stats API (Referenzertraege Kansas, Umfrage, 1991-2025)
https://quickstats.nass.usda.gov/api
Kostenloser Key, Zeile NASS_API_KEY=... in .env (git-ignoriert). Abfrageparameter stehen im Skript und in nass_reference_yields.csv.

--- Zwischenfruechte ---

Clark, A. (ed.) 2007. Managing Cover Crops Profitably, 3rd ed. SARE Handbook Series Book 9 (3. Auflage 2012)
https://www.sare.org/wp-content/uploads/Managing-Cover-Crops-Profitably.pdf
Alle Artwerte (Chart 2, 3A, 3B, 4B und Kapitel). Buchseite = PDF-Seite minus 2, Seiten stehen in `source`/`locator`.
Grenze: US-weite Sammlung von 2007, keine Kansas-Tabelle. N gesamt = ganze Pflanze inkl. Boden-N, keine Fixierung.

Simon, L. M. (2024) Cover crops to regenerate soils and increase profitability in dryland crop production in the semi-arid central Great Plains,
PhD dissertation, Kansas State University
https://krex.k-state.edu/items/0d3734ba-9a62-4ca7-90d8-e10387a5b60b   (hdl 2097/44223)
Zahlen zum Bodenwasser (21 mm weniger zur Weizensaat) und Sorghum-Ertrag (-11 %). Nur die Zusammenfassung der Seite wurde gelesen, nicht die Arbeit.
Es nennt keine Arten und keinen Ort in Kansas.

NRCS Cover Crop Termination Guidelines, Non-Irrigated Cropland, June 2013 (RMA)
https://www.rma.usda.gov/sites/default/files/2024-12/NRCS-Cover-Crop-Termination-Guidelines-version-1-June-2013.pdf
Zone 1: 35 Tage, Zone 2: 15 Tage vor der Saat beenden. Kearny County liegt auf der Karte an der Grenze von Zone 1/2, nicht aufloesbar. Bei RMA/NRCS pruefen.

USDA Plant Hardiness Zone Map (2012), abgefragt ueber https://phzmapi.org/67838.json (ZIP 67838): Zone 6a, -10 bis -5 F.
Die gerasterten POWER-Daten geben einen waermeren Extremwert (3,6 F, Zone 7a). Verwendet wird 6a.

Nicht beschafft: K-State- und NRCS-Kansas-Tabellen (Kansas 340, MLRA-Saatfenster). Die K-State-Extension-Seite von 2018 ist offline und wurde
nicht verwendet. Triticale hat in SARE keine Tabellenzeile, deshalb keine Werte.

--- Auswaschung, Mineralisierung, Boden (Fragen 6 und 7 des Plans) ---

SWAT+ Theoretical Documentation, Nitrate Movement (Gleichungen 4:2.1.2 und 4:2.1.8)
https://swatplus.gitbook.io/io-docs/theoretical-documentation/section-4-erosion/nutrient-transport/nitrate-movement
Mischungsmodell fuer Nitrat im Sickerwasser. Die Formel des Plans ist die lineare Naeherung davon (Herleitung in fertilizer_model_references.csv, nicht in der Quelle).
Offen: theta_e (ANION_EXCL) und SAT_ly (gesaettigter Wassergehalt) sind im Repo noch nicht beschafft.

University of Nebraska-Lincoln CropWatch, Credit Soil Organic Matter for Nitrogen
https://cropwatch.unl.edu/credit-soil-organic-matter-nitrogen
0,14 x Ertragsziel je 1 % OM (max. 3 %), Beispiel 28 lb N/ac je 1 % bei 200 bu/ac. Gibt Unter- und Obergrenze der Mineralisierungs-Sensitivitaet.

Top Crop Manager, Understanding N mineralization (zitiert J. Schoenau, University of Saskatchewan)
https://www.topcropmanager.com/understanding-n-mineralization-10515/
15-50 kg N/ha je Saison im Oberboden, Schaetzung. Nur Plausibilitaetscheck, Sekundaerquelle.

USDA NRCS SSURGO, lokal in data/base-data/z_processed/soil_ssurgo_long.csv (organic_matter: 1,5 % 0-23 cm, 0,7 % 23-69 cm, 0,3 % 69-200 cm, Ulysses 65 %)
https://websoilsurvey.nrcs.usda.gov/
