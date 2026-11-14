"""Crop temperature risk scoring package."""

from crop_scorer.risk_score.config import (
    CROP_MAPPINGS,
    DEFAULT_DATA_DIR,
    DEFAULT_ECOCROP_PATH,
    DEFAULT_KILL_PENALTY,
    DEFAULT_KILL_TEMP_FALLBACK,
    DEFAULT_NASS_PATH,
    DEFAULT_POWER_PATH,
    DEFAULT_WINTER_REST_END,
    DEFAULT_WINTER_REST_START,
    DEFAULT_WINTER_WHEAT_REST_KILL_TEMP,
    CropConfig,
    load_crop_configs,
)
from crop_scorer.risk_score.loader import load_temperature_data, validate_temperature_data
from crop_scorer.risk_score.rotation import ROTATION_SEASON_COLUMNS, rotation_daily_risk, rotation_season_risk
from crop_scorer.risk_score.seasons import (
    SEASON_COLUMNS,
    aggregate_yearly,
    check_season_lengths,
    simulate_seasons,
)
from crop_scorer.risk_score.severity import SEVERITY_COLUMNS, compute_daily_risk, in_winter_rest

__all__ = [
    "CROP_MAPPINGS",
    "CropConfig",
    "DEFAULT_DATA_DIR",
    "DEFAULT_ECOCROP_PATH",
    "DEFAULT_KILL_PENALTY",
    "DEFAULT_KILL_TEMP_FALLBACK",
    "DEFAULT_NASS_PATH",
    "DEFAULT_POWER_PATH",
    "DEFAULT_WINTER_REST_END",
    "DEFAULT_WINTER_REST_START",
    "DEFAULT_WINTER_WHEAT_REST_KILL_TEMP",
    "ROTATION_SEASON_COLUMNS",
    "SEASON_COLUMNS",
    "SEVERITY_COLUMNS",
    "aggregate_yearly",
    "check_season_lengths",
    "compute_daily_risk",
    "in_winter_rest",
    "load_crop_configs",
    "load_temperature_data",
    "rotation_daily_risk",
    "rotation_season_risk",
    "simulate_seasons",
    "validate_temperature_data",
]
