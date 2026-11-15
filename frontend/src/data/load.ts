import { useEffect, useState } from 'react';
import type { ApiExplorer, ExplorerData } from '../types';
import { normalize } from './normalize';

/**
 * Where the data comes from. Default: the explorer API (`uv run python -m explorer.api`, proxied by Vite under /api).
 * It runs the scorer ranking and the explorer for the page state, sent as query parameters:
 * crops=corn,soybean&n=3&w=water:5,risk:3,soil_health:3,nitrogen:2&rotation=corn-soybean-sorghum%2Btriticale
 * Set VITE_EXPLORER_DATA_URL to use another source, e.g. a static explorer.json (it then ignores the inputs).
 */
export const DATA_URL: string = import.meta.env.VITE_EXPLORER_DATA_URL ?? '/api/explorer';
const DEBOUNCE_MS = 250; // sliders fire on every step; wait until they rest

async function readError(r: Response): Promise<string> {
  try { const body = (await r.json()) as { error?: string }; if (body.error) return body.error; } catch { /* not JSON */ }
  return r.status === 502 || r.status === 504 || r.status === 500
    ? 'The explorer API is not running. Start it in the repo root with: uv run python -m explorer.api'
    : `${r.status} ${r.statusText} (${DATA_URL})`;
}

/** The last good data stays on screen while new data loads or when a request fails. */
export interface DataState { data: ExplorerData | null; loading: boolean; error: string | null }

export function useExplorerData(query: string, weights: Record<string, number>): DataState {
  const [state, setState] = useState<DataState>({ data: null, loading: true, error: null });
  useEffect(() => {
    const ctrl = new AbortController();
    const timer = setTimeout(() => {
      setState((s) => ({ ...s, loading: true }));
      fetch(`${DATA_URL}${DATA_URL.includes('?') ? '&' : '?'}${query}`, { signal: ctrl.signal, headers: { Accept: 'application/json' } })
        .then(async (r) => { if (!r.ok) throw new Error(await readError(r)); return r.json() as Promise<ApiExplorer>; })
        .then((raw) => setState({ data: normalize(raw, weights), loading: false, error: null }))
        .catch((e: unknown) => { if (!ctrl.signal.aborted) setState((s) => ({ ...s, loading: false, error: e instanceof Error ? e.message : String(e) })); });
    }, DEBOUNCE_MS);
    return () => { clearTimeout(timer); ctrl.abort(); };
  }, [query, weights]);
  return state;
}
