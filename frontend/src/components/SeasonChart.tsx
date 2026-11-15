import { cropColor, cropLabel } from '../config/crops';
import { fmtWater, inToUnit, type Units } from '../lib/units';
import type { ApiExplorer, ApiMonth, Rotation } from '../types';

export type SeasonView = 'water' | 'n' | 'stress';
type Weather = NonNullable<ApiExplorer['weather_monthly']>;
const MONTH = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
/** Round the axis maximum up to a readable step without leaving half the plot empty. */
const nice = (v: number) => { const s = 10 ** Math.floor(Math.log10(Math.max(v, 1e-6))); return [1, 1.2, 1.5, 2, 2.5, 3, 4, 5, 6, 8, 10].map((k) => k * s).find((k) => k >= v) ?? 10 * s; };
const mlabel = (m: string) => `${MONTH[Number(m.slice(5, 7)) - 1]} ${m.slice(0, 4)}`;
const day = (iso: string) => new Date(`${iso}T00:00:00`).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
const landUse = (m: ApiMonth) => (m.kind === 'bare' ? 'Bare soil' : m.kind === 'cover' ? `${cropLabel(m.crop)} cover crop` : cropLabel(m.crop));
const days = (v: number) => `${v < 1 && v > 0 ? v.toFixed(1) : Math.round(v)} ${Math.round(v) === 1 ? 'day' : 'days'}`;

/**
 * One rotation month by month. On top the field band (crop, cover crop, hatched bare soil), then one of three views:
 * water (crop water use behind the irrigation that tops up the rain), fertilizer (the crop's nitrogen need behind the
 * fertilizer actually applied, per season at planting, as K-State gives it), or weather stress (the average temperature
 * course when the API sends it, then heat and cold stress days as a heatmap).
 */
export function SeasonChart({ r, units, view, weather }: { r: Rotation; units: Units; view: SeasonView; weather?: Weather }) {
  const M = r.monthly;
  if (!M.length) return <p className="empty">No monthly values for this rotation.</p>;
  const n = M.length, w = 1000, L = 104, R = 12, bw = (w - L - R) / n;
  const bandY = 36, bandH = 12, chT = 64;
  const month = (k: number) => Number(M[k].m.slice(5, 7));
  const runs: { i: number; j: number }[] = [];
  for (let i = 0; i < n; ) { const key = M[i].kind + (M[i].crop ?? ''); let j = i; while (j + 1 < n && M[j + 1].kind + (M[j + 1].crop ?? '') === key) j++; runs.push({ i, j }); i = j + 1; }

  // vertical layout per view
  const temps = view === 'stress' && weather?.length === 12 ? weather : null;
  const chH = view === 'stress' ? (temps ? 90 : 0) : 110;
  const rows: [string, (m: ApiMonth) => number, string][] = view === 'stress'
    ? [['Heat stress', (m) => m.heat_days ?? 0, 'heat'], ['Cold stress', (m) => m.cold_stress_days ?? 0, 'cold'],
      ...(M.some((m) => (m.kill_days ?? 0) > 0) ? [['Killing frost', (m: ApiMonth) => m.kill_days ?? 0, 'kill'] as [string, (m: ApiMonth) => number, string]] : [])]
    : [];
  const rowH = 24, heatY = chT + chH + (temps ? 30 : 0), monthY = view === 'stress' ? heatY + rows.length * (rowH + 4) + 14 : chT + chH + 18;
  const h = monthY + 10;

  // scales
  const planted = (m: string) => r.sequence.find((s) => s.plant_date.slice(0, 7) === m) ?? null;
  const need = (s: Rotation['sequence'][number]) => (s.n_lb ?? 0) - (s.n_adj_lb ?? 0); // K-State need before the previous-crop adjustment
  const ymax = view === 'water' ? nice(Math.max(...M.map((m) => inToUnit(Math.max(m.et_in, m.irr_in, m.rain_in), units))))
    : view === 'n' ? nice(Math.max(50, ...r.sequence.flatMap((s) => [s.n_lb ?? 0, need(s)])))
    : temps ? nice(Math.max(...temps.map((t) => t.tmax_f))) : 1;
  const tmin = temps ? Math.floor(Math.min(...temps.map((t) => t.tmin_f)) / 10) * 10 : 0;
  const y = (v: number) => chT + chH - ((Math.min(v, ymax) - (view === 'stress' ? tmin : 0)) / (ymax - (view === 'stress' ? tmin : 0))) * chH;
  const yw = (inches: number) => y(inToUnit(inches, units));
  const unit = view === 'water' ? units : view === 'n' ? 'lb' : '°F';
  // each row on its own scale, so a row with few days (cold) still shows where its days are
  const rowMax = rows.map(([, f]) => Math.max(1, ...M.map((m) => (m.kind === 'bare' ? 0 : f(m)))));

  return (
    <svg viewBox={`0 0 ${w} ${h}`} className="chart season-chart" role="img" aria-label={`Month by month: ${runs.map(({ i, j }) => `${landUse(M[i])} ${mlabel(M[i].m)} to ${mlabel(M[j].m)}`).join('; ')}`} style={{ minWidth: 760 }}>
      <defs>
        <pattern id="bare-hatch" width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
          <line x1="0" y1="0" x2="0" y2="6" className="hatch-line" />
        </pattern>
      </defs>
      {M.map((m, k) => (month(k) === 1 || k === 0) && (
        <g key={`y${k}`}><text x={L + k * bw + 4} y={16} className="year-label">{m.m.slice(0, 4)}</text>
          {k > 0 && <line x1={L + k * bw} x2={L + k * bw} y1={4} y2={h - 22} className="year-rule" />}</g>
      ))}
      <text x={L - 10} y={bandY + 10} textAnchor="end">Field</text>
      {runs.map(({ i, j }) => {
        const m = M[i], x0 = L + i * bw, wd = (j - i + 1) * bw;
        const label = m.kind === 'bare' ? '' : cropLabel(m.crop);
        return (
          <g key={i}>
            <rect x={x0 + 1} y={bandY} width={wd - 2} height={bandH} rx={3} className={`band ${m.kind}`} style={m.kind === 'bare' ? { fill: 'url(#bare-hatch)' } : { fill: cropColor(m.crop ?? '') }}
              data-tip={`${landUse(m)}, ${mlabel(m.m)} to ${mlabel(M[j].m)}`} />
            {label && wd > label.length * 8 + 12 && <text x={x0 + 2} y={bandY - 5} className="band-label">{label}{m.kind === 'cover' ? ' cover' : ''}</text>}
          </g>
        );
      })}

      {chH > 0 && (view === 'stress' && temps
        ? [ymax, tmin + (ymax - tmin) / 2, tmin].map((v) => <g key={v}><line className="grid" x1={L} x2={w - R} y1={y(v)} y2={y(v)} /><text x={L - 10} y={y(v) + 4} textAnchor="end">{Math.round(v)} {unit}</text></g>)
        : [0, ymax].map((v) => <g key={v}><line className="grid" x1={L} x2={w - R} y1={y(v)} y2={y(v)} /><text x={L - 10} y={y(v) + 4} textAnchor="end">{+v.toFixed(1)} {unit}</text></g>))}

      {view === 'water' && M.map((m, k) => {
        const x0 = L + k * bw;
        return (
          <g key={k}>
            {m.et_in > 0 && <rect x={x0 + 2} y={yw(m.et_in)} width={bw - 4} height={y(0) - yw(m.et_in)} rx={2} className="b-use" />}
            {m.irr_in > 0 && <rect x={x0 + bw / 2 - 3.5} y={yw(m.irr_in)} width={7} height={y(0) - yw(m.irr_in)} rx={2} className="b-irr" />}
            <rect x={x0} y={chT} width={bw} height={chH} fill="transparent" data-tip={`${mlabel(m.m)}: the crop uses ${fmtWater(m.et_in, units)}, rain ${fmtWater(m.rain_in, units)}, irrigation ${fmtWater(m.irr_in, units)}`} />
          </g>
        );
      })}
      {view === 'water' && <polyline points={M.map((m, k) => `${L + k * bw + bw / 2},${yw(m.rain_in)}`).join(' ')} className="l-rain" />}

      {view === 'n' && M.map((m, k) => {
        const x0 = L + k * bw, s = planted(m.m);
        const nd = s ? need(s) : 0, fert = s?.n_lb ?? 0;
        const tip = s ? `${mlabel(m.m)}: ${cropLabel(s.crop)} planted. It needs ${Math.round(nd)} lb N per acre; you apply ${Math.round(fert)} lb${s.n_adj_lb ? ` (${s.n_adj_lb < 0 ? 'credit' : 'extra'} ${Math.abs(Math.round(s.n_adj_lb))} lb from the crop before)` : ''}` : `${mlabel(m.m)}: no fertilizer`;
        return (
          <g key={k}>
            {nd > 0 && <rect x={x0 + 2} y={y(nd)} width={bw - 4} height={y(0) - y(nd)} rx={2} className="b-need" />}
            {fert > 0 && <rect x={x0 + bw / 2 - 3.5} y={y(fert)} width={7} height={y(0) - y(fert)} rx={2} className="b-n" />}
            <rect x={x0} y={chT} width={bw} height={chH} fill="transparent" data-tip={tip} />
          </g>
        );
      })}

      {temps && <>
        <polyline points={M.map((_, k) => `${L + k * bw + bw / 2},${y(temps[month(k) - 1].tmax_f)}`).join(' ')} className="l-tmax" />
        <polyline points={M.map((_, k) => `${L + k * bw + bw / 2},${y(temps[month(k) - 1].tmin_f)}`).join(' ')} className="l-tmin" />
        {M.map((_, k) => <rect key={k} x={L + k * bw} y={chT} width={bw} height={chH} fill="transparent"
          data-tip={`${MONTH[month(k) - 1]}: on average ${Math.round(temps[month(k) - 1].tmax_f)} °F by day, ${Math.round(temps[month(k) - 1].tmin_f)} °F at night (NASA POWER 1991–2025)`} />)}
      </>}

      {rows.map(([label, f, cls], ri) => (
        <g key={label}>
          <text x={L - 10} y={heatY + ri * (rowH + 4) + 16} textAnchor="end">{label}</text>
          {M.map((m, k) => {
            const v = m.kind === 'bare' ? 0 : f(m);
            const x0 = L + k * bw, y0 = heatY + ri * (rowH + 4);
            return (
              <g key={k}>
                <rect x={x0 + 1} y={y0} width={bw - 2} height={rowH} rx={3} className={v > 0 ? `cell ${cls}` : 'cell empty'}
                  style={v > 0 ? { fillOpacity: 0.2 + 0.8 * Math.min(1, v / rowMax[ri]) } : undefined}
                  data-tip={m.kind === 'bare' ? `${mlabel(m.m)}: bare soil, no crop at risk` : `${mlabel(m.m)}: ${label.toLowerCase()} on ${days(v)} in an average year`} />
                {v >= 0.5 && bw > 18 && <text x={x0 + bw / 2} y={y0 + 16} textAnchor="middle" className={v / rowMax[ri] > 0.55 ? 'cell-num on' : 'cell-num'}>{Math.round(v)}</text>}
              </g>
            );
          })}
        </g>
      ))}

      {M.map((_, k) => <text key={k} x={L + k * bw + bw / 2} y={monthY} textAnchor="middle" className="month-label">{MONTH[month(k) - 1][0]}</text>)}
      {chH > 0 && view !== 'stress' && <line className="axis" x1={L} x2={w - R} y1={y(0)} y2={y(0)} />}
    </svg>
  );
}

/** The seasons of one rotation as a table: dates, water, yield, nitrogen, notes. */
export function SeasonTable({ r, units }: { r: Rotation; units: Units }) {
  return (
    <div className="table-wrap">
      <table className="data-table">
        <thead><tr><th scope="col">Crop</th><th scope="col">Planted</th><th scope="col">Harvested</th><th scope="col">Irrigation</th><th scope="col">Yield</th><th scope="col">Nitrogen</th><th scope="col">Good to know</th></tr></thead>
        <tbody>
          {r.sequence.map((s, i) => (
            <tr key={i}>
              <th scope="row"><i className="dot" style={{ background: cropColor(s.crop) }} />{cropLabel(s.crop)}{s.cover && i < r.sequence.length - 1 && <small>then {cropLabel(s.cover).toLowerCase()} cover crop</small>}</th>
              <td>{day(s.plant_date)}</td>
              <td>{day(s.harvest_date)}</td>
              <td>{fmtWater(s.irr_in.v, units)}<small>{fmtWater(s.irr_in.p10, units)} to {fmtWater(s.irr_in.p90, units)}</small></td>
              <td>{Math.round(s.yield.v).toLocaleString('en-US')} {s.yield.unit} per acre</td>
              <td>{s.n_lb == null ? '–' : `${Math.round(s.n_lb)} lb`}{s.n_adj_lb ? <small>{s.n_adj_lb < 0 ? 'credit' : 'extra'} {Math.abs(Math.round(s.n_adj_lb))} lb from the crop before</small> : null}</td>
              <td>{s.effects.length ? <ul className="effects">{s.effects.map((e, k) => <li key={k}>{e.text}</li>)}</ul> : '–'}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
