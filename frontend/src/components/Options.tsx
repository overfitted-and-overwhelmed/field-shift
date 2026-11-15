import { CONTENT } from '../config/content';
import { HEADLINE, type MetricCtx, type MetricDef } from '../config/metrics';
import { compare } from '../data/metrics';
import type { Units } from '../lib/units';
import type { ExplorerData, Rotation } from '../types';
import { Strip } from './Strip';

interface Props { data: ExplorerData; metrics: MetricDef[]; mctx: MetricCtx; selectedId: string; onSelect: (id: string) => void; units: Units; onUnits: (u: Units) => void }

/** Today and the options as rows; three numbers each, change against today underneath. Choose a row to see its details. */
export function Options({ data, metrics, mctx, selectedId, onSelect, units, onUnits }: Props) {
  const cols = HEADLINE.map((k) => metrics.find((m) => m.key === k)).filter((m): m is MetricDef => !!m);
  const cur = data.current;
  const cells = (r: Rotation) => cols.map((m) => {
    const k = r.kpi[m.key], base = cur.kpi[m.key];
    if (!k) return <span className="cell" data-l={m.label} key={m.key}>–</span>;
    const diff = base ? +(k.v - base.v).toFixed(2) : 0;
    const verdict = base && !r.is_current ? compare(m, k.v, base.v) : 'same';
    return (
      <span className="cell" data-l={m.label} key={m.key}>
        <span className="v">{m.fmt(k.v, mctx)}</span>
        {!r.is_current && diff !== 0 && <span className={`d ${verdict}`}>{m.delta(Math.abs(diff), diff < 0 ? -1 : 1, mctx)}</span>}
      </span>
    );
  });
  const gridCols = { gridTemplateColumns: `minmax(0, 1.7fr) repeat(${cols.length}, minmax(0, 1fr))` };
  return (
    <section aria-labelledby="options-h">
      <div className="head-row">
        <h2 id="options-h">{CONTENT.optionsTitle}</h2>
        <div className="seg" role="group" aria-label="Units"><button aria-pressed={units === 'in'} onClick={() => onUnits('in')}>in</button><button aria-pressed={units === 'mm'} onClick={() => onUnits('mm')}>mm</button></div>
      </div>
      <div className="rows" role="radiogroup" aria-label="Rotation options">
        <div className="row heads" style={gridCols} aria-hidden="true"><span />{cols.map((m) => <span key={m.key}>{m.label}</span>)}</div>
        <div className="row today" style={gridCols}>
          <div className="who"><span className="tag">Today</span><strong>{cur.short}</strong><Strip r={cur} /></div>
          {cells(cur)}
        </div>
        {data.options.map((r) => (
          <label className={`row opt${r.id === selectedId ? ' on' : ''}`} style={gridCols} key={r.id}>
            <input type="radio" name="option" value={r.id} checked={r.id === selectedId} onChange={() => onSelect(r.id)} />
            <div className="who"><span className="tag">{r.pick === 1 ? 'Best match' : `Option ${r.pick}`}</span><strong>{r.name}</strong><Strip r={r} /></div>
            {cells(r)}
          </label>
        ))}
      </div>
      <p className="note">{CONTENT.optionsNote}</p>
    </section>
  );
}
