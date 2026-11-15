nass
https://esmis.nal.usda.gov/sites/default/release-files/vm40xr56k/dv13zw65p/w9505297d/planting-10-29-2010.pdf
USDA NASS, Field Crops Usual Planting and Harvesting Dates, Agricultural Handbook 628, Oct 2010, Kansas rows
(PDF pages: corn 9, sorghum 23, soybean 25, sunflower 29, winter wheat 34). Dates as day of year (non-leap year).
begin/end = ~5 % / ~95 % planted or harvested, most active = 15-85 %.

Formel fuer effektiven Niederschlag
Assessing Climate Change Impact on Future Reference Evapotranspiration Pattern of West Bengal, India
https://www.scirp.org/journal/paperinformation?paperid=103110
fao56 table 22
https://www.fao.org/4/x0490e/x0490e0e.htm
Allen et al. 1998, FAO Irrigation and Drainage Paper 56, Table 22: maximum effective root depth Zr and
soil water depletion fraction for no stress p (ETc ~5 mm/day). Only the rows of the scorer crops.
Crop names as in Table 12 (FAO lists sorghum as "Sorghum - grain").
Footnote: larger Zr for soils without layering that restricts rooting, for modelling soil water stress or rainfed conditions.

literature/cover_crop_effects.csv
Taken over unchanged from branch feat/fertilizer-need (commit a35c0c7, data/cover_crop_effects.csv), one row per
literature value with source, url_or_doi, locator (page) and retrieval date. Used by the scorer for the cover crop rules:
n_cereal_cover_extra_fert (Clark (ed.) 2007, Managing Cover Crops Profitably, 3rd ed., SARE, p. 46: +25-30 lb N/ac after
a cereal cover, scorer uses 27.5) and termination_zone_1 (NRCS Cover Crop Termination Guidelines, non-irrigated cropland,
June 2013: terminate >= 35 days before planting). The other rows (e.g. Simon 2024, K-State: 21 mm less soil water at wheat
planting and 11 % less sorghum yield after cover crops) are reference only, not used in a calculation.
