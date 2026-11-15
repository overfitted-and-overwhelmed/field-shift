import { useEffect, useState } from 'react';
import { toQuery, type FieldRequest } from '../lib/request';
import type { ExplorerData, RawExplorerData } from '../types';
import { normalize } from './normalize';

/**
 * Where the data comes from. Set VITE_EXPLORER_DATA_URL (e.g. the scorer API) to switch the source.
 * Default: the static mock in public/data/explorer.json. The response must match RawExplorerData in types.ts.
 * The form inputs are sent as query parameters: lat=38.02511&lon=-101.12608&crops=corn,soybean&n=3&w=water:5,profit:4,…
 * The weights entered by the user override the ones in the response.
 */
export const DATA_URL: string = import.meta.env.VITE_EXPLORER_DATA_URL ?? `${import.meta.env.BASE_URL}data/explorer.json`;

/** Keeps the best `count` options (they are sorted by pick) plus today's rotation. */
function limitOptions(data: ExplorerData, count: number): ExplorerData {
  const options = data.options.slice(0, count);
  return { ...data, options, rotations: data.rotations.filter((r) => r.is_current || options.includes(r)) };
}

export type DataState = { status: 'loading' } | { status: 'error'; error: string } | { status: 'ready'; data: ExplorerData };

export function useExplorerData(req: FieldRequest): DataState {
  const [state, setState] = useState<DataState>({ status: 'loading' });
  useEffect(() => {
    const ctrl = new AbortController();
    const url = `${DATA_URL}${DATA_URL.includes('?') ? '&' : '?'}${toQuery(req)}`;
    fetch(url, { signal: ctrl.signal, headers: { Accept: 'application/json' } })
      .then((r) => { if (!r.ok) throw new Error(`${r.status} ${r.statusText}`); return r.json() as Promise<RawExplorerData>; })
      .then((raw) => setState({ status: 'ready', data: limitOptions(normalize({ ...raw, weights: req.weights }), req.count) }))
      .catch((e: unknown) => { if (!ctrl.signal.aborted) setState({ status: 'error', error: e instanceof Error ? e.message : String(e) }); });
    return () => ctrl.abort();
  }, [req]);
  return state;
}
