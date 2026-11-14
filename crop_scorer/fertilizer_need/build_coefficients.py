"""Build the N coefficient table for the fertilizer-need model (plan: crop_scorer/fertilizer-need-plan.md, Sub-Task 1).

Reads data/base-data/dryad/Combined_crop_data.csv (Dryad, DOI 10.5061/dryad.n2z34tn0x) and writes
    data/fertilizer_n_coefficients.csv   every candidate row for the 5 scorer crops, the chosen one flagged `selected`,
                                         plus derived values. Each row carries the citation fields of the plan.
Run from the repo root:  uv run python crop_scorer/fertilizer_need/build_coefficients.py

Choice rule (plan: USA/North America preferred, else World, and the basis must match the yields):
  - Yields are fresh matter at standard moisture, so N in grain/residue comes from `N_pc_fresh`.
    USA rows exist only for `N_pc` (percent of dry matter); they are kept as candidates and used as cross-check.
  - Among the `N_pc_fresh` rows the IPNI (2014) crop-specific grain/residue rows are chosen, because they name the crop part.
  - Harvest index: the two USA rows per crop (Prince 2001, Johnson 2006, both via Unkovich 2010) are both listed,
    the mean is the derived selected value.
"""
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "data" / "base-data" / "dryad" / "Combined_crop_data.csv"
OUT = ROOT / "data" / "fertilizer_n_coefficients.csv"
UNITS = ROOT / "data" / "crop_unit_conversion.csv"
ADDED = "2026-11-14"  # date the Dryad file was committed to the repo (git log); the dataset itself is the Dryad release
DOI = "doi:10.5061/dryad.n2z34tn0x"

CROPS = {  # scorer crop -> (`item` in Combined_crop_data, grain row name, residue row name)
    "corn": ("Maize", "Corn grain", "Corn stover"),
    "sorghum": ("Sorghum", "Sorghum grain", "Sorghum stover"),
    "soybean": ("Soybeans", "Soybean grain", "Soybean stover"),
    "sunflower": ("Sunflower seed", "Sunflower grain", "Sunflower stover"),
    "winter_wheat": ("Wheat", "Wheat (winter) grain", "Wheat straw"),
}
US_REGIONS = {"United States of America", "North America"}


def clean(s) -> str:
    return " ".join(str(s).split()) if pd.notna(s) else ""


def row_out(crop, parameter, r, value, unit, selected, kind="data", note=""):
    ref = clean(r["reference_where_data_were_collated"])
    prim = clean(r["primary_reference_of_dataset"])
    site = clean(r["website_of_source_of_collated_data"])
    return {
        "crop": crop, "crop_part": "grain" if r["crop_component"] == "Crop_products" else "residue",
        "parameter": parameter, "value": value, "unit": unit, "selected": selected,
        "source": f"{ref} (primary: {prim})" if prim and prim != ref else ref,
        "locator": f'Combined_crop_data.csv, data row {r.name} (0-based): item="{r["item"]}", original_crop="{clean(r["original_crop"])}", original_region="{clean(r["original_region"])}", variable={r["variable"]}',
        "url_or_doi": f"{DOI}" + (f"; {site}" if site else ""),
        "retrieved": ADDED, "kind": kind, "note": note,
    }


def main() -> None:
    d = pd.read_csv(SRC, encoding="cp1252", low_memory=False)
    out = []
    for crop, (item, grain_name, resid_name) in CROPS.items():
        x = d[d["item"] == item]
        # candidates: N in fresh matter (all regions), N in dry matter (USA / North America), harvest index (USA), fixation
        for _, r in x[(x["variable"] == "N_pc_fresh") & x["crop_component"].isin(["Crop_products", "Crop_residues"])].iterrows():
            part_name = grain_name if r["crop_component"] == "Crop_products" else resid_name
            sel = clean(r["original_crop"]) == part_name and clean(r["reference_where_data_were_collated"]).startswith("IPNI")
            out.append(row_out(crop, "n_content_fresh", r, r["value"], "% N of fresh matter", sel,
                               note="chosen: crop-specific IPNI (2014) row, fresh basis matches the NASS yields" if sel else ""))
        for _, r in x[(x["variable"] == "N_pc") & x["original_region"].isin(US_REGIONS)].iterrows():
            out.append(row_out(crop, "n_content_dry", r, r["value"], "% N of dry matter", False,
                               note="USA/North America candidate, dry-matter basis: used only for the cross-check"))
        us_hi = x[(x["variable"] == "HI") & (x["crop_component"] == "Crop_products") & (x["original_region"] == "United States of America")]
        for _, r in us_hi.iterrows():
            out.append(row_out(crop, "harvest_index", r, r["value"], "kg grain / kg above-ground biomass (dry)", False))
        for _, r in x[x["variable"] == "Fixed_N_kg_N_metric_t_fresh_crop_product"].iterrows():
            out.append(row_out(crop, "n_fixed_gross", r, r["value"], "kg N per t grain", True, kind="data",
                               note="gross fixation. Open question of the plan: grain only or whole plant? Check IPNI/IFA before use"))

    df = pd.DataFrame(out)
    # ---- derived values (formula in `note`) ----
    der = []
    for crop in CROPS:
        c = df[df["crop"] == crop]
        g = c[(c["parameter"] == "n_content_fresh") & (c["crop_part"] == "grain") & c["selected"]].iloc[0]
        rr = c[(c["parameter"] == "n_content_fresh") & (c["crop_part"] == "residue") & c["selected"]].iloc[0]
        hi = c[c["parameter"] == "harvest_index"]
        hi_mean = round(hi["value"].mean(), 3)
        ratio = round((1 - hi_mean) / hi_mean, 3)
        base = {"crop": crop, "selected": True, "kind": "derived", "retrieved": ADDED, "url_or_doi": DOI}
        der += [
            {**base, "crop_part": "grain", "parameter": "n_removal_grain", "value": round(g["value"] * 10, 2), "unit": "kg N per t grain",
             "source": "derived from the selected n_content_fresh grain row", "locator": g["locator"], "note": "= n_content_fresh x 10 (1 % = 10 kg per t)"},
            {**base, "crop_part": "grain", "parameter": "harvest_index_selected", "value": hi_mean, "unit": "kg grain / kg above-ground biomass (dry)",
             "source": "mean of the USA rows (Prince 2001; Johnson 2006; both via Unkovich et al. 2010)", "locator": "; ".join(hi["locator"].str.extract(r"data row (\d+)")[0]).join(["rows ", ""]),
             "note": f"mean of {', '.join(str(v) for v in hi['value'])}"},
            {**base, "crop_part": "residue", "parameter": "residue_to_grain_ratio", "value": ratio, "unit": "t residue per t grain (dry basis)",
             "source": "derived from harvest_index_selected", "locator": "see harvest_index_selected", "note": "= (1 - HI) / HI. Dry basis, used as an approximation for fresh basis"},
            {**base, "crop_part": "residue", "parameter": "n_removal_residue", "value": round(ratio * rr["value"] * 10, 2), "unit": "kg N per t grain (residue N)",
             "source": "derived from the selected residue n_content_fresh row and residue_to_grain_ratio", "locator": rr["locator"],
             "note": "= ratio x n_content_fresh(residue) x 10. Residue N is only taken up again if residue stays on the field"},
        ]
        # cross-check against the USDA (2009) dry-matter value, using the moisture basis of the unit table
        dry = c[(c["parameter"] == "n_content_dry") & (c["crop_part"] == "grain") & (c["source"].str.contains("USDA", na=False)) & (c["locator"].str.contains('original_region="United States of America"'))]
        if len(dry) and UNITS.exists():
            u = pd.read_csv(UNITS)
            u = u[u["crop"] == crop]
            if len(u):
                est = round(dry.iloc[0]["value"] * (1 - u.iloc[0]["moisture_basis_pct"] / 100), 2)
                der.append({**base, "crop_part": "grain", "parameter": "n_content_fresh_crosscheck", "value": est, "selected": False, "unit": "% N of fresh matter",
                            "source": "USDA (2009) value (dry basis) converted with the moisture basis in crop_unit_conversion.csv", "locator": dry.iloc[0]["locator"],
                            "note": f"= n_content_dry {dry.iloc[0]['value']} x (1 - {u.iloc[0]['moisture_basis_pct']} %). Compare with selected {g['value']} (IPNI)"})
    df = pd.concat([df, pd.DataFrame(der)], ignore_index=True)
    cols = ["crop", "crop_part", "parameter", "value", "unit", "selected", "source", "locator", "url_or_doi", "retrieved", "kind", "note"]
    df = df[cols].sort_values(["crop", "parameter", "selected"], ascending=[True, True, False])
    df.to_csv(OUT, index=False, encoding="utf-8")
    print(f"wrote {len(df)} rows to {OUT}")


if __name__ == "__main__":
    main()
