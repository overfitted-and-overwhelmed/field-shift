import { useState } from 'react';
import { FieldPanel } from '../components/FieldPanel';
import { FieldsLayer, type Layer } from '../components/FieldsLayer';
import { LocationPicker } from '../components/LocationPicker';
import { SceneBar } from '../components/SceneBar';
import { CONTENT } from '../config/content';
import { useFieldData } from '../lib/fields/useFieldData';
import { DEFAULT_LOCATION, type LatLon } from '../lib/request';
import { SecHead } from './ui';

const LAYERS: { id: Layer; label: string }[] = [{ id: 'ndvi', label: 'NDVI' }, { id: 'crop', label: 'Crop type' }, { id: 'plain', label: 'Outlines' }];

/**
 * The fields around the farm (USDA CDL crops, Sentinel-2 NDVI). For orientation only: moving the marker does not change
 * the numbers on the page, which are computed for the Kearny County field.
 */
export function FieldMap() {
  const [location, setLocation] = useState<LatLon | null>(DEFAULT_LOCATION);
  const [layer, setLayer] = useState<Layer>('ndvi');
  const [picked, setPicked] = useState<{ at: string; id: string } | null>(null);
  const fd = useFieldData(location);
  const at = location ? `${location.lat},${location.lon}` : '';
  const selectedId = picked?.at === at ? picked.id : fd.surr.status === 'ready' ? fd.surr.data.ownId : null;
  const setSelectedId = (id: string) => setPicked({ at, id });
  const ndvi = fd.ndvi.status === 'ready' ? fd.ndvi.data : null;

  return (
    <section id="field" aria-labelledby="field-h">
      <SecHead id="field-h" {...CONTENT.field} />
      <div className="land mapsec">
        <div className="stage" aria-label="Map of the fields around your farm">
          <LocationPicker value={location} onChange={setLocation} scrollWheelZoom={false}>
            {fd.surr.status === 'ready' && <FieldsLayer data={fd.surr.data} layer={layer} ndvi={ndvi} selectedId={selectedId} onSelect={setSelectedId} />}
          </LocationPicker>
          <div className="hud layers" role="group" aria-label="Map layer">
            {LAYERS.map((l) => <button key={l.id} type="button" aria-pressed={layer === l.id} onClick={() => setLayer(l.id)}>{l.label}</button>)}
          </div>
          <FieldPanel surr={fd.surr} ndvi={ndvi} ndviLoading={fd.ndvi.status === 'loading'} layer={layer} selectedId={selectedId} onSelect={setSelectedId} />
          <SceneBar scenes={fd.scenes} sceneId={fd.sceneId} onScene={fd.setSceneId} surr={fd.surr} layer={layer}
            state={fd.ndvi.status === 'error' ? 'error' : fd.ndvi.status === 'loading' ? 'loading' : 'ready'} error={fd.ndvi.status === 'error' ? fd.ndvi.error : undefined} />
        </div>
      </div>
    </section>
  );
}
