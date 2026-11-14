import { humanize } from '../config/crops';
import { METRICS, type MetricDef } from '../config/metrics';
import type { ExplorerData } from '../types';

/** Row for a KPI that METRICS does not know. Lower is assumed better; define it in config/metrics.ts to change. */
const generic = (key: string, group: string): MetricDef => ({
  key, group, label: humanize(key), short: humanize(key).toLowerCase(), sub: () => '', tag: 'assumption', better: 'lower',
  fmt: (v) => String(Math.round(v * 100) / 100), delta: (a, s) => `${Math.round(a * 100) / 100} ${s < 0 ? 'less' : 'more'}`,
});

/** Configured metrics that exist in the data, plus any unknown KPI as a generic row in the last priority group. */
export function activeMetrics(data: ExplorerData): MetricDef[] {
  const present = new Set(data.rotations.flatMap((r) => Object.keys(r.kpi)));
  const known = new Set(METRICS.map((m) => m.key));
  const lastGroup = data.priorities[data.priorities.length - 1]?.id ?? 'other';
  return [...METRICS.filter((m) => present.has(m.key)), ...[...present].filter((k) => !known.has(k)).map((k) => generic(k, lastGroup))];
}

export type Verdict = 'better' | 'worse' | 'same';
export function compare(m: MetricDef, value: number, base: number): Verdict {
  const diff = +(value - base).toFixed(2);
  if (diff === 0) return 'same';
  return (m.better === 'lower') === diff < 0 ? 'better' : 'worse';
}
