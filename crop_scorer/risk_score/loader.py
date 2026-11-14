"""Temperature data loading and validation from NASA POWER dataset."""

from pathlib import Path
import pandas as pd

from crop_scorer.risk_score.config import DEFAULT_POWER_PATH

TARGET_TEMP_PARAMETERS = [
    "air_temperature_min",
    "air_temperature_max",
    "air_temperature_mean",
]


def load_temperature_data(
    power_path: Path | str = DEFAULT_POWER_PATH,
    start_date: str = "1991-01-01",
    end_date: str = "2025-12-31",
) -> pd.DataFrame:
    """Load, pivot, and validate daily temperature series (Tmin, Tmax, Tmean).

    Parameters:
        power_path: Path to power_daily_long.csv.
        start_date: Start date string (YYYY-MM-DD).
        end_date: End date string (YYYY-MM-DD).

    Returns:
        DataFrame with columns:
        - date: pd.Timestamp
        - tmin: float (°C, air_temperature_min)
        - tmax: float (°C, air_temperature_max)
        - tmean: float (°C, air_temperature_mean)
        - year: int
        - doy: int (Day of Year, 1-366)
        - month: int (1-12)
        - day: int (1-31)
    """
    path = Path(power_path)
    if not path.exists():
        raise FileNotFoundError(f"Temperature data file not found at: {path}")

    # Read CSV
    df = pd.read_csv(path)

    # Filter for temperature parameters
    temp_df = df[df["parameter"].isin(TARGET_TEMP_PARAMETERS)].copy()
    if temp_df.empty:
        raise ValueError(f"No temperature parameters found in {path}")

    # Pivot so each date has air_temperature_min, air_temperature_max, air_temperature_mean
    pivoted = temp_df.pivot(index="date", columns="parameter", values="value").reset_index()

    # Verify all expected columns exist
    for col in TARGET_TEMP_PARAMETERS:
        if col not in pivoted.columns:
            raise ValueError(f"Missing temperature column '{col}' after pivot")

    # Rename and add date helper columns
    pivoted["date"] = pd.to_datetime(pivoted["date"])
    pivoted = pivoted.sort_values("date").reset_index(drop=True)

    # Filter to requested date range
    start_dt = pd.to_datetime(start_date)
    end_dt = pd.to_datetime(end_date)
    mask = (pivoted["date"] >= start_dt) & (pivoted["date"] <= end_dt)
    pivoted = pivoted[mask].copy().reset_index(drop=True)

    # Format result DataFrame
    result = pd.DataFrame(
        {
            "date": pivoted["date"],
            "tmin": pivoted["air_temperature_min"].astype(float),
            "tmax": pivoted["air_temperature_max"].astype(float),
            "tmean": pivoted["air_temperature_mean"].astype(float),
            "year": pivoted["date"].dt.year.astype(int),
            "doy": pivoted["date"].dt.dayofyear.astype(int),
            "month": pivoted["date"].dt.month.astype(int),
            "day": pivoted["date"].dt.day.astype(int),
        }
    )

    validate_temperature_data(result, start_dt, end_dt)
    return result


def validate_temperature_data(
    df: pd.DataFrame,
    start_dt: pd.Timestamp,
    end_dt: pd.Timestamp,
) -> None:
    """Validate that temperature data covers the complete range without gaps or sentinel values.

    Parameters:
        df: DataFrame containing date, tmin, tmax, tmean.
        start_dt: Expected start timestamp.
        end_dt: Expected end timestamp.
    """
    if df.empty:
        raise ValueError("Temperature dataset is empty")

    # Check date range coverage
    min_date = df["date"].min()
    max_date = df["date"].max()
    if min_date > start_dt:
        raise ValueError(f"Data starts at {min_date.date()}, expected {start_dt.date()}")
    if max_date < end_dt:
        raise ValueError(f"Data ends at {max_date.date()}, expected {end_dt.date()}")

    # Check for complete continuity (no missing calendar days)
    expected_dates = pd.date_range(start_dt, end_dt, freq="D")
    if len(df) != len(expected_dates):
        missing = set(expected_dates) - set(df["date"])
        raise ValueError(
            f"Dataset has {len(df)} rows, expected {len(expected_dates)} days. Missing: {len(missing)} days"
        )

    # Check for NaN / null values
    for col in ["tmin", "tmax", "tmean"]:
        null_count = df[col].isnull().sum()
        if null_count > 0:
            raise ValueError(f"Column '{col}' has {null_count} null/NaN values")

    # Check for sentinel / unreasonable values (e.g. -999 or out-of-earth bounds)
    for col in ["tmin", "tmax", "tmean"]:
        out_of_bounds = df[(df[col] < -60.0) | (df[col] > 65.0)]
        if not out_of_bounds.empty:
            raise ValueError(
                f"Column '{col}' contains values outside reasonable temperature range [-60, 65] °C: "
                f"{out_of_bounds[['date', col]].head()}"
            )

    # Check logical relationship tmin <= tmax
    inverted_days = df[df["tmin"] > df["tmax"]]
    if not inverted_days.empty:
        raise ValueError(
            f"Found {len(inverted_days)} days where tmin > tmax: {inverted_days[['date', 'tmin', 'tmax']].head()}"
        )
