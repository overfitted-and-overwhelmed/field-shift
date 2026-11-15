## Frontend: live data sources and how they are used

Everything the browser fetches **at runtime** on the landing page (map with the fields around the picked point), with link,
usage in the code and what we compute ourselves. Checked on 2026-11-15 (links reachable, endpoints queried, class names compared
with the official list). No API key and no account is used; all requests go straight from the browser.

Numbers on the results page (`/api/explorer`) are **not** live external data. They come from the explorer backend, the scorer and the
datasets, documented in `data/base-data/*_sources.md`.

### 1. Live data (fetched in the browser)

| Data | Source | Type | Content | Used for (code) |
|---|---|---|---|---|
| USDA NASS Cropland Data Layer (CDL), 2008–2021 | https://planetarycomputer.microsoft.com/dataset/usda-cdl (STAC collection `usda-cdl`); original: https://www.nass.usda.gov/Research_and_Science/Cropland/SARS1a.php | API (STAC) + cloud-optimised GeoTIFF, range requests | crop class per 30 m pixel and year, EPSG:5070 | field patches and outlines, crop name and colour, area, crop per year ("Crop each year" strip), map legend. `src/lib/fields/surroundings.ts`, `cdl.ts` |
| Sentinel-2 L2A bands B04 (red), B08 (near infrared), 10 m | https://planetarycomputer.microsoft.com/dataset/sentinel-2-l2a (STAC collection `sentinel-2-l2a`); original: Copernicus Sentinel-2 (ESA) | API (STAC) + cloud-optimised GeoTIFF | surface reflectance, scenes of the last 160 days with < 35 % cloud over the tile | NDVI raster on the map, NDVI value per field. `src/lib/fields/ndvi.ts` |
| Sentinel-2 L2A scene classification (SCL), 20 m | same collection, asset `SCL` | same | per-pixel class (cloud, shadow, snow, …) | cloud mask for NDVI. `ndvi.ts` |
| Sentinel-2 scene list (date, cloud cover of the tile) | `POST https://planetarycomputer.microsoft.com/api/stac/v1/search`, fields `datetime`, `eo:cloud_cover`, `proj:epsg`, `s2:processing_baseline` | API | metadata of the scenes | date bar at the bottom of the map. `ndvi.ts` `findScenes` |
| Read tokens for the files | `GET https://planetarycomputer.microsoft.com/api/sas/v1/token/{collection}` (docs: https://planetarycomputer.microsoft.com/docs/concepts/sas/) | API | anonymous, short-lived read token (SAS) appended to the blob URL | needed to read the GeoTIFFs. `src/lib/fields/stac.ts` |
| Satellite photo (base map) | Esri World Imagery, `https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}`; terms/credits: https://www.arcgis.com/home/item.html?id=10df2279f9684e4a9f6a7f08febac2a9 | map tiles | aerial and satellite imagery, **age varies by place**, not the date of the NDVI scene | background of the map. `src/components/LocationPicker.tsx` |
| Street map (alternative base map) | OpenStreetMap, `https://tile.openstreetmap.org/{z}/{x}/{y}.png`; credits: https://www.openstreetmap.org/copyright | map tiles | street map | layer switch on the map. `LocationPicker.tsx` |

Files are read from these storage hosts, reached through the STAC items:
`landcoverdata.blob.core.windows.net/usda-cdl/…` (CDL) and `sentinel2l2a01.blob.core.windows.net/sentinel2-l2/…` (Sentinel-2).

### 2. Derived in our code (not a data source, but shown to the user)

| Shown value | How it is computed | Where |
|---|---|---|
| Field outline | 4-connected patches of one crop class in the latest CDL year (2021), isolated pixels removed, patches < 30 px (~2.7 ha) dropped, outline traced from pixel edges and smoothed (Chaikin, Douglas–Peucker) | `surroundings.ts` |
| Touching fields split | distance-transform watershed on patches > 600 px; a hill is kept separate only if the pass between two hills is lower than 70 % of the smaller hill (min. radius 7 px = 210 m) | `surroundings.ts` `splitTouching` |
| Area (ha) | pixel count × 900 m² / 10 000 | `surroundings.ts` |
| Distance ("380 m away") | from the marker to the nearest pixel of the field, in EPSG:5070 metres (equal-area projection, error about 1 % at this scale) | `surroundings.ts` |
| "Your field" | the patch that contains the marker. If the marker is not on cropland the banner says so and shows the closest fields | `surroundings.ts` |
| Crop per year in the history strip | the most frequent CDL class among the field's pixels in that year | `surroundings.ts` `mode` |
| "Corn 14× in 14 years" | count of years per class in that history | `FieldPanel.tsx` |
| NDVI | `(NIR − Red) / (NIR + Red)` with NIR = B08, Red = B04 after subtracting the L2A radiometric offset of 1000 for processing baseline ≥ 04.00 (https://sentiwiki.copernicus.eu/web/s2-processing); standard definition by Rouse et al. 1974, https://ntrs.nasa.gov/citations/19740022614 | `ndvi.ts` |
| Masked pixels | SCL classes 0, 1, 3, 8, 9, 10, 11 (no data, saturated, cloud shadow, cloud medium/high, thin cirrus, snow) | `ndvi.ts` |
| NDVI per field | mean over the clear pixels inside the field; shown as "–" if less than 30 % of the field is clear | `ndvi.ts` |
| NDVI image | Sentinel-2 pixels resampled to a north-up Web-Mercator grid (512 px, ~12 m), clipped to the field outlines; colour ramp is ours | `ndvi.ts`, `geo.ts` |
| Crop names | CDL class table in `cdl.ts`, compared on 2026-11-15 against the official list in the STAC item (`classification:classes`, 133 classes): all 88 names we use match | `cdl.ts` |
| Crop colours, NDVI colour ramp | our design choice (crop colours follow the app palette) | `cdl.ts`, `ndvi.ts` |

### 3. Limits to keep in mind

- **CDL year:** the newest CDL on Planetary Computer is **2021** (collection range 2008–2021). Newer years (up to 2025) exist at USDA CropScape,
  but that service has no CORS headers and cannot be called from the browser. The page labels the year it uses.
- **CDL is a classification, not a survey:** NASS derives it from satellite imagery with ground reference data; accuracy differs by crop
  (published in the metadata: https://www.nass.usda.gov/Research_and_Science/Cropland/metadata/meta.php). It maps crops per pixel, not legal parcels, so
  neighbouring fields of the same crop can be merged or split by our outline step.
- **NDVI date vs crop year:** NDVI is from the selected Sentinel-2 scene (up to 5 months back), the crop map from 2021. They are different years.
  The "cloud" figure on the date buttons is the **tile** cloud cover, not the cloud over the field. The field masks use SCL.
- **Coverage:** the CDL covers the contiguous United States. Outside it the page shows an error message. The area read is 3 km around the point.
- **Availability and speed:** Planetary Computer answers are fast to slow (measured 0.3 to 10 s for the same search). There is no fallback server.
- **Terms of the base maps (check before a public release):** the Esri and OpenStreetMap tile servers are used without a key. Both need the
  attribution shown in the map corner. The OSM tile usage policy (https://operations.osmfoundation.org/policies/tiles/) limits heavy use, and Esri's
  terms for this public tile service should be read before anything beyond a demo.
- **Licences:** CDL is a US government product. Sentinel-2 data are free and open (Copernicus). Planetary Computer lists both collections with the license
  field `proprietary` (its generic label for "see the provider's terms"); read the dataset pages above for the exact terms.

### 4. Libraries that touch the data (bundled, no live request)

| Library | Link | Use |
|---|---|---|
| geotiff.js | https://github.com/geotiffjs/geotiff.js | reads the cloud-optimised GeoTIFFs by range request |
| proj4js | https://github.com/proj4js/proj4js | EPSG:5070 (CDL), UTM (Sentinel-2) and Web Mercator conversions |
| Leaflet / react-leaflet | https://leafletjs.com/ | map, polygons, image overlay |
