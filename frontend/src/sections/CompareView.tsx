import { Delta } from '../components/Delta';
import { Info } from '../components/Info';
import { MonthStrip } from '../components/MonthStrip';
import { CONTENT } from '../config/content';
import { TAG_LABELS, type MetricCtx, type MetricDef } from '../config/metrics';
import { priorityLabel } from '../config/priorities';
import { calendarSpan } from '../lib/calendar';
import type { PageState } from '../lib/request';
import { inToUnit, type Units } from '../lib/units';
import type { ExplorerData, Rotation } from '../types';
import { coverNote, cropsName, pickLabel, toBuilder } from './helpers';

interface Col { key: string; label: string; r: Rotation; pick: boolean }
interface Props {
  data: ExplorerData; mine: Rotation; picks: Rotation[];
  metrics: MetricDef[]; ctx: MetricCtx; units: Units; set: (f: (s: PageState) => PageState) => void; onMonths: (id: string) => void;
}

const standing = (part: number) => (part <= 0.33 ? 'Good' : part <= 0.66 ? 'Fair' : 'Poor');

/** Points that land within a few pixels of each other share one stacked label, so equal rotations stay readable. */
function clusters(pts: Col[], x: (v: number) => number, y: (v: number) => number) {
  const out: { x: number; y: number; labels: string[] }[] = [];
  for (const c of pts) {
    const px = x(c.r.kpi.irrigation_in.v), py = y(c.r.kpi.n_lb.v);
    const near = out.find((g) => Math.abs(g.x - px) < 14 && Math.abs(g.y - py) < 14);
    if (near) near.labels.push(c.label); else out.push({ x: px, y: py, labels: [c.label] });
  }
  return out;
}

/** "Best match, options 2 and 3": rotations at the same spot named in one line. */
function joinLabels(labels: string[]) {
  if (labels.length === 1) return labels[0];
  const rest = labels.slice(1).map((l) => l.replace(/^Option /, ''));
  const head = labels[0];
  const tail = rest.length > 1 ? `${rest.slice(0, -1).join(', ')} and ${rest[rest.length - 1]}` : rest[0];
  return `${head}, option${rest.length > 1 ? 's' : ''} ${tail}`;
}

/** Irrigation (x) against nitrogen (y), both per year: down and to the left is better on both. */
function TradeOff({ cols, units }: { cols: Col[]; units: Units }) {
  const pts = cols.filter((c) => c.r.kpi.irrigation_in && c.r.kpi.n_lb);
  if (pts.length < 2) return null;
  const w = 520, h = 260, L = 56, R = 16, T = 14, B = 44, iw = w - L - R, ih = h - T - B;
  const xmax = Math.max(...pts.map((c) => inToUnit(c.r.kpi.irrigation_in.hi ?? c.r.kpi.irrigation_in.v, units))) * 1.08;
  const ymax = Math.max(50, ...pts.map((c) => c.r.kpi.n_lb.v)) * 1.18;
  const x = (inches: number) => L + (inToUnit(inches, units) / xmax) * iw, y = (v: number) => T + ih - (v / ymax) * ih;
  const step = (m: number) => { const s = 10 ** Math.floor(Math.log10(m / 4)); return [1, 2, 5, 10].map((k) => k * s).find((k) => m / k <= 6) ?? s * 10; };
  const xs = step(xmax), ys = step(ymax);
  const mine = pts[0].r;
  return (
    <svg viewBox={`0 0 ${w} ${h}`} className="chart" role="img" aria-label="Irrigation water against nitrogen fertilizer per year for each rotation">
      <rect x={L} y={y(mine.kpi.n_lb.v)} width={Math.max(0, x(mine.kpi.irrigation_in.v) - L)} height={Math.max(0, T + ih - y(mine.kpi.n_lb.v))} className="better-zone" />
      <text x={L + 8} y={T + ih - 10} className="better-label">Less water and less fertilizer than yours</text>
      {Array.from({ length: Math.floor(xmax / xs) + 1 }, (_, i) => i * xs).map((v) => <g key={`x${v}`}><line className="grid" x1={L + (v / xmax) * iw} x2={L + (v / xmax) * iw} y1={T} y2={T + ih} /><text x={L + (v / xmax) * iw} y={T + ih + 18} textAnchor="middle">{v}</text></g>)}
      {Array.from({ length: Math.floor(ymax / ys) + 1 }, (_, i) => i * ys).map((v) => <g key={`y${v}`}><line className="grid" x1={L} x2={w - R} y1={y(v)} y2={y(v)} /><text x={L - 8} y={y(v) + 4} textAnchor="end">{v}</text></g>)}
      <text x={L + iw / 2} y={h - 4} textAnchor="middle" className="axis-title">Irrigation water per year ({units})</text>
      <text x={14} y={T + ih / 2} textAnchor="middle" transform={`rotate(-90 14 ${T + ih / 2})`} className="axis-title">Nitrogen, lb per acre</text>
      {pts.map((c) => {
        const k = c.r.kpi.irrigation_in, cy = y(c.r.kpi.n_lb.v);
        return (
          <g key={c.key} className={`pt ${c.pick ? 'pick' : 'mine'}`} data-tip={`${c.label}: ${cropsName(c.r)}`}>
            {k.lo != null && k.hi != null && <line x1={x(k.lo)} x2={x(k.hi)} y1={cy} y2={cy} className="whisker" />}
            <circle cx={x(k.v)} cy={cy} r={7} />
          </g>
        );
      })}
      {clusters(pts, x, y).map((g) => (
        <text key={g.labels.join()} x={g.x + 10} y={g.y - 13} className="pt-label">{joinLabels(g.labels)}</text>
      ))}
    </svg>
  );
}

/** Each rotation on the four priorities, in words and bars: where it stands among all rotations. */
function Strengths({ cols, data }: { cols: Col[]; data: ExplorerData }) {
  const prios = data.priorities.map((p) => p.id);
  return (
    <table className="strengths">
      <thead><tr><th scope="col">Rotation</th>{prios.map((p) => <th scope="col" key={p}>{priorityLabel(p)}</th>)}</tr></thead>
      <tbody>
        {cols.map((c) => (
          <tr key={c.key}>
            <th scope="row">{c.label}</th>
            {prios.map((p) => {
              const part = Math.min(1, Math.max(0, c.r.score_parts[p] ?? 1));
              return (
                <td key={p}>
                  <span className="part-bar"><i style={{ width: `${Math.max(3, (1 - part) * 100)}%` }} /></span>
                  <span className={`part-word ${standing(part).toLowerCase()}`}>{standing(part)}</span>
                </td>
              );
            })}
          </tr>
        ))}
      </tbody>
    </table>
  );
}

/** Every number side by side: your rotation and the three suggestions. */
export function CompareView({ data, mine, picks, metrics, ctx, units, set, onMonths }: Props) {
  const cols: Col[] = [{ key: 'mine', label: 'Your rotation', r: mine, pick: false }, ...picks.map((r) => ({ key: r.id, label: pickLabel(r), r, pick: true }))];
  const groups = [...data.priorities.map((p) => ({ id: p.id, weight: p.weight as number | null })), { id: 'overall', weight: null }];
  const span = calendarSpan(cols.map((c) => c.r));
  return (
    <div className="compare">
      <section className="panel" aria-labelledby="cmp-h">
        <header className="panel-head"><h2 id="cmp-h">{CONTENT.compare.title}</h2></header>
        <div className="table-wrap">
          <table className="cmp-table" style={{ minWidth: 200 + cols.length * 170 }}>
            <thead>
              <tr>
                <th scope="col" className="corner">Rotation</th>
                {cols.map((c) => (
                  <th scope="col" key={c.key} className={c.pick ? '' : 'is-mine'}>
                    <b className="col-name">{cropsName(c.r)}</b>
                    <span className={`rot-tag${c.pick ? '' : ' mine'}`}>{c.label}</span>
                    <span className="col-note">{coverNote(c.r) || 'No cover crop'}</span>
                    <MonthStrip r={c.r} {...span} size="sm" />
                    <span className="col-actions">
                      {c.pick && <button type="button" className="btn primary sm" onClick={() => set((s) => ({ ...s, ...toBuilder(c.r), tab: 'plan' }))}>Use this rotation</button>}
                      <button type="button" className="btn ghost sm" onClick={() => onMonths(c.key)}>See month by month</button>
                    </span>
                  </th>
                ))}
              </tr>
            </thead>
            {groups.map(({ id, weight }) => {
              const ms = metrics.filter((m) => m.group === id);
              if (!ms.length) return null;
              return (
                <tbody key={id}>
                  <tr className="grp-head"><th colSpan={cols.length + 1} scope="rowgroup"><span>{priorityLabel(id)}</span>{weight != null && <span className="weight-chip">your weight {weight} of 5</span>}</th></tr>
                  {ms.map((m) => (
                    <tr key={m.key}>
                      <th scope="row">
                        <span className="row-label">{m.label}<Info label={m.label}><p>{m.info}</p><p className="tag-line">Kind of number: {TAG_LABELS[m.tag]}. {m.better === 'lower' ? 'Less is better.' : 'More is better.'}</p></Info></span>
                        <small>{m.unit(ctx)}</small>
                      </th>
                      {cols.map((c) => {
                        const k = c.r.kpi[m.key], base = mine.kpi[m.key];
                        return (
                          <td key={c.key} className={c.pick ? '' : 'is-mine'}>
                            {k ? <><span className="cell-num">{m.fmt(k.v, ctx)}</span>
                              {c.pick && base && <Delta m={m} v={k.v} base={base.v} ctx={ctx} against="yours" />}
                              {m.range?.(k, ctx) && <small className="cell-range">{m.range(k, ctx)}</small>}</> : '–'}
                          </td>
                        );
                      })}
                    </tr>
                  ))}
                </tbody>
              );
            })}
          </table>
        </div>
      </section>
      <div className="compare-cols">
        <section className="panel" aria-labelledby="trade-h">
          <header className="panel-head">
            <h2 id="trade-h">{CONTENT.compare.chart}</h2>
            <Info label={CONTENT.compare.chart}>Each dot is one rotation. The lines show the irrigation need in wet and dry years (10th to 90th percentile of 35 seasons). Dots in the shaded corner need less water and less fertilizer than your rotation.</Info>
          </header>
          <TradeOff cols={cols} units={units} />
        </section>
        <section className="panel" aria-labelledby="str-h">
          <header className="panel-head">
            <h2 id="str-h">{CONTENT.compare.strengths}</h2>
            <Info label={CONTENT.compare.strengths}>Where each rotation stands on each priority among all {data.nRotations ?? ''} rotations the scorer compared. A full bar is the best of all; Good, Fair and Poor are the top, middle and bottom third.</Info>
          </header>
          <Strengths cols={cols} data={data} />
        </section>
      </div>
    </div>
  );
}
