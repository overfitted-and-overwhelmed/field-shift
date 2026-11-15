"""Temperature risk on the seasons of a crop rotation (the same days as water_usage and erosion)."""

import pandas as pd

from crop_scorer.risk_score.config import DEFAULT_KILL_PENALTY, CropConfig
from crop_scorer.risk_score.severity import SEVERITY_COLUMNS, compute_daily_risk

ROTATION_SEASON_COLUMNS = [
    "season",
    "crop_key",
    "sow_date",
    "harvest_date",
    "season_days",
    "frost_days",
    "heat_days",
    "kill_days",
    "season_score",
]


def rotation_daily_risk(
    temps: pd.DataFrame,
    crops: dict[str, CropConfig],
    seasons: list[tuple[str, pd.Timestamp, pd.Timestamp]],
    kill_penalty: float = DEFAULT_KILL_PENALTY,
) -> pd.DataFrame:
    """Daily risk on every season day of a rotation. Fallow days have no row.

    Parameters:
        temps: DataFrame from ``load_temperature_data`` (continuous daily series).
        crops: CropConfigs from ``load_crop_configs``.
        seasons: ``[(crop_key, sow, harvest), ...]`` as returned by ``water_usage.build_timeline``.
            A season covers ``[sow, harvest)``: the harvest day is not scored.
        kill_penalty: Daily score on kill days.

    Returns:
        DataFrame with ``season`` (index in ``seasons``), ``crop_key``, ``date`` and ``SEVERITY_COLUMNS``.
    """
    dates = pd.DatetimeIndex(temps["date"], name="date")
    # the daily risk does not depend on the season, so it is computed once per crop
    risk_by_crop = {
        key: compute_daily_risk(temps, crops[key], kill_penalty).set_index(dates)
        for key in {crop for crop, _, _ in seasons}
    }

    frames = []
    for i, (crop_key, sow, harvest) in enumerate(seasons):
        days = risk_by_crop[crop_key].loc[sow : harvest - pd.Timedelta(days=1)]
        if len(days) != (harvest - sow).days:
            raise ValueError(f"season {i} ({crop_key}, {sow.date()}-{harvest.date()}) is not fully covered by temps")
        frames.append(days.reset_index().assign(season=i, crop_key=crop_key))
    return pd.concat(frames, ignore_index=True)[["season", "crop_key", "date", *SEVERITY_COLUMNS]]


def rotation_season_risk(daily: pd.DataFrame) -> pd.DataFrame:
    """Condense ``rotation_daily_risk`` to one row per season.

    Same rules as ``simulate_seasons``: ``season_score`` is the mean daily score over the season days,
    frost_days / heat_days count stress days on non-kill days, kill_days counts cold-kill days.
    ``harvest_date`` is the day after the last season day.
    """
    flags = daily.assign(
        frost=(daily["frost_severity"] > 0) & ~daily["kill"],
        heat=(daily["heat_severity"] > 0) & ~daily["kill"],
    )
    out = (
        flags.groupby(["season", "crop_key"], sort=True)
        .agg(
            sow_date=("date", "min"),
            last_day=("date", "max"),
            season_days=("date", "size"),
            frost_days=("frost", "sum"),
            heat_days=("heat", "sum"),
            kill_days=("kill", "sum"),
            season_score=("daily_score", "mean"),
        )
        .reset_index()
    )
    out["harvest_date"] = out["last_day"] + pd.Timedelta(days=1)
    return out[ROTATION_SEASON_COLUMNS]
