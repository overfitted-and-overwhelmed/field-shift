import { useState, type FormEvent } from 'react';
import { CONTENT } from '../config/content';
import { cropColor, cropLabel } from '../config/crops';
import { priorityLabel } from '../config/priorities';
import { COUNT_MAX, COUNT_MIN, CROP_IDS, PRIORITY_IDS, WEIGHT_MAX, WEIGHT_MIN, emptyRequest, goResults, type FieldRequest } from '../lib/request';
import { MultiSelect } from './MultiSelect';

const WEIGHT_WORDS = ['', 'not important', 'minor', 'moderate', 'important', 'top priority'];

/** Start page: which crops, how many in the rotation, and what matters (1–5 per priority). */
export function InputForm({ prefill }: { prefill: FieldRequest | null }) {
  const [req, setReq] = useState<FieldRequest>(() => prefill ?? emptyRequest());
  const [tried, setTried] = useState(false);
  const maxCount = COUNT_MAX;
  const count = Math.min(req.count, maxCount);
  const cropsMissing = req.crops.length === 0;

  const submit = (e: FormEvent) => {
    e.preventDefault();
    setTried(true);
    if (cropsMissing) return;
    goResults({ ...req, count });
  };

  return (
    <>
      <header className="top"><div className="page"><span className="brand">{CONTENT.brand}</span></div></header>
      <main className="page">
        <div className="intro">
          <h1>{CONTENT.formTitle}</h1>
          <p className="lead">{CONTENT.formLead}</p>
        </div>

        <form className="form" onSubmit={submit} noValidate>
          <fieldset>
            <legend><h2>Crops</h2></legend>
            <MultiSelect
              label="Crops you can grow"
              placeholder="Select crops…"
              options={CROP_IDS.map((id) => ({ id, label: cropLabel(id), color: cropColor(id) }))}
              value={req.crops}
              onChange={(crops) => setReq((r) => ({ ...r, crops }))}
            />
            {tried && cropsMissing && <p role="alert" className="err">Select at least one crop.</p>}

            <div className="count">
              <label className="field-label" htmlFor="count">Number of crop rotations to predict</label>
              <div className="stepper">
                <button type="button" aria-label="Fewer" disabled={count <= COUNT_MIN} onClick={() => setReq((r) => ({ ...r, count: count - 1 }))}>−</button>
                <input id="count" type="number" inputMode="numeric" min={COUNT_MIN} max={maxCount} value={count}
                  onChange={(e) => { const n = Number(e.target.value); if (Number.isFinite(n)) setReq((r) => ({ ...r, count: Math.min(maxCount, Math.max(COUNT_MIN, Math.round(n))) })); }} />
                <button type="button" aria-label="More" disabled={count >= maxCount} onClick={() => setReq((r) => ({ ...r, count: count + 1 }))}>+</button>
              </div>
              <p className="note">Between {COUNT_MIN} and {COUNT_MAX}. Your current rotation is always shown for comparison.</p>
            </div>
          </fieldset>

          <fieldset>
            <legend><h2>What matters to you</h2></legend>
            <p className="note">Rate each point from {WEIGHT_MIN} (not important) to {WEIGHT_MAX} (top priority).</p>
            <div className="sliders">
              {PRIORITY_IDS.map((id) => {
                const w = req.weights[id] ?? 3;
                return (
                  <div key={id} className="slider">
                    <label htmlFor={`w-${id}`}>{priorityLabel(id)}</label>
                    <input id={`w-${id}`} type="range" min={WEIGHT_MIN} max={WEIGHT_MAX} step={1} value={w}
                      aria-valuetext={`${w} – ${WEIGHT_WORDS[w]}`}
                      onChange={(e) => setReq((r) => ({ ...r, weights: { ...r.weights, [id]: Number(e.target.value) } }))} />
                    <output htmlFor={`w-${id}`}><b>{w}</b> <span>{WEIGHT_WORDS[w]}</span></output>
                  </div>
                );
              })}
            </div>
          </fieldset>

          <div><button type="submit" className="primary">Show rotations</button></div>
        </form>
      </main>
      <footer className="foot"><div className="page"><p>{CONTENT.footer}</p></div></footer>
    </>
  );
}
