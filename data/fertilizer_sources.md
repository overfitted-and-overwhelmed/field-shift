Quellen und Dateien fuer den Duengebedarf (Stickstoff), Plan: crop_scorer/fertilizer-need-plan.md

Dateien in data/
fertilizer_n_coefficients.csv        N-Gehalt Korn/Reste, Harvest-Index, Soja-Fixierung je Kultur. Alle Kandidaten-Zeilen, die gewaehlte ist `selected`.
                                     Spalten nach Zitierpflicht: value, unit, source, locator, url_or_doi, retrieved, kind (data/derived/assumption), note.
                                     Erzeugt mit crop_scorer/fertilizer_need/build_coefficients.py
crop_unit_conversion.csv             bu/acre bzw. lb/acre in t/ha (Kornmasse und Feuchte je Kultur). Kornmassen aus origin/main (Team), Umrechnung abgeleitet.
ksu_mf2586_n_recommendations_long.csv        K-State Duengeformel mit Ausnutzung (ie), Boden-N-Gutschrift (SOM*20), Grenzen. Aus origin/main (Team).
ksu_mf2586_previous_crop_adjustments.csv     Vorfruchtkorrektur in lb N/acre je Vorfrucht. Aus origin/main (Team).
nass_yields_kansas_raw.csv           NOCH NICHT VORHANDEN: braucht NASS_API_KEY in .env. Skript: crop_scorer/fertilizer_need/fetch_nass_yields.py
nass_reference_yields.csv            NOCH NICHT VORHANDEN: Mittel je Kultur und Praxis (unbewaessert, bewaessert, alle), Jahre, t/ha, Abfrageparameter

Hinweis zur Pruefung: Die Werte in fertilizer_n_coefficients.csv stammen aus der Dryad-Sammlung (Combined_crop_data.csv). Die dort
genannten Originalquellen (IPNI, USDA, IFA) wurden hier nicht erneut geoeffnet. `source` nennt immer die Sammlung und die Originalquelle.

Combined_crop_data.csv (Datensammlung, Spalten reference_where_data_were_collated / primary_reference_of_dataset je Zeile)
Dryad, DOI 10.5061/dryad.n2z34tn0x  (steht auch in max_sources.md)

IPNI (2014) IPNI Estimates of Nutrient Uptake and Removal
http://www.ipni.net/ipniweb/portal.nsf/0/CBDC9962624CDFCD85257AC60050BBD2/$FILE/Metric%204_1%20&%204_5%200115.pdf
Gewaehlte Zeilen: N in Korn und Reste (N_pc_fresh, Frischmasse) fuer Mais, Hirse, Soja, Sonnenblume, Winterweizen.

International Fertilizer Association (2020), Soja N-Fixierung 45 kg N/t Korn (brutto, Quelle dort IPNI)
https://api.ifastat.org/reports/download/12965
Offen laut Plan: Meint der Wert Korn oder ganze Pflanze?

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
