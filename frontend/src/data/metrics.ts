import { METRICS, type MetricDef } from '../config/metrics';
import type { ExplorerData } from '../types';

/** Configured metrics that exist in the data. KPIs are derived in data/normalize.ts, labels live in config/metrics.ts. */
export function activeMetrics(data: ExplorerData): MetricDef[] {
  const present = new Set(data.rotations.flatMap((r) => Object.keys(r.kpi)));
  return METRICS.filter((m) => present.has(m.key));
}

export type Verdict = 'better' | 'worse' | 'same';
export function compare(m: MetricDef, value: number, base: number): Verdict {
  const diff = +(value - base).toFixed(2);
  if (diff === 0) return 'same';
  return (m.better === 'lower') === diff < 0 ? 'better' : 'worse';
}
