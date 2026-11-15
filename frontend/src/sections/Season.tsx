import { useState } from 'react';
import { CONTENT } from '../config/content';
import { cropColor, cropLabel } from '../config/crops';
import { inToUnit, type Units } from '../lib/units';
import type { ApiMonth, ExplorerData, Rotation } from '../types';
import { pickLabel } from './helpers';
import { SecHead } from './ui';

const MON = 'JFMAMJJASOND';
const FULL_STRESS_DAYS = 20; // risk cells are fully colored from this many stress days per month
const nice = (v: number) => { const s = 10 ** Math.floor(Math.log10(Math.max(v, 1e-6))); return [1, 2, 2.5, 5, 10].map((k) => k * s).find((k) => k >= v) ?? 10 * s; };
const day = (iso: string) => new Date(`${iso}T00:00:00`).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });

/** Index of the season planted in month "YYYY-MM", if any. */
const plantedIn = (r: Rotation, m: string) => r.sequence.findIndex((s) => s.plant_date.slice(0, 7) === m);

/**
 * Monthly timeline over the rotation's window: field band (crop, cover, bare), then water (crop use, irrigation, rain)
 * or nitrogen (fertilizer per season at planting), then heat and cold-stress risk rows.
 */
function Timeline({ r, units, metric }: { r: Rotation; units: Units; metric: 'water' | 'n' }) {
  const M = r.monthly;
  if (!M.length) return <p className="small muted">No monthly values for this rotation.</p>;
  const NV = metric === 'n';
  const n = M.length, w = Math.max(980, 70 + n * 26), L = 70, R = 10, bw = (w - L - R) / n;
  const bandY = 40, bandH = 26, chT = 92, chH = 150, riskY = chT + chH + 34, h = riskY + 46;
  const val = (m: ApiMonth) => inToUnit(Math.max(m.et_in, m.irr_in, m.rain_in), units);
  const nMax = Math.max(...r.sequence.map((s) => s.n_lb ?? 0));
  const ymax = NV ? nice(Math.max(50, nMax)) : nice(Math.max(...M.map(val)));
  const y = (v: number) => chT + chH - (v / ymax) * chH;
  const yw = (inches: number) => y(inToUnit(inches, units));
  const month = (k: number) => Number(M[k].m.slice(5, 7));
  const segs: { i: number; j: number }[] = [];
  for (let i = 0; i < n; ) { const key = M[i].kind + (M[i].crop ?? ''); let j = i; while (j + 1 < n && M[j + 1].kind + (M[j + 1].crop ?? '') === key) j++; segs.push({ i, j }); i = j + 1; }
  const years = M.map((m, k) => ({ k, year: m.m.slice(0, 4) })).filter(({ k }) => k === 0 || month(k) === 1);
  const unit = NV ? 'lb' : units;
  const risks: [string, keyof ApiMonth, string][] = [['Heat', 'heat_days', 'var(--heat)'], ['Cold stress', 'cold_stress_days', 'var(--frost)']];
  return (
    <svg viewBox={`0 0 ${w} ${h}`} role="img" aria-label={`Monthly view of ${r.name}`} style={{ minWidth: Math.min(w, 1400) }}>
      <defs>
        <pattern id="hatch" width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><rect width="6" height="6" style={{ fill: 'var(--surface-2)' }} /><line x1="0" y1="0" x2="0" y2="6" style={{ stroke: 'var(--ink-3)', strokeWidth: 1 }} /></pattern>
      </defs>
      {years.map(({ k, year }) => (
        <g key={k}>
          <text className="lab" x={L + k * bw + 4} y={14}>{year}</text>
          {k > 0 && <line x1={L + k * bw} x2={L + k * bw} y1={4} y2={h - 4} style={{ stroke: 'var(--ink-3)', strokeDasharray: '2 3' }} />}
        </g>
      ))}
      {segs.map(({ i, j }) => {
        const m = M[i], x0 = L + i * bw, wd = (j - i + 1) * bw;
        const name = m.kind === 'bare' ? 'bare' : m.kind === 'cover' ? 'cover' : cropLabel(m.crop);
        return (
          <g key={i}>
            <rect x={x0 + 1} y={bandY} width={wd - 2} height={bandH} rx={3} style={{ fill: m.kind === 'bare' ? 'url(#hatch)' : cropColor(m.crop ?? ''), opacity: m.kind === 'cover' ? 0.7 : 1 }}
              data-tip={`${M[i].m} to ${M[j].m}: ${m.kind === 'bare' ? 'bare soil' : m.kind === 'cover' ? `${cropLabel(m.crop).toLowerCase()} cover crop` : cropLabel(m.crop)}`} />
            {wd > 34 && <text x={x0 + wd / 2} y={bandY - 6} textAnchor="middle" className={m.kind === 'bare' ? '' : 'lab'}>{name}</text>}
          </g>
        );
      })}
      <text x={L - 8} y={bandY + 17} textAnchor="end">Field</text>
      {[0, ymax / 2, ymax].map((v) => <g key={v}><line className="grid" x1={L} x2={w - R} y1={y(v)} y2={y(v)} /><text x={L - 8} y={y(v) + 4} textAnchor="end">{+v.toFixed(1)} {unit}</text></g>)}
      {M.map((m, k) => {
        const x0 = L + k * bw;
        if (NV) {
          const si = plantedIn(r, m.m), s = si >= 0 ? r.sequence[si] : null;
          return (
            <g key={k}>
              {s && s.n_lb != null && s.n_lb > 0 && <rect x={x0 + 2} y={y(s.n_lb)} width={bw - 4} height={y(0) - y(s.n_lb)} rx={2} style={{ fill: 'var(--accent)' }} />}
              <rect x={x0} y={chT} width={bw} height={chH} fill="transparent"
                data-tip={s ? `${m.m}: ${cropLabel(s.crop)} planted · fertilizer ${s.n_lb == null ? 'not computed' : `${Math.round(s.n_lb)} lb N/ac`}${s.n_adj_lb ? ` (previous-crop adjustment ${s.n_adj_lb > 0 ? '+' : ''}${Math.round(s.n_adj_lb)} lb)` : ''}` : `${m.m}: no planting`} />
              <text x={x0 + bw / 2} y={chT + chH + 14} textAnchor="middle" style={{ fontSize: 10 }}>{MON[month(k) - 1]}</text>
            </g>
          );
        }
        return (
          <g key={k}>
            {m.et_in > 0 && <rect x={x0 + 1.5} y={yw(m.et_in)} width={bw - 3} height={y(0) - yw(m.et_in)} rx={2} style={{ fill: 'var(--ink-3)', opacity: 0.4 }} />}
            {m.irr_in > 0 && <rect x={x0 + bw / 2 - 3} y={yw(m.irr_in)} width={6} height={y(0) - yw(m.irr_in)} rx={2} style={{ fill: 'var(--accent)' }} />}
            <rect x={x0} y={chT} width={bw} height={chH} fill="transparent"
              data-tip={`${m.m}: crop water use ${inToUnit(m.et_in, units).toFixed(units === 'in' ? 1 : 0)} ${units}, rain ${inToUnit(m.rain_in, units).toFixed(units === 'in' ? 1 : 0)} ${units}, irrigation ${inToUnit(m.irr_in, units).toFixed(units === 'in' ? 1 : 0)} ${units}`} />
            <text x={x0 + bw / 2} y={chT + chH + 14} textAnchor="middle" style={{ fontSize: 10 }}>{MON[month(k) - 1]}</text>
          </g>
        );
      })}
      {!NV && <polyline points={M.map((m, k) => `${L + k * bw + bw / 2},${yw(m.rain_in)}`).join(' ')} style={{ fill: 'none', stroke: 'var(--rain)', strokeWidth: 2, strokeDasharray: '5 3', pointerEvents: 'none' }} />}
      <line className="ax" x1={L} x2={w - R} y1={y(0)} y2={y(0)} />
      {risks.map(([nm, key, col], ri) => (
        <g key={nm}>
          <text x={L - 8} y={riskY + ri * 20 + 12} textAnchor="end">{nm}</text>
          {M.map((m, k) => {
            const p = m.kind === 'bare' ? 0 : (m[key] as number);
            return <rect key={k} x={L + k * bw + 1} y={riskY + ri * 20} width={bw - 2} height={16} rx={2}
              style={{ fill: p ? col : 'var(--surface-2)', opacity: p ? 0.2 + 0.8 * Math.min(p / FULL_STRESS_DAYS, 1) : 1 }}
              data-tip={m.kind === 'bare' ? `${m.m}: bare soil, no crop at risk` : `${m.m}: ${nm.toLowerCase()} on ${p.toFixed(1)} days on average`} />;
          })}
        </g>
      ))}
    </svg>
  );
}

/** Per season: what it inherits from the season before (rotation effects, N credit). */
function Effects({ r }: { r: Rotation }) {
  return (
    <div className="effects">
      {r.sequence.map((s, i) => (
        <div className="eff" key={i} style={{ borderLeftColor: cropColor(s.crop) }}>
          <b>{s.year} · {cropLabel(s.crop)}</b>
          <span className="small muted">{day(s.plant_date)} – {day(s.harvest_date)}</span>
          <ul>
            <li>Yield {Math.round(s.yield.v).toLocaleString('en-US')} {s.yield.unit}/ac{s.yield_pct_rotation ? ` (${s.yield_pct_rotation > 0 ? '+' : ''}${s.yield_pct_rotation} % against the crop’s reference yield)` : ''}</li>
            {s.n_lb != null && <li>Nitrogen {Math.round(s.n_lb)} lb N/ac{s.n_adj_lb ? `, ${s.n_adj_lb < 0 ? 'credit' : 'extra'} ${Math.abs(Math.round(s.n_adj_lb))} lb from the crop before` : ''}</li>}
            {s.effects.map((e, k) => <li key={k}>{e.text}</li>)}
            {s.cover && i < r.sequence.length - 1 && <li>Then a {cropLabel(s.cover).toLowerCase()} cover crop until the next sowing</li>}
          </ul>
        </div>
      ))}
    </div>
  );
}

/** Step 4: one rotation month by month. The tabs choose the rotation; the table's "View season" buttons do too. */
export function Season({ data, selected, onSelect, units }: { data: ExplorerData; selected: Rotation; onSelect: (id: string) => void; units: Units }) {
  const [metric, setMetric] = useState<'water' | 'n'>('water');
  const rows = [data.current, ...data.options];
  const crops = [...new Set(selected.sequence.map((s) => s.crop))];
  return (
    <section id="season" aria-labelledby="season-h">
      <SecHead id="season-h" {...CONTENT.season} />
      <div className="toolbar">
        <div className="tabs" role="tablist" aria-label="Rotation">
          {rows.map((r) => (
            <button key={r.id} type="button" role="tab" aria-selected={r.id === selected.id} onClick={() => onSelect(r.id)}>
              {pickLabel(r)}<small>{r.name}</small>
            </button>
          ))}
        </div>
        <div className="seg" role="group" aria-label="Show in season view">
          <button type="button" aria-pressed={metric === 'water'} onClick={() => setMetric('water')}>Water</button>
          <button type="button" aria-pressed={metric === 'n'} onClick={() => setMetric('n')}>Nitrogen</button>
        </div>
      </div>
      <div className="card">
        <div className="scroll"><Timeline r={selected} units={units} metric={metric} /></div>
        <div className="legend">
          {crops.map((c) => <span key={c}><i style={{ background: cropColor(c) }} />{cropLabel(c)}</span>)}
          {selected.sequence.some((s) => s.cover) && <span><i style={{ background: cropColor('triticale'), opacity: 0.7 }} />triticale cover</span>}
          <span><i className="hatch" />bare</span>
          {metric === 'water'
            ? <><span><i style={{ background: 'var(--ink-3)', opacity: 0.4 }} />crop water use</span><span><i style={{ background: 'var(--accent)' }} />irrigation</span><span><i style={{ background: 'none', borderTop: '2px dashed var(--rain)', height: 0 }} />rain</span></>
            : <span><i style={{ background: 'var(--accent)' }} />N fertilizer for the season, at planting</span>}
          <span className="muted">Risk rows: average stress days per month</span>
        </div>
      </div>
      <div>
        <h3 className="effects-h">How each season affects the next</h3>
        <Effects r={selected} />
      </div>
    </section>
  );
}
