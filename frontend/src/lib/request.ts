import { useEffect, useState } from 'react';
import { CROP_LABELS } from '../config/crops';
import { PRIORITY_LABELS } from '../config/priorities';

/**
 * What the farmer enters on the start page. It lives in the URL hash (#/results?crops=…&n=…&w=…),
 * so a results page can be reloaded or shared. No router library needed.
 */
export interface FieldRequest {
  crops: string[]; // crop ids the farmer can grow
  count: number; // how many crop rotations to predict (options shown besides today's rotation)
  weights: Record<string, number>; // priority id -> 1..5
}

export const CROP_IDS = Object.keys(CROP_LABELS);
export const PRIORITY_IDS = Object.keys(PRIORITY_LABELS);
export const WEIGHT_MIN = 1;
export const WEIGHT_MAX = 5;
export const COUNT_MIN = 1;
export const COUNT_MAX = 5;

const clamp = (v: number, lo: number, hi: number) => Math.min(hi, Math.max(lo, v));

export const emptyRequest = (): FieldRequest => ({
  crops: [],
  count: 3,
  weights: Object.fromEntries(PRIORITY_IDS.map((id) => [id, 3])),
});

/** Query string for the URL hash and for the data request to the scorer. */
export function toQuery(req: FieldRequest): string {
  const q = new URLSearchParams();
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
  const weights: Record<string, number> = {};
  for (const pair of (q.get('w') ?? '').split(',').filter(Boolean)) {
    const [id, w] = pair.split(':');
    const n = Number(w);
    if (id && Number.isFinite(n)) weights[id] = clamp(Math.round(n), WEIGHT_MIN, WEIGHT_MAX);
  }
  if (!crops.length || !Number.isInteger(count) || count < COUNT_MIN) return null;
  if (!Object.keys(weights).length) return null;
  return { crops, count: clamp(count, COUNT_MIN, COUNT_MAX), weights };
}

export type Route = { page: 'form'; prefill: FieldRequest | null } | { page: 'results'; req: FieldRequest };

function parseHash(hash: string): Route {
  const [path, qs = ''] = hash.replace(/^#/, '').split('?');
  const req = fromQuery(qs);
  if (path === '/results' && req) return { page: 'results', req };
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
