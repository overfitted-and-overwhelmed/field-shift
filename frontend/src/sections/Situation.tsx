import { MultiSelect } from '../components/MultiSelect';
import { CONTENT } from '../config/content';
import { cropColor, cropLabel } from '../config/crops';
import { priorityLabel } from '../config/priorities';
import { COUNT_MAX, COUNT_MIN, CROP_IDS, PRIORITY_IDS, WEIGHT_MAX, WEIGHT_MIN, type PageState } from '../lib/request';
import { SecHead } from './ui';

const WEIGHT_WORDS = ['', 'not important', 'minor', 'moderate', 'important', 'top priority'];

interface Props { state: PageState; set: (f: (s: PageState) => PageState) => void }

/** Step 1: crops the picks may use, how many picks, and the weights. Every change reloads the data. */
export function Situation({ state, set }: Props) {
  return (
    <section id="inputs" aria-labelledby="inputs-h">
      <SecHead id="inputs-h" {...CONTENT.inputs} />
      <div className="inputs">
        <div className="card">
          <h3>Your crops and limits</h3>
          <MultiSelect
            label="Crops you can grow"
            placeholder="Select crops…"
            options={CROP_IDS.map((id) => ({ id, label: cropLabel(id), color: cropColor(id) }))}
            value={state.crops}
            onChange={(crops) => crops.length && set((s) => ({ ...s, crops }))}
          />
          <div className="limits">
            <div className="limit">
              <span className="field-label" id="count-l">Picks to compare</span>
              <div className="seg" role="group" aria-labelledby="count-l">
                {Array.from({ length: COUNT_MAX - COUNT_MIN + 1 }, (_, i) => COUNT_MIN + i).map((n) => (
                  <button type="button" key={n} aria-pressed={state.count === n} onClick={() => set((s) => ({ ...s, count: n }))}>{n}</button>
                ))}
              </div>
            </div>
          </div>
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
