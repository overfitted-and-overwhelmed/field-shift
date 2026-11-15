import { cropColor, cropLabel } from '../config/crops';
import type { ApiMonth, Rotation } from '../types';

const MONTH = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
const label = (m: ApiMonth) => `${MONTH[Number(m.m.slice(5, 7)) - 1]} ${m.m.slice(0, 4)}`;

/** Months of a rotation grouped into runs of the same use (crop, cover or bare), for one block per run. */
function runs(M: ApiMonth[]) {
  const out: { i: number; j: number }[] = [];
  for (let i = 0; i < M.length; ) {
    const key = M[i].kind + (M[i].crop ?? '');
    let j = i;
    while (j + 1 < M.length && M[j + 1].kind + (M[j + 1].crop ?? '') === key) j++;
    out.push({ i, j }); i = j + 1;
  }
  return out;
}

/**
 * What stands on the field each month, as one strip: a block per crop, cover crop or bare spell.
 * `start`/`months` place it on a shared calendar so several strips line up; `names` writes crop names into wide blocks.
 */
export function MonthStrip({ r, start, months, names = false, size = 'md' }: { r: Rotation; start?: string; months?: number; names?: boolean; size?: 'sm' | 'md' }) {
  const M = r.monthly;
  if (!M.length) return null;
  const first = start ?? M[0].m;
  const offset = (Number(M[0].m.slice(0, 4)) - Number(first.slice(0, 4))) * 12 + Number(M[0].m.slice(5, 7)) - Number(first.slice(5, 7));
  const total = months ?? offset + M.length;
  return (
    <div className={`mstrip ${size}`} style={{ gridTemplateColumns: `repeat(${total}, minmax(0, 1fr))` }}
      role="img" aria-label={`On the field from ${label(M[0])} to ${label(M[M.length - 1])}: ${runs(M).map(({ i, j }) => `${M[i].kind === 'bare' ? 'bare' : M[i].kind === 'cover' ? 'cover crop' : cropLabel(M[i].crop)} ${label(M[i])} to ${label(M[j])}`).join('; ')}`}>
      {runs(M).map(({ i, j }) => {
        const m = M[i];
        const what = m.kind === 'bare' ? 'Bare soil' : m.kind === 'cover' ? `${cropLabel(m.crop)} cover crop` : cropLabel(m.crop);
        return (
          <span key={i} className={`run ${m.kind}`} style={{ gridColumn: `${offset + i + 1} / span ${j - i + 1}`, ...(m.kind === 'bare' ? {} : { background: cropColor(m.crop ?? '') }) }}
            data-tip={`${what}, ${label(m)} to ${label(M[j])}`}>
            {names && m.kind !== 'bare' && j - i >= 2 && <span className="run-name">{cropLabel(m.crop)}</span>}
          </span>
        );
      })}
    </div>
  );
}
