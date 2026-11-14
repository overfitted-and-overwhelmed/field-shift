"""Tests for WP1 (explorer/field_climate.py): values match the processed files, blocks fit the contract."""

import json
from pathlib import Path

import pandas as pd
import pytest

from explorer.field_climate import PROVENANCE, SOURCES, build_climate, build_crops, build_field
from explorer.schema import ExplorerExport

EXAMPLE = Path(__file__).resolve().parents[1] / "explorer" / "examples" / "explorer.json"


def test_field_matches_profile_and_cdl():
    field = build_field()
    assert field.id == "ks-kearny-01"
    assert field.soil.water_capacity_in == 7.2  # 183 mm
    assert [h.year for h in field.crop_history] == list(range(2008, 2026))
    assert {h.crop for h in field.crop_history} == {"corn"}
    assert field.previous_crop == "corn"


def test_climate_matches_annual_features():
    climate = build_climate()
    assert climate.weather_years == list(range(1991, 2026))
    i = climate.weather_years.index(2025)
    # 2025 in the file: rain 531.88 mm, ET0 Apr-Sep 1125.19 mm, rain minus ET0 Apr-Sep -655.52 mm, 38 days
    assert (climate.rain_in[i], climate.et0_apr_sep_in[i]) == (20.94, 44.3)
    assert climate.deficit_apr_sep_in[i] == 25.81
    assert climate.heat_days_ge_35[i] == 38
    assert all(d > 0 for d in climate.deficit_apr_sep_in)  # semi-arid: ET0 exceeds rain every summer


def _cdl(tmp_path, rows):
    path = tmp_path / "cdl.csv"
    pd.DataFrame(rows, columns=["year", "cdl_code", "cdl_class"]).to_csv(path, index=False)
    return path


def test_previous_crop_skips_classes_outside_our_list(tmp_path):
    cdl = _cdl(tmp_path, [(2024, 5, "Soybeans"), (2025, 61, "Fallow/Idle Cropland")])
    field = build_field(cdl_path=cdl)
    assert [h.crop for h in field.crop_history] == ["soybean", "fallow/idle cropland"]
    assert field.previous_crop == "soybean"


def test_previous_crop_fails_without_any_of_our_crops(tmp_path):
    with pytest.raises(ValueError, match="previous_crop"):
        build_field(cdl_path=_cdl(tmp_path, [(2025, 36, "Alfalfa")]))


def test_blocks_fit_the_explorer_contract():
    # Swap our blocks into the WP0 example and validate the whole export.
    data = json.loads(EXAMPLE.read_text(encoding="utf-8"))
    data["field"] = build_field().model_dump(mode="json")
    data["crops"] = {k: v.model_dump(mode="json") for k, v in build_crops().items()}
    data["climate"] = build_climate().model_dump(mode="json")
    data["provenance"] |= {k: v.model_dump(mode="json") for k, v in PROVENANCE.items()}
    data["sources"] |= {k: v.model_dump(mode="json") for k, v in SOURCES.items()}
    ExplorerExport.model_validate(data)
