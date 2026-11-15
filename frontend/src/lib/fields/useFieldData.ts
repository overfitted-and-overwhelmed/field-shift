import { useEffect, useRef, useState } from 'react';
import type { LatLon } from '../request';
import { findScenes, renderNdvi, type NdviResult, type Scene } from './ndvi';
import { loadSurroundings, type Surroundings } from './surroundings';

export type Load<T> = { status: 'idle' } | { status: 'loading' } | { status: 'ready'; data: T } | { status: 'error'; error: string };
const msg = (e: unknown) => (e instanceof Error ? e.message : String(e));
const aborted = (e: unknown) => e instanceof DOMException && e.name === 'AbortError';

/**
 * Real data around a picked coordinate, fetched live in the browser:
 *  1. USDA Cropland Data Layer -> the fields (outline, crop, area, crop history since 2008)
 *  2. recent Sentinel-2 scenes -> NDVI per field for the scene the user selects (newest by default)
 */
export function useFieldData(location: LatLon | null) {
  const [surr, setSurr] = useState<Load<Surroundings>>({ status: 'idle' });
  const [scenes, setScenes] = useState<Load<Scene[]>>({ status: 'idle' });
  const [sceneId, setSceneId] = useState<string | null>(null);
  const [ndvi, setNdvi] = useState<Load<NdviResult>>({ status: 'idle' });
  const cache = useRef(new Map<string, NdviResult>());
  const lat = location?.lat, lon = location?.lon;

  useEffect(() => {
    cache.current.clear();
    setSceneId(null);
    setNdvi({ status: 'idle' });
    if (lat === undefined || lon === undefined) { setSurr({ status: 'idle' }); setScenes({ status: 'idle' }); return; }
    const ac = new AbortController();
    const at = { lat, lon };
    setSurr({ status: 'loading' });
    setScenes({ status: 'loading' });
    loadSurroundings(at, ac.signal).then((data) => setSurr({ status: 'ready', data }), (e) => { if (!aborted(e)) setSurr({ status: 'error', error: msg(e) }); });
    findScenes(at, ac.signal).then((data) => { setScenes({ status: 'ready', data }); setSceneId(data[0]?.id ?? null); }, (e) => { if (!aborted(e)) setScenes({ status: 'error', error: msg(e) }); });
    return () => ac.abort();
  }, [lat, lon]);

  useEffect(() => {
    if (surr.status !== 'ready' || scenes.status !== 'ready' || !sceneId) return;
    const scene = scenes.data.find((s) => s.id === sceneId);
    if (!scene) return;
    const hit = cache.current.get(sceneId);
    if (hit) { setNdvi({ status: 'ready', data: hit }); return; }
    const ac = new AbortController();
    setNdvi({ status: 'loading' });
    renderNdvi(surr.data, scene, ac.signal).then(
      (data) => { cache.current.set(sceneId, data); setNdvi({ status: 'ready', data }); },
      (e) => { if (!aborted(e)) setNdvi({ status: 'error', error: msg(e) }); },
    );
    return () => ac.abort();
  }, [surr, scenes, sceneId]);

  return { surr, scenes, sceneId, setSceneId, ndvi };
}
