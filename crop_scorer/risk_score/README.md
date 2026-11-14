Bewertet werden nur Tage innerhalb einer Saison, also vom Saattag bis harvest_begin laut NASS.
Frost und Hitze bekommen einen Schweregrad von 0 bis 1.
Ein Kill-Tag zählt +100. Dabei gilt 0 °C als untere Kill-Grenze, außer Ecocrop hat einen eigenen Wert.
Winterweizen hat eine Winterruhe mit −20 °C Kill-Grenze.

Datei	Was sie macht
config.py	Sie liest die Ecocrop-CSV und den NASS-Kalender und baut pro Crop ein CropConfig-Objekt. Dort stehen auch die zentralen Parameter: Kill-Strafe 100, Fallback-Kill-Temperatur 0 °C, Winterruhe 1. Dez. bis 28. Feb. und −20 °C.
loader.py	Sie liest power_daily_long.csv und macht daraus eine Tabelle mit einer Zeile pro Tag und den Spalten tmin, tmax, tmean, year, doy, month, day. Danach prüft sie die Daten.
__init__.py	Sie exportiert die öffentliche API.