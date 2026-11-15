import { useState } from 'react';
import { CONTENT } from '../config/content';
import type { MetricCtx, MetricDef } from '../config/metrics';
import { priorityLabel } from '../config/priorities';
import { compare } from '../data/metrics';
import { inToUnit, type Units } from '../lib/units';
import type { ExplorerData, Rotation } from '../types';
import { pickLabel, vsCurrent } from './helpers';
import { Badge, SecHead, Seq } from './ui';

interface Props {
  data: ExplorerData; metrics: MetricDef[]; mctx: MetricCtx; edited: boolean;
  units: Units; onUnits: (u: Units) => void; onView: (id: string) => void;
}

function Verdict({ r, data, metrics, edited }: { r: Rotation; data: ExplorerData; metrics: MetricDef[]; edited: boolean }) {
  if (r.is_current) return <span className="verdict base">{edited ? 'Built by you' : 'From your crop history'}{r.score != null && ` · score ${r.score.toFixed(2)}`}</span>;
  const vc = vsCurrent(r, data.current, metrics);
  const worse = vc.filter((x) => x.verdict === 'worse').map((x) => x.m.short), better = vc.filter((x) => x.verdict === 'better').length;
  if (!worse.length) return <span className="verdict good">Beats yours on every measure</span>;
  return <span className="verdict mixed">Better on {better} of {vc.length}; worse on {worse.join(', ')}</span>;
}

function Table({ data, metrics, mctx, edited, onView }: Omit<Props, 'units' | 'onUnits'>) {
  const rows = [data.current, ...data.options];
  const groups = [...data.priorities.map((p) => ({ id: p.id, weight: p.weight as number | null })), { id: 'overall', weight: null }];
  return (
    <table className="cmp" style={{ minWidth: 260 + rows.length * 200 }}>
      <colgroup><col className="labelcol" />{rows.map((r) => <col key={r.id} className={r.is_current ? 'cur' : ''} />)}</colgroup>
      <thead>
        <tr>
          <th><span className="eyebrow">Rotation from {data.field.rotation_start_year}</span></th>
          {rows.map((r) => (
            <th scope="col" key={r.id}>
              <div className="colhead">
                <span className={`pick${r.pick === 1 ? ' top' : ''}`}>{pickLabel(r)}</span>
                <h3>{r.name}</h3>
                <Seq r={r} />
                <Verdict r={r} data={data} metrics={metrics} edited={edited} />
                <button type="button" className="btn viewbtn" onClick={() => onView(r.id)}>View season</button>
              </div>
            </th>
          ))}
        </tr>
      </thead>
      <tbody>
        {groups.map(({ id, weight }) => {
          const ms = metrics.filter((m) => m.group === id);
          if (!ms.length) return null;
          return [
            <tr className="grp" key={`g-${id}`}><th colSpan={rows.length + 1} scope="rowgroup">{priorityLabel(id)}{weight != null && <span>your weight {weight}/5</span>}</th></tr>,
            ...ms.map((m) => {
              const base = data.current.kpi[m.key];
              return (
                <tr key={m.key}>
                  <th scope="row"><div className="rlabel">{m.label}<small>{m.sub(mctx)}</small><Badge tag={m.tag} /></div></th>
                  {rows.map((r) => {
                    const k = r.kpi[m.key];
                    if (!k) return <td key={r.id}>–</td>;
                    const diff = base ? +(k.v - base.v).toFixed(2) : 0;
                    const v = base && !r.is_current ? compare(m, k.v, base.v) : 'same';
                    const cls = v === 'better' ? 'good' : v === 'worse' ? 'bad' : 'same';
                    const rng = m.range?.(k, mctx);
                    return (
                      <td key={r.id}>
                        <div className="cval">{m.fmt(k.v, mctx)}</div>
                        {rng && <div className="rng">{rng}</div>}
                        {!r.is_current && base && (
                          <div><span className={`delta ${cls}`} aria-label={cls === 'good' ? 'better than yours' : cls === 'bad' ? 'worse than yours' : 'same as yours'}>
                            <span aria-hidden="true">{cls === 'good' ? '▲' : cls === 'bad' ? '▼' : '='}</span>{diff === 0 ? 'same' : m.delta(Math.abs(diff), diff < 0 ? -1 : 1, mctx)}
                          </span></div>
                        )}
                      </td>
                    );
                  })}
                </tr>
              );
            }),
          ];
        })}
      </tbody>
    </table>
  );
}

/** Irrigation (x) against nitrogen (y), both per year: down and to the left is better. Whiskers: irrigation P10–P90. */
function Scatter({ data, units }: { data: ExplorerData; units: Units }) {
  const rows = [data.current, ...data.options].filter((r) => r.kpi.irrigation_in && r.kpi.n_lb);
  if (rows.length < 2) return <p className="small muted">Nitrogen is missing for some rotations.</p>;
  const w = 480, h = 300, L = 54, R = 16, T = 14, B = 40, iw = w - L - R, ih = h - T - B;
  const U = (v: number) => inToUnit(v, units);
  const xmax = Math.max(...rows.map((r) => U(r.kpi.irrigation_in.hi ?? r.kpi.irrigation_in.v))) * 1.08;
  const ymax = Math.max(50, Math.max(...rows.map((r) => r.kpi.n_lb.v)) * 1.15);
  const x = (v: number) => L + (U(v) / xmax) * iw, y = (v: number) => T + ih - (v / ymax) * ih;
  const step = (m: number) => { const s = 10 ** Math.floor(Math.log10(m / 4)); return [1, 2, 5, 10].map((k) => k * s).find((k) => m / k <= 6) ?? s * 10; };
  const xs = step(xmax), ys = step(ymax);
  const c = data.current;
  return (
    <svg viewBox={`0 0 ${w} ${h}`} role="img" aria-label="Irrigation need against nitrogen fertilizer per year">
      <rect x={L} y={y(c.kpi.n_lb.v)} width={Math.max(0, x(c.kpi.irrigation_in.v) - L)} height={Math.max(0, T + ih - y(c.kpi.n_lb.v))} style={{ fill: 'var(--good-bg)' }} />
      <text x={L + 6} y={T + ih - 8} style={{ fill: 'var(--good)', fontWeight: 600 }}>better than yours on both</text>
      {Array.from({ length: Math.floor(xmax / xs) + 1 }, (_, i) => i * xs).map((v) => <g key={`x${v}`}><line className="grid" x1={L + (v / xmax) * iw} x2={L + (v / xmax) * iw} y1={T} y2={T + ih} /><text x={L + (v / xmax) * iw} y={T + ih + 14} textAnchor="middle">{v}</text></g>)}
      {Array.from({ length: Math.floor(ymax / ys) + 1 }, (_, i) => i * ys).map((v) => <g key={`y${v}`}><line className="grid" x1={L} x2={w - R} y1={y(v)} y2={y(v)} /><text x={L - 6} y={y(v) + 4} textAnchor="end">{v}</text></g>)}
      <line className="ax" x1={L} x2={w - R} y1={T + ih} y2={T + ih} /><line className="ax" x1={L} x2={L} y1={T} y2={T + ih} />
      <text x={L + iw / 2} y={h - 4} textAnchor="middle">Irrigation need per year ({units}) · less is better</text>
      <text x={12} y={T + ih / 2} textAnchor="middle" transform={`rotate(-90 12 ${T + ih / 2})`}>Nitrogen, lb N per acre and year</text>
      {rows.map((r, i) => {
        const k = r.kpi.irrigation_in, cx = x(k.v), cy = y(r.kpi.n_lb.v), col = r.is_current ? 'var(--ink)' : 'var(--accent)';
        // labels of points close to an earlier one go below the point instead of above
        const crowded = rows.slice(0, i).some((o) => Math.abs(x(o.kpi.irrigation_in.v) - cx) < 40 && Math.abs(y(o.kpi.n_lb.v) - cy) < 16);
        return (
          <g key={r.id} data-tip={`${pickLabel(r)}: ${r.name}`}>
            {k.lo != null && k.hi != null && <line x1={x(k.lo)} x2={x(k.hi)} y1={cy} y2={cy} style={{ stroke: col, strokeWidth: 1.5, opacity: 0.5 }} />}
            <circle cx={cx} cy={cy} r={r.is_current ? 7 : 6} style={{ fill: r.is_current ? 'var(--surface)' : col, stroke: col, strokeWidth: 2 }} />
            <text x={cx + 10} y={crowded ? cy + 16 : cy - 8} className="lab">{r.is_current ? 'Yours' : `#${r.pick}`}</text>
          </g>
        );
      })}
    </svg>
  );
}

/** Step 3: the comparison table and the water/nitrogen trade-off. */
export function Compare(p: Props) {
  const [ranges, setRanges] = useState(true);
  const { data, metrics, units, onUnits } = p;
  const vcs = data.options.map((r) => ({ r, worse: vsCurrent(r, data.current, metrics).filter((x) => x.verdict === 'worse') }));
  const dominant = vcs.filter((x) => !x.worse.length);
  return (
    <section id="compare" aria-labelledby="compare-h">
      <SecHead id="compare-h" {...CONTENT.compare} />
      <div className="toolbar">
        <div className="seg" role="group" aria-label="Units">
          <button type="button" aria-pressed={units === 'in'} onClick={() => onUnits('in')}>inches</button>
          <button type="button" aria-pressed={units === 'mm'} onClick={() => onUnits('mm')}>mm</button>
        </div>
        <label className="small"><input type="checkbox" checked={ranges} onChange={(e) => setRanges(e.target.checked)} /> Show ranges across the weather years (10th–90th percentile)</label>
        <span className="small muted">Tags: <Badge tag="measured" /> <Badge tag="modeled" /> <Badge tag="rule" /> <Badge tag="assumption" /></span>
      </div>
      <div className={`tablewrap${ranges ? '' : ' hide-ranges'}`}><Table {...p} /></div>
      <p className="note">
        {dominant.length
          ? <b>{dominant.map((x) => `#${x.r.pick}`).join(', ')} beat{dominant.length === 1 ? 's' : ''} your rotation on every measure.</b>
          : <><b>No pick beats your rotation on everything.</b> {vcs.map((x) => `#${x.r.pick} is worse on ${x.worse.map((w) => w.m.short).join(' and ')}`).join('; ')}.</>}
      </p>
      <div className="trade single">
        <div className="card">
          <h3>Water against nitrogen</h3>
          <p className="small muted">Down and to the left is better on both. Whiskers show the irrigation need in wet (P10) and dry (P90) years.</p>
          <Scatter data={data} units={units} />
        </div>
      </div>
    </section>
  );
}
