import { MultiSelect } from '../components/MultiSelect';
import { CONTENT } from '../config/content';
import { cropColor, cropLabel } from '../config/crops';
import { priorityLabel } from '../config/priorities';
import { CROP_IDS, PRIORITY_IDS, WEIGHT_MAX, WEIGHT_MIN, type PageState } from '../lib/request';
import { SecHead } from './ui';

const WEIGHT_WORDS = ['', 'not important', 'minor', 'moderate', 'important', 'top priority'];

interface Props { state: PageState; set: (f: (s: PageState) => PageState) => void }

/** Step 1: crops the picks may use, and the weights. Every change reloads the data. The page always shows 3 picks. */
export function Situation({ state, set }: Props) {
  return (
    <section id="inputs" aria-labelledby="inputs-h">
      <SecHead id="inputs-h" {...CONTENT.inputs} />
      <div className="inputs">
        <div className="card">
          <h3>Your crops</h3>
          <MultiSelect
            label="Crops you can grow"
            placeholder="Select crops…"
            options={CROP_IDS.map((id) => ({ id, label: cropLabel(id), color: cropColor(id) }))}
            value={state.crops}
            onChange={(crops) => crops.length && set((s) => ({ ...s, crops }))}
          />
        </div>
        <div className="card">
          <h3>What matters to you</h3>
          <p className="small muted">Rate each point from {WEIGHT_MIN} (not important) to {WEIGHT_MAX} (top priority). The scorer weighs its four criteria by these numbers.</p>
          <div className="weights">
            {PRIORITY_IDS.map((id) => {
              const w = state.weights[id] ?? 3;
              return (
                <div className="wrow" key={id}>
                  <label htmlFor={`w-${id}`}>{priorityLabel(id)}</label>
                  <input id={`w-${id}`} type="range" min={WEIGHT_MIN} max={WEIGHT_MAX} step={1} value={w} aria-valuetext={`${w} – ${WEIGHT_WORDS[w]}`}
                    style={{ '--fill': `${((w - WEIGHT_MIN) / (WEIGHT_MAX - WEIGHT_MIN)) * 100}%`, '--wc': `var(--w${w})` } as React.CSSProperties}
                    onChange={(e) => { const v = Number(e.target.value); set((s) => ({ ...s, weights: { ...s.weights, [id]: v } })); }} />
                  <output htmlFor={`w-${id}`} className="num">{w}/5</output>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </section>
  );
}
