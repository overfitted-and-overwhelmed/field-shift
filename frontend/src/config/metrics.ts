import { fmtWater, fmtWaterNum, type Units } from '../lib/units';
import type { Kpi } from '../types';

export type Tag = 'measured' | 'modeled' | 'rule' | 'assumption';
export interface MetricCtx { units: Units; nRotations: number | null }

export interface MetricDef {
  key: string; // key in rotation.kpi (derived in data/normalize.ts)
  group: string; // priority id = scorer criterion
  label: string; short: string;
  sub: (c: MetricCtx) => string;
  tag: Tag; better: 'lower' | 'higher';
  fmt: (v: number, c: MetricCtx) => string;
  range?: (k: Kpi, c: MetricCtx) => string | null;
  delta: (absDiff: number, sign: -1 | 1, c: MetricCtx) => string;
}

const num = (v: number, d = 1) => v.toFixed(d);
const lessMore = (s: -1 | 1) => (s < 0 ? 'less' : 'more');
const fewerMore = (s: -1 | 1) => (s < 0 ? 'fewer' : 'more');

/**
 * One row per KPI in the comparison table; order inside a priority group = order here.
 * Groups are the scorer's criteria (score_parts). Values per year are divided by the length of the pass.
 * To change a label, unit or direction (better = lower/higher), edit only this file.
 */
export const METRICS: MetricDef[] = [
  { key: 'irrigation_in', group: 'water', label: 'Irrigation need', short: 'water use', sub: () => 'per year, mean over weather 1991–2025', tag: 'modeled', better: 'lower',
    fmt: (v, c) => fmtWater(v, c.units), range: (k, c) => (k.lo != null && k.hi != null ? `${fmtWaterNum(k.lo, c.units)}–${fmtWaterNum(k.hi, c.units)} (dry vs. wet years)` : null),
    delta: (a, s, c) => `${fmtWater(a, c.units)} ${lessMore(s)}` },
  { key: 'risk', group: 'risk', label: 'Temperature risk', short: 'weather risk', sub: () => 'mean daily heat and frost risk per crop day (0 = none)', tag: 'modeled', better: 'lower',
    fmt: (v) => num(v, 2), delta: (a, s) => `${num(a, 2)} ${s < 0 ? 'lower' : 'higher'}` },
  { key: 'kill_days', group: 'risk', label: 'Killing frost days', short: 'frost kill', sub: () => 'per year, days below the crop’s killing temperature', tag: 'modeled', better: 'lower',
    fmt: (v) => `${num(v)} d`, delta: (a, s) => `${num(a)} d ${fewerMore(s)}` },
  { key: 'heat_days', group: 'risk', label: 'Heat stress days', short: 'heat', sub: () => 'per year, days above the crop’s optimum', tag: 'modeled', better: 'lower',
    fmt: (v) => `${Math.round(v)} d`, delta: (a, s) => `${Math.round(a)} d ${fewerMore(s)}` },
  { key: 'bare_months', group: 'soil_health', label: 'Bare-soil months', short: 'bare soil', sub: () => 'per year within the rotation (first sowing to last harvest), without crop or cover', tag: 'rule', better: 'lower',
    fmt: (v) => `${num(v)} mo`, delta: (a, s) => `${num(a)} mo ${fewerMore(s)}` },
  { key: 'cover_seasons', group: 'soil_health', label: 'Cover crop gaps', short: 'cover crop', sub: () => 'gaps between crops with a triticale cover', tag: 'rule', better: 'higher',
    fmt: (v) => String(v), delta: (a, s) => `${a} ${s > 0 ? 'more' : 'fewer'}` },
  { key: 'same_crop', group: 'soil_health', label: 'Same crop back to back', short: 'same crop', sub: () => 'seasons that repeat the crop before (pests and disease carry over)', tag: 'rule', better: 'lower',
    fmt: (v) => String(v), delta: (a, s) => `${a} ${fewerMore(s)}` },
  { key: 'n_lb', group: 'nitrogen', label: 'Nitrogen fertilizer', short: 'nitrogen', sub: () => 'lb N per acre and year, K-State MF2586 incl. previous-crop credit', tag: 'rule', better: 'lower',
    fmt: (v) => `${Math.round(v)} lb`, delta: (a, s) => `${Math.round(a)} lb ${lessMore(s)}` },
  { key: 'score', group: 'overall', label: 'Overall score', short: 'score', sub: (c) => `weighted for your priorities; 0 = best, 1 = worst of ${c.nRotations ?? 'all'} rotations`, tag: 'modeled', better: 'lower',
    fmt: (v) => num(v, 2), delta: (a, s) => `${num(a, 2)} ${s < 0 ? 'better' : 'worse'}` },
];

export const TAG_LABELS: Record<Tag, string> = { measured: 'Measured', modeled: 'Modeled', rule: 'Rule', assumption: 'Assumption' };
export const TAG_HELP: Record<Tag, string> = {
  measured: 'Taken from observations', modeled: 'Calculated with a model from observed weather', rule: 'Follows a fixed agronomic rule', assumption: 'Placeholder or estimate, check locally',
};

/** The numbers shown for every option in the list. Everything else sits under "All numbers". Keys refer to METRICS. */
export const HEADLINE = ['irrigation_in', 'n_lb', 'bare_months', 'risk'];
