"""WP4 Nitrogen Adapter: N fertilizer per season, from the scorer.

The scorer computes the N fertilizer need of every season after K-State MF2586 (``crop_scorer/scoring/nitrogen.py``),
including the previous crop adjustment and the extra N after a cover crop. We only convert kg N/ha to lb N/acre.

K-State gives the need per season, not a monthly N balance and no N losses, so ``MonthDetail.nitrogen`` and
``Summary.n_loss_lb`` stay null.
"""

from __future__ import annotations

from dataclasses import dataclass

from crop_scorer.scoring.nitrogen import COVER_N_LB, LB_PER_AC_TO_KG_PER_HA, NO_FORMULA_KG
from explorer.field_calendar import load_scorer_seasons, scorer_rows
from explorer.schema import Effect, ProvenanceEntry, Source

PROVENANCE: dict[str, ProvenanceEntry] = {
    "sequence.n_lb": ProvenanceEntry(label="rule", source="ksu_mf2586"),
    "sequence.n_adj_lb": ProvenanceEntry(label="rule", source="ksu_mf2586"),
}

SOURCES: dict[str, Source] = {
    "ksu_mf2586": Source(
        title="K-State MF2586 Soil Test Interpretations and Fertilizer Recommendations (Ruiz Diaz, Jan 2024)",
        url="https://bookstore.ksre.ksu.edu/pubs/soil-test-interpretations-and-fertilizer-recommendations_MF2586.pdf",
    ),
    "sare_2007": Source(
        title="Clark (ed.) 2007, Managing Cover Crops Profitably, 3rd ed., SARE, p. 46",
        url="https://www.sare.org/wp-content/uploads/Managing-Cover-Crops-Profitably.pdf",
    ),
}


@dataclass(frozen=True)
class SeasonNitrogen:
    n_lb: float
    n_adj_lb: float
    effects: list[Effect]


def season_nitrogen(rotation: str) -> list[SeasonNitrogen]:
    """N fertilizer and previous crop adjustment per season in lb N/acre, with effect texts for the assumptions."""
    rows = scorer_rows(load_scorer_seasons(), rotation, "seasons table")
    seasons = [g for _, g in rows.groupby("season")]
    out = []
    for i, g in enumerate(seasons):
        crop = g["crop"].iloc[0]
        effects = []
        if crop in NO_FORMULA_KG:
            effects.append(Effect(text=f"No K-State N recommendation for {crop} (legume): no fertilizer assumed",
                                  source="ksu_mf2586", provenance="assumption"))
        elif i > 0 and seasons[i - 1]["cover"].notna().any():
            effects.append(Effect(text=f"After the cover crop: +{COVER_N_LB} lb N/acre (cereal residue ties up N)",
                                  source="sare_2007", provenance="rule"))
        # the K-State need does not depend on the weather, the mean over the weather years is the value of every year
        out.append(SeasonNitrogen(
            n_lb=round(g["n_fertilizer_kg_ha"].mean() / LB_PER_AC_TO_KG_PER_HA, 1),
            n_adj_lb=round(g["n_adjustment_kg_ha"].mean() / LB_PER_AC_TO_KG_PER_HA, 1),
            effects=effects,
        ))
    return out
