import { useEffect, useRef } from 'react';
import { cdlColor, cdlName } from '../lib/fields/cdl';
import { NDVI_GRADIENT, type Scene } from '../lib/fields/ndvi';
import type { Surroundings } from '../lib/fields/surroundings';
import type { Load } from '../lib/fields/useFieldData';
import type { Layer } from './FieldsLayer';

const day = (d: string) => new Date(`${d}T12:00:00Z`).toLocaleDateString('en-US', { day: 'numeric', month: 'short', timeZone: 'UTC' });

interface Props {
  scenes: Load<Scene[]>;
  sceneId: string | null;
  onScene: (id: string) => void;
  surr: Load<Surroundings>;
  layer: Layer;
  state: 'idle' | 'loading' | 'ready' | 'error';
  error?: string;
}

/** Bottom bar of the map: legend of the active layer, and the real Sentinel-2 acquisition dates to choose from. */
export function SceneBar({ scenes, sceneId, onScene, surr, layer, state, error }: Props) {
  const area = new Map<number, number>();
  if (surr.status === 'ready') for (const f of surr.data.fields) area.set(f.cls, (area.get(f.cls) ?? 0) + f.ha);
  const ranked = [...area.entries()].sort((a, b) => b[1] - a[1]).map(([c]) => c);
  const crops = ranked.slice(0, 5), more = ranked.length - crops.length;
  const dates = useRef<HTMLDivElement>(null);
  useEffect(() => { // keep the chosen date in view (the row is oldest -> newest and scrolls)
    const box = dates.current, on = box?.querySelector<HTMLElement>('[aria-pressed="true"]');
    if (box && on) box.scrollLeft = on.offsetLeft - box.clientWidth / 2 + on.offsetWidth / 2;
  }, [sceneId, scenes.status]);
  return (
    <div className="hud bar">
      <div className="legend">
        {layer === 'ndvi' && <><span className="k">NDVI</span><i className="ramp" style={{ background: NDVI_GRADIENT }} /><span className="ends"><span>0</span><span>0.9</span></span></>}
        {layer === 'crop' && <ul>{crops.map((c) => <li key={c}><i style={{ background: cdlColor(c) }} />{cdlName(c)}</li>)}{more > 0 && <li className="more">+{more} more</li>}</ul>}
        {layer === 'plain' && <span className="k">Field outlines on satellite imagery</span>}
      </div>
      <div className="dates" role="group" aria-label="Sentinel-2 scene date" ref={dates}>
        {scenes.status === 'loading' && <span className="k">Finding satellite scenes…</span>}
        {scenes.status === 'error' && <span className="k err">{scenes.error}</span>}
        {scenes.status === 'ready' && scenes.data.length === 0 && <span className="k">No clear Sentinel-2 scene in the last months.</span>}
        {scenes.status === 'ready' && [...scenes.data].reverse().map((s) => (
          <button key={s.id} type="button" aria-pressed={s.id === sceneId} onClick={() => onScene(s.id)} title={`Sentinel-2, ${s.date}, ${s.cloud.toFixed(0)} % cloud over the tile`}>
            {day(s.date)}<small>{s.cloud < 1 ? '<1' : s.cloud.toFixed(0)}% cloud</small>
          </button>
        ))}
      </div>
      <p className="status" role="status">{state === 'loading' ? 'Reading Sentinel-2…' : state === 'error' ? error : ''}</p>
    </div>
  );
}
