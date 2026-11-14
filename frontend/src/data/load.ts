import { useEffect, useState } from 'react';
import type { ExplorerData, RawExplorerData } from '../types';
import { normalize } from './normalize';

/**
 * Where the data comes from. Set VITE_EXPLORER_DATA_URL (e.g. the scorer API) to switch the source.
 * Default: the static mock in public/data/explorer.json. The response must match RawExplorerData in types.ts.
 */
export const DATA_URL: string = import.meta.env.VITE_EXPLORER_DATA_URL ?? `${import.meta.env.BASE_URL}data/explorer.json`;

export type DataState = { status: 'loading' } | { status: 'error'; error: string } | { status: 'ready'; data: ExplorerData };

export function useExplorerData(): DataState {
  const [state, setState] = useState<DataState>({ status: 'loading' });
  useEffect(() => {
    const ctrl = new AbortController();
    fetch(DATA_URL, { signal: ctrl.signal, headers: { Accept: 'application/json' } })
      .then((r) => { if (!r.ok) throw new Error(`${r.status} ${r.statusText}`); return r.json() as Promise<RawExplorerData>; })
      .then((raw) => setState({ status: 'ready', data: normalize(raw) }))
      .catch((e: unknown) => { if (!ctrl.signal.aborted) setState({ status: 'error', error: e instanceof Error ? e.message : String(e) }); });
    return () => ctrl.abort();
  }, []);
  return state;
}
