"""Explorer data contract (v1) as pydantic models.

This module is the single source of truth for the JSON around the explorer backend.
If a format changes, it changes here first.

Input (from the scorer, a separate API that is still a black box, so this is an assumption):

* ``scorer/response.json`` -> :class:`ScorerResponse` (which rotations, rank, score, kpi)

Output (what we hand to the frontend, one file, like the mockup's ``D`` object):

* ``explorer.json``        -> :class:`ExplorerExport` (field, crops, climate, rotations, sources)

Each rotation in ``explorer.json`` is the scorer rotation passed through unchanged, plus
``placeholder``, and per season / month / summary the values we add (yield, N, calendar, ...).

Who computes what: water use comes from the scorer (we only adapt it), yield and the rest
come from us. Placeholders are marked with ``placeholder=True``.

Units are part of the field names: ``_in`` inches of water, ``_lb`` lb N per acre, ``_ft`` feet,
``_pct`` percent 0-100. Everything is in US units except temperature thresholds (°C, e.g.
``heat_days_ge_35``). There is no unit toggle in the UI.

Why pydantic: it turns these classes into a validator. ``Model.model_validate_json(text)``
either returns a typed object or raises an error that names the broken field. That way a bad
export fails here, in our tests, and not later as a blank chart in the frontend.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

# Bump this when the JSON format changes. Major = breaking for the frontend.
CONTRACT_VERSION = "3.0.0-draft"

N_SEASONS = 4
N_MONTHS = N_SEASONS * 12

# Literal = "only these exact strings are allowed". Typos like "Corn" or "winterwheat"
# are rejected instead of silently creating a new crop.
CropId = Literal["corn", "sorghum", "soybean", "winter_wheat", "sunflower", "triticale"]
Irrigation = Literal["full", "reduced", "none"]  # reduced = 50 % of full (assumption)
MonthKind = Literal["crop", "cover", "bare", "fallow"]
ProvenanceLabel = Literal["measured", "modeled", "rule", "assumption"]


class _Strict(BaseModel):
    """Base for all models.

    ``extra="forbid"`` makes unknown keys an error. Without it, a typo such as ``rain_inn``
    would be accepted and silently ignored.
    """

    model_config = ConfigDict(extra="forbid")


# --------------------------------------------------------------------------------------
# Shared building blocks
# --------------------------------------------------------------------------------------


class Spread(_Strict):
    """Mean ``v`` with 10th and 90th percentile over all weather years.

    Mean (not median), so that the 12 monthly means add up exactly to the season value.
    """

    v: float
    p10: float
    p90: float

    # A model_validator runs after the single fields are checked, so it can compare fields.
    @model_validator(mode="after")
    def _ordered(self) -> Spread:
        if not self.p10 <= self.v <= self.p90:
            raise ValueError(f"expected p10 <= v <= p90, got {self.p10}, {self.v}, {self.p90}")
        return self


class YieldSpread(Spread):
    unit: Literal["bu", "lb"]


class Effect(_Strict):
    """A rotation effect shown as text, e.g. 'Corn after corn: ~2 % yield drag'."""

    text: str
    source: str | None = None  # key in ExplorerExport.sources
    provenance: ProvenanceLabel


# --------------------------------------------------------------------------------------
# Field, crops, climate
# --------------------------------------------------------------------------------------


class Soil(_Strict):
    texture: str
    # Field(ge=..., le=...) = allowed value range (ge: greater or equal, le: less or equal).
    water_capacity_in: float = Field(ge=0)
    organic_matter_pct: float = Field(ge=0, le=100)


class CropHistoryYear(_Strict):
    year: int
    crop: str  # free text: the CDL class can be outside our crop list (e.g. "fallow/idle")


class FieldInfo(_Strict):
    id: str
    name: str
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)
    elevation_ft: float
    slope_pct: float = Field(ge=0)
    soil: Soil
    crop_history: list[CropHistoryYear]
    previous_crop: CropId
    rotation_start_year: int


class Crop(_Strict):
    label: str
    yield_unit: Literal["bu", "lb"] | None  # None for cover crops (no harvest)
    season: Literal["summer", "winter"]
    legume: bool
    is_cover: bool


class Climate(_Strict):
    """One value per weather year. All lists are index-aligned to ``weather_years``."""

    weather_years: list[int] = Field(min_length=1)
    rain_in: list[float]
    et0_apr_sep_in: list[float]
    deficit_apr_sep_in: list[float]  # ET0 minus rain, April-September; positive = water missing
    heat_days_ge_35: list[float]

    @model_validator(mode="after")
    def _aligned(self) -> Climate:
        n = len(self.weather_years)
        for name in ("rain_in", "et0_apr_sep_in", "deficit_apr_sep_in", "heat_days_ge_35"):
            if len(getattr(self, name)) != n:
                raise ValueError(f"climate.{name} has {len(getattr(self, name))} values, expected {n}")
        if self.weather_years != sorted(set(self.weather_years)):
            raise ValueError("climate.weather_years must be strictly increasing")
        return self


# --------------------------------------------------------------------------------------
# Scorer (our INPUT, assumed format)
# --------------------------------------------------------------------------------------


class SequenceStep(_Strict):
    year: int  # harvest year; winter crops (winter wheat) are planted in the autumn before
    crop: CropId
    irrigation: Irrigation
    cover: CropId | None = None


class ScoreParts(_Strict):
    water: float
    profit: float
    soil: float
    erosion: float


class ScorerRotation(_Strict):
    """One rotation as we EXPECT the scorer to send it.

    The scorer is a separate API and still a black box, so this is our assumption, derived
    from the mockup. When the real API exists, only this class and ScorerResponse change.
    Water use per season/month will also come from the scorer; its format is still unknown.
    """

    # pattern = regex; ids are used as keys in the frontend, so keep them simple.
    id: str = Field(pattern=r"^[a-z0-9_\-]+$")
    is_current: bool
    rank: int | None = Field(default=None, ge=1, le=3)
    name: str
    short: str
    category: str | None = None
    sequence: list[SequenceStep] = Field(min_length=N_SEASONS, max_length=N_SEASONS)
    score: float | None = None
    score_parts: ScoreParts | None = None
    # The scorer owns the kpi format. We pass it through untouched instead of guessing a shape.
    kpi: dict[str, Any] | None = None

    @model_validator(mode="after")
    def _check(self) -> ScorerRotation:
        if self.is_current and self.rank is not None:
            raise ValueError(f"rotation {self.id}: the current rotation must not have a rank")
        years = [s.year for s in self.sequence]
        if years != list(range(years[0], years[0] + N_SEASONS)):
            raise ValueError(f"rotation {self.id}: sequence years must be consecutive, got {years}")
        return self


class ScorerResponse(_Strict):
    """Assumed scorer output = our INPUT. Example: examples/scorer/response.json."""

    placeholder: bool  # true while we use mockup values instead of the real scorer
    rotations: list[ScorerRotation] = Field(min_length=1)


# --------------------------------------------------------------------------------------
# Explorer (our OUTPUT): a scorer rotation plus what we add per season and month
# --------------------------------------------------------------------------------------


class SeasonDetail(SequenceStep):
    """A scorer sequence step (year, crop, irrigation, cover) plus our values for that season."""

    # "yield" is a Python keyword, so the attribute is called yield_ and the alias maps it
    # back to "yield" in the JSON. serialize_by_alias makes model_dump() write "yield" too.
    model_config = ConfigDict(extra="forbid", populate_by_name=True, serialize_by_alias=True)

    # doy = day of year. harvest_doy is in `year`; for winter crops plant_doy is in `year - 1`.
    plant_doy: int = Field(ge=1, le=366)
    harvest_doy: int = Field(ge=1, le=366)
    irr_in: Spread  # from the scorer (adapted)
    yield_: YieldSpread = Field(alias="yield")
    n_lb: float = Field(ge=0)
    n_adj_lb: float  # previous-crop adjustment, can be negative (e.g. after soybean)
    yield_pct_rotation: float
    effects: list[Effect]

    @model_validator(mode="after")
    def _no_water_without_irrigation(self) -> SeasonDetail:
        if self.irrigation == "none" and self.irr_in.p90 > 0:
            raise ValueError(f"season {self.year}: irrigation 'none' but irr_in.p90 = {self.irr_in.p90}")
        return self


class MonthDetail(_Strict):
    """One month of the 'typical year' view: mean over all weather years.

    Mean (not median), so that months add up to the season and balances stay consistent.
    """

    m: str = Field(pattern=r"^\d{4}-(0[1-9]|1[0-2])$")  # "YYYY-MM"
    kind: MonthKind
    crop: CropId | None
    et_in: float = Field(ge=0)
    rain_in: float = Field(ge=0)
    irr_in: float = Field(ge=0)
    heat_risk_pct: float = Field(ge=0, le=100)
    frost_risk_pct: float = Field(ge=0, le=100)
    n_fert_lb: float = Field(ge=0)
    n_uptake_lb: float = Field(ge=0)
    n_fix_lb: float = Field(ge=0)
    n_credit_lb: float = Field(ge=0)
    n_pool_lb: float = Field(ge=0)
    n_loss_lb: float = Field(ge=0)
    n_short_lb: float = Field(ge=0)

    @model_validator(mode="after")
    def _crop_matches_kind(self) -> MonthDetail:
        if self.kind in ("bare", "fallow") and self.crop is not None:
            raise ValueError(f"{self.m}: kind '{self.kind}' must have crop null")
        if self.kind in ("crop", "cover") and self.crop is None:
            raise ValueError(f"{self.m}: kind '{self.kind}' needs a crop")
        return self


class Summary(_Strict):
    bare_months: float = Field(ge=0, le=12)  # months per year without crop or cover, mean
    # Seasons whose crop equals the crop before it; season 1 compares to field.previous_crop.
    # Continuous corn after corn = 4.
    same_crop_repeats: int = Field(ge=0, le=N_SEASONS)
    n_loss_lb: float = Field(ge=0)  # mean per year


class Rotation(ScorerRotation):
    """A rotation in explorer.json: the scorer rotation passed through, plus our data.

    ``sequence`` is redefined here: same scorer fields per season, plus our season values.
    """

    placeholder: bool  # tells the frontend whether the values are still mockup values
    sequence: list[SeasonDetail] = Field(min_length=N_SEASONS, max_length=N_SEASONS)
    monthly: list[MonthDetail] = Field(min_length=N_MONTHS, max_length=N_MONTHS)
    summary: Summary

    @model_validator(mode="after")
    def _months_cover_sequence(self) -> Rotation:
        first = self.sequence[0].year
        expected = [f"{first + i // 12}-{i % 12 + 1:02d}" for i in range(N_MONTHS)]
        if [m.m for m in self.monthly] != expected:
            raise ValueError(f"rotation {self.id}: monthly must run {expected[0]}..{expected[-1]} without gaps")
        return self


class ProvenanceEntry(_Strict):
    label: ProvenanceLabel
    source: str | None  # key in ExplorerExport.sources


class Source(_Strict):
    title: str
    url: str | None = None
    retrieved: str | None = None


class ExplorerExport(_Strict):
    """The whole explorer.json."""

    contract_version: str
    generated_at: str
    field: FieldInfo
    crops: dict[CropId, Crop]
    climate: Climate
    rotations: list[Rotation] = Field(min_length=1)
    # Which kind of number a field is, e.g. "climate.*" -> measured, from source "nasa_power".
    provenance: dict[str, ProvenanceEntry]
    sources: dict[str, Source]

    @model_validator(mode="after")
    def _consistent(self) -> ExplorerExport:
        if self.contract_version != CONTRACT_VERSION:
            raise ValueError(f"contract_version {self.contract_version!r}, expected {CONTRACT_VERSION!r}")
        current = [r.id for r in self.rotations if r.is_current]
        if len(current) != 1:
            raise ValueError(f"expected exactly one current rotation, got {current}")
        ids = [r.id for r in self.rotations]
        if len(ids) != len(set(ids)):
            raise ValueError(f"rotation ids must be unique, got {ids}")
        ranks = [r.rank for r in self.rotations if r.rank is not None]
        if len(ranks) != len(set(ranks)):
            raise ValueError(f"ranks must be unique, got {ranks}")
        for r in self.rotations:
            for s in r.sequence:
                for c in (s.crop, s.cover):
                    if c is not None and c not in self.crops:
                        raise ValueError(f"rotation {r.id} uses crop '{c}' missing from crops")
        for key, entry in self.provenance.items():
            if entry.source is not None and entry.source not in self.sources:
                raise ValueError(f"provenance '{key}' points to unknown source '{entry.source}'")
        return self


def load_explorer(path: Path) -> ExplorerExport:
    """Read and validate an explorer.json."""
    return ExplorerExport.model_validate_json(path.read_text(encoding="utf-8"))
