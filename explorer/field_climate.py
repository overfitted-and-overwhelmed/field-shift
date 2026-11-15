"""WP1 Field & Climate: the ``field``, ``crops`` and ``climate`` blocks of explorer.json.

Reads only from ``data/processed/`` and returns the pydantic models from ``schema.py``,
so every block is validated when it is built. Units are converted to US (mm -> in, m -> ft);
temperature stays in °C.

``PROVENANCE`` and ``SOURCES`` are this package's entries for the export; the pipeline (WP7)
merges them with those of the other packages.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from explorer.paths import CDL_HISTORY, CLIMATE_ANNUAL, FIELD_PROFILE
from explorer.schema import Climate, Crop, CropId, FieldInfo, ProvenanceEntry, Source

MM_PER_IN = 25.4
M_PER_FT = 0.3048

# Year of the first sowing of the explored rotations (a winter wheat start is harvested the year after).
# CDL ends in 2025 and 2026 is already in the ground.
ROTATION_START_YEAR = 2027

# CDL code -> our crop id (codes from the NASS CDL legend). Every other class, including
# fallow and double crops, stays as free text in crop_history.
CDL_TO_CROP: dict[int, CropId] = {1: "corn", 4: "sorghum", 5: "soybean", 6: "sunflower", 24: "winter_wheat", 205: "triticale"}

CROPS: dict[CropId, Crop] = {
    "corn": Crop(label="Corn", yield_unit="bu", season="summer", legume=False, is_cover=False),
    "sorghum": Crop(label="Sorghum", yield_unit="bu", season="summer", legume=False, is_cover=False),
    "soybean": Crop(label="Soybean", yield_unit="bu", season="summer", legume=True, is_cover=False),
    "winter_wheat": Crop(label="Winter wheat", yield_unit="bu", season="winter", legume=False, is_cover=False),
    "sunflower": Crop(label="Sunflower", yield_unit="lb", season="summer", legume=False, is_cover=False),
    "triticale": Crop(label="Triticale (cover)", yield_unit=None, season="winter", legume=False, is_cover=True),
}

# parameters read from features_annual_long.csv -> the unit we expect there
CLIMATE_UNITS = {
    "precipitation_total": "mm",
    "reference_evapotranspiration_apr_sep": "mm",
    "water_balance_apr_sep": "mm",  # rain minus ET0, so the deficit is its negative
    "heat_days_ge_35": "days",
}

PROVENANCE: dict[str, ProvenanceEntry] = {
    "field.elevation_ft": ProvenanceEntry(label="measured", source="usgs_3dep"),
    "field.slope_pct": ProvenanceEntry(label="measured", source="usgs_3dep"),
    "field.soil": ProvenanceEntry(label="measured", source="ssurgo"),
    "field.crop_history": ProvenanceEntry(label="measured", source="nass_cdl"),
    # 2026 is not in the CDL yet, so the crop before the rotation is the last CDL crop
    "field.previous_crop": ProvenanceEntry(label="assumption", source="nass_cdl"),
    "field.rotation_start_year": ProvenanceEntry(label="assumption", source=None),
    "climate.rain_in": ProvenanceEntry(label="measured", source="nasa_power"),
    "climate.heat_days_ge_35": ProvenanceEntry(label="measured", source="nasa_power"),
    # FAO-56 Penman-Monteith from POWER weather (computed by the data team)
    "climate.et0_apr_sep_in": ProvenanceEntry(label="modeled", source="nasa_power"),
    "climate.deficit_apr_sep_in": ProvenanceEntry(label="modeled", source="nasa_power"),
}

# URLs as documented in data/base-data/{benni,caleb}_sources.md; retrieval dates only where documented
SOURCES: dict[str, Source] = {
    "nasa_power": Source(title="NASA POWER daily weather, ~50 km grid", url="https://power.larc.nasa.gov/parameters/"),
    "ssurgo": Source(title="USDA NRCS SSURGO via Soil Data Access", url="https://sdmdataaccess.sc.egov.usda.gov/"),
    "usgs_3dep": Source(title="USGS 3DEP/NED 10 m via OpenTopoData", url="https://api.opentopodata.org/v1/ned10m"),
    "nass_cdl": Source(
        title="USDA NASS Cropland Data Layer via CropScape",
        url="https://nassgeodata.gmu.edu/CropScape/",
        retrieved="2026-11-14",
    ),
}


def build_field(profile_path: Path = FIELD_PROFILE, cdl_path: Path = CDL_HISTORY) -> FieldInfo:
    profile = json.loads(profile_path.read_text(encoding="utf-8"))
    loc, terrain, soil = profile["location"], profile["terrain"], profile["soil"]

    cdl = pd.read_csv(cdl_path).sort_values("year")
    crops = [CDL_TO_CROP.get(code, cls.lower()) for code, cls in zip(cdl["cdl_code"].tolist(), cdl["cdl_class"])]
    # shortcut: fallow and double crops are skipped, the last single crop of ours counts as previous crop
    ours = [c for c in crops if c in CROPS]
    if not ours:
        raise ValueError(f"{cdl_path.name}: no year with one of our crops {list(CROPS)}, cannot set previous_crop")

    return FieldInfo(
        id=profile["field_id"],
        name=f"{loc['county']} County, {loc['state']}",
        lat=loc["lat"],
        lon=loc["lon"],
        elevation_ft=round(terrain["elevation_m"] / M_PER_FT),
        slope_pct=terrain["slope_pct"],
        soil={
            "texture": soil["texture"],
            "water_capacity_in": round(soil["water_capacity_mm"] / MM_PER_IN, 2),
            "organic_matter_pct": soil["organic_matter_pct"],
        },
        crop_history=[{"year": y, "crop": c} for y, c in zip(cdl["year"].tolist(), crops)],
        previous_crop=ours[-1],
        rotation_start_year=ROTATION_START_YEAR,
    )


def build_crops() -> dict[CropId, Crop]:
    return dict(CROPS)


def build_climate(annual_path: Path = CLIMATE_ANNUAL) -> Climate:
    df = pd.read_csv(annual_path)
    df = df[df["parameter"].isin(CLIMATE_UNITS)]
    for param, unit in CLIMATE_UNITS.items():
        found = set(df.loc[df["parameter"] == param, "unit"])
        if found != {unit}:
            raise ValueError(f"{annual_path.name}: '{param}' has unit {found or 'missing'}, expected {unit}")

    wide = df.pivot(index="year", columns="parameter", values="value").sort_index()
    if wide.isna().any().any():
        raise ValueError(f"{annual_path.name}: missing values in {wide.columns[wide.isna().any()].tolist()}")

    def inches(param: str, sign: int = 1) -> list[float]:
        return (sign * wide[param] / MM_PER_IN).round(2).tolist()

    return Climate(
        weather_years=wide.index.astype(int).tolist(),
        rain_in=inches("precipitation_total"),
        et0_apr_sep_in=inches("reference_evapotranspiration_apr_sep"),
        deficit_apr_sep_in=inches("water_balance_apr_sep", sign=-1),
        heat_days_ge_35=wide["heat_days_ge_35"].tolist(),
    )
