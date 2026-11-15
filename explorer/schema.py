"""Explorer data contract as pydantic models.

This module is the single source of truth for the JSON around the explorer backend.
If a format changes, it changes here first.

Input (from the scorer, ``crop_scorer/scoring/score_rotations.py``):

* ``scorer/response.json`` -> :class:`ScorerResponse` (which rotations, their seasons with dates, rank, scores)

Output (what we hand to the frontend, one file):

* ``explorer.json``        -> :class:`ExplorerExport` (field, crops, climate, rotations, sources)

Each rotation in ``explorer.json`` is the scorer rotation passed through unchanged, plus
``placeholder``, and per season / month / summary the values we add (yield, calendar view, ...).

A rotation is ONE PASS of the scorer: its crops in order (3 today), from the first sowing to the
last harvest. Its length varies: two harvests can fall into one year (double crop) and a year can
be skipped (the next crop missed its planting window). So the number of seasons and months is not
fixed, and seasons are not one per year.

Who computes what: the scorer decides the seasons (dates) and computes water and temperature risk;
we take them over, also its N fertilizer need per season (K-State). Yield comes from us (WP3). What nobody
computes (monthly N balance, N loss) is null.
Placeholders are marked with ``placeholder=True``.

Units are part of the field names: ``_in`` inches of water, ``_lb`` lb N per acre, ``_ft`` feet,
``_pct`` percent 0-100. Everything is in US units except temperature thresholds (°C, e.g.
``heat_days_ge_35``). There is no unit toggle in the UI.

Why pydantic: it turns these classes into a validator. ``Model.model_validate_json(text)``
either returns a typed object or raises an error that names the broken field. That way a bad
export fails here, in our tests, and not later as a blank chart in the frontend.
"""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

# Bump this when the JSON format changes. Major = breaking for the frontend.
CONTRACT_VERSION = "6.3.0-draft"

# Literal = "only these exact strings are allowed". Typos like "Corn" or "winterwheat"
# are rejected instead of silently creating a new crop.
MainCropId = Literal["corn", "sorghum", "soybean", "winter_wheat", "sunflower"]
CoverCropId = Literal["triticale"]  # the only cover crop we support
CropId = MainCropId | CoverCropId  # any crop that can be on the field (catalog, monthly view)
Irrigation = Literal["full", "reduced", "none"]  # reduced = 50 % of full (assumption)
MonthKind = Literal["crop", "cover", "bare"]
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
# Scorer (our INPUT)
# --------------------------------------------------------------------------------------


class SequenceStep(_Strict):
    year: int  # harvest year; winter crops (winter wheat) are planted in the autumn before
    crop: MainCropId  # a cover crop can never be a season's main crop
    irrigation: Irrigation
    cover: CoverCropId | None = None  # and a main crop can never be a cover crop


class ScorerSeason(SequenceStep):
    """A season as the scorer plans it: crop, irrigation and its real dates.

    Dates are written as "YYYY-MM-DD" in the JSON. Like the scorer, the harvest day itself is not
    part of the season (the season runs from ``plant_date`` to the day before ``harvest_date``).
    """

    plant_date: date
    harvest_date: date

    @model_validator(mode="after")
    def _dates(self) -> ScorerSeason:
        if self.harvest_date.year != self.year:
            raise ValueError(f"season {self.year}: harvest_date {self.harvest_date} is not in the harvest year")
        if self.plant_date >= self.harvest_date:
            raise ValueError(f"season {self.year}: plant_date {self.plant_date} is not before harvest_date")
        return self


class ScoreParts(_Strict):
    """The scorer's normalised scores, 0 = best, 1 = worst among all its rotations."""

    water: float
    risk: float
    soil_health: float
    nitrogen: float  # N fertilizer need after K-State MF2586 (scorer criterion since crop-scorer #2)


class ScorerRotation(_Strict):
    """One rotation as the scorer sends it: one pass of its crops, with dates."""

    # pattern = regex; ids are used as keys in the frontend, so keep them simple.
    # "+" for the scorer's cover crop variant, e.g. "corn-soybean-sorghum+triticale"
    id: str = Field(pattern=r"^[a-z0-9_+\-]+$")
    is_current: bool
    rank: int | None = Field(default=None, ge=1, le=3)  # 1-3 for the picks, None for the current rotation
    name: str
    short: str
    category: str | None = None
    # One pass of the rotation. Not one season per year: double crops share a year, skipped years exist.
    sequence: list[ScorerSeason] = Field(min_length=1)
    score: float | None = None  # the scorer's weighted total, 0 = best
    score_parts: ScoreParts | None = None
    # The scorer owns the kpi values, so their shape is not fixed here (keys: explorer/build.py, in US units).
    kpi: dict[str, Any] | None = None
    # The same crops with the cover crop toggled (with <-> without), for the cover crop switch in the UI. It takes
    # the same slot (is_current, rank, short); score, kpi and everything else are its own. None if no gap of the
    # rotation fits a cover crop. One level only: a variant has no variant itself.
    cover_variant: ScorerRotation | None = None

    @model_validator(mode="after")
    def _check(self) -> ScorerRotation:
        if self.is_current and self.rank is not None:
            raise ValueError(f"rotation {self.id}: the current rotation must not have a rank")
        if (v := self.cover_variant) is not None:
            crops, _, cover = self.id.partition("+")
            v_crops, _, v_cover = v.id.partition("+")
            if v_crops != crops or bool(v_cover) == bool(cover):
                raise ValueError(f"rotation {self.id}: cover_variant {v.id} is not the same crops with the cover toggled")
            if (v.is_current, v.rank, v.short) != (self.is_current, self.rank, self.short):
                raise ValueError(f"rotation {self.id}: cover_variant {v.id} must take the same slot (is_current, rank, short)")
            if v.cover_variant is not None:
                raise ValueError(f"rotation {self.id}: cover_variant {v.id} must not have a cover_variant itself")
        for before, after in zip(self.sequence, self.sequence[1:]):
            if after.plant_date < before.harvest_date:
                raise ValueError(
                    f"rotation {self.id}: {after.crop} planted {after.plant_date} "
                    f"before {before.crop} is harvested ({before.harvest_date})"
                )
        return self


class ScorerResponse(_Strict):
    """Scorer output = our INPUT. Example: examples/scorer/response.json."""

    placeholder: bool  # true while values are not the scorer's real results
    rotations: list[ScorerRotation] = Field(min_length=1)


# --------------------------------------------------------------------------------------
# Explorer (our OUTPUT): a scorer rotation plus what we add per season and month
# --------------------------------------------------------------------------------------


class SeasonDetail(ScorerSeason):
    """A scorer season (year, crop, irrigation, cover, dates) plus our values for that season."""

    # "yield" is a Python keyword, so the attribute is called yield_ and the alias maps it
    # back to "yield" in the JSON. serialize_by_alias makes model_dump() write "yield" too.
    model_config = ConfigDict(extra="forbid", populate_by_name=True, serialize_by_alias=True)

    irr_in: Spread  # from the scorer's water balance, with the season's irrigation level applied
    yield_: YieldSpread = Field(alias="yield")
    n_lb: float = Field(ge=0)  # N fertilizer of the season after K-State MF2586, from the scorer
    # previous-crop adjustment in that formula (+27.5 lb after a cover crop), negative = credit (e.g. after soybean)
    n_adj_lb: float
    yield_pct_rotation: float
    effects: list[Effect]

    @model_validator(mode="after")
    def _no_water_without_irrigation(self) -> SeasonDetail:
        if self.irrigation == "none" and self.irr_in.p90 > 0:
            raise ValueError(f"season {self.year}: irrigation 'none' but irr_in.p90 = {self.irr_in.p90}")
        return self


class MonthNitrogen(_Strict):
    """Nitrogen balance of one month (not computed: K-State gives the need per season, no monthly balance)."""

    fert_lb: float = Field(ge=0)
    uptake_lb: float = Field(ge=0)
    fix_lb: float = Field(ge=0)
    credit_lb: float = Field(ge=0)
    pool_lb: float = Field(ge=0)
    loss_lb: float = Field(ge=0)
    short_lb: float = Field(ge=0)


class MonthDetail(_Strict):
    """One calendar month of the rotation's window: mean over all weather years.

    Mean (not median), so that months add up to the season. The first and the last month of the
    window can be partial (the window starts at the first sowing and ends before the last harvest).
    """

    m: str = Field(pattern=r"^\d{4}-(0[1-9]|1[0-2])$")  # "YYYY-MM"
    kind: MonthKind
    crop: CropId | None  # what stands on most days of the month (the scorer's rule)
    et_in: float = Field(ge=0)  # crop water use; on bare months evaporation from bare soil
    rain_in: float = Field(ge=0)
    irr_in: float = Field(ge=0)
    # Share of weather years with at least one stress day in this month (see explorer/frost_heat.py):
    # heat = Tmax above the crop's optimum; cold stress = below the optimum for at least half the day;
    # kill = below the crop's killing temperature (real frost damage).
    heat_years_pct: float = Field(ge=0, le=100)
    cold_stress_years_pct: float = Field(ge=0, le=100)
    kill_years_pct: float = Field(ge=0, le=100)
    nitrogen: MonthNitrogen | None = None  # null, see MonthNitrogen

    @model_validator(mode="after")
    def _crop_matches_kind(self) -> MonthDetail:
        if self.kind == "bare" and self.crop is not None:
            raise ValueError(f"{self.m}: kind 'bare' must have crop null")
        if self.kind in ("crop", "cover") and self.crop is None:
            raise ValueError(f"{self.m}: kind '{self.kind}' needs a crop")
        return self


class Summary(_Strict):
    # months per year without crop or cover INSIDE the window (first sowing to last harvest): the gap after the last
    # harvest is not counted (team decision; the scorer sows no cover crop there). Not per cycle like kpi.*_per_year.
    bare_months: float = Field(ge=0, le=12)
    # Seasons whose crop equals the crop before it; season 0 compares to field.previous_crop.
    same_crop_repeats: int = Field(ge=0)
    n_loss_lb: float | None = Field(default=None, ge=0)  # null: N losses are not modelled


def _month(d: date) -> str:
    return f"{d.year}-{d.month:02d}"


class Rotation(ScorerRotation):
    """A rotation in explorer.json: the scorer rotation passed through, plus our data.

    ``sequence`` is redefined here: same scorer fields per season, plus our season values.
    """

    placeholder: bool  # tells the frontend whether the values are still mockup values
    sequence: list[SeasonDetail] = Field(min_length=1)
    monthly: list[MonthDetail] = Field(min_length=1)
    summary: Summary
    cover_variant: Rotation | None = None  # see ScorerRotation.cover_variant, with our data added

    @model_validator(mode="after")
    def _months_cover_window(self) -> Rotation:
        # window = month of the first sowing .. month of the day before the last harvest, no gaps
        first = self.sequence[0].plant_date
        last = self.sequence[-1].harvest_date - timedelta(days=1)
        expected, y, m = [], first.year, first.month
        while (y, m) <= (last.year, last.month):
            expected.append(f"{y}-{m:02d}")
            y, m = (y + 1, 1) if m == 12 else (y, m + 1)
        if [x.m for x in self.monthly] != expected:
            raise ValueError(
                f"rotation {self.id}: monthly must run {_month(first)}..{_month(last)} without gaps"
            )
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
