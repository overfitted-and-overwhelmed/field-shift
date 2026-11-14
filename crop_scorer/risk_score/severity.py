"""Daily frost / heat severity, kill flags and daily risk score for a single crop."""

import numpy as np
import pandas as pd

from crop_scorer.risk_score.config import (
    DEFAULT_KILL_PENALTY,
    DEFAULT_WINTER_REST_END,
    DEFAULT_WINTER_REST_START,
    CropConfig,
)

SEVERITY_COLUMNS = [
    "frost_severity",
    "heat_severity",
    "kill_cold",
    "kill",
    "stress_flag",
    "comfort_deviation",
    "daily_score",
]


def in_winter_rest(
    month: pd.Series,
    day: pd.Series,
    rest_start: tuple[int, int] = DEFAULT_WINTER_REST_START,
    rest_end: tuple[int, int] = DEFAULT_WINTER_REST_END,
) -> pd.Series:
    """Boolean mask: date lies in the dormancy window (inclusive, wraps over New Year).

    A Feb 29 is treated as part of the window if the window ends on Feb 28.
    """
    md = month * 100 + day
    start = rest_start[0] * 100 + rest_start[1]
    end = rest_end[0] * 100 + rest_end[1]
    if rest_end == (2, 28):
        end = 229  # include leap day

    if start <= end:
        return (md >= start) & (md <= end)
    return (md >= start) | (md <= end)


def _linear_severity(distance: pd.Series, span: float, cap: float | None = 1.0) -> pd.Series:
    """Linear severity for a positive distance beyond a threshold (1.0 after ``span``).

    ``cap`` limits the severity (default 1.0); ``cap=None`` leaves it unbounded.
    """
    if span <= 0:
        raise ValueError(f"Severity span must be > 0, got {span}")
    return (distance / span).clip(lower=0.0, upper=cap)


def compute_daily_risk(
    temps: pd.DataFrame,
    crop: CropConfig,
    kill_penalty: float = DEFAULT_KILL_PENALTY,
    rest_start: tuple[int, int] = DEFAULT_WINTER_REST_START,
    rest_end: tuple[int, int] = DEFAULT_WINTER_REST_END,
) -> pd.DataFrame:
    """Compute daily temperature stress for one crop (independent of the growing season).

    Rules (see README.md):
    - heat_severity: 0 at ``temp_opt_max`` rising linearly, reaching 1 at ``temp_abs_max`` and
      continuing to rise above it (no cap, no heat kill) (on Tmax).
    - frost_severity: 0 at ``temp_opt_min`` rising linearly to 1 at ``temp_abs_min`` (on Tmin),
      capped at 1.
    - kill_cold: Tmin < ``kill_temp_lower``. There is no heat kill.
    - Winter wheat only: in the dormancy window kill_cold uses ``kill_temp_rest`` and
      frost_severity is 0. Heat is unchanged.
    - daily_score: ``kill_penalty`` on kill days, otherwise frost_severity + heat_severity.
      The severity columns keep their raw values on kill days; the score is not double counted.
    - stress_flag: severity > 0 on a non-kill day.
    - comfort_deviation: distance of Tmean from the optimum range, normalised by the distance
      opt->abs on the same side (informational, not part of the score, may exceed 1).

    Parameters:
        temps: DataFrame from ``load_temperature_data`` (needs date, tmin, tmax, tmean, month, day).
        crop: CropConfig of the crop.
        kill_penalty: Daily score assigned to kill days.
        rest_start: (month, day) start of the dormancy window.
        rest_end: (month, day) end of the dormancy window.

    Returns:
        DataFrame with the index of ``temps`` and the columns in ``SEVERITY_COLUMNS``.
    """
    tmin, tmax, tmean = temps["tmin"], temps["tmax"], temps["tmean"]

    cold_span = crop.temp_opt_min - crop.temp_abs_min
    heat_span = crop.temp_abs_max - crop.temp_opt_max

    heat_severity = _linear_severity(tmax - crop.temp_opt_max, heat_span, cap=None)
    frost_severity = _linear_severity(crop.temp_opt_min - tmin, cold_span)

    kill_cold = tmin < crop.kill_temp_lower

    # Dormancy only applies to winter crops (Ecocrop also lists a rest value for sunflower,
    # but it does not overwinter in the field).
    if crop.is_winter_crop and crop.kill_temp_rest is not None:
        rest = in_winter_rest(temps["month"], temps["day"], rest_start, rest_end)
        kill_cold = pd.Series(np.where(rest, tmin < crop.kill_temp_rest, kill_cold), index=temps.index)
        frost_severity = frost_severity.where(~rest, 0.0)

    kill = kill_cold
    severity_sum = frost_severity + heat_severity
    stress_flag = (severity_sum > 0) & ~kill
    daily_score = severity_sum.where(~kill, float(kill_penalty))

    comfort_deviation = pd.Series(
        np.select(
            [tmean < crop.temp_opt_min, tmean > crop.temp_opt_max],
            [
                (crop.temp_opt_min - tmean) / cold_span,
                (tmean - crop.temp_opt_max) / heat_span,
            ],
            default=0.0,
        ),
        index=temps.index,
    )

    return pd.DataFrame(
        {
            "frost_severity": frost_severity,
            "heat_severity": heat_severity,
            "kill_cold": kill_cold.astype(bool),
            "kill": kill.astype(bool),
            "stress_flag": stress_flag.astype(bool),
            "comfort_deviation": comfort_deviation,
            "daily_score": daily_score,
        },
        index=temps.index,
    )
