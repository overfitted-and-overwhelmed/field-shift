# FAO-56: Wachstumsphasen und Kc-Werte

Quelle: Allen et al. (1998), *Crop evapotranspiration – Guidelines for computing crop water requirements*, FAO Irrigation and Drainage Paper 56, Kapitel 6.
<https://www.fao.org/4/x0490e/x0490e0b.htm#tabulated%20kc%20values>

| Datei | Inhalt | Zeilen |
|---|---|---|
| `fao56_table11_stage_lengths.csv` | Tabelle 11: Länge der Wachstumsphasen in Tagen | 167 (72 Kulturen) |
| `fao56_table12_kc.csv` | Tabelle 12: Kc-Werte und maximale Pflanzenhöhe | 124 (94 Kulturen) |

## Wofür man die Werte braucht

Mit den Tabellen berechnet man den Wasserbedarf einer Kultur:

```
ETc = Kc × ETo
```

- **ETo**: Referenzverdunstung einer Grasfläche (mm/Tag), berechnet aus Wetterdaten.
- **Kc**: Kulturkoeffizient (ohne Einheit). Er sagt, wie viel mehr oder weniger die Kultur im Vergleich zum Referenzgras verdunstet. Kc = 1.15 heißt 15 % mehr als das Gras.
- **ETc**: Verdunstung der Kultur (mm/Tag) bei guter Wasserversorgung und ohne Stress.

Kc ändert sich im Lauf der Saison. FAO-56 teilt die Saison in vier Phasen (Tabelle 11) und gibt drei Kc-Stützwerte an (Tabelle 12). Daraus entsteht die Kc-Kurve:

```
Kc
 |            ____________  kc_mid
 |           /            \
 |          /              \
 |_________/                \  kc_end
 | kc_ini
 +---------+------+---------+------+--> Tage nach Aussaat
   L_ini    L_dev    L_mid   L_late
```

| Phase | Kc-Verlauf |
|---|---|
| `L_ini` | konstant `kc_ini` |
| `L_dev` | steigt linear von `kc_ini` auf `kc_mid` |
| `L_mid` | konstant `kc_mid` |
| `L_late` | fällt linear von `kc_mid` auf `kc_end` |

## Die vier Wachstumsphasen

| Phase | Beginn | Ende |
|---|---|---|
| **Initial** (`ini`) | Aussaat oder Pflanzung | etwa 10 % Bodenbedeckung. Der Boden ist kaum bedeckt, die Verdunstung kommt vor allem vom Boden. |
| **Entwicklung** (`dev`) | etwa 10 % Bodenbedeckung | volle Bodenbedeckung (bei vielen Kulturen der Beginn der Blüte) |
| **Hauptsaison** (`mid`) | volle Bodenbedeckung | Beginn der Reife (Blätter vergilben oder fallen ab). Hier ist Kc am höchsten. |
| **Spätsaison** (`late`) | Beginn der Reife | Ernte oder vollständiges Absterben |

## `fao56_table11_stage_lengths.csv`

Eine Zeile ist eine Kombination aus Kultur, Pflanztermin und Region. Dieselbe Kultur kommt deshalb mehrfach vor.

| Spalte | Bedeutung |
|---|---|
| `group` | Kulturgruppe nach FAO, z. B. `Cereals`, `Oil Crops` |
| `crop` | Kultur |
| `variant` | Unterscheidung innerhalb einer Kultur: `year 1` / `year 2` (Cassava), `dry` / `green` (Faba bean). Meist leer. |
| `L_ini` | Länge der Initialphase in Tagen |
| `L_dev` | Länge der Entwicklungsphase in Tagen |
| `L_mid` | Länge der Hauptsaison in Tagen |
| `L_late` | Länge der Spätsaison in Tagen |
| `L_total` | Länge der gesamten Saison in Tagen (Summe der vier Phasen) |
| `plant_date` | Monat der Aussaat oder Pflanzung. Bei mehrjährigen Kulturen der Monat des Blattaustriebs. |
| `region` | Region oder Klima, für das die Werte gelten |
| `footnotes` | Nummer der Fußnote, siehe unten |

Die Werte sind Richtwerte für typische Bedingungen. FAO-56 empfiehlt, sie wenn möglich durch lokale Beobachtungen zu ersetzen.

### Sonderwerte

| Wert | Bedeutung |
|---|---|
| `50/30`, `25/30` | Zwei Werte, die zu den zwei Pflanzterminen in `plant_date` gehören. Beispiel Carrots: `L_mid` = `50/30` bei `plant_date` = `Oct/Jan`. Die Zuordnung in dieser Reihenfolge ist eine Annahme, FAO-56 erklärt sie nicht. |
| `var` | variabel, keine feste Länge (Alfalfa, ganze Saison) |
| `--` | kein Wert angegeben (Grass Pasture) |
| `footnotes` = `st`, `nd` | Reste von „1st“ / „2nd“ (erstes bzw. zweites Jahr oder erster Schnitt), keine echte Fußnote |

Bei Alfalfa (ganze Saison) und Grass Pasture steht in `region` statt eines Orts die Regel für die Saisonlänge.

### Fußnoten

| Nr. | Bedeutung |
|---|---|
| 1 | Crucifers umfasst Kohl, Blumenkohl, Brokkoli und Rosenkohl. Die Saisonlänge schwankt stark je nach Sorte. |
| 2 | Bei Winterweizen verlängern sich die Phasen in Frostklimaten um die Tage ohne Wachstum (Winterruhe). Ohne lokale Daten gilt als Aussaattermin: Winterweizen, wenn das 10-Tage-Mittel der Lufttemperatur im Herbst auf 17 °C fällt, spätestens am 1. Dezember. Sommerweizen, wenn es im Frühjahr auf 5 °C steigt. Körnermais, wenn es auf 13 °C steigt. |
| 3 | Bei Zuckermais dauert die Spätsaison etwa 35 Tage, wenn das Korn ausreifen und trocknen soll. |
| 4 | In Klimaten mit starkem Frost: Alfalfa wächst vom letzten Tag mit −4 °C im Frühjahr bis zum ersten Tag mit −4 °C im Herbst. Gras beginnt 7 Tage früher und endet 7 Tage später. |
| 5 | Olivenbäume treiben im März neue Blätter aus. Siehe Fußnote 24 in Tabelle 12. |

## `fao56_table12_kc.csv`

Eine Zeile ist eine Kultur, teilweise mit Variante.

| Spalte | Bedeutung |
|---|---|
| `group` | Kulturgruppe nach FAO |
| `crop` | Kultur |
| `variant` | Variante, z. B. `grain` / `sweet` (Sorghum), `with frozen soils` (Winter Wheat). Oft leer. |
| `kc_ini` | Kc in der Initialphase |
| `kc_ini_source` | `group`: FAO gibt nur einen Wert für die ganze Gruppe an, er wurde auf die Kultur übertragen. `crop`: eigener Wert für diese Kultur. |
| `kc_mid` | Kc in der Hauptsaison |
| `kc_end` | Kc am Ende der Spätsaison, also am Tag der Ernte |
| `max_height_m` | mittlere maximale Pflanzenhöhe *h* in Metern. Wird für die Klimakorrektur gebraucht. |
| `footnotes` | Nummern der Fußnoten. Mehrere sind mit `;` oder `,` getrennt. |

### Für welche Bedingungen die Werte gelten

- Gesunde, gut versorgte Kultur ohne Wasserstress.
- Subhumides Klima: minimale relative Luftfeuchte **RHmin ≈ 45 %**, Windgeschwindigkeit in 2 m Höhe **u2 ≈ 2 m/s**.
- `kc_ini` gilt für übliche Bewässerung. Wird der Boden sehr häufig nass (tägliche Beregnung oder Regen), kann der Wert auf 1.0 bis 1.2 steigen.

Für trockeneres oder windigeres Klima korrigiert FAO-56 `kc_mid` (Gleichung 62):

```
Kc_mid = Kc_mid(Tabelle) + [0.04 × (u2 − 2) − 0.004 × (RHmin − 45)] × (h / 3)^0.3
```

- Gültig für u2 von 1 bis 6 m/s, RHmin von 20 bis 80 % und h von 0.1 bis 10 m.
- Für `kc_end` gilt dieselbe Korrektur (Gleichung 65), aber nur wenn der Tabellenwert **größer als 0.45** ist.
- Ein `kc_end` unter 0.45 bedeutet, dass die Kultur auf dem Feld abreift und trocknet. Dann wird nicht korrigiert.

Die Gleichungen sind auf der FAO-Seite nur als Bild eingebunden. Die Formel oben ist aus FAO-56 übernommen und sollte vor der Verwendung mit dem Original abgeglichen werden.

### Sonderwerte

| Wert | Bedeutung |
|---|---|
| `0.60-0.35`, `1.0-1.15` | Spanne. Welcher Wert wann gilt, erklärt die Fußnote der Zeile. Ohne Fußnote hängt der Wert von Sorte, Bestandsdichte oder Management ab. |
| `kc_ini` leer | Bei Open Water gibt es keine Initialphase. |
| `footnotes` = `st`, `nd` | Reste von „1st“ / „2nd“ year (Banana), keine echte Fußnote |

### Vermutlicher Fehler in den Rohdaten

In der Zeile `Open Water, > 5 m depth` steht `kc_mid` = `0.6525` und `kc_end` = `1.2525`. Sehr wahrscheinlich sind das die Werte **0.65** und **1.25**, an die beim Einlesen die Fußnotennummer 25 angehängt wurde. Die Rohdatei ist nicht korrigiert.

### Fußnoten

| Nr. | Bedeutung |
|---|---|
| 1 | `kc_ini` gilt für übliche Bewässerung. Bei sehr häufiger Benetzung kann der Wert auf 1.0 bis 1.2 steigen. |
| 2 | Bohnen, Erbsen, Tomaten, Paprika und Gurken werden teils an 1.5 bis 2 m hohen Stangen gezogen. Dann gilt Kc = 1.15 (grüne Bohnen, Paprika, Gurken) oder 1.20 (Tomaten, Trockenbohnen, Erbsen), und *h* ist zu erhöhen. |
| 3 | Cassava: `kc_mid` gilt ohne Stress, `kc_end` berücksichtigt die Ruhephase in der Trockenzeit. |
| 4 | Kartoffel: `kc_end` etwa 0.40 bei spät reifenden Sorten mit Krautabtötung. |
| 5 | Zuckerrübe: `kc_end` kann bis 1.0 steigen, wenn im letzten Monat bewässert wird oder viel Regen fällt. |
| 6 | Erster Wert bei Frischernte, zweiter bei Ernte in trockenem Zustand. |
| 7 | Spargel: Während der Stangenernte bleibt Kc bei `kc_ini`. `kc_mid` gilt nach dem Wiederaustrieb. |
| 8 | Sisal: Kc hängt von Pflanzdichte und Wassermanagement ab. |
| 9 | Der niedrigere Wert gilt für Regenfeldbau mit dünnerem Bestand. |
| 10 | Der höhere Wert gilt bei Handernte. |
| 11 | Körnermais: erster Wert bei Ernte mit hoher Kornfeuchte, zweiter nach Abtrocknen auf dem Feld auf etwa 18 % Kornfeuchte. |
| 12 | Zuckermais: Der Wert gilt bei Frischernte. Reift der Mais auf dem Feld ab, gilt der `kc_end` von Körnermais. |
| 13 | Heu: `kc_mid` ist ein Mittelwert über die ganze Saison mit allen Schnitten. |
| 14 | Heu: Werte für einzelne Schnittperioden (direkt nach dem Schnitt, bei vollem Bestand, direkt vor dem Schnitt). |
| 15 | Rasen der kühlen und der warmen Jahreszeit. Mit sorgfältigem Wassermanagement etwa 0.10 niedriger. |
| 16 | Ananas verdunstet wenig, der größte Teil kommt vom Boden. Tropfbewässerung unter Mulch senkt Kc um etwa 0.10. |
| 17 | Tee: Kc enthält den Wasserbedarf der Schattenbäume. |
| 18 | Obstbäume: `kc_end` gilt vor dem Laubfall. Danach sinkt Kc stark. |
| 19 | Junge Obstanlagen: Kc lässt sich mit Gleichung 94, 97 oder 98 abschätzen. |
| 20 | „Stone fruit“ umfasst Pfirsich, Aprikose, Birne, Pflaume und Pekannuss. |
| 21 | Zitrus ohne Bodenbewuchs: Kc lässt sich aus dem Kronenanteil berechnen (Gleichung 98). |
| 22 | Zitrus mit Bodenbewuchs: gewichteter Wert aus Kc ohne und mit Bewuchs. |
| 23 | Nadelbäume regeln die Verdunstung stark. Kc kann deutlich unter dem Tabellenwert liegen. |
| 24 | Oliven: Werte für 40 bis 60 % Bodenbedeckung durch die Krone. |

Die Fußnoten sind sinngemäß zusammengefasst. Der genaue Wortlaut steht auf der FAO-Seite unter den Tabellen 11 und 12.

## Hinweise für die Kansas-Kulturen

| Kultur | Tabelle 11 (`crop`) | Tabelle 12 (`crop`) |
|---|---|---|
| Soja | `Soybeans` (Region `Central USA`) | `Soybeans` |
| Sonnenblume | `Sunflower` | `Sunflower` |
| Sorghum | `Sorghum` | `Sorghum` (`grain` / `sweet`) |
| Winterweizen | `Winter Wheat` | `Winter Wheat` (`with frozen soils` / `with non-frozen soils`) |
| Mais | `Maize (grain)`, `Maize (sweet)` | `Maize, Field (grain) (field corn)`, `Maize, Sweet (sweet corn)` |
| Roggen / Triticale | kein eigener Eintrag, am nächsten: `Barley/Oats/Wheat`, `Grains (small)` | kein eigener Eintrag, am nächsten: `Winter Wheat`, `Barley`, `Oats` |

Die Kulturnamen sind in beiden Tabellen nicht einheitlich. Für einen Join braucht man eine Zuordnungstabelle.
