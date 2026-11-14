import { fmtWater, fmtWaterNum, type Units } from '../lib/units';
import type { Kpi } from '../types';

export type Tag = 'measured' | 'modeled' | 'rule' | 'assumption';
export interface MetricCtx { units: Units; seasons: number; capIn: number | null; rotationYears: number; prices: { pump: number; n: number; n_lo: number; n_hi: number } }

export interface MetricDef {
  key: string; // key in rotation.kpi
  group: string; // priority id
  label: string; short: string;
  sub: (c: MetricCtx) => string;
  tag: Tag; better: 'lower' | 'higher';
  fmt: (v: number, c: MetricCtx) => string;
  range?: (k: Kpi, c: MetricCtx) => string | null;
  delta: (absDiff: number, sign: -1 | 1, c: MetricCtx) => string;
}

const usd = (v: number) => `$${Math.round(v)}`;
const usdRange = (k: Kpi) => (k.lo != null && k.hi != null ? `$${Math.round(k.lo)}–${Math.round(k.hi)}` : null);
const dollars = (a: number, s: -1 | 1) => `${usd(a)} ${s < 0 ? 'less' : 'more'}`;

/**
 * One row per KPI in the comparison table; order inside a priority group = order here.
 * A KPI the scorer sends but that is not listed gets a generic row (see data/metrics.ts).
 * To change a label, unit or direction (better = lower/higher), edit only this file.
 */
export const METRICS: MetricDef[] = [
  { key: 'irrigation_in', group: 'water', label: 'Irrigation need', short: 'water use', sub: () => 'per year, average over the rotation', tag: 'modeled', better: 'lower',
    fmt: (v, c) => fmtWater(v, c.units), range: (k, c) => (k.lo != null && k.hi != null ? `${fmtWaterNum(k.lo, c.units)}–${fmtWaterNum(k.hi, c.units)}` : null),
    delta: (a, s, c) => `${fmtWater(a, c.units)} ${s < 0 ? 'less' : 'more'}` },
  { key: 'within_right', group: 'water', label: 'Fits your water right', short: 'water-right fit', sub: (c) => `weather years in which every year stays within ${c.capIn ?? '–'} in`, tag: 'modeled', better: 'higher',
    fmt: (v, c) => `${v} of ${c.seasons}`, delta: (a, s) => `${a} ${s > 0 ? 'more' : 'fewer'} years` },
  { key: 'profit', group: 'profit', label: 'Net return', short: 'income', sub: () => 'per acre and year, after pumping and fertilizer cost', tag: 'assumption', better: 'higher',
    fmt: (v) => usd(v), range: usdRange, delta: (a, s) => `${usd(a)} ${s > 0 ? 'more' : 'less'}` },
  { key: 'pump_cost', group: 'profit', label: 'Pumping cost', short: 'pumping cost', sub: (c) => `per acre and year at $${c.prices.pump} per acre-inch`, tag: 'assumption', better: 'lower',
    fmt: (v) => usd(v), range: usdRange, delta: dollars },
  { key: 'n_cost', group: 'profit', label: 'Nitrogen fertilizer cost', short: 'fertilizer cost', sub: (c) => `per acre and year at $${c.prices.n.toFixed(2)}/lb N; range uses $${c.prices.n_lo.toFixed(2)}–${c.prices.n_hi.toFixed(2)}`, tag: 'assumption', better: 'lower',
    fmt: (v) => usd(v), range: usdRange, delta: dollars },
  { key: 'bare_months', group: 'soil', label: 'Bare-soil months', short: 'bare soil', sub: () => 'per year without crop or cover', tag: 'rule', better: 'lower',
    fmt: (v) => `${v.toFixed(1)} mo`, delta: (a, s) => `${a.toFixed(1)} mo ${s < 0 ? 'fewer' : 'more'}` },
  { key: 'n_lb', group: 'soil', label: 'Nitrogen fertilizer', short: 'nitrogen', sub: () => 'lb N per acre and year, after legume credit', tag: 'assumption', better: 'lower',
    fmt: (v) => `${Math.round(v)} lb`, delta: (a, s) => `${Math.round(a)} lb ${s < 0 ? 'less' : 'more'}` },
  { key: 'n_loss', group: 'soil', label: 'Nitrate lost', short: 'nitrate loss', sub: () => 'lb N per acre and year leaving the root zone, mostly under bare soil', tag: 'modeled', better: 'lower',
    fmt: (v) => `${Math.round(v)} lb`, delta: (a, s) => `${Math.round(a)} lb ${s < 0 ? 'less' : 'more'}` },
  { key: 'same_crop', group: 'soil', label: 'Same crop back to back', short: 'same crop', sub: (c) => `years of ${c.rotationYears} (pests and disease carry over)`, tag: 'rule', better: 'lower',
    fmt: (v, c) => `${v} of ${c.rotationYears}`, delta: (a, s) => `${a} ${s < 0 ? 'fewer' : 'more'}` },
  { key: 'spring_bare', group: 'erosion', label: 'Bare in the windy season', short: 'wind erosion', sub: () => 'months per year, Feb–May', tag: 'rule', better: 'lower',
    fmt: (v) => `${v.toFixed(1)} mo`, delta: (a, s) => `${a.toFixed(1)} mo ${s < 0 ? 'fewer' : 'more'}` },
];

export const TAG_LABELS: Record<Tag, string> = { measured: 'Measured', modeled: 'Modeled', rule: 'Rule', assumption: 'Assumption' };
export const TAG_HELP: Record<Tag, string> = {
  measured: 'Taken from observations', modeled: 'Calculated with a model from observed weather', rule: 'Follows a fixed agronomic rule', assumption: 'Placeholder or estimate, check locally',
};

/** Scatter plot axes: x = lower is better, y = higher is better. Keys refer to METRICS. */
export const SCATTER = { x: 'irrigation_in', y: 'profit', xTitle: 'Irrigation need per year', yTitle: 'Net return per acre' };

/** The three numbers shown for every option in the list. Everything else sits under "All numbers". Keys refer to METRICS. */
export const HEADLINE = ['irrigation_in', 'profit', 'bare_months'];
