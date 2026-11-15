import { useEffect, useState } from 'react';
import { CROP_LABELS } from '../config/crops';
import { PRIORITY_IDS } from '../config/priorities';

/**
 * What the farmer enters on the start page. It lives in the URL hash (#/results?crops=…&n=…&w=…),
 * so a results page can be reloaded or shared. No router library needed.
 */
export interface LatLon { lat: number; lon: number }

export interface FieldRequest {
  location: LatLon | null; // field position, picked on the map; required for results
  crops: string[]; // crop ids the farmer can grow
  count: number; // how many crop rotations to predict (options shown besides today's rotation)
  weights: Record<string, number>; // priority id -> 1..5
}

/** Main crops the scorer can rotate. Triticale is not offered: the scorer adds it as a cover crop where it fits. */
export const CROP_IDS = Object.keys(CROP_LABELS).filter((id) => id !== 'triticale');
export { PRIORITY_IDS };
export const WEIGHT_MIN = 1;
export const WEIGHT_MAX = 5;
export const COUNT_MIN = 1;
export const COUNT_MAX = 3; // the explorer returns at most 3 picks

const clamp = (v: number, lo: number, hi: number) => Math.min(hi, Math.max(lo, v));

/** Preselected field position (Kearny County, Kansas). The user can click elsewhere on the map. */
export const DEFAULT_LOCATION: LatLon = { lat: 38.02511, lon: -101.126084 };

export const emptyRequest = (): FieldRequest => ({
  location: DEFAULT_LOCATION,
  crops: [],
  count: 3,
  weights: Object.fromEntries(PRIORITY_IDS.map((id) => [id, 3])),
});

/** Query string for the URL hash and for the data request to the scorer. */
export function toQuery(req: FieldRequest): string {
  const q = new URLSearchParams();
  if (req.location) { q.set('lat', req.location.lat.toFixed(5)); q.set('lon', req.location.lon.toFixed(5)); }
  q.set('crops', req.crops.join(','));
  q.set('n', String(req.count));
  q.set('w', Object.entries(req.weights).map(([id, w]) => `${id}:${w}`).join(','));
  return q.toString();
}

/** Parses a query string. Returns null if it does not describe a complete request. */
export function fromQuery(qs: string): FieldRequest | null {
  const q = new URLSearchParams(qs);
  const crops = (q.get('crops') ?? '').split(',').filter(Boolean);
  const count = Number(q.get('n'));
  const lat = Number(q.get('lat')), lon = Number(q.get('lon'));
  const location = q.has('lat') && q.has('lon') && Math.abs(lat) <= 90 && Math.abs(lon) <= 180 ? { lat, lon } : null;
  const weights: Record<string, number> = {};
  for (const pair of (q.get('w') ?? '').split(',').filter(Boolean)) {
    const [id, w] = pair.split(':');
    const n = Number(w);
    if (id && PRIORITY_IDS.includes(id) && Number.isFinite(n)) weights[id] = clamp(Math.round(n), WEIGHT_MIN, WEIGHT_MAX);
  }
  if (!crops.length || !Number.isInteger(count) || count < COUNT_MIN) return null;
  if (!Object.keys(weights).length) return null;
  return { location, crops, count: clamp(count, COUNT_MIN, COUNT_MAX), weights };
}

export type Route = { page: 'form'; prefill: FieldRequest | null } | { page: 'results'; req: FieldRequest & { location: LatLon } };

function parseHash(hash: string): Route {
  const [path, qs = ''] = hash.replace(/^#/, '').split('?');
  const req = fromQuery(qs);
  if (path === '/results' && req?.location) return { page: 'results', req: { ...req, location: req.location } };
  return { page: 'form', prefill: req };
}

export const goResults = (req: FieldRequest) => { window.location.hash = `/results?${toQuery(req)}`; };
export const goForm = (req?: FieldRequest) => { window.location.hash = req ? `/?${toQuery(req)}` : '/'; };

export function useRoute(): Route {
  const [route, setRoute] = useState(() => parseHash(window.location.hash));
  useEffect(() => {
    const on = () => { setRoute(parseHash(window.location.hash)); window.scrollTo(0, 0); };
    window.addEventListener('hashchange', on);
    return () => window.removeEventListener('hashchange', on);
  }, []);
  return route;
}
