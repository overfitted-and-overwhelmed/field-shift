import { CONTENT } from '../config/content';
import { cropLabel } from '../config/crops';
import type { MetricCtx, MetricDef } from '../config/metrics';
import { priorityLabel } from '../config/priorities';
import { fmtWater, type Units } from '../lib/units';
import type { ExplorerData, Rotation } from '../types';
import { pickLabel, vsCurrent } from './helpers';
import { SecHead } from './ui';

/** One color per scorer criterion, so the parts stay apart even with equal weights. */
const CRIT_COLOR: Record<string, string> = { water: 'var(--accent)', risk: 'var(--heat)', soil_health: 'var(--c-soybean)', nitrogen: 'var(--c-winter_wheat)' };

const List = ({ items }: { items: string[] }) => <ul>{items.map((x, i) => <li key={i}>{x}</li>)}</ul>;

/** Plain-language summary built from the numbers (the backend sends no explanation texts). */
function summary(r: Rotation, data: ExplorerData, units: Units): string {
  const k = r.kpi, crops = r.sequence.map((s) => cropLabel(s.crop)).join(', then ');
  const parts = [`${crops}${r.sequence.some((s) => s.cover) ? ', with a triticale cover crop in the gaps' : ''}.`];
  if (k.irrigation_in) parts.push(`It needs about ${fmtWater(k.irrigation_in.v, units)} of irrigation per year.`);
  if (k.n_lb) parts.push(`Nitrogen by K-State rules: ${Math.round(k.n_lb.v)} lb N per acre and year.`);
  if (k.bare_months) parts.push(`The soil is bare ${k.bare_months.v.toFixed(1)} months per year.`);
  if (!r.is_current && r.raw.rank_all) parts.push(`For your priorities it ranks ${r.raw.rank_all} of ${data.nRotations ?? 'all'} rotations the scorer compared.`);
  return parts.join(' ');
}

/** Stacked bars: each priority's share of the total score (weight × part score / sum of weights). Shorter = better. */
function ScoreParts({ data, selected }: { data: ExplorerData; selected: Rotation }) {
  const rows = [data.current, ...data.options].filter((r) => r.score != null);
  const ws = data.priorities.filter((p) => p.weight > 0), wsum = ws.reduce((a, p) => a + p.weight, 0) || 1;
  const w = 1100, rowH = 34, L = 300, R = 60, iw = w - L - R, h = rows.length * rowH + 10;
  const max = Math.max(...rows.map((r) => r.score ?? 0), 0.01);
  return (
    <>
      <svg viewBox={`0 0 ${w} ${h}`} role="img" aria-label="Score by priority">
        {rows.map((r, i) => {
          const y0 = 6 + i * rowH; let x0 = L;
          return (
            <g key={r.id}>
              <text x={L - 8} y={y0 + 17} textAnchor="end" className={r.id === selected.id ? 'lab' : ''}>{r.is_current ? 'Yours' : `#${r.pick}`} · {r.name.length > 40 ? `${r.name.slice(0, 39)}…` : r.name}</text>
              {ws.map((p) => {
                const part = (r.score_parts[p.id] ?? 0) * p.weight / wsum, bw = (part / max) * iw, x = x0;
                x0 += bw;
                return bw > 0.5 ? <rect key={p.id} x={x} y={y0 + 4} width={Math.max(bw - 2, 1)} height={20} rx={3} style={{ fill: CRIT_COLOR[p.id] ?? 'var(--ink-3)' }}
                  data-tip={`${priorityLabel(p.id)} (weight ${p.weight}): part score ${(r.score_parts[p.id] ?? 0).toFixed(2)} → ${part.toFixed(3)} of the total`} /> : null;
              })}
              <text x={x0 + 6} y={y0 + 18} className="lab">{r.score!.toFixed(2)}</text>
            </g>
          );
        })}
      </svg>
      <div className="legend">{ws.map((p) => <span key={p.id}><i style={{ background: CRIT_COLOR[p.id] ?? 'var(--ink-3)' }} />{priorityLabel(p.id)} ({p.weight}/5)</span>)}</div>
    </>
  );
}

/** Step 5: why the selected rotation, what speaks for and against it, and how the scores add up. */
export function Why({ data, selected, metrics, mctx, units }: { data: ExplorerData; selected: Rotation; metrics: MetricDef[]; mctx: MetricCtx; units: Units }) {
  const r = selected, cur = data.current;
  const vc = r.is_current ? [] : vsCurrent(r, cur, metrics);
  const better = vc.filter((x) => x.verdict === 'better').map((x) => `${x.m.label}: ${x.m.delta(Math.abs(+x.diff.toFixed(2)), x.diff < 0 ? -1 : 1, mctx)} than yours`);
  const worse = vc.filter((x) => x.verdict === 'worse').map((x) => `${x.m.label}: ${x.m.delta(Math.abs(+x.diff.toFixed(2)), x.diff < 0 ? -1 : 1, mctx)} than yours`);
  const assumptions = [...new Set(r.sequence.flatMap((s) => s.effects.filter((e) => e.provenance === 'assumption').map((e) => `${cropLabel(s.crop)}: ${e.text}`)))];
  const picksBetter = data.options.map((o) => `#${o.pick} ${o.name}: better on ${vsCurrent(o, cur, metrics).filter((x) => x.verdict === 'better').length} of ${vsCurrent(o, cur, metrics).length} measures`);
  const srcTitles = Object.values(data.sources).map((s) => s.title);
  return (
    <section id="why" aria-labelledby="why-h">
      <SecHead id="why-h" eyebrow={CONTENT.why.eyebrow} title={r.is_current ? `Your rotation: ${r.name}` : `${pickLabel(r)}: ${r.name}`} />
      <div className="why">
        <div className="card wide"><h3>{r.is_current ? 'What your rotation does' : 'Why it is suggested'}</h3><p>{summary(r, data, units)}</p></div>
        <div className="card"><h3>Evidence</h3><List items={srcTitles.slice(0, 6)} /></div>
        <div className="card"><h3>{r.is_current ? 'Where the picks do better' : 'Better than your rotation'}</h3><List items={r.is_current ? picksBetter : better.length ? better : ['No measure better than your rotation']} /></div>
        <div className="card"><h3>What to check</h3><List items={[...worse, ...assumptions, 'Irrigation is assumed full on every season.'].slice(0, 7)} /></div>
      </div>
      <div className="card">
        <h3>How the scores compare</h3>
        <p className="small muted">The scorer scales each criterion from the best (0) to the worst (1) of {data.nRotations ?? 'all'} rotations and averages them with your weights. Shorter bars are better.</p>
        <ScoreParts data={data} selected={r} />
      </div>
      <div className="disclaimer">
        <h3>{CONTENT.caution.title}</h3>
        <p className="muted">{CONTENT.caution.text}</p>
      </div>
    </section>
  );
}
