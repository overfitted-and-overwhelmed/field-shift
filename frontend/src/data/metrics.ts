import type { MetricDef } from '../config/metrics';

export type Verdict = 'better' | 'worse' | 'same';
export function compare(m: MetricDef, value: number, base: number): Verdict {
  const diff = +(value - base).toFixed(2);
  if (diff === 0) return 'same';
  return (m.better === 'lower') === diff < 0 ? 'better' : 'worse';
}
