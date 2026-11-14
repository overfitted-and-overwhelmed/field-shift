"""Cited coefficient table for the N fertilizer need criterion.

Every number carries its citation (see crop_scorer/fertilizer-need-plan.md, "Zitierpflicht").
Entries with ``kind="data"`` are copied from a source row, ``"derived"`` are computed from
source rows and ``"assumption"`` have no source and are flagged as such.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Final, Literal

PACKAGE_DIR: Final[Path] = Path(__file__).resolve().parents[2]
DEFAULT_DATA_DIR: Final[Path] = PACKAGE_DIR / "data"
DEFAULT_DRYAD_PATH: Final[Path] = DEFAULT_DATA_DIR / "base-data" / "dryad" / "Combined_crop_data.csv"
# The Dryad file is cp1252, not UTF-8.
DRYAD_ENCODING: Final[str] = "cp1252"

DRYAD_URL: Final[str] = "https://doi.org/10.5061/dryad.n2z34tn0x"
IFA_URL: Final[str] = "https://api.ifastat.org/reports/download/12965"
FAO_ESB_URL: Final[str] = "https://fenixservices.fao.org/faostat/static/documents/ESB/ESB_e.pdf"
UNKOVICH_DOI: Final[str] = "https://doi.org/10.1016/S0065-2113(10)05005-4"
RETRIEVED: Final[str] = "2026-11-14"

Kind = Literal["data", "derived", "assumption"]


@dataclass(frozen=True)
class Coefficient:
    """A single number with unit and full citation."""

    value: float | None
    unit: str
    source: str
    locator: str
    url_or_doi: str
    retrieved: str
    kind: Kind


# Scorer crop key -> item name in Combined_crop_data.csv
DRYAD_ITEMS: Final[dict[str, str]] = {
    "corn": "Maize",
    "sorghum": "Sorghum",
    "winter_wheat": "Wheat",
    "soybean": "Soybeans",
    "sunflower": "Sunflower seed",
}


def _grain_n(value: float, item: str) -> Coefficient:
    return Coefficient(
        value=value,
        unit="% N of fresh grain mass",
        source="International Fertilizer Association (2020), primary ref. IPNI, via Dryad Combined_crop_data.csv",
        locator=f"item={item}, crop_component=Crop_products, original_region=World, variable=N_pc_fresh",
        url_or_doi=f"{IFA_URL} ; dataset {DRYAD_URL}",
        retrieved=RETRIEVED,
        kind="data",
    )


def _residue_n(value: float, item: str) -> Coefficient:
    return Coefficient(
        value=value,
        unit="% N of fresh residue mass",
        source="FAO (2020) FAOSTAT Soil Nutrient Budget Metadata, primary ref. IPNI calculator, via Dryad Combined_crop_data.csv",
        locator=f"item={item}, crop_component=Crop_residues, original_region=World, variable=N_pc_fresh",
        url_or_doi=f"{FAO_ESB_URL} ; dataset {DRYAD_URL}",
        retrieved=RETRIEVED,
        kind="data",
    )


def _harvest_index(value: float, item: str) -> Coefficient:
    # The file also has Johnson et al. (2006) values for the USA (Maize 0.53, Sorghum 0.47,
    # Soybeans 0.46, Sunflower 0.40, Wheat 0.45). Prince et al. (2001) is used for all crops.
    return Coefficient(
        value=value,
        unit="kg grain / kg above-ground biomass",
        source="Unkovich et al. (2010), primary ref. Prince et al. (2001), via Dryad Combined_crop_data.csv",
        locator=f"item={item}, crop_component=Crop_products, original_region=United States of America, variable=HI",
        url_or_doi=f"{UNKOVICH_DOI} ; dataset {DRYAD_URL}",
        retrieved=RETRIEVED,
        kind="data",
    )


# Reference yield: filled from USDA NASS Quick Stats (Kansas, unirrigated, mean 1991-2025).
# Not available in the repo yet, so value=None until the NASS file is added.
def _pending_yield(crop_key: str) -> Coefficient:
    return Coefficient(
        value=None,
        unit="t grain / ha (unirrigated, mean 1991-2025)",
        source="USDA NASS Quick Stats, Kansas (pending)",
        locator=f"crop={crop_key}",
        url_or_doi="https://quickstats.nass.usda.gov/",
        retrieved="",
        kind="data",
    )


@dataclass(frozen=True)
class CropNCoefficients:
    """N coefficients of one crop."""

    crop_key: str
    grain_n: Coefficient
    residue_n: Coefficient
    harvest_index: Coefficient
    reference_yield: Coefficient
    # Biological N fixation per t grain; only legumes.
    fixation: Coefficient | None = None


CROP_COEFFICIENTS: Final[dict[str, CropNCoefficients]] = {
    "corn": CropNCoefficients(
        crop_key="corn",
        grain_n=_grain_n(1.2, "Maize"),
        residue_n=_residue_n(0.8, "Maize"),
        harvest_index=_harvest_index(0.53, "Maize"),
        reference_yield=_pending_yield("corn"),
    ),
    "sorghum": CropNCoefficients(
        crop_key="sorghum",
        grain_n=_grain_n(1.3, "Sorghum"),
        residue_n=_residue_n(1.1, "Sorghum"),
        harvest_index=_harvest_index(0.44, "Sorghum"),
        reference_yield=_pending_yield("sorghum"),
    ),
    "winter_wheat": CropNCoefficients(
        crop_key="winter_wheat",
        grain_n=_grain_n(1.9, "Wheat"),
        residue_n=_residue_n(1.2, "Wheat"),
        harvest_index=_harvest_index(0.50, "Wheat"),
        reference_yield=_pending_yield("winter_wheat"),
    ),
    "soybean": CropNCoefficients(
        crop_key="soybean",
        grain_n=_grain_n(5.5, "Soybeans"),
        residue_n=_residue_n(1.8, "Soybeans"),
        harvest_index=_harvest_index(0.42, "Soybeans"),
        reference_yield=_pending_yield("soybean"),
        fixation=Coefficient(
            value=45.0,
            unit="kg N fixed / t fresh grain",
            source="International Fertilizer Association (2020), primary ref. IPNI, via Dryad Combined_crop_data.csv",
            locator="item=Soybeans, crop_component=Crop_products, original_region=World, "
            "variable=Fixed_N_kg_N_metric_t_fresh_crop_product",
            url_or_doi=f"{IFA_URL} ; dataset {DRYAD_URL}",
            retrieved=RETRIEVED,
            kind="data",
        ),
    ),
    "sunflower": CropNCoefficients(
        crop_key="sunflower",
        grain_n=_grain_n(2.7, "Sunflower seed"),
        residue_n=_residue_n(1.8, "Sunflower seed"),
        harvest_index=_harvest_index(0.27, "Sunflower seed"),
        reference_yield=_pending_yield("sunflower"),
    ),
}


def n_removal_per_t_grain(crop_key: str) -> float:
    """Return N in the harvested grain in kg N per t fresh grain (% N * 10)."""
    return CROP_COEFFICIENTS[crop_key].grain_n.value * 10.0
