import { useState, type FormEvent } from 'react';
import { CONTENT } from '../config/content';
import { cropColor, cropLabel } from '../config/crops';
import { priorityLabel } from '../config/priorities';
import { useFieldData } from '../lib/fields/useFieldData';
import { COUNT_MAX, COUNT_MIN, CROP_IDS, PRIORITY_IDS, WEIGHT_MAX, WEIGHT_MIN, emptyRequest, goResults, type FieldRequest } from '../lib/request';
import { FieldPanel } from './FieldPanel';
import { FieldsLayer, type Layer } from './FieldsLayer';
import { LocationPicker } from './LocationPicker';
import { MultiSelect } from './MultiSelect';
import { SceneBar } from './SceneBar';

const WEIGHT_WORDS = ['', 'not important', 'minor', 'moderate', 'important', 'top priority'];
const LAYERS: { id: Layer; label: string }[] = [{ id: 'ndvi', label: 'NDVI' }, { id: 'crop', label: 'Crop type' }, { id: 'plain', label: 'Outlines' }];

/**
 * Start page: where the field is, which crops, how many in the rotation, and what matters (1–5 per priority).
 * The map shows the fields around the picked point with real data: crops from the USDA Cropland Data Layer, NDVI from Sentinel-2.
 */
export function InputForm({ prefill }: { prefill: FieldRequest | null }) {
  const [req, setReq] = useState<FieldRequest>(() => prefill ?? emptyRequest());
  const [tried, setTried] = useState(false);
  const [layer, setLayer] = useState<Layer>('ndvi');
  const [picked, setPicked] = useState<{ at: string; id: string } | null>(null);
  const fd = useFieldData(req.location);
  const maxCount = COUNT_MAX;
  const count = Math.min(req.count, maxCount);
  const cropsMissing = req.crops.length === 0;
  const locationMissing = !req.location;

  // the field with the marker is selected until the user clicks another one; a new location starts over
  const at = req.location ? `${req.location.lat},${req.location.lon}` : '';
  const selectedId = picked?.at === at ? picked.id : fd.surr.status === 'ready' ? fd.surr.data.ownId : null;
  const setSelectedId = (id: string) => setPicked({ at, id });

  const submit = (e: FormEvent) => {
    e.preventDefault();
    setTried(true);
    if (cropsMissing || locationMissing) return;
    goResults({ ...req, count });
  };

  const ndvi = fd.ndvi.status === 'ready' ? fd.ndvi.data : null;

  return (
    <div className="land">
      <form className="side" onSubmit={submit} noValidate>
        <header className="brandbar">
          <svg viewBox="0 0 24 24" width="26" height="26" aria-hidden="true"><rect width="24" height="24" rx="7" fill="var(--ln-teal)" /><path d="M5 16.5c3.2-5.5 6.8-7.7 14-8.5-1 6.3-4.6 9.7-11 9.9" fill="none" stroke="#0b2b25" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" /></svg>
          <span>{CONTENT.brand}</span>
        </header>

        <div className="intro">
          <h1>{CONTENT.formTitle}</h1>
          <p>{CONTENT.formLead}</p>
        </div>

        <fieldset>
          <legend><span className="step">1</span>Field location</legend>
          <p className="note">{req.location ? 'Hover or click the marker to see its coordinates; remove it from its menu to pick a new spot.' : 'Click on the map where your field is.'}</p>
          <p className="coords" aria-live="polite">
            {req.location ? <>Selected: <b>{req.location.lat.toFixed(4)}, {req.location.lon.toFixed(4)}</b></> : 'No location selected yet.'}
          </p>
          {tried && locationMissing && <p role="alert" className="err">Choose your field on the map.</p>}
        </fieldset>

        <fieldset>
          <legend><span className="step">2</span>Crops</legend>
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
          <legend><span className="step">3</span>What matters to you</legend>
          <p className="note">Rate each point from {WEIGHT_MIN} (not important) to {WEIGHT_MAX} (top priority).</p>
          <div className="sliders">
            {PRIORITY_IDS.map((id) => {
              const w = req.weights[id] ?? 3;
              return (
                <div key={id} className="slider">
                  <label htmlFor={`w-${id}`}>{priorityLabel(id)}</label>
                  <output htmlFor={`w-${id}`}><b>{w}</b> <span>{WEIGHT_WORDS[w]}</span></output>
                  <input id={`w-${id}`} type="range" min={WEIGHT_MIN} max={WEIGHT_MAX} step={1} value={w}
                    style={{ '--fill': `${((w - WEIGHT_MIN) / (WEIGHT_MAX - WEIGHT_MIN)) * 100}%` } as React.CSSProperties}
                    aria-valuetext={`${w} – ${WEIGHT_WORDS[w]}`}
                    onChange={(e) => setReq((r) => ({ ...r, weights: { ...r.weights, [id]: Number(e.target.value) } }))} />
                </div>
              );
            })}
          </div>
        </fieldset>

        <div className="cta"><button type="submit" className="primary">Show rotations</button></div>
        <p className="foot-note">{CONTENT.footer}</p>
      </form>

      <section className="stage" aria-label="Map of the fields around your location">
        <LocationPicker value={req.location} onChange={(location) => setReq((r) => ({ ...r, location }))}>
          {fd.surr.status === 'ready' && (
            <FieldsLayer data={fd.surr.data} layer={layer} ndvi={ndvi} selectedId={selectedId} onSelect={setSelectedId} />
          )}
        </LocationPicker>

        <div className="hud layers" role="group" aria-label="Map layer">
          {LAYERS.map((l) => <button key={l.id} type="button" aria-pressed={layer === l.id} onClick={() => setLayer(l.id)}>{l.label}</button>)}
        </div>

        <FieldPanel surr={fd.surr} ndvi={ndvi} ndviLoading={fd.ndvi.status === 'loading'} layer={layer} selectedId={selectedId} onSelect={setSelectedId} />

        <SceneBar scenes={fd.scenes} sceneId={fd.sceneId} onScene={fd.setSceneId} surr={fd.surr} layer={layer}
          state={fd.ndvi.status === 'error' ? 'error' : fd.ndvi.status === 'loading' ? 'loading' : 'ready'} error={fd.ndvi.status === 'error' ? fd.ndvi.error : undefined} />

      </section>
    </div>
  );
}
