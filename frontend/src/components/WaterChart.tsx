import { cropColor, cropLabel } from '../config/crops';
import { fmtMm, type Units } from '../lib/units';
import type { Rotation } from '../types';

const MON = 'JFMAMJJASOND';
const nice = (v: number) => [100, 150, 200, 250, 300].find((s) => s >= v) ?? Math.ceil(v / 50) * 50;

/** Irrigation (bars) and rain (line) by month, with the crop on the field above. Values in mm, shown as in or mm. */
export function WaterChart({ r, units, pump }: { r: Rotation; units: Units; pump: number }) {
  const M = r.monthly ?? [];
  if (!M.length) return null;
  const N = M.length, w = 980, L = 44, R = 8, bw = (w - L - R) / N, bandY = 22, bandH = 16, top = 64, ch = 120, h = top + ch + 36;
  const max = nice(Math.max(...M.map((m) => Math.max(m.irr, m.rain))));
  const y = (v: number) => top + ch - (v / max) * ch;
  const first = Number(M[0].m.slice(0, 4));
  const segs: { i: number; j: number }[] = [];
  for (let i = 0; i < N; ) { const k = M[i].kind + (M[i].crop ?? ''); let j = i; while (j + 1 < N && M[j + 1].kind + (M[j + 1].crop ?? '') === k) j++; segs.push({ i, j }); i = j + 1; }
  const ticks = [0, max / 2, max];
  return (
    <figure className="chart">
      <figcaption>Irrigation and rain by month in a typical year. Bars: irrigation. Line: rain.</figcaption>
      <div className="scroll">
        <svg viewBox={`0 0 ${w} ${h}`} role="img" aria-label={`Monthly irrigation and rain for ${r.name}`}>
          {Array.from({ length: Math.ceil(N / 12) }, (_, k) => <text key={k} x={L + k * 12 * bw + 3} y={12} className="yr">{first + k}</text>)}
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
          {ticks.map((v) => <g key={v}><line x1={L} x2={w - R} y1={y(v)} y2={y(v)} className="grid" /><text x={L - 6} y={y(v) + 4} textAnchor="end">{units === 'in' ? `${Math.round(v / 25.4)}` : v}</text></g>)}
          {M.map((m, k) => {
            const x0 = L + k * bw;
            return (
              <g key={k}>
                {m.irr > 0 && <rect x={x0 + 2} y={y(m.irr)} width={bw - 4} height={y(0) - y(m.irr)} className="irr" />}
                <rect x={x0} y={top} width={bw} height={ch} fill="transparent" data-tip={`${m.m}: irrigation ${fmtMm(m.irr, units)}${m.irr ? ` (about $${Math.round((m.irr / 25.4) * pump)})` : ''}, rain ${fmtMm(m.rain, units)}`} />
                <text x={x0 + bw / 2} y={top + ch + 14} textAnchor="middle" className="mo">{MON[k % 12]}</text>
              </g>
            );
          })}
          <polyline points={M.map((m, k) => `${L + k * bw + bw / 2},${y(m.rain)}`).join(' ')} className="rain" />
        </svg>
      </div>
      <p className="unit">{units === 'in' ? 'inches' : 'millimetres'} per month</p>
    </figure>
  );
}
