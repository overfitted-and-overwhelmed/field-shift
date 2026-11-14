"""Feature engineering on the cleaned NASA POWER daily series (time series only, no static data).

Writes two long-format files (lat, lon, <date|year>, parameter, value, unit):
  data/processed/features_daily_long.csv    derived daily features (ET0, balances, rolling, anomalies)
  data/processed/features_annual_long.csv   per-year agro-climate indicators

Usage: uv run python src/features_timeseries.py
"""
from pathlib import Path

import numpy as np
import pandas as pd

PROC = Path("data/processed")
CLIM = ("1991-01-01", "2020-12-31")  # reference period for anomalies
GROWING = [4, 5, 6, 7, 8, 9]          # Apr-Sep


def load():
    d = pd.read_csv(PROC / "power_daily_long.csv", parse_dates=["date"])
    lat, lon = d.lat.iloc[0], d.lon.iloc[0]
    terr = pd.read_csv(PROC / "terrain_long.csv")
    z = float(terr.loc[terr.parameter == "elevation", "value"].iloc[0])
    return d.pivot(index="date", columns="parameter", values="value"), lat, lon, z


def et0_fao56(w, lat_deg, z):
    """FAO-56 Penman-Monteith reference evapotranspiration [mm/day] (G = 0 for daily steps)."""
    tmax, tmin, tm = w.air_temperature_max, w.air_temperature_min, w.air_temperature_mean
    rs, u2, rh = w.solar_radiation, w.wind_speed, w.relative_humidity  # u2 is already 2 m
    es = lambda t: 0.6108 * np.exp(17.27 * t / (t + 237.3))
    e_s, ea = (es(tmax) + es(tmin)) / 2, es(tm) * rh / 100
    doy = w.index.day_of_year.values
    lat = np.radians(lat_deg)
    dr = 1 + 0.033 * np.cos(2 * np.pi * doy / 365)
    dec = 0.409 * np.sin(2 * np.pi * doy / 365 - 1.39)
    ws = np.arccos(-np.tan(lat) * np.tan(dec))
    ra = 24 * 60 / np.pi * 0.0820 * dr * (ws * np.sin(lat) * np.sin(dec) + np.cos(lat) * np.cos(dec) * np.sin(ws))
    rso = (0.75 + 2e-5 * z) * ra
    rnl = 4.903e-9 * (((tmax + 273.16) ** 4 + (tmin + 273.16) ** 4) / 2) * (0.34 - 0.14 * np.sqrt(ea)) \
        * (1.35 * np.clip(rs / rso, 0.3, 1.0) - 0.35)
    rn = 0.77 * rs - rnl
    gamma = 0.000665 * 101.3 * ((293 - 0.0065 * z) / 293) ** 5.26
    delta = 4098 * es(tm) / (tm + 237.3) ** 2
    et0 = (0.408 * delta * rn + gamma * 900 / (tm + 273) * u2 * (e_s - ea)) / (delta + gamma * (1 + 0.34 * u2))
    return et0.clip(lower=0), (e_s - ea)


def run_length(flag: pd.Series) -> pd.Series:
    """Length of the current consecutive run of True values (0 where False)."""
    grp = (flag != flag.shift()).cumsum()
    return flag.astype(int).groupby(grp).cumsum() * flag.astype(int)


def smooth_clim(s: pd.Series) -> pd.Series:
    """Day-of-year climatology over CLIM period, circular +/-7 day smoothing, keyed by (month, day)."""
    ref = s[CLIM[0]:CLIM[1]]
    clim = ref.groupby([ref.index.month, ref.index.day]).mean()
    v = clim.values
    sm = pd.Series(np.concatenate([v[-7:], v, v[:7]])).rolling(15, center=True).mean().values[7:-7]
    return pd.Series(sm, index=clim.index)


def anomaly(s: pd.Series) -> pd.Series:
    clim = smooth_clim(s.dropna())
    base = pd.Series(list(zip(s.index.month, s.index.day))).map(clim).values
    return s - base


def daily_features(w, lat, z):
    et0, vpd = et0_fao56(w, lat, z)
    tmax, tmin, tm, p = w.air_temperature_max, w.air_temperature_min, w.air_temperature_mean, w.precipitation
    f = {}
    f["reference_evapotranspiration"] = (et0, "mm/day")
    f["water_balance"] = (p - et0, "mm/day")
    f["air_temperature_range"] = (tmax - tmin, "C")
    f["vapor_pressure_deficit"] = (vpd, "kPa")
    # growing degree days, daily temperatures capped (corn-style, base 10 / cap 30) and uncapped base 0 (winter wheat)
    gdd10 = ((tmax.clip(10, 30) + tmin.clip(10, 30)) / 2 - 10).clip(lower=0)
    f["growing_degree_days_base_10"] = (gdd10, "C_day")
    f["growing_degree_days_base_0"] = (((tmax + tmin) / 2).clip(lower=0), "C_day")
    f["growing_degree_days_base_10_cumulative"] = (gdd10.groupby(w.index.year).cumsum(), "C_day")
    f["dry_spell_length"] = (run_length(p < 1.0).astype(float), "days")
    wb = p - et0
    for n in (30, 90):
        f[f"precipitation_sum_{n}d"] = (p.rolling(n, min_periods=n).sum(), "mm")
        f[f"water_balance_sum_{n}d"] = (wb.rolling(n, min_periods=n).sum(), "mm")
    f["heat_days_count_30d"] = ((tmax >= 35).astype(float).rolling(30, min_periods=30).sum(), "days")
    f["air_temperature_mean_anomaly"] = (anomaly(tm), "C")
    f["precipitation_sum_30d_anomaly"] = (anomaly(f["precipitation_sum_30d"][0]), "mm")
    f["water_balance_sum_90d_anomaly"] = (anomaly(f["water_balance_sum_90d"][0]), "mm")
    return f, et0


def annual_features(w, et0):
    yr = w.index.year
    tmax, tmin, tm, p = w.air_temperature_max, w.air_temperature_min, w.air_temperature_mean, w.precipitation
    gs = w.index.month.isin(GROWING)
    gdd10 = ((tmax.clip(10, 30) + tmin.clip(10, 30)) / 2 - 10).clip(lower=0)
    a = {}
    g = lambda s, m=None, how="sum": getattr(s[m] if m is not None else s, "groupby")(yr[m] if m is not None else yr).agg(how)
    a["air_temperature_mean_annual"] = (g(tm, how="mean"), "C")
    a["air_temperature_mean_jun_aug"] = (g(tm, w.index.month.isin([6, 7, 8]), "mean"), "C")
    a["precipitation_total"] = (g(p), "mm")
    a["precipitation_apr_sep"] = (g(p, gs), "mm")
    a["precipitation_max_1d"] = (g(p, how="max"), "mm")
    a["wet_days_ge_1mm"] = (g((p >= 1).astype(int)), "days")
    a["heavy_rain_days_ge_25mm"] = (g((p >= 25).astype(int)), "days")
    a["reference_evapotranspiration_apr_sep"] = (g(et0, gs), "mm")
    a["water_balance_apr_sep"] = (g(p, gs) - g(et0, gs), "mm")
    a["aridity_index"] = (g(p) / g(et0), "1")  # precipitation / ET0, <0.5 = semi-arid
    a["growing_degree_days_base_10_apr_sep"] = (g(gdd10, gs), "C_day")
    a["frost_days"] = (g((tmin < 0).astype(int)), "days")
    a["heat_days_ge_32"] = (g((tmax >= 32).astype(int)), "days")
    a["heat_days_ge_35"] = (g((tmax >= 35).astype(int)), "days")
    dry = run_length(p < 1.0)
    a["max_dry_spell_apr_sep"] = (dry[gs].groupby(yr[gs]).max(), "days")  # note: runs may start before April
    # frost dates: last frost before 1 Jul, first frost from 1 Jul on (day of year)
    doy = w.index.day_of_year
    last_sp = pd.Series(doy, index=w.index)[(tmin < 0) & (w.index.month <= 6)].groupby(yr[(tmin < 0) & (w.index.month <= 6)]).max()
    first_fa = pd.Series(doy, index=w.index)[(tmin < 0) & (w.index.month >= 7)].groupby(yr[(tmin < 0) & (w.index.month >= 7)]).min()
    a["last_spring_frost_doy"] = (last_sp, "day_of_year")
    a["first_fall_frost_doy"] = (first_fa, "day_of_year")
    a["frost_free_days"] = (first_fa - last_sp, "days")
    return a


def to_long(feats, lat, lon, key):
    parts = []
    for name, (s, unit) in feats.items():
        df = s.rename("value").reset_index()
        df.columns = [key, "value"]
        df.insert(1, "parameter", name)
        df["unit"] = unit
        parts.append(df)
    out = pd.concat(parts, ignore_index=True)
    out.insert(0, "lon", lon)
    out.insert(0, "lat", lat)
    return out.sort_values(["parameter", key]).reset_index(drop=True)


if __name__ == "__main__":
    w, lat, lon, z = load()
    daily, et0 = daily_features(w, lat, z)
    to_long(daily, lat, lon, "date").to_csv(PROC / "features_daily_long.csv", index=False)
    ann = to_long(annual_features(w, et0), lat, lon, "year")
    ann.to_csv(PROC / "features_annual_long.csv", index=False)
    dl = pd.read_csv(PROC / "features_daily_long.csv")
    print(f"daily: {len(dl)} rows, {dl.parameter.nunique()} features; annual: {len(ann)} rows, {ann.parameter.nunique()} features")
    print(dl.groupby("parameter").agg(unit=("unit", "first"), n_nan=("value", lambda s: s.isna().sum()),
                                      mean=("value", "mean")).round(2).to_string())
    print(ann.pivot(index="year", columns="parameter", values="value").describe().round(1).T[["mean", "min", "max"]].to_string())
