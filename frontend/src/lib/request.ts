import { useCallback, useEffect, useState } from 'react';
import { COVER_CROP, CROP_LABELS } from '../config/crops';
import { PRIORITY_IDS } from '../config/priorities';

/**
 * Everything the farmer sets on the page. It lives in the URL hash (#crops=…&n=…&w=…&r=…&cv=1), so the page can be
 * reloaded or shared. Every change reloads the data from the explorer API.
 */
export interface LatLon { lat: number; lon: number }

export interface PageState {
  crops: string[]; // main crops the picks may use
  count: number; // number of picks shown besides your rotation (fixed: COUNT_MAX, no control on the page)
  weights: Record<string, number>; // priority id -> 1..5
  rotation: string[] | null; // the rotation built in step 2; null = the one from the crop history
  cover: boolean[]; // per gap of the built rotation (gap i = after year i): cover crop there
  tab: Tab; // the dashboard tab on screen
}

export const TABS = ['field', 'plan', 'compare', 'data'] as const;
export type Tab = (typeof TABS)[number];

/** Main crops the scorer can rotate. The cover crop is not offered: the scorer adds it in the gaps where it fits. */
export const CROP_IDS = Object.keys(CROP_LABELS).filter((id) => id !== COVER_CROP);
export { PRIORITY_IDS };
export const WEIGHT_MIN = 1;
export const WEIGHT_MAX = 5;
export const COUNT_MIN = 1;
export const COUNT_MAX = 3; // the explorer returns at most 3 picks
export const ROTATION_LENGTH = 3; // the scorer ranks rotations of three crops

/** Map start position (Kearny County, Kansas). The map is illustration only; the data is for this field. */
export const DEFAULT_LOCATION: LatLon = { lat: 38.02511, lon: -101.126084 };

const clamp = (v: number, lo: number, hi: number) => Math.min(hi, Math.max(lo, v));

export const defaultState = (): PageState => ({
  crops: [...CROP_IDS],
  count: COUNT_MAX,
  weights: Object.fromEntries(PRIORITY_IDS.map((id) => [id, 3])),
  rotation: null,
  cover: noCover(),
  tab: 'field',
});

/** No cover crop in any gap. There is no gap after the last year: that is outside the rotation's window. */
export const noCover = () => Array<boolean>(ROTATION_LENGTH - 1).fill(false);

/**
 * Rotation key as the scorer writes it: "corn-soybean-sorghum", with a cover in every gap "+triticale",
 * in some gaps "+triticale_1" (only after year 1). The API scores the latter on request.
 */
export function rotationKey(crops: string[], cover: boolean[]): string {
  const on = cover.map((c, i) => (c ? i + 1 : 0)).filter(Boolean);
  if (!on.length) return crops.join('-');
  return crops.join('-') + (on.length === cover.length ? `+${COVER_CROP}` : `+${COVER_CROP}_${on.join('')}`);
}

/** Query string for the explorer API. Leaves out the tab: switching tabs never reloads. */
export function apiQuery(s: Pick<PageState, 'crops' | 'count' | 'weights' | 'rotation' | 'cover'>): string {
  const q = new URLSearchParams();
  q.set('crops', s.crops.join(','));
  q.set('n', String(s.count));
  q.set('w', Object.entries(s.weights).map(([id, w]) => `${id}:${w}`).join(','));
  if (s.rotation) q.set('rotation', rotationKey(s.rotation, s.cover));
  return q.toString();
}

function toHash(s: PageState): string {
  const q = new URLSearchParams();
  q.set('crops', s.crops.join(','));
  q.set('w', Object.entries(s.weights).map(([id, w]) => `${id}:${w}`).join(','));
  if (s.rotation) { q.set('r', s.rotation.join('-')); if (s.cover.some(Boolean)) q.set('cv', s.cover.map((c) => (c ? '1' : '0')).join('')); }
  if (s.tab !== 'field') q.set('tab', s.tab);
  return `#${q.toString()}`;
}

function fromHash(hash: string): PageState {
  const s = defaultState();
  const q = new URLSearchParams(hash.replace(/^#\/?(results)?\??/, ''));
  if (q.has('crops')) {
    const crops = (q.get('crops') ?? '').split(',').filter((c) => CROP_IDS.includes(c));
    if (crops.length) s.crops = crops;
  }
  for (const pair of (q.get('w') ?? '').split(',').filter(Boolean)) {
    const [id, w] = pair.split(':');
    if (PRIORITY_IDS.includes(id) && Number.isFinite(Number(w))) s.weights[id] = clamp(Math.round(Number(w)), WEIGHT_MIN, WEIGHT_MAX);
  }
  const r = (q.get('r') ?? '').split('-').filter((c) => CROP_IDS.includes(c));
  if (r.length === ROTATION_LENGTH) {
    s.rotation = r;
    const cv = q.get('cv') ?? '';
    s.cover = noCover().map((_, i) => (cv === '1' ? true : cv[i] === '1')); // "1" from older links = every gap
  }
  const tab = q.get('tab') === 'season' ? 'plan' : q.get('tab'); // the season view now lives on the Plan tab
  if (tab && (TABS as readonly string[]).includes(tab)) s.tab = tab as Tab;
  return s;
}

/** Page state backed by the URL hash. replaceState: editing does not fill the browser history. */
export function usePageState(): [PageState, (update: (s: PageState) => PageState) => void] {
  const [state, setState] = useState(() => fromHash(window.location.hash));
  useEffect(() => {
    const on = () => setState(fromHash(window.location.hash));
    window.addEventListener('hashchange', on);
    return () => window.removeEventListener('hashchange', on);
  }, []);
  const update = useCallback((f: (s: PageState) => PageState) => {
    setState((s) => { const next = f(s); history.replaceState(null, '', toHash(next)); return next; });
  }, []);
  return [state, update];
}
