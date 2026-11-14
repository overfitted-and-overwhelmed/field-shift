import { CONTENT } from '../config/content';
import { TAG_LABELS, type MetricCtx, type MetricDef } from '../config/metrics';
import { priorityLabel } from '../config/priorities';
import type { Units } from '../lib/units';
import type { ExplorerData, Rotation } from '../types';
import { WaterChart } from './WaterChart';

const List = ({ items }: { items: string[] }) => <ul>{items.map((x, i) => <li key={i}>{x}</li>)}</ul>;

export function Detail({ data, r, metrics, mctx, units }: { data: ExplorerData; r: Rotation; metrics: MetricDef[]; mctx: MetricCtx; units: Units }) {
  const t = data.explanations?.[r.id];
  return (
    <section aria-labelledby="detail-h" className="detail">
      <h2 id="detail-h">{r.name}</h2>
      <div className="cols">
        <div>{t ? t.why.map((p, i) => <p className="why" key={i}>{p}</p>) : <p className="note">No explanation for this option yet.</p>}</div>
        {t && (
          <div>
            <h3 className="first">{CONTENT.checkTitle}</h3>
            <List items={t.risks.slice(0, 3)} />
            <p className="note">{CONTENT.checkNote}</p>
          </div>
        )}
      </div>
      <WaterChart r={r} units={units} pump={data.prices.pump} />

      {t && (
        <details>
          <summary>More reasoning</summary>
          <div className="cols3">
            <div><h3>Evidence</h3><List items={t.evidence} /></div>
            <div><h3>Benefits</h3><List items={t.benefits} /></div>
            <div><h3>What we do not know</h3><List items={t.gaps} /></div>
            <div><h3>Questions for your advisor</h3><List items={t.ask} /></div>
          </div>
        </details>
      )}

      <details>
        <summary>All numbers</summary>
        <div className="scroll">
          <table className="all">
            <thead><tr><th /><th>Today</th><th>{r.name}</th></tr></thead>
            <tbody>
              {data.priorities.map(({ id }) => {
                const rows = metrics.filter((m) => m.group === id);
                return rows.length ? [
                  <tr className="grp" key={`g${id}`}><th colSpan={3}>{priorityLabel(id)}</th></tr>,
                  ...rows.map((m) => (
                    <tr key={m.key}>
                      <th scope="row">{m.label}<small>{m.sub(mctx)} · {TAG_LABELS[m.tag].toLowerCase()}</small></th>
                      <td>{data.current.kpi[m.key] ? m.fmt(data.current.kpi[m.key].v, mctx) : '–'}</td>
                      <td>{r.kpi[m.key] ? <>{m.fmt(r.kpi[m.key].v, mctx)}{m.range && r.kpi[m.key] ? <small className="rng">{m.range(r.kpi[m.key], mctx)}</small> : null}</> : '–'}</td>
                    </tr>
                  )),
                ] : null;
              })}
            </tbody>
          </table>
        </div>
      </details>
    </section>
  );
}
