import type { MetricDef } from '../config/metrics';
import { compare } from '../data/metrics';
import type { Rotation } from '../types';

/** Label used for a rotation everywhere: "Your rotation" or "#1 · Best match". */
export const pickLabel = (r: Rotation) => (r.is_current ? 'Your rotation' : r.pick === 1 ? '#1 · Best match' : `#${r.pick}`);

/** Per metric: is this rotation better, worse or the same as yours? The overall score is left out. */
export function vsCurrent(r: Rotation, cur: Rotation, metrics: MetricDef[]) {
  return metrics.filter((m) => r.kpi[m.key] && cur.kpi[m.key] && m.group !== 'overall')
    .map((m) => ({ m, verdict: compare(m, r.kpi[m.key].v, cur.kpi[m.key].v), diff: r.kpi[m.key].v - cur.kpi[m.key].v }));
}
