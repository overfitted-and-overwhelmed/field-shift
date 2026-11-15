/**
 * Data contract with the backend: explorer.json as written by explorer/build.py and served by explorer/api.py.
 * The source of truth is explorer/schema.py (ExplorerExport). Keep the Api* types in sync with it.
 * Units are part of the field names: _in = inches of water, _lb = lb N per acre, _pct = 0-100.
 */

/** Mean over the weather years with 10th and 90th percentile. */
export interface Spread { v: number; p10: number; p90: number }

export interface ApiEffect { text: string; source: string | null; provenance: string }

export interface ApiSeason {
  year: number; // harvest year; winter crops are planted in the autumn before
  crop: string;
  irrigation: string; // 'full' | 'reduced' | 'none'
  cover: string | null; // cover crop in the gap after this season
  plant_date: string; harvest_date: string; // 'YYYY-MM-DD'; the harvest day is not part of the season
  irr_in: Spread;
  yield: Spread & { unit: 'bu' | 'lb' };
  n_lb: number | null; n_adj_lb: number | null; // null until WP4 nitrogen delivers
  yield_pct_rotation: number;
  effects: ApiEffect[];
}

export interface ApiMonth {
  m: string; // 'YYYY-MM'
  kind: 'crop' | 'cover' | 'bare';
  crop: string | null;
  et_in: number; rain_in: number; irr_in: number;
  heat_days: number; cold_stress_days: number; kill_days: number; // mean stress days in the month
  heat_years_pct: number; cold_stress_years_pct: number; kill_years_pct: number; // share of weather years, 0-100
}

/** Scores 0 = best, 1 = worst among all rotations the scorer ranked. */
export type ScoreParts = Record<string, number>;

export interface ApiRotation {
  id: string; is_current: boolean; rank: number | null;
  name: string; short: string; category: string | null;
  sequence: ApiSeason[]; // one pass of the rotation; not one season per year
  score: number | null; score_parts: ScoreParts | null;
  kpi: Record<string, number> | null; // the scorer's values for the whole pass, US units
  placeholder: boolean;
  monthly: ApiMonth[];
  summary: { bare_months: number; same_crop_repeats: number; n_loss_lb: number | null };
}

export interface ApiField {
  id: string; name: string; lat: number; lon: number; elevation_ft: number; slope_pct: number;
  soil: { texture: string; water_capacity_in: number; organic_matter_pct: number };
  crop_history: { year: number; crop: string }[];
  previous_crop: string; rotation_start_year: number;
}

export interface ApiExplorer {
  contract_version: string; generated_at: string;
  field: ApiField;
  crops: Record<string, { label: string; yield_unit: 'bu' | 'lb' | null; season: string; legume: boolean; is_cover: boolean }>;
  climate: { weather_years: number[]; rain_in: number[]; et0_apr_sep_in: number[]; deficit_apr_sep_in: number[]; heat_days_ge_35: number[] };
  rotations: ApiRotation[];
  provenance: Record<string, { label: string; source: string | null }>;
  sources: Record<string, { title: string; url?: string | null; retrieved?: string | null }>;
}

/* ---------- normalized shape used by components ---------- */
export interface Kpi { v: number; lo?: number; hi?: number }

export interface Rotation extends Omit<ApiRotation, 'kpi' | 'rank' | 'score_parts'> {
  pick: number | null; // 1 = best match; null for today's rotation
  years: number; // length of the pass in years (window days / 365.25)
  score_parts: ScoreParts;
  raw: Record<string, number>; // the scorer's kpi as sent
  kpi: Record<string, Kpi>; // derived values shown in the UI, keys in config/metrics.ts
}

export interface ExplorerData extends Omit<ApiExplorer, 'rotations'> {
  rotations: Rotation[]; current: Rotation; options: Rotation[];
  nRotations: number | null; // how many rotations the scorer ranked
  priorities: { id: string; weight: number }[]; // highest weight first
}
