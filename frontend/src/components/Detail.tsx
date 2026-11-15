import { CONTENT } from '../config/content';
import { cropColor, cropLabel } from '../config/crops';
import { TAG_LABELS, type MetricCtx, type MetricDef } from '../config/metrics';
import { priorityLabel } from '../config/priorities';
import { fmtWater, fmtWaterNum, type Units } from '../lib/units';
import type { ApiSeason, ExplorerData, Rotation } from '../types';
import { WaterChart } from './WaterChart';

const day = (iso: string) => new Date(`${iso}T00:00:00`).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
const yieldText = (s: ApiSeason) => `${Math.round(s.yield.v).toLocaleString('en-US')} ${s.yield.unit}/ac`;

/** The scorer's part scores (0 = best, 1 = worst of all rotations), this option against today. */
function ScoreBars({ data, r }: { data: ExplorerData; r: Rotation }) {
  const ids = data.priorities.map((p) => p.id).filter((id) => r.score_parts[id] != null);
  if (!ids.length) return null;
  const bar = (v: number, cls: string) => <span className={`sbar ${cls}`}><i style={{ width: `${Math.max(2, (1 - Math.min(1, Math.max(0, v))) * 100)}%` }} /></span>;
  return (
    <div className="scores">
      <h3 className="first">How it scores</h3>
      <p className="note">Longer bar = better. Each criterion is scaled from the worst (empty) to the best (full) of {data.nRotations ?? 'all'} rotations.</p>
      <dl>
        {ids.map((id) => {
          const w = data.priorities.find((p) => p.id === id)?.weight;
          return (
            <div key={id} data-tip={`${priorityLabel(id)}: ${r.score_parts[id].toFixed(2)} here, ${(data.current.score_parts[id] ?? NaN).toFixed(2)} today (0 = best)`}>
              <dt>{priorityLabel(id)}{w != null && <small> weight {w}/5</small>}</dt>
              <dd>{bar(r.score_parts[id], 'this')}{!r.is_current && data.current.score_parts[id] != null && bar(data.current.score_parts[id], 'today')}</dd>
            </div>
          );
        })}
      </dl>
      {!r.is_current && <p className="note sbar-legend"><span className="sbar this"><i /></span> this option <span className="sbar today"><i /></span> today</p>}
    </div>
  );
}

function Seasons({ r, units }: { r: Rotation; units: Units }) {
  return (
    <div className="scroll">
      <table className="all seasons">
        <thead><tr><th>Crop</th><th>Planted</th><th>Harvested</th><th>Irrigation need</th><th>Yield</th><th>After harvest</th></tr></thead>
        <tbody>
          {r.sequence.map((s, i) => (
            <tr key={i}>
              <th scope="row"><i className="dot" style={{ background: cropColor(s.crop) }} />{cropLabel(s.crop)}</th>
              <td>{day(s.plant_date)}</td>
              <td>{day(s.harvest_date)}</td>
              <td>{fmtWater(s.irr_in.v, units)}<small className="rng">{fmtWaterNum(s.irr_in.p10, units)}–{fmtWaterNum(s.irr_in.p90, units)}</small></td>
              <td data-tip={s.effects.map((e) => e.text).join(' · ') || undefined}>{yieldText(s)}<small className="rng">{Math.round(s.yield.p10).toLocaleString('en-US')}–{Math.round(s.yield.p90).toLocaleString('en-US')}</small></td>
              <td>{i === r.sequence.length - 1 ? '–' : s.cover ? `${cropLabel(s.cover)} cover` : 'bare'}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <p className="note">Ranges: 10th–90th percentile over the weather years. Irrigation level: {r.sequence[0].irrigation} (assumption).</p>
    </div>
  );
}

export function Detail({ data, r, metrics, mctx, units }: { data: ExplorerData; r: Rotation; metrics: MetricDef[]; mctx: MetricCtx; units: Units }) {
  const groups = [...data.priorities.map((p) => p.id), 'overall'];
  return (
    <section aria-labelledby="detail-h" className="detail">
      <h2 id="detail-h">{r.name}</h2>
      <div className="cols">
        <ScoreBars data={data} r={r} />
        <div>
          <h3 className="first">{CONTENT.checkTitle}</h3>
          <p className="note">{CONTENT.checkNote}</p>
        </div>
      </div>
      <Seasons r={r} units={units} />
      <WaterChart r={r} units={units} />

      <details>
        <summary>All numbers</summary>
        <div className="scroll">
          <table className="all">
            <thead><tr><th /><th>Today</th><th>{r.name}</th></tr></thead>
            <tbody>
              {groups.map((id) => {
                const rows = metrics.filter((m) => m.group === id);
                return rows.length ? [
                  <tr className="grp" key={`g${id}`}><th colSpan={3}>{priorityLabel(id)}</th></tr>,
                  ...rows.map((m) => (
                    <tr key={m.key}>
                      <th scope="row">{m.label}<small>{m.sub(mctx)} · {TAG_LABELS[m.tag].toLowerCase()}</small></th>
                      <td>{data.current.kpi[m.key] ? m.fmt(data.current.kpi[m.key].v, mctx) : '–'}</td>
                      <td>{r.kpi[m.key] ? <>{m.fmt(r.kpi[m.key].v, mctx)}{m.range ? <small className="rng">{m.range(r.kpi[m.key], mctx)}</small> : null}</> : '–'}</td>
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
