import type { ApiExplorer, ApiRotation, ExplorerData, Kpi, Rotation } from '../types';

const fail = (msg: string): never => { throw new Error(`Invalid explorer data: ${msg}`); };
const DAYS_PER_YEAR = 365.25;

/** Days from the first sowing to the day before the last harvest, if the scorer did not send window_days. */
function windowDays(r: ApiRotation): number {
  const first = Date.parse(r.sequence[0].plant_date), last = Date.parse(r.sequence[r.sequence.length - 1].harvest_date);
  return (last - first) / 86_400_000;
}

/**
 * The values the UI compares. Passes differ in length (double crops, skipped years), so totals are shown per year.
 * Keys must match config/metrics.ts.
 */
function deriveKpis(r: ApiRotation, years: number): Record<string, Kpi> {
  const k = r.kpi ?? {};
  const perYear = (v: number) => v / years;
  const out: Record<string, Kpi> = {};
  const irr = r.sequence.reduce((a, s) => ({ v: a.v + s.irr_in.v, lo: a.lo + s.irr_in.p10, hi: a.hi + s.irr_in.p90 }), { v: 0, lo: 0, hi: 0 });
  out.irrigation_in = { v: perYear(k.irrigation_in ?? irr.v), lo: perYear(irr.lo), hi: perYear(irr.hi) };
  if (k.n_fertilizer_lb != null) out.n_lb = { v: perYear(k.n_fertilizer_lb) };
  if (k.risk_per_crop_day != null) out.risk = { v: k.risk_per_crop_day };
  if (k.kill_days != null) out.kill_days = { v: perYear(k.kill_days) };
  if (k.heat_days != null) out.heat_days = { v: perYear(k.heat_days) };
  out.bare_months = { v: r.summary.bare_months };
  out.same_crop = { v: r.summary.same_crop_repeats };
  out.cover_seasons = { v: r.sequence.filter((s) => s.cover).length };
  if (r.score != null) out.score = { v: r.score };
  return out;
}

/** Validates the minimum shape and derives what the components need. Throws a readable error otherwise. */
export function normalize(raw: ApiExplorer, weights: Record<string, number>): ExplorerData {
  if (!raw || typeof raw !== 'object') fail('not an object');
  if (!raw.field) fail('missing "field"');
  if (!Array.isArray(raw.rotations) || raw.rotations.length < 2) fail('need the current rotation and at least one option');

  const rotations: Rotation[] = raw.rotations.map((r) => {
    if (!r.id || !Array.isArray(r.sequence) || !r.sequence.length) fail(`rotation "${r.id ?? '?'}" needs id and sequence`);
    const years = (r.kpi?.window_days ?? windowDays(r)) / DAYS_PER_YEAR;
    const { rank, kpi, ...rest } = r;
    return { ...rest, pick: rank, years, score_parts: r.score_parts ?? {}, raw: kpi ?? {}, kpi: deriveKpis(r, years), monthly: r.monthly ?? [] };
  });
  const current = rotations.find((r) => r.is_current) ?? fail('no rotation has is_current = true');
  const options = rotations.filter((r) => !r.is_current);
  if (options.some((r) => r.pick == null)) [...options].sort((a, b) => (a.score ?? 1) - (b.score ?? 1)).forEach((r, i) => (r.pick = i + 1)); // 0 = best
  options.sort((a, b) => (a.pick ?? 99) - (b.pick ?? 99));

  return {
    ...raw, rotations, current, options,
    nRotations: current.raw.n_rotations ?? null,
    priorities: Object.entries(weights).map(([id, weight]) => ({ id, weight })).sort((a, b) => b.weight - a.weight),
  };
}
