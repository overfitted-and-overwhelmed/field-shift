import { ChevronDown, ChevronLeft, ChevronRight, GripVertical, LoaderCircle, Sprout, TriangleAlert } from 'lucide-react';
import { useState, type DragEvent } from 'react';
import { Delta } from '../components/Delta';
import { Info } from '../components/Info';
import { MonthStrip } from '../components/MonthStrip';
import { SeasonChart, SeasonTable, type SeasonView } from '../components/SeasonChart';
import { CONTENT } from '../config/content';
import { COVER_CROP, coverCropOf, cropColor, cropLabel, SCLEROTINIA_HOSTS, sclerotiniaExcess } from '../config/crops';
import { HEADLINE, type MetricCtx, type MetricDef } from '../config/metrics';
import { priorityLabel } from '../config/priorities';
import { CROP_IDS, type PageState } from '../lib/request';
import type { Units } from '../lib/units';
import type { ExplorerData, Rotation } from '../types';
import { coverNote, cropsName, pickLabel, toBuilder } from './helpers';

/** The Sclerotinia hosts in the years before year i, e.g. "Soybean" or "Sunflower and soybean". */
const hostsBefore = (seq: string[], i: number) => {
  const names = [...new Set(seq.slice(0, i).filter((c) => SCLEROTINIA_HOSTS.includes(c)))].map((c) => cropLabel(c).toLowerCase());
  const s = names.join(' and '); return s.charAt(0).toUpperCase() + s.slice(1);
};
const move = <T,>(a: T[], from: number, to: number) => { const b = [...a]; const [x] = b.splice(from, 1); b.splice(to, 0, x); return b; };
/** Short labels for the compact numbers in a rotation row. */
const SHORT: Record<string, string> = { irrigation_in: 'Water', heat_days: 'Heat stress', bare_months: 'Bare soil', n_lb: 'Fertilizer' };
const CRIT_HELP: Record<string, string> = { water: 'irrigation water', risk: 'heat and cold stress', soil_health: 'bare soil, same crop twice', nitrogen: 'fertilizer' };
const LEGEND: Record<SeasonView, [string, string][]> = {
  water: [['b-use', 'Water the crop uses'], ['b-irr', 'Irrigation (the part rain does not cover)'], ['l-rain', 'Rain']],
  n: [['b-need', 'Nitrogen the crop needs (K-State)'], ['b-n', 'Fertilizer you apply, after the credit or extra from the crop before']],
  stress: [['cell-heat', 'Heat stress days'], ['cell-cold', 'Cold stress days']],
};
/** Where a rotation stands on one priority among all rotations, in words (score part: 0 = best, 1 = worst). */
const standing = (part: number) => (part <= 0.33 ? 'Good' : part <= 0.66 ? 'Fair' : 'Poor');

export interface PlanProps {
  state: PageState; set: (f: (s: PageState) => PageState) => void;
  data: ExplorerData; mine: Rotation | null; picks: Rotation[];
  edited: boolean; history: string[]; scoring: boolean; notice: string | null; error: string | null;
  ctx: MetricCtx; units: Units; selectedId: string; onSelect: (id: string) => void;
}

/* ---------- builder ---------- */

function Builder({ state, set, history, edited, scoring, notice, error, data }: PlanProps) {
  const [over, setOver] = useState<number | null>(null);
  const seq = state.rotation ?? history;
  const change = (rotation: string[], cover = state.cover) => set((s) => ({ ...s, rotation, cover }));
  const start = data.field.rotation_start_year;
  const cover = cropLabel(coverCropOf(data.crops));
  const excess = sclerotiniaExcess(seq);
  const onDrop = (i: number) => (e: DragEvent) => {
    e.preventDefault(); setOver(null);
    const [kind, value] = e.dataTransfer.getData('text/plain').split(':');
    if (kind === 'crop' && CROP_IDS.includes(value)) change(seq.map((c, k) => (k === i ? value : c)));
    if (kind === 'year') { const from = Number(value); if (from !== i) change(move(seq, from, i)); }
  };
  return (
    <section className="panel builder" aria-labelledby="builder-h">
      <header className="panel-head">
        <h2 id="builder-h">{CONTENT.plan.builder}</h2>
        <p className="panel-sub">{CONTENT.plan.builderHint}</p>
      </header>

      <div className="ybuild">
        {seq.map((c, i) => (
          <div key={i} className="years-cell">
            <div className={`year${over === i ? ' drop' : ''}`} draggable onDragStart={(e) => e.dataTransfer.setData('text/plain', `year:${i}`)}
              onDragOver={(e) => { e.preventDefault(); if (over !== i) setOver(i); }} onDragLeave={() => setOver(null)} onDrop={onDrop(i)}>
              <span className="year-band" style={{ background: cropColor(c) }} />
              <div className="year-head">
                <b>Year {i + 1}</b><span>{start + i}</span>
                <span className="year-move">
                  <button type="button" className="icon-btn sm" aria-label={`Move year ${i + 1} earlier`} disabled={i === 0} onClick={() => change(move(seq, i, i - 1))}><ChevronLeft size={17} aria-hidden="true" /></button>
                  <button type="button" className="icon-btn sm" aria-label={`Move year ${i + 1} later`} disabled={i === seq.length - 1} onClick={() => change(move(seq, i, i + 1))}><ChevronRight size={17} aria-hidden="true" /></button>
                  <GripVertical size={17} className="grip" aria-hidden="true" />
                </span>
              </div>
              <select aria-label={`Crop in year ${i + 1}`} value={c} onChange={(e) => change(seq.map((x, k) => (k === i ? e.target.value : x)))}>
                {CROP_IDS.map((id) => <option key={id} value={id}>{cropLabel(id)}</option>)}
              </select>
              {i > 0 && seq[i - 1] === c && !SCLEROTINIA_HOSTS.includes(c) && <span className="year-warn"><TriangleAlert size={15} aria-hidden="true" />Same crop as year {i}: pests carry over</span>}
              {excess.includes(i) && <span className="year-warn"><TriangleAlert size={15} aria-hidden="true" />White mold risk: {hostsBefore(seq, i)} already in this rotation</span>}
            </div>
            {i < seq.length - 1 && (
              <button type="button" className="gap-cover" aria-pressed={state.cover[i] ?? false}
                onClick={() => change(seq, state.cover.map((v, k) => (k === i ? !v : v)))}
                data-tip={`${cover} sown after the harvest and ended before the next crop. Not irrigated; it covers the soil and changes the next crop's water and nitrogen.`}>
                <Sprout size={18} aria-hidden="true" />
                <b>{cover}</b>
                <span>{state.cover[i] ? 'cover crop' : 'add cover crop'}</span>
              </button>
            )}
          </div>
        ))}
      </div>

      <div className="shelf">
        <span className="shelf-label">Drag onto a year</span>
        {CROP_IDS.map((c) => (
          <span key={c} className="crop-chip" draggable onDragStart={(e) => e.dataTransfer.setData('text/plain', `crop:${c}`)}>
            <i style={{ background: cropColor(c) }} aria-hidden="true" />{cropLabel(c)}
          </span>
        ))}
        <span className="status" role="status" aria-live="polite">
          {notice ? <span className="warn-text"><TriangleAlert size={15} aria-hidden="true" />{notice}</span>
            : error && state.rotation ? <span className="warn-text"><TriangleAlert size={15} aria-hidden="true" />{error}</span>
            : scoring ? <span><LoaderCircle size={15} className="spin" aria-hidden="true" />Scoring your rotation</span>
            : excess.length ? <span className="warn-text"><TriangleAlert size={15} aria-hidden="true" />{CONTENT.plan.sclerotinia}</span>
            : edited ? 'Scored on the same scale as the suggestions.'
            : 'What your field grew the last three years.'}
        </span>
      </div>
    </section>
  );
}

/* ---------- result ---------- */

/** Your rotation and the best match as two labelled bars on one scale, values written out. */
function Bars({ m, mine, best, ctx }: { m: MetricDef; mine: number; best: number | null; ctx: MetricCtx }) {
  const max = Math.max(mine, best ?? 0) || 1;
  const w = (v: number) => `${Math.max(2, (v / max) * 100)}%`;
  return (
    <div className="bars">
      <span className="bars-label">Yours</span><span className="bars-val">{m.fmt(mine, ctx)}</span>
      <span className="bars-track"><i className="mine" style={{ width: w(mine) }} /></span>
      {best != null && <>
        <span className="bars-label">Best match</span><span className="bars-val">{m.fmt(best, ctx)}</span>
        <span className="bars-track"><i className="best" style={{ width: w(best) }} /></span>
      </>}
    </div>
  );
}

function Result({ mine, picks, ctx, data }: PlanProps) {
  if (!mine) return <section className="panel result skeleton" aria-busy="true" aria-label="Scoring your rotation" />;
  const best = picks[0] ?? null;
  const rank = mine.raw.rank_all, n = data.nRotations;
  const prios = data.priorities.filter((p) => mine.score_parts[p.id] != null);
  return (
    <section className="panel result" aria-labelledby="result-h">
      <header className="panel-head"><h2 id="result-h">{CONTENT.plan.result}</h2></header>
      <div className="result-grid">
        {HEADLINE.map((m) => {
          const k = mine.kpi[m.key], b = best?.kpi[m.key];
          if (!k) return null;
          const range = m.range?.(k, ctx);
          return (
            <div className="kpi" key={m.key}>
              <div className="kpi-head">
                <h3>{m.label}</h3>
                <Info label={m.label}><p>{m.info}</p>{range && <p>Your rotation: {range}.</p>}<p>{m.better === 'lower' ? 'Less is better.' : 'More is better.'}</p></Info>
              </div>
              <p className="kpi-value"><span className="num" key={k.v}>{m.num(k.v, ctx)}</span><span className="unit">{m.unit(ctx)}</span></p>
              <Bars m={m} mine={k.v} best={b?.v ?? null} ctx={ctx} />
              {b && <Delta m={m} v={b.v} base={k.v} ctx={ctx} against="yours" prefix="Best match: " compact />}
            </div>
          );
        })}
        <div className="rank">
          <div className="kpi-head">
            <h3>Rank for your priorities</h3>
            <Info label="Rank for your priorities">The scorer compares {n ?? 'all'} three-crop rotations, with and without cover crops, and sorts them by your weights. Rotations with more than one sunflower or soybean crop come after all others (white mold). For each priority the bar shows where your rotation stands among all of them: a full bar is the best of all.</Info>
          </div>
          {rank != null && <p className="kpi-value"><span className="num" key={rank}>{rank}</span><span className="unit">of {n ?? '–'} rotations, 1 = best</span></p>}
          <ul className="parts">
            {prios.map((p) => {
              const part = Math.min(1, Math.max(0, mine.score_parts[p.id]));
              return (
                <li key={p.id} data-tip={`${priorityLabel(p.id)} (${CRIT_HELP[p.id]}): ${standing(part).toLowerCase()} compared with all ${n ?? ''} rotations`}>
                  <span>{priorityLabel(p.id)}</span>
                  <span className="part-bar"><i style={{ width: `${Math.max(3, (1 - part) * 100)}%` }} /></span>
                  <span className={`part-word ${standing(part).toLowerCase()}`}>{standing(part)}</span>
                </li>
              );
            })}
          </ul>
        </div>
      </div>
    </section>
  );
}

/* ---------- rotations + month by month ---------- */

interface Row { id: string; label: string; r: Rotation; pick: boolean; hasVariant: boolean }

function Rotations({ mine, picks, ctx, units, set, selectedId, onSelect, data }: PlanProps) {
  const [variants, setVariants] = useState<Record<string, boolean>>({});
  const [view, setView] = useState<SeasonView>('water');
  const [table, setTable] = useState(false);
  const rows: Row[] = [];
  if (mine) rows.push({ id: 'mine', label: 'Your rotation', r: mine, pick: false, hasVariant: false });
  picks.forEach((p) => rows.push({ id: p.id, label: pickLabel(p), r: variants[p.id] && p.cover_variant ? p.cover_variant : p, pick: true, hasVariant: !!p.cover_variant }));
  const sel = rows.find((x) => x.id === selectedId) ?? rows[0];
  if (!sel) return null;
  const hasCover = (r: Rotation) => r.sequence.slice(0, -1).some((s) => s.cover);
  const coverName = (r: Rotation) => `${cropLabel(r.sequence.find((s) => s.cover)?.cover ?? r.cover_variant?.sequence.find((s) => s.cover)?.cover ?? COVER_CROP)} cover crop`;
  return (
    <section className="panel rotations" aria-labelledby="rot-h">
      <header className="panel-head">
        <h2 id="rot-h">{CONTENT.plan.rotations}</h2>
        <p className="panel-sub">{CONTENT.plan.rotationsHint}</p>
      </header>
      <ol className="rot-list">
        {rows.map((row) => (
          <li key={row.id} className={`rot${row.id === sel.id ? ' on' : ''}`}>
            <button type="button" className="rot-select" aria-pressed={row.id === sel.id} onClick={() => onSelect(row.id)}>
              <span className="rot-name">
                <span className="rot-title"><b>{cropsName(row.r)}</b><span className={`rot-tag${row.pick ? '' : ' mine'}`}>{row.label}</span></span>
                <span className="rot-note">{coverNote(row.r) || 'No cover crop'}</span>
              </span>
              <MonthStrip r={row.r} size="sm" />
              <span className="rot-nums">
                {HEADLINE.map((m) => row.r.kpi[m.key] && (
                  <span key={m.key} className="rot-num">
                    <span className="rot-num-label">{SHORT[m.key]}</span>
                    <b>{m.fmt(row.r.kpi[m.key].v, ctx)}</b>
                    {row.pick && mine?.kpi[m.key] && <Delta m={m} v={row.r.kpi[m.key].v} base={mine.kpi[m.key].v} ctx={ctx} against="yours" compact />}
                  </span>
                ))}
              </span>
            </button>
            <span className="rot-actions">
              {row.pick && <button type="button" className="btn primary sm" onClick={() => set((s) => ({ ...s, ...toBuilder(row.r) }))}>Use this rotation</button>}
            </span>
          </li>
        ))}
      </ol>

      <div className="month-view">
        <div className="month-head">
          <h3>{sel.label}: {cropsName(sel.r)}, month by month</h3>
          <div className="toolbar">
            {sel.hasVariant && (
              <label className="switch">
                <input type="checkbox" role="switch" checked={hasCover(sel.r)} onChange={() => setVariants((v) => ({ ...v, [sel.id]: !v[sel.id] }))} />
                <span>{coverName(sel.r)}</span>
              </label>
            )}
            <div className="seg" role="group" aria-label="Show">
              <button type="button" aria-pressed={view === 'water'} onClick={() => setView('water')}>Water</button>
              <button type="button" aria-pressed={view === 'n'} onClick={() => setView('n')}>Fertilizer</button>
              <button type="button" aria-pressed={view === 'stress'} onClick={() => setView('stress')}>Weather stress</button>
            </div>
            <Info label="Month by month">A typical year from 35 seasons of NASA POWER weather (1991–2025), not a forecast. The band on top shows what is on the field. Water: the grey bar is what the crop uses, the blue bar the irrigation that tops up the rain. Fertilizer: K-State gives the nitrogen per season, so it is shown in the month of planting. Weather stress: the average temperature by day and night, and on how many days per month the crop is too hot (above its optimum) or too cold (below its optimum for at least half the day); the stronger the colour, the more days.</Info>
          </div>
        </div>
        <div className="chart-scroll"><SeasonChart r={sel.r} units={units} view={view} weather={data.weather_monthly} /></div>
        <p className="legend-inline">
          {[...new Set(sel.r.sequence.map((s) => s.crop))].map((c) => <span key={c}><i style={{ background: cropColor(c) }} />{cropLabel(c)}</span>)}
          {hasCover(sel.r) && <span><i className="sw-cover" />{coverName(sel.r)}</span>}
          <span><i className="sw-bare" />Bare soil</span>
          {view === 'stress' && data.weather_monthly && <><span><i className="sw l-tmax" />Average day temperature</span><span><i className="sw l-tmin" />Average night temperature</span></>}
          {LEGEND[view].map(([cls, label]) => <span key={cls}><i className={`sw ${cls}`} />{label}</span>)}
        </p>
        <button type="button" className="btn ghost disclose" aria-expanded={table} onClick={() => setTable((t) => !t)}>
          <ChevronDown size={18} className="chev" aria-hidden="true" />{table ? 'Hide the seasons' : 'Show the seasons: dates, yield, nitrogen'}
        </button>
        {table && <SeasonTable r={sel.r} units={units} />}
      </div>
    </section>
  );
}

/** Plan tab: build your rotation, read what it means, compare it month by month with the best suggestions. */
export function PlanView(p: PlanProps) {
  return (
    <div className="plan">
      <Builder {...p} />
      <Result {...p} />
      <Rotations {...p} />
    </div>
  );
}
