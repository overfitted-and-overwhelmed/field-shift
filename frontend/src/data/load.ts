import { useEffect, useState } from 'react';
import { toQuery, type FieldRequest } from '../lib/request';
import type { ApiExplorer, ExplorerData } from '../types';
import { normalize } from './normalize';

/**
 * Where the data comes from. Default: the explorer API (`uv run python -m explorer.api`, proxied by Vite under /api).
 * It runs the scorer ranking and the explorer for the form inputs, sent as query parameters:
 * lat=38.02511&lon=-101.12608&crops=corn,soybean&n=3&w=water:5,risk:3,soil_health:3,nitrogen:2
 * Set VITE_EXPLORER_DATA_URL to use another source, e.g. a static explorer.json (it then ignores the inputs).
 */
export const DATA_URL: string = import.meta.env.VITE_EXPLORER_DATA_URL ?? '/api/explorer';

/** Keeps the best `count` options (sorted by pick) plus today's rotation. */
function limitOptions(data: ExplorerData, count: number): ExplorerData {
  const options = data.options.slice(0, count);
  return { ...data, options, rotations: data.rotations.filter((r) => r.is_current || options.includes(r)) };
}

async function readError(r: Response): Promise<string> {
  try { const body = (await r.json()) as { error?: string }; if (body.error) return body.error; } catch { /* not JSON */ }
  return r.status === 502 || r.status === 504 ? 'The explorer API is not running. Start it with: uv run python -m explorer.api' : `${r.status} ${r.statusText}`;
}

export type DataState = { status: 'loading' } | { status: 'error'; error: string } | { status: 'ready'; data: ExplorerData };

export function useExplorerData(req: FieldRequest): DataState {
  const [state, setState] = useState<DataState>({ status: 'loading' });
  useEffect(() => {
    const ctrl = new AbortController();
    const url = `${DATA_URL}${DATA_URL.includes('?') ? '&' : '?'}${toQuery(req)}`;
    fetch(url, { signal: ctrl.signal, headers: { Accept: 'application/json' } })
      .then(async (r) => { if (!r.ok) throw new Error(await readError(r)); return r.json() as Promise<ApiExplorer>; })
      .then((raw) => setState({ status: 'ready', data: limitOptions(normalize(raw, req.weights), req.count) }))
      .catch((e: unknown) => { if (!ctrl.signal.aborted) setState({ status: 'error', error: e instanceof Error ? e.message : String(e) }); });
    return () => ctrl.abort();
  }, [req]);
  return state;
}
