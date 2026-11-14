## Data Sources and Mapping to extracted datasets

Dataset Name | Source | Type | Content
power_daily_long.csv | https://power.larc.nasa.gov/parameters/ | API | temperature, precipitation, rad
soil_ssurgo_long.csv, soil_ssurgo_meta.csv | https://sdmdataaccess.sc.egov.usda.gov/ (USDA SSURGO, Soil Data Access) | API | soil texture, sand/silt/clay, pH, organic matter, available water capacity, bulk density, CEC per horizon (0-200 cm); hydrologic group, drainage and irrigation capability class
soil_long.csv | https://rest.isric.org/soilgrids/v2.0/ (ISRIC SoilGrids) | API | sand/silt/clay, organic carbon, pH, bulk density, CEC, nitrogen in 6 depths (0-200 cm), cross-check for SSURGO
terrain_long.csv | https://api.opentopodata.org/v1/ned10m (USGS 3DEP/NED 10 m) | API | elevation and slope (derived from 3x3 elevation grid)
features_daily_long.csv, features_annual_long.csv | derived from power_daily_long.csv and terrain_long.csv | Derived | FAO-56 reference evapotranspiration, water balance, growing degree days, dry spells, rolling sums, anomalies; annual agro-climate indicators (frost dates, heat days, aridity)
field_profile.json | derived from soil_ssurgo_long.csv, soil_ssurgo_meta.csv, terrain_long.csv; county via https://geo.fcc.gov/api/census/block/find (FCC Census Block API) | Derived | static field profile (location, terrain, soil, constraints) and description of all time series variables