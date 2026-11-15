/**
 * Microsoft Planetary Computer: public STAC catalogue plus anonymous, short-lived read tokens for its cloud-optimised GeoTIFFs.
 * No account and no API key; the endpoints answer with CORS headers, so the browser can query them directly.
 */
const API = 'https://planetarycomputer.microsoft.com/api';

export interface StacItem {
  id: string;
  properties: Record<string, unknown>;
  assets: Record<string, { href: string; 'classification:classes'?: { value: number; description: string }[] }>;
}

export async function stacSearch(body: object, signal?: AbortSignal): Promise<StacItem[]> {
  const res = await fetch(`${API}/stac/v1/search`, { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify(body), signal });
  if (!res.ok) throw new Error(`Planetary Computer search failed (HTTP ${res.status})`);
  return ((await res.json()) as { features: StacItem[] }).features;
}

const tokens = new Map<string, Promise<string>>();

/** Query string that has to be appended to a blob URL of the given collection. Cached for the session (tokens last about an hour). */
export function sasToken(collection: string): Promise<string> {
  let t = tokens.get(collection);
  if (!t) {
    t = fetch(`${API}/sas/v1/token/${collection}`)
      .then((r) => { if (!r.ok) throw new Error(`Planetary Computer token failed (HTTP ${r.status})`); return r.json() as Promise<{ token: string }>; })
      .then((j) => j.token);
    t.catch(() => tokens.delete(collection));
    tokens.set(collection, t);
  }
  return t;
}

export const signed = async (collection: string, href: string) => `${href}?${await sasToken(collection)}`;
