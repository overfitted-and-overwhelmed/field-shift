import { cropLabel } from '../config/crops';
import type { MetricDef } from '../config/metrics';
import { compare } from '../data/metrics';
import type { Rotation } from '../types';

/** "Corn, soybean, sorghum": the crops in order, in plain words. */
export const cropsName = (r: Rotation) => r.sequence.map((s, i) => (i ? cropLabel(s.crop).toLowerCase() : cropLabel(s.crop))).join(', ');

/** "Triticale cover crop in both gaps", "Triticale cover crop after year 1 (corn)", or "". No gap after the last crop. */
export function coverNote(r: Rotation): string {
  const gaps = r.sequence.slice(0, -1);
  const on = gaps.map((s, i) => ({ s, i })).filter(({ s }) => s.cover);
  if (!on.length) return '';
  const cover = `${cropLabel(on[0].s.cover)} cover crop`;
  if (on.length === gaps.length) return `${cover} ${gaps.length === 2 ? 'in both gaps' : 'in every gap'}`;
  return `${cover} after year ${on.map(({ i }) => i + 1).join(' and ')} (${on.map(({ s }) => cropLabel(s.crop).toLowerCase()).join(', ')})`;
}

/** Label of a pick: "Best match", "Option 2". */
export const pickLabel = (r: Rotation) => (r.pick === 1 ? 'Best match' : `Option ${r.pick}`);

/** Crops and cover flags to load a rotation into the builder. */
export const toBuilder = (r: Rotation) => ({
  rotation: r.sequence.map((s) => s.crop),
  cover: r.sequence.slice(0, -1).map((s) => !!s.cover),
});

/** Per metric: is this rotation better, worse or the same as the base? The overall score is left out. */
export function vsBase(r: Rotation, base: Rotation, metrics: MetricDef[]) {
  return metrics.filter((m) => r.kpi[m.key] && base.kpi[m.key] && m.group !== 'overall')
    .map((m) => ({ m, verdict: compare(m, r.kpi[m.key].v, base.kpi[m.key].v), diff: r.kpi[m.key].v - base.kpi[m.key].v }));
}
