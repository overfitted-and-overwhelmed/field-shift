"""Configuration and crop parameter models for temperature risk scoring."""

from dataclasses import dataclass
from pathlib import Path
from typing import Final
import pandas as pd

# Default project paths
PACKAGE_DIR: Final[Path] = Path(__file__).resolve().parents[2]
DEFAULT_DATA_DIR: Final[Path] = PACKAGE_DIR / "data"
DEFAULT_ECOCROP_PATH: Final[Path] = DEFAULT_DATA_DIR / "base-data" / "ecocrop" / "ecocrop_selected_crops.csv"
DEFAULT_NASS_PATH: Final[Path] = DEFAULT_DATA_DIR / "base-data" / "nass" / "kansas_crop_calendar_long.csv"
DEFAULT_POWER_PATH: Final[Path] = DEFAULT_DATA_DIR / "processed" / "climate_data" / "power_daily_long.csv"

# Default scoring and simulation parameters
DEFAULT_KILL_PENALTY: Final[float] = 100.0
DEFAULT_WINTER_REST_START: Final[tuple[int, int]] = (11, 1)   # Nov 1 (month, day)
DEFAULT_WINTER_REST_END: Final[tuple[int, int]] = (3, 31)     # Mar 31 (month, day)
DEFAULT_WINTER_WHEAT_REST_KILL_TEMP: Final[float] = -20.0

# Crop mapping: NASS crop key -> Ecocrop name / metadata
CROP_MAPPINGS: Final[dict[str, dict[str, str | int | bool]]] = {
    "winter_wheat": {
        "ecocrop_de": "Winterweizen",
        "display_name": "Winterweizen",
        "ecocrop_id": 2114,
        "is_winter_crop": True,
    },
    "corn": {
        "ecocrop_de": "Mais",
        "display_name": "Mais",
        "ecocrop_id": 2175,
        "is_winter_crop": False,
    },
    "sorghum": {
        "ecocrop_de": "Sorghum",
        "display_name": "Hirse",
        "ecocrop_id": 48747,
        "is_winter_crop": False,
    },
    "soybean": {
        "ecocrop_de": "Soja",
        "display_name": "Soja",
        "ecocrop_id": 1150,
        "is_winter_crop": False,
    },
    "sunflower": {
        "ecocrop_de": "Sonnenblume",
        "display_name": "Sonnenblume",
        "ecocrop_id": 1191,
        "is_winter_crop": False,
    },
}


@dataclass(frozen=True)
class CropConfig:
    """Consolidated thermal parameters and calendar windows for a single crop."""

    crop_key: str
    display_name: str
    ecocrop_de: str
    ecocrop_id: int
    is_winter_crop: bool

    # Ecocrop thermal limits (°C)
    temp_opt_min: float
    temp_opt_max: float
    temp_abs_min: float
    temp_abs_max: float
    killing_temp_early_growth: float | None
    killing_temp_during_rest: float | None

    # Effective kill threshold (°C), only during the winter rest of winter crops. Outside it no crop has a
    # documented killing temperature for the whole season, so cold only counts as stress (see README).
    kill_temp_rest: float | None

    # NASS Calendar windows (day of year)
    planting_begin: int
    planting_most_active_start: int
    planting_most_active_end: int
    planting_end: int
    harvest_begin: int
    harvest_most_active_start: int
    harvest_most_active_end: int
    harvest_end: int | None = None


def load_crop_configs(
    ecocrop_path: Path | str = DEFAULT_ECOCROP_PATH,
    nass_path: Path | str = DEFAULT_NASS_PATH,
    winter_wheat_rest_kill: float = DEFAULT_WINTER_WHEAT_REST_KILL_TEMP,
) -> dict[str, CropConfig]:
    """Load and combine Ecocrop limits and NASS calendar windows for the 5 target crops.

    Parameters:
        ecocrop_path: Path to ecocrop_selected_crops.csv.
        nass_path: Path to kansas_crop_calendar_long.csv.
        winter_wheat_rest_kill: Kill threshold (°C) for winter wheat during dormancy.

    Returns:
        Dictionary mapping crop_key to CropConfig.
    """
    ecocrop_df = pd.read_csv(ecocrop_path)
    nass_df = pd.read_csv(nass_path)

    configs: dict[str, CropConfig] = {}

    for crop_key, meta in CROP_MAPPINGS.items():
        ecocrop_de = meta["ecocrop_de"]
        ecocrop_id = int(meta["ecocrop_id"])
        display_name = str(meta["display_name"])
        is_winter_crop = bool(meta["is_winter_crop"])

        # Match Ecocrop row by ID or name
        eco_rows = ecocrop_df[ecocrop_df["ecocrop_id"] == ecocrop_id]
        if eco_rows.empty:
            eco_rows = ecocrop_df[ecocrop_df["crop_de"] == ecocrop_de]
        if eco_rows.empty:
            raise ValueError(f"Crop {crop_key} (ecocrop_id={ecocrop_id}) not found in {ecocrop_path}")

        eco_row = eco_rows.iloc[0]

        temp_opt_min = float(eco_row["temp_opt_min"])
        temp_opt_max = float(eco_row["temp_opt_max"])
        temp_abs_min = float(eco_row["temp_abs_min"])
        temp_abs_max = float(eco_row["temp_abs_max"])

        early_kill = (
            float(eco_row["killing_temp_early_growth"])
            if pd.notna(eco_row["killing_temp_early_growth"])
            else None
        )
        rest_kill = (
            float(eco_row["killing_temp_during_rest"])
            if pd.notna(eco_row["killing_temp_during_rest"])
            else None
        )

        # No kill threshold outside the winter rest: Ecocrop has none for corn, sorghum and soybean, and its
        # early-growth value (wheat, sunflower 0 °C) is for seedlings only, not for the whole season
        kill_temp_rest = winter_wheat_rest_kill if is_winter_crop else rest_kill

        # Match NASS calendar parameters
        crop_nass = nass_df[nass_df["crop"] == crop_key]
        if crop_nass.empty:
            raise ValueError(f"Crop key {crop_key} not found in NASS calendar {nass_path}")

        nass_dict = dict(zip(crop_nass["parameter"], crop_nass["value"], strict=False))

        required_params = [
            "planting_begin",
            "planting_most_active_start",
            "planting_most_active_end",
            "planting_end",
            "harvest_begin",
            "harvest_most_active_start",
            "harvest_most_active_end",
        ]
        for param in required_params:
            if param not in nass_dict:
                raise ValueError(f"Missing required NASS parameter '{param}' for crop {crop_key}")

        config = CropConfig(
            crop_key=crop_key,
            display_name=display_name,
            ecocrop_de=str(ecocrop_de),
            ecocrop_id=ecocrop_id,
            is_winter_crop=is_winter_crop,
            temp_opt_min=temp_opt_min,
            temp_opt_max=temp_opt_max,
            temp_abs_min=temp_abs_min,
            temp_abs_max=temp_abs_max,
            killing_temp_early_growth=early_kill,
            killing_temp_during_rest=rest_kill,
            kill_temp_rest=kill_temp_rest,
            planting_begin=int(nass_dict["planting_begin"]),
            planting_most_active_start=int(nass_dict["planting_most_active_start"]),
            planting_most_active_end=int(nass_dict["planting_most_active_end"]),
            planting_end=int(nass_dict["planting_end"]),
            harvest_begin=int(nass_dict["harvest_begin"]),
            harvest_most_active_start=int(nass_dict["harvest_most_active_start"]),
            harvest_most_active_end=int(nass_dict["harvest_most_active_end"]),
            harvest_end=int(nass_dict["harvest_end"]) if "harvest_end" in nass_dict else None,
        )
        configs[crop_key] = config

    return configs
