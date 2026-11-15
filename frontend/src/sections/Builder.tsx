import { useState, type DragEvent } from 'react';
import { CONTENT } from '../config/content';
import { cropColor, cropLabel } from '../config/crops';
import { CROP_IDS, ROTATION_LENGTH, noCover, type PageState } from '../lib/request';
import type { ExplorerData } from '../types';
import { SecHead } from './ui';

interface Props { state: PageState; set: (f: (s: PageState) => PageState) => void; data: ExplorerData | null; error: string | null; loading: boolean; notice: string | null }

/** The last three main crops of the field's CDL history: the rotation the page starts from. */
function historyRotation(data: ExplorerData): string[] {
  return data.field.crop_history.map((h) => h.crop).filter((c) => CROP_IDS.includes(c)).slice(-ROTATION_LENGTH);
}

const move = <T,>(a: T[], from: number, to: number) => { const b = [...a]; const [x] = b.splice(from, 1); b.splice(to, 0, x); return b; };

/**
 * Step 2: the farmer's rotation as three year cards. Drag a crop from the shelf onto a year, drag years to reorder,
 * or use the menu and the arrows (keyboard and touch). Every change is scored by the API.
 */
export function Builder({ state, set, data, error, loading, notice }: Props) {
  const [over, setOver] = useState<number | null>(null);
  if (!data) return null;
  const history = historyRotation(data);
  const seq = state.rotation ?? history;
  const covered = state.cover.some(Boolean);
  const edited = state.rotation != null && (state.rotation.join('-') !== history.join('-') || covered);
  const change = (next: string[], cover = state.cover) => set((s) => ({ ...s, rotation: next, cover }));
  const setCover = (i: number, on: boolean) => change(seq, state.cover.map((c, k) => (k === i ? on : c)));
  const startYear = data.field.rotation_start_year;

  const onDrop = (i: number) => (e: DragEvent) => {
    e.preventDefault(); setOver(null);
    const [kind, value] = e.dataTransfer.getData('text/plain').split(':');
    if (kind === 'crop' && CROP_IDS.includes(value)) change(seq.map((c, k) => (k === i ? value : c)));
    if (kind === 'year') { const from = Number(value); if (from !== i) change(move(seq, from, i)); }
  };
  const dragOver = (i: number) => (e: DragEvent) => { e.preventDefault(); if (over !== i) setOver(i); };

  return (
    <section id="build" aria-labelledby="build-h">
      <SecHead id="build-h" {...CONTENT.build} />
      <div className="card">
        <div className="shelf">
          <span className="eyebrow">Crops</span>
          <div className="palette">
            {CROP_IDS.map((c) => (
              <span key={c} className="pchip" draggable onDragStart={(e) => e.dataTransfer.setData('text/plain', `crop:${c}`)} data-tip={`Drag ${cropLabel(c).toLowerCase()} onto a year`}>
                <i style={{ background: cropColor(c) }} />{cropLabel(c)}
              </span>
            ))}
          </div>
          <button type="button" className="btn" disabled={!edited} onClick={() => set((s) => ({ ...s, rotation: null, cover: noCover() }))}>Reset to crop history</button>
        </div>
        <ol className="ycards">
          {seq.map((c, i) => (
            <li key={i} className={`ycard${over === i ? ' drop' : ''}`} draggable
              onDragStart={(e) => e.dataTransfer.setData('text/plain', `year:${i}`)}
              onDragOver={dragOver(i)} onDragLeave={() => setOver(null)} onDrop={onDrop(i)}>
              <span className="cbar" style={{ background: cropColor(c) }} />
              <div className="yhead"><b>Year {i + 1}</b><span className="small muted">from {startYear + i}</span><span className="handle" aria-hidden="true">⠿</span></div>
              <select aria-label={`Crop in year ${i + 1}`} value={c} onChange={(e) => change(seq.map((x, k) => (k === i ? e.target.value : x)))}>
                {CROP_IDS.map((id) => <option key={id} value={id}>{cropLabel(id)}</option>)}
              </select>
              <div className="ytools">
                <button type="button" className="iconbtn" aria-label={`Move year ${i + 1} earlier`} disabled={i === 0} onClick={() => change(move(seq, i, i - 1))}>◀</button>
                <button type="button" className="iconbtn" aria-label={`Move year ${i + 1} later`} disabled={i === seq.length - 1} onClick={() => change(move(seq, i, i + 1))}>▶</button>
              </div>
              {i < seq.length - 1 ? (
                <label className="covertoggle" data-tip="Sown after the harvest, ended before the next crop is planted. It is not irrigated, covers the soil and changes the next crop's nitrogen and water.">
                  <input type="checkbox" checked={state.cover[i] ?? false} onChange={(e) => setCover(i, e.target.checked)} />
                  <i style={{ background: cropColor('triticale') }} />Triticale cover crop after harvest
                </label>
              ) : <span className="small muted">No cover after the last crop: the rotation starts over.</span>}
              {i > 0 && seq[i - 1] === c && <p className="warn">Same crop as the year before: pests and disease carry over.</p>}
            </li>
          ))}
        </ol>
        <p className="small muted" aria-live="polite">
          {notice ? <span className="warn">{notice}</span>
            : error && state.rotation ? <span className="err">{error}</span>
            : loading ? 'Scoring your rotation…'
            : edited ? `Your rotation: ${seq.map((c, i) => cropLabel(c) + (state.cover[i] ? ' + cover' : '')).join(' → ')}. Scored on the same scale as the picks.`
            : `From your crop history: ${seq.map(cropLabel).join(' → ')}.`}
        </p>
      </div>
    </section>
  );
}
