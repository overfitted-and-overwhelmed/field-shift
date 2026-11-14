"""Bare (fallow) days of a crop rotation as a first erosion indicator.

Uses the season timeline of water_usage (sowing and harvest in the middle of the NASS "most active" windows),
so water and erosion look at the same days. A day is bare when no main crop is on the field, i.e. from harvest
to the next sowing. A rotation is evaluated from the first sowing to the last harvest (every crop once), so the
fallow after the last crop is not counted. No cover crops, no crop residue and no seasonal weighting yet.

Output: bare days for every ordered rotation of 3 crops (ranking) and the timeline of the test rotation.
Run from the repo root: uv run python -m crop_scorer.erosion.erosion
"""

import itertools

import pandas as pd

from crop_scorer.water_usage.water_usage import FIRST_YEAR, REPO, ROTATION, build_timeline, load_crop_params

OUT_DIR = REPO / "data/processed/erosion"
RANKING_LENGTH = 3


def rotation_timeline(rotation: list[str]) -> pd.DataFrame:
    # every crop once: first sowing to last harvest
    seasons = build_timeline(load_crop_params(), rotation, FIRST_YEAR)[: len(rotation)]
    rows = []
    for i, (crop, sow, harvest) in enumerate(seasons):
        rows.append({"status": crop, "start_date": sow, "end_date": harvest - pd.Timedelta(days=1)})
        next_sow = seasons[i + 1][1] if i + 1 < len(seasons) else harvest
        if next_sow > harvest:
            rows.append({"status": "fallow", "start_date": harvest, "end_date": next_sow - pd.Timedelta(days=1)})
    timeline = pd.DataFrame(rows)
    timeline["days"] = (timeline["end_date"] - timeline["start_date"]).dt.days + 1
    return timeline


def bare_days(rotation: list[str]) -> int:
    timeline = rotation_timeline(rotation)
    return int(timeline.loc[timeline["status"] == "fallow", "days"].sum())


def main():
    timeline = rotation_timeline(ROTATION)
    print(f"[erosion] timeline {'-'.join(ROTATION)}:")
    print(timeline.to_string(index=False))

    rows = []
    for rotation in itertools.product(load_crop_params().index, repeat=RANKING_LENGTH):
        t = rotation_timeline(list(rotation))
        rows.append({
            "rotation": "-".join(rotation),
            "span_days": int(t["days"].sum()),
            "bare_days": int(t.loc[t["status"] == "fallow", "days"].sum()),
        })
    ranking = pd.DataFrame(rows).sort_values(["bare_days", "span_days"]).reset_index(drop=True)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    timeline.assign(rotation="-".join(ROTATION)).to_csv(OUT_DIR / "rotation_timeline.csv", index=False)
    ranking.to_csv(OUT_DIR / "bare_days_ranking.csv", index=False)

    print(f"\n[erosion] {len(ranking)} rotations of {RANKING_LENGTH} crops, fewest bare days first:")
    print(ranking.head(10).to_string(index=False))
    print("...")
    print(ranking.tail(5).to_string(index=False))
    print(f"\n[erosion] written to {OUT_DIR.relative_to(REPO)}")


if __name__ == "__main__":
    main()
