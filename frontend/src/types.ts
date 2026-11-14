/**
 * Data contract between the scorer/backend and the frontend.
 * Required: field, weights, rotations (one with is_current, plus options). Everything else is optional:
 * the UI hides the matching part when it is missing. Unknown crop ids, priority ids and KPI keys are fine.
 */

/** A KPI value: a number, or a value with a spread (p10/p90 = percentile range, lo/hi = scenario range). */
export type KpiValue = number | { v: number; p10?: number; p90?: number; lo?: number; hi?: number };

export interface RawSeasonYear {
  year: number;
  crop: string;
  irrigation: string; // 'full' | 'reduced' | 'none' | other ids from config/irrigation.ts
  cover?: string | null;
  effects?: string[];
  n_adj?: number;
  yield_pct?: number;
  n_usd?: number;
  pump_usd?: number;
}

export interface RawMonth {
  m: string; // 'YYYY-MM'
  kind: 'crop' | 'cover' | 'bare' | string;
  crop: string | null;
  use: number; rain: number; irr: number; // mm
  heat: number; frost: number; // 0..1 share of past years at risk
  n_fert: number; n_up: number; n_fix: number; n_credit: number; n_pool: number; n_loss: number; // lb N / acre
}

export interface Explanation { title: string; why: string[]; evidence: string[]; benefits: string[]; gaps: string[]; risks: string[]; ask: string[] }

export interface RawRotation {
  id: string; name: string; short: string;
  is_current?: boolean;
  pick?: number; score?: number; score_parts?: Record<string, number>;
  sequence: RawSeasonYear[];
  kpi: Record<string, KpiValue>;
  fits_by_year?: number[]; // 1 = stays within the water right in that weather year
  monthly?: RawMonth[];
}

export interface RawExplorerData {
  field: { name: string; lat: number; lon: number; previous_crop?: string; start_year?: number };
  prices?: { pump?: number; n?: number; n_lo?: number; n_hi?: number };
  weights: Record<string, number>; // priority id -> 1..5
  rotations: RawRotation[];
  climate?: { years: number[] };
  cap_in?: number; // water right, inches per year
  constraints?: { id?: string; ok: boolean; label: string; note?: string }[];
  explanations?: Record<string, Explanation>;
}

/* ---------- normalized shape used by components ---------- */
export interface Kpi { v: number; lo?: number; hi?: number }
export interface Rotation extends Omit<RawRotation, 'kpi' | 'pick' | 'score' | 'score_parts'> {
  is_current: boolean; pick: number | null; score: number | null; score_parts: Record<string, number>; kpi: Record<string, Kpi>;
}
export interface ExplorerData extends Omit<RawExplorerData, 'rotations' | 'prices' | 'cap_in'> {
  rotations: Rotation[]; current: Rotation; options: Rotation[];
  prices: { pump: number; n: number; n_lo: number; n_hi: number };
  cap_in: number | null; seasons: number;
  priorities: { id: string; weight: number }[]; // highest weight first
}
