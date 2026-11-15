"""Run the N balance over all start years of the test rotation and write the results.

    uv run python -m crop_scorer.fertilizer_need.run

Outputs in data/processed/fertilizer_need/ (long format like water_usage):
    fertilizer_need_season_long.csv   one row per crop season and variant, mean over the start years
    fertilizer_need_rotation.csv      per variant: fertilizer need per year of the rotation, mean and 90th percentile over start years
"""

import json

import numpy as np
import pandas as pd

from crop_scorer.fertilizer_need import inputs as I
from crop_scorer.fertilizer_need.balance import SPECIES, Settings, run_balance
from crop_scorer.water_usage.water_usage import FIELD_FILE, FIRST_YEAR, LAST_YEAR, ROTATION, load_crop_params, simulate

VALUE_COLUMNS = {
    "removal": "n_removal",
    "fixation": "n_fixation_own",
    "mineralization_season": "n_mineralization_season",
    "mineralization_fallow": "n_mineralization_fallow",
    "leaching_fallow": "n_leaching_fallow",
    "carried_from_fallow": "n_carried_from_fallow",
    "previous_crop_credit": "n_previous_crop_credit",
    "cover_effect": "n_cover_effect",
    "balance_unfloored": "n_balance_unfloored",
    "leaching_charged": "n_leaching_charged",
    "fertilizer_need": "fertilizer_need",
    "ksu_fertilizer_need": "fertilizer_need_ksu_formula",
}

VARIANTS: dict[str, Settings] = {
    "no_cover": Settings(),
    **{f"cover_{s}": Settings(cover=s) for s in SPECIES},
    "no_cover_theta_low": Settings(theta_e=I.THETA_E_SENSITIVITY[0]),
    "no_cover_theta_high": Settings(theta_e=I.THETA_E_SENSITIVITY[1]),
    "no_cover_min_low": Settings(mineralization="low"),
    "no_cover_min_high": Settings(mineralization="high"),
}


def start_year_runs(rotation: list[str], variants: dict[str, Settings]) -> pd.DataFrame:
    params = load_crop_params()
    frames = []
    for start_year in range(FIRST_YEAR, LAST_YEAR + 1):
        daily, seasons = simulate(rotation, start_year)
        if len(seasons) < len(rotation) + 1:  # the first season has no known previous crop and is skipped
            continue
        for name, settings in variants.items():
            frames.append(run_balance(daily, seasons, params, settings).assign(start_year=start_year, variant=name))
    return pd.concat(frames, ignore_index=True)


def rotation_totals(runs: pd.DataFrame, n_crops: int) -> pd.DataFrame:
    """Per start year and variant: fertilizer need of one full cycle (n_crops consecutive seasons after the first), per year of the cycle."""
    rows = []
    for (variant, start_year), g in runs.groupby(["variant", "start_year"]):
        cycle = g.iloc[:n_crops]
        if len(cycle) < n_crops:
            continue
        years = (pd.Timestamp(int(cycle["harvest_year"].iloc[-1]), 12, 31) - pd.Timestamp(int(cycle["harvest_year"].iloc[0]) - 1, 12, 31)).days / 365.25
        rows.append({"variant": variant, "start_year": start_year, "cycle_years": years,
                     **{c: cycle[c].sum() / years for c in ("fertilizer_need", "balance_unfloored", "ksu_fertilizer_need", "leaching_fallow", "leaching_charged", "removal")}})
    return pd.DataFrame(rows)


def check_config_against_csv() -> None:
    """config.py (hand-copied from Combined_crop_data.csv) must agree with the selected rows of fertilizer_n_coefficients.csv."""
    from crop_scorer.fertilizer_need.config import CROP_COEFFICIENTS

    for crop, c in CROP_COEFFICIENTS.items():
        assert abs(c.grain_n.value - I.coef(crop, "grain", "n_content_fresh")) < 1e-9, crop
        assert abs(c.residue_n.value - I.coef(crop, "residue", "n_content_fresh")) < 1e-9, crop
        assert abs(c.harvest_index.value - I.coef(crop, "grain", "harvest_index")) < 1e-9, crop
        if c.fixation:
            assert abs(c.fixation.value - I.coef(crop, "grain", "n_fixed_gross")) < 1e-9, crop


def sanity_checks(runs: pd.DataFrame) -> None:
    check_config_against_csv()
    assert runs["removal"].between(10, 120).all(), "removal outside 10-120 kg N/ha"
    assert (runs["fertilizer_need"] >= 0).all()
    assert (runs["leaching_fallow"] >= -1e-9).all()
    leaching = runs.groupby("variant")["leaching_fallow"].mean()
    assert leaching["no_cover_theta_high"] >= leaching["no_cover"] >= leaching["no_cover_theta_low"], "more excluded porosity must leach more"
    base = runs[runs["variant"] == "no_cover"]
    rye = runs[runs["variant"] == "cover_cereal_rye"]
    assert rye["cover_days"].gt(0).any(), "rye never fits into a fallow"
    assert (rye["leaching_fallow"].to_numpy() <= base["leaching_fallow"].to_numpy() + 1e-9).all(), "a cover crop must not increase leaching"
    print("[fertilizer] sanity checks passed")


def main() -> None:
    runs = start_year_runs(ROTATION, VARIANTS)
    sanity_checks(runs)
    location = json.loads(FIELD_FILE.read_text())["location"]
    I.OUT_DIR.mkdir(parents=True, exist_ok=True)

    per_season = runs.groupby(["variant", "crop", "harvest_year"])[list(VALUE_COLUMNS)].mean().reset_index()
    long = per_season.melt(id_vars=["variant", "crop", "harvest_year"], value_vars=list(VALUE_COLUMNS), var_name="column")
    long["parameter"] = long["column"].map(VALUE_COLUMNS)
    long["unit"] = "kg N/ha"
    long["value"] = long["value"].round(2)
    long.assign(lat=location["lat"], lon=location["lon"])[["lat", "lon", "variant", "crop", "harvest_year", "parameter", "value", "unit"]].to_csv(
        I.OUT_DIR / "fertilizer_need_season_long.csv", index=False)

    totals = rotation_totals(runs, len(ROTATION))
    summary = totals.groupby("variant").agg(
        n_start_years=("start_year", "size"),
        fertilizer_need_mean=("fertilizer_need", "mean"),
        fertilizer_need_p90=("fertilizer_need", lambda s: np.percentile(s, 90)),
        balance_unfloored_mean=("balance_unfloored", "mean"),
        ksu_formula_mean=("ksu_fertilizer_need", "mean"),
        leaching_mean=("leaching_fallow", "mean"),
        leaching_p90=("leaching_fallow", lambda s: np.percentile(s, 90)),
        leaching_charged_mean=("leaching_charged", "mean"),
        removal_mean=("removal", "mean"),
    ).round(2)
    summary["unit"] = "kg N/ha/year of the rotation"
    summary.reset_index().to_csv(I.OUT_DIR / "fertilizer_need_rotation.csv", index=False)

    print(f"[fertilizer] reference yields:\n{I.reference_yields().round(3).to_string()}")
    print(f"\n[fertilizer] rotation {' -> '.join(ROTATION)}, mean over start years:")
    print(summary.drop(columns="unit").to_string())
    by_crop = runs[runs["variant"] == "no_cover"].groupby("crop")[["removal", "mineralization_season", "carried_from_fallow", "balance_unfloored", "fertilizer_need", "ksu_fertilizer_need"]].mean().round(1)
    print(f"\n[fertilizer] per crop (no cover), kg N/ha:\n{by_crop.to_string()}")
    print(f"\n[fertilizer] written to {I.OUT_DIR.relative_to(I.REPO)}")


if __name__ == "__main__":
    main()
