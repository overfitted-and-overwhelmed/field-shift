import { fmtWater, fmtWaterNum, type Units } from '../lib/units';
import type { Kpi } from '../types';

export type Tag = 'measured' | 'modeled' | 'rule' | 'assumption';
export interface MetricCtx { units: Units; nRotations: number | null }

export interface MetricDef {
  key: string; // key in rotation.kpi (derived in data/normalize.ts)
  group: string; // priority id = scorer criterion, or 'overall'
  label: string; // plain words, as a farmer would say it
  unit: (c: MetricCtx) => string; // short unit line under the number
  info: string; // one or two sentences: what it is and how it is made (info point, Data tab)
  provenance: string[]; // keys into the API's provenance table (Data tab: source and kind of number)
  tag: Tag; better: 'lower' | 'higher';
  headline?: boolean; // one of the four numbers on the Plan tab
  arrowByVerdict?: boolean; // arrow points up when better (ranks: a smaller number is a better place)
  fmt: (v: number, c: MetricCtx) => string; // value with its unit
  num: (v: number, c: MetricCtx) => string; // value without unit, for big numerals
  range?: (k: Kpi, c: MetricCtx) => string | null;
  delta: (absDiff: number, sign: -1 | 1, c: MetricCtx) => string; // "2.6 in less"
}

const one = (v: number) => v.toFixed(1);
const lessMore = (s: -1 | 1) => (s < 0 ? 'less' : 'more');
const fewerMore = (s: -1 | 1) => (s < 0 ? 'fewer' : 'more');

/**
 * Every number the dashboard shows, in the order of the Compare tab. Groups are the scorer's criteria.
 * Totals are per year of the rotation cycle, so rotations of different length compare.
 */
export const METRICS: MetricDef[] = [
  { key: 'irrigation_in', group: 'water', label: 'Irrigation water', headline: true, tag: 'modeled', better: 'lower',
    unit: (c) => (c.units === 'in' ? 'inches per year' : 'mm per year'),
    info: 'Water you would pump on top of rain, per year. A daily soil water balance (FAO-56) runs every season of the rotation through 35 years of NASA POWER weather; the number is the average, the range the 10th to 90th percentile.',
    provenance: ['sequence.irr_in', 'monthly.rain_in'],
    fmt: (v, c) => fmtWater(v, c.units), num: (v, c) => fmtWaterNum(v, c.units),
    range: (k, c) => (k.lo != null && k.hi != null ? `${fmtWaterNum(k.lo, c.units)} to ${fmtWater(k.hi, c.units)} (wet to dry years)` : null),
    delta: (a, s, c) => `${fmtWater(a, c.units)} ${lessMore(s)}` },
  { key: 'heat_days', group: 'risk', label: 'Heat stress', headline: true, tag: 'modeled', better: 'lower',
    unit: () => 'days per year',
    info: 'Days per year when the crop on the field is hotter than its comfortable range (FAO Ecocrop limits), counted on NASA POWER daily temperatures.',
    provenance: ['monthly.heat_days'],
    fmt: (v) => `${Math.round(v)} days`, num: (v) => String(Math.round(v)),
    delta: (a, s) => `${Math.round(a)} ${a === 1 ? 'day' : 'days'} ${fewerMore(s)}` },
  { key: 'risk', group: 'risk', label: 'Weather stress score', tag: 'modeled', better: 'lower',
    unit: () => 'per crop day, 0 = none',
    info: 'Average daily heat and cold stress of the crops, weighted by how strongly the temperature leaves the crop’s range. Lower is safer.',
    provenance: ['rotations.*'],
    fmt: (v) => v.toFixed(2), num: (v) => v.toFixed(2),
    delta: (a, s) => `${a.toFixed(2)} ${s < 0 ? 'lower' : 'higher'}` },
  { key: 'kill_days', group: 'risk', label: 'Killing frost', tag: 'modeled', better: 'lower',
    unit: () => 'days per year',
    info: 'Days colder than the crop can survive. Only winter wheat in its winter rest has a documented killing temperature, so this is 0 for most rotations.',
    provenance: ['monthly.kill_days'],
    fmt: (v) => `${one(v)} days`, num: (v) => one(v),
    delta: (a, s) => `${one(a)} days ${fewerMore(s)}` },
  { key: 'bare_months', group: 'soil_health', label: 'Bare soil', headline: true, tag: 'rule', better: 'lower',
    unit: () => 'months per year',
    info: 'Months per year with neither a crop nor a cover crop on the field. Bare soil blows away and loses nitrate; a cover crop closes the gaps.',
    provenance: ['summary.bare_months', 'monthly.kind'],
    fmt: (v) => `${one(v)} months`, num: (v) => one(v),
    delta: (a, s) => `${one(a)} months ${fewerMore(s)}` },
  { key: 'cover_seasons', group: 'soil_health', label: 'Cover crops', tag: 'rule', better: 'higher',
    unit: () => 'gaps with a cover crop',
    info: 'Gaps between two crops that get a cover crop. It is not irrigated and lives on rain.',
    provenance: ['monthly.kind'],
    fmt: (v) => String(v), num: (v) => String(v),
    delta: (a, s) => `${a} ${s > 0 ? 'more' : 'fewer'}` },
  { key: 'same_crop', group: 'soil_health', label: 'Same crop twice in a row', tag: 'rule', better: 'lower',
    unit: () => 'seasons',
    info: 'Seasons that grow the same crop as the season before. Pests and diseases carry over, and yields usually drop a little.',
    provenance: ['field.crop_history'],
    fmt: (v) => String(v), num: (v) => String(v),
    delta: (a, s) => `${a} ${fewerMore(s)}` },
  { key: 'n_lb', group: 'nitrogen', label: 'Nitrogen fertilizer', headline: true, tag: 'rule', better: 'lower',
    unit: () => 'lb N per acre and year',
    info: 'Fertilizer by the K-State MF2586 recommendation for each crop, including the credit after soybean and the extra after a cover crop.',
    provenance: ['sequence.n_lb', 'sequence.n_adj_lb'],
    fmt: (v) => `${Math.round(v)} lb`, num: (v) => String(Math.round(v)),
    delta: (a, s) => `${Math.round(a)} lb ${lessMore(s)}` },
  { key: 'rank', group: 'overall', label: 'Rank for your priorities', tag: 'modeled', better: 'lower', arrowByVerdict: true,
    unit: (c) => `of ${c.nRotations ?? 'all'} rotations, 1 = best`,
    info: 'The scorer rates every three-crop rotation, with and without cover crops, on water, weather stress, soil health and fertilizer, weighs the four by your priorities and sorts them. Rotations with more than one sunflower or soybean crop (white mold) come after all others. 1 is the best match for you.',
    provenance: ['rotations.*'],
    fmt: (v, c) => `${Math.round(v)} of ${c.nRotations ?? '–'}`, num: (v) => String(Math.round(v)),
    delta: (a, s) => `${Math.round(a)} ${a === 1 ? 'place' : 'places'} ${s < 0 ? 'better' : 'worse'}` },
];

export const HEADLINE = METRICS.filter((m) => m.headline);
export const metricByKey = (key: string) => METRICS.find((m) => m.key === key);

export const TAG_LABELS: Record<Tag, string> = { measured: 'Measured', modeled: 'Modeled', rule: 'Rule', assumption: 'Assumption' };
export const TAG_HELP: Record<Tag, string> = {
  measured: 'Taken from observations', modeled: 'Calculated with a model from observed weather', rule: 'Follows a fixed agronomic rule', assumption: 'An estimate or setting; check it for your farm',
};
