import { cropColor, cropLabel } from '../config/crops';
import { fmtWater, inToUnit, type Units } from '../lib/units';
import type { Rotation } from '../types';

const MON = 'JFMAMJJASOND';
/** Round the axis maximum up to a readable step. */
const nice = (v: number) => { const step = 10 ** Math.floor(Math.log10(Math.max(v, 1e-6))); return [1, 2, 2.5, 5, 10].map((s) => s * step).find((s) => s >= v) ?? 10 * step; };
const pct = (v: number) => `${Math.round(v)} %`;

/**
 * Irrigation (bars) and rain (line) by month over the rotation's window, with the crop on the field above.
 * The window starts with the first sowing, so the first month is not always January. Values arrive in inches.
 */
export function WaterChart({ r, units }: { r: Rotation; units: Units }) {
  const M = r.monthly;
  if (!M.length) return null;
  const N = M.length, w = 980, L = 44, R = 8, bw = (w - L - R) / N, bandY = 22, bandH = 16, top = 64, ch = 120, h = top + ch + 36;
  const max = nice(Math.max(...M.map((m) => inToUnit(Math.max(m.irr_in, m.rain_in), units))));
  const y = (inches: number) => top + ch - (inToUnit(inches, units) / max) * ch;
  const month = (k: number) => Number(M[k].m.slice(5, 7));
  const segs: { i: number; j: number }[] = [];
  for (let i = 0; i < N; ) { const k = M[i].kind + (M[i].crop ?? ''); let j = i; while (j + 1 < N && M[j + 1].kind + (M[j + 1].crop ?? '') === k) j++; segs.push({ i, j }); i = j + 1; }
  const ticks = [0, max / 2, max];
  const yearStarts = M.map((m, k) => ({ k, year: m.m.slice(0, 4) })).filter(({ k }) => k === 0 || month(k) === 1);
  return (
    <figure className="chart">
      <figcaption>Irrigation and rain by month, from the first sowing to the last harvest, mean over the weather years. Bars: irrigation. Line: rain.</figcaption>
      <div className="scroll">
        <svg viewBox={`0 0 ${w} ${h}`} role="img" aria-label={`Monthly irrigation and rain for ${r.name}`}>
          {yearStarts.map(({ k, year }) => <text key={k} x={L + k * bw + 3} y={12} className="yr">{year}</text>)}
          {segs.map(({ i, j }) => {
            const m = M[i], x0 = L + i * bw, wd = (j - i + 1) * bw;
            const nm = m.kind === 'bare' ? 'bare' : m.kind === 'cover' ? 'cover' : cropLabel(m.crop);
            return (
              <g key={i}>
                <rect x={x0 + 1} y={bandY} width={wd - 2} height={bandH} rx={2} fill={m.kind === 'bare' ? 'var(--hatch)' : cropColor(m.crop ?? '')} opacity={m.kind === 'cover' ? 0.7 : 1} data-tip={`${M[i].m} to ${M[j].m}: ${m.kind === 'bare' ? 'bare soil' : m.kind === 'cover' ? `${cropLabel(m.crop).toLowerCase()} cover crop` : cropLabel(m.crop)}`} />
                {wd > 34 && <text x={x0 + wd / 2} y={bandY + 12} textAnchor="middle" className={m.kind === 'bare' ? 'dim' : 'on'}>{nm}</text>}
              </g>
            );
          })}
          {ticks.map((v) => <g key={v}><line x1={L} x2={w - R} y1={top + ch - (v / max) * ch} y2={top + ch - (v / max) * ch} className="grid" /><text x={L - 6} y={top + ch - (v / max) * ch + 4} textAnchor="end">{+v.toFixed(1)}</text></g>)}
          {M.map((m, k) => {
            const x0 = L + k * bw;
            const risk = m.kind === 'bare' ? '' : `; heat stress in ${pct(m.heat_years_pct)}, killing frost in ${pct(m.kill_years_pct)} of years`;
            return (
              <g key={k}>
                {m.irr_in > 0 && <rect x={x0 + 2} y={y(m.irr_in)} width={bw - 4} height={y(0) - y(m.irr_in)} className="irr" />}
                <rect x={x0} y={top} width={bw} height={ch} fill="transparent" data-tip={`${m.m}: irrigation ${fmtWater(m.irr_in, units)}, rain ${fmtWater(m.rain_in, units)}, crop water use ${fmtWater(m.et_in, units)}${risk}`} />
                <text x={x0 + bw / 2} y={top + ch + 14} textAnchor="middle" className="mo">{MON[month(k) - 1]}</text>
              </g>
            );
          })}
          <polyline points={M.map((m, k) => `${L + k * bw + bw / 2},${y(m.rain_in)}`).join(' ')} className="rain" />
        </svg>
      </div>
      <p className="unit">{units === 'in' ? 'inches' : 'millimetres'} per month</p>
    </figure>
  );
}
