import type { ExplorerData, Kpi, KpiValue, RawExplorerData, RawRotation, Rotation } from '../types';

const toKpi = (x: KpiValue): Kpi => (typeof x === 'number' ? { v: x } : { v: x.v, lo: x.p10 ?? x.lo, hi: x.p90 ?? x.hi });
const fail = (msg: string): never => { throw new Error(`Invalid explorer data: ${msg}`); };

/** Validates the minimum shape and fills in everything that can be derived. Throws a readable error otherwise. */
export function normalize(raw: RawExplorerData): ExplorerData {
  if (!raw || typeof raw !== 'object') fail('not an object');
  if (!raw.field) fail('missing "field"');
  if (!raw.weights || !Object.keys(raw.weights).length) fail('missing "weights"');
  if (!Array.isArray(raw.rotations) || raw.rotations.length < 2) fail('need the current rotation and at least one option');

  const rotations: Rotation[] = raw.rotations.map((r: RawRotation) => {
    if (!r.id || !Array.isArray(r.sequence) || !r.kpi) fail(`rotation "${r.id ?? '?'}" needs id, sequence and kpi`);
    return { ...r, is_current: !!r.is_current, pick: r.pick ?? null, score: r.score ?? null, score_parts: r.score_parts ?? {}, kpi: Object.fromEntries(Object.entries(r.kpi).map(([k, v]) => [k, toKpi(v)])) };
  });
  const current = rotations.find((r) => r.is_current) ?? fail('no rotation has is_current = true');
  const options = rotations.filter((r) => !r.is_current);
  if (options.some((r) => r.pick == null)) [...options].sort((a, b) => (b.score ?? 0) - (a.score ?? 0)).forEach((r, i) => (r.pick = i + 1)); // rank by score if the scorer sent no pick
  options.sort((a, b) => (a.pick ?? 99) - (b.pick ?? 99));

  return {
    ...raw, rotations, current, options,
    prices: { pump: 0, n: 0, n_lo: 0, n_hi: 0, ...raw.prices },
    cap_in: raw.cap_in ?? null,
    seasons: raw.climate?.years?.length ?? current.fits_by_year?.length ?? 0,
    priorities: Object.entries(raw.weights).map(([id, weight]) => ({ id, weight })).sort((a, b) => b.weight - a.weight),
  };
}
