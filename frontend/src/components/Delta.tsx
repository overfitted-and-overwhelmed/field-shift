import { ArrowDown, ArrowUp, Equal } from 'lucide-react';
import type { MetricCtx, MetricDef } from '../config/metrics';
import { compare } from '../data/metrics';

/**
 * Change of one number against a base, in words, with direction and verdict:
 * green = better for the farmer, red = worse. Never colour alone: the words say "less"/"more".
 * `compact` drops "than yours" where the column already says what it is compared with.
 */
export function Delta({ m, v, base, ctx, against, prefix = '', compact = false }: {
  m: MetricDef; v: number; base: number; ctx: MetricCtx; against: string; prefix?: string; compact?: boolean;
}) {
  const diff = +(v - base).toFixed(2);
  if (diff === 0) return <span className="delta same"><Equal size={14} aria-hidden="true" />{prefix}{compact ? 'same' : `same as ${against}`}</span>;
  const verdict = compare(m, v, base);
  const up = m.arrowByVerdict ? verdict === 'better' : diff > 0;
  const Icon = up ? ArrowUp : ArrowDown;
  const words = m.delta(Math.abs(diff), diff < 0 ? -1 : 1, ctx);
  return (
    <span className={`delta ${verdict === 'better' ? 'good' : 'bad'}`} title={compact ? `${words} than ${against}` : undefined}>
      <Icon size={14} strokeWidth={2.5} aria-hidden="true" />
      {prefix}{compact ? words : `${words} than ${against}`}
      {compact && <span className="sr-only"> than {against}</span>}
    </span>
  );
}
