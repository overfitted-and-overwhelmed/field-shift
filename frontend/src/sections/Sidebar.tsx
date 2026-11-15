import { Check } from 'lucide-react';
import { Info } from '../components/Info';
import { cropColor, cropLabel } from '../config/crops';
import { priorityLabel } from '../config/priorities';
import { CROP_IDS, PRIORITY_IDS, WEIGHT_MAX, WEIGHT_MIN, type PageState } from '../lib/request';
import type { Units } from '../lib/units';
import type { ExplorerData } from '../types';

const WORDS = ['', 'Not important', 'Minor', 'Moderate', 'Important', 'Top priority'];
const PRIORITY_HELP: Record<string, string> = {
  water: 'Less irrigation water pumped from the aquifer.',
  risk: 'Fewer days of heat and cold stress on the crop.',
  soil_health: 'Fewer months of bare soil, and no crop twice in a row.',
  nitrogen: 'Less nitrogen fertilizer to buy and spread.',
};

interface Props {
  state: PageState; set: (f: (s: PageState) => PageState) => void;
  units: Units; onUnits: (u: Units) => void; data: ExplorerData | null;
}

/** Fixed left column: what the scorer weighs and which crops it may use. Changes apply to every tab at once. */
export function Sidebar({ state, set, units, onUnits, data }: Props) {
  const toggleCrop = (c: string) => set((s) => {
    const on = s.crops.includes(c);
    if (on && s.crops.length === 1) return s; // at least one crop must stay
    return { ...s, crops: on ? s.crops.filter((x) => x !== c) : CROP_IDS.filter((x) => x === c || s.crops.includes(x)) };
  });
  const f = data?.field;
  return (
    <aside className="sidebar" aria-label="Settings">
      <section className="side-group" aria-labelledby="prio-h">
        <div className="side-head">
          <h2 id="prio-h">What matters to you</h2>
          <Info label="What matters to you">The scorer rates every rotation on these four points and ranks them by your weights. Only the ratio between the weights counts.</Info>
        </div>
        {PRIORITY_IDS.map((id) => {
          const w = state.weights[id] ?? 3;
          return (
            <div className="weight" key={id}>
              <div className="weight-top">
                <label htmlFor={`w-${id}`}>{priorityLabel(id)}</label>
                <output htmlFor={`w-${id}`}>{WORDS[w]}</output>
              </div>
              <input id={`w-${id}`} type="range" min={WEIGHT_MIN} max={WEIGHT_MAX} step={1} value={w}
                aria-valuetext={`${w} of 5, ${WORDS[w]}`} aria-describedby={`wh-${id}`}
                style={{ '--fill': `${((w - WEIGHT_MIN) / (WEIGHT_MAX - WEIGHT_MIN)) * 100}%` } as React.CSSProperties}
                onChange={(e) => { const v = Number(e.target.value); set((s) => ({ ...s, weights: { ...s.weights, [id]: v } })); }} />
              <p id={`wh-${id}`} className="weight-help">{PRIORITY_HELP[id]}</p>
            </div>
          );
        })}
      </section>

      <section className="side-group" aria-labelledby="crops-h">
        <div className="side-head">
          <h2 id="crops-h">Crops you can grow</h2>
          <Info label="Crops you can grow">The suggestions only use these crops. Your own rotation can use any crop.</Info>
        </div>
        <div className="crop-toggles">
          {CROP_IDS.map((c) => {
            const on = state.crops.includes(c);
            return (
              <button key={c} type="button" className="crop-toggle" aria-pressed={on} onClick={() => toggleCrop(c)}
                disabled={on && state.crops.length === 1} title={on && state.crops.length === 1 ? 'Keep at least one crop' : undefined}>
                <i style={{ background: cropColor(c) }} aria-hidden="true" />
                {cropLabel(c)}
                {on && <Check size={15} strokeWidth={2.5} aria-hidden="true" className="tick" />}
              </button>
            );
          })}
        </div>
      </section>

      <section className="side-group" aria-labelledby="units-h">
        <h2 id="units-h">Water in</h2>
        <div className="seg" role="group" aria-labelledby="units-h">
          <button type="button" aria-pressed={units === 'in'} onClick={() => onUnits('in')}>Inches</button>
          <button type="button" aria-pressed={units === 'mm'} onClick={() => onUnits('mm')}>Millimetres</button>
        </div>
      </section>

      {f && (
        <section className="side-group field-facts" aria-labelledby="field-h">
          <h2 id="field-h">Your field</h2>
          <dl>
            <div><dt>Place</dt><dd>{f.name}</dd></div>
            <div><dt>Soil</dt><dd>{f.soil.texture}, holds {f.soil.water_capacity_in} in of water</dd></div>
            <div><dt>Elevation</dt><dd>{f.elevation_ft.toLocaleString('en-US')} ft</dd></div>
            <div><dt>Grown so far</dt><dd>{[...new Set(f.crop_history.map((h) => cropLabel(h.crop)))].join(', ')} ({f.crop_history[0]?.year}–{f.crop_history[f.crop_history.length - 1]?.year})</dd></div>
          </dl>
        </section>
      )}
    </aside>
  );
}
