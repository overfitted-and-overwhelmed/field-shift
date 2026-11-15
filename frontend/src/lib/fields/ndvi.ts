import { fromUrl } from 'geotiff';
import type { LatLon } from '../request';
import { gridMapper, lonLatToMercator, mercatorToLonLat, utmCode } from './geo';
import { sasToken, signed, stacSearch, type StacItem } from './stac';
import type { Surroundings } from './surroundings';

/**
 * NDVI from real Sentinel-2 L2A scenes (ESA, 10 m, every ~5 days), read from Planetary Computer: NDVI = (B08 − B04) / (B08 + B04).
 * Clouds, cloud shadow, snow and saturated pixels are masked with the scene's own classification (SCL). The raster is resampled onto a
 * north-up Web-Mercator grid so Leaflet can lay it over the map, then clipped to the field outlines.
 */
const SIZE = 512;
const WINDOW_DAYS = 160;

export interface Scene { id: string; date: string; cloud: number; item: StacItem }
export interface NdviResult {
  url: string; // PNG (data URL) with transparent background
  bounds: [[number, number], [number, number]]; // [[south, west], [north, east]]
  means: Record<string, number | null>; // field id -> mean NDVI (null if too little clear sky)
  scene: Scene;
}

export async function findScenes(center: LatLon, signal?: AbortSignal): Promise<Scene[]> {
  const to = new Date();
  const from = new Date(to.getTime() - WINDOW_DAYS * 864e5);
  void sasToken('sentinel-2-l2a').catch(() => {});
  const items = await stacSearch({
    collections: ['sentinel-2-l2a'], intersects: { type: 'Point', coordinates: [center.lon, center.lat] },
    datetime: `${from.toISOString().slice(0, 10)}/${to.toISOString().slice(0, 10)}`, query: { 'eo:cloud_cover': { lt: 35 } },
    sortby: [{ field: 'datetime', direction: 'desc' }], limit: 60,
  }, signal);
  const byDate = new Map<string, Scene>();
  for (const item of items) {
    const date = String(item.properties.datetime).slice(0, 10);
    const cloud = Number(item.properties['eo:cloud_cover']);
    const cur = byDate.get(date);
    if (!cur || cloud < cur.cloud) byDate.set(date, { id: item.id, date, cloud, item });
  }
  return [...byDate.values()].sort((a, b) => b.date.localeCompare(a.date)).slice(0, 12);
}

/** Light yellow (bare soil / stubble) to deep green (dense canopy). */
const STOPS: [number, [number, number, number]][] = [
  [0.0, [248, 250, 168]], [0.15, [230, 242, 140]], [0.3, [188, 226, 100]], [0.45, [112, 197, 78]],
  [0.6, [52, 164, 84]], [0.75, [16, 118, 62]], [0.9, [5, 78, 40]],
];
export function ndviRgb(v: number): [number, number, number] {
  if (v <= STOPS[0][0]) return STOPS[0][1];
  for (let i = 1; i < STOPS.length; i++) {
    if (v <= STOPS[i][0]) {
      const [a, ca] = STOPS[i - 1], [b, cb] = STOPS[i], t = (v - a) / (b - a);
      return [0, 1, 2].map((k) => Math.round(ca[k] + (cb[k] - ca[k]) * t)) as [number, number, number];
    }
  }
  return STOPS[STOPS.length - 1][1];
}
export const ndviCss = (v: number) => `rgb(${ndviRgb(v).join(',')})`;
/** Colour ramp as a CSS gradient, for the legend. */
export const NDVI_GRADIENT = `linear-gradient(90deg, ${STOPS.map(([v, c]) => `rgb(${c.join(',')}) ${(v / 0.9) * 100}%`).join(', ')})`;

// pixel -> field label on the output grid, computed once per surroundings
const labelMaps = new WeakMap<Surroundings, { mx0: number; my0: number; step: number; labels: Uint16Array; bounds: NdviResult['bounds'] }>();

function labelMap(s: Surroundings) {
  let m = labelMaps.get(s);
  if (m) return m;
  const [cx, cy] = lonLatToMercator(s.center.lon, s.center.lat);
  const half = (3000 / Math.cos((s.center.lat * Math.PI) / 180)) * 1.02;
  const mx0 = cx - half, my0 = cy + half, step = (2 * half) / SIZE;
  const { grid } = s;
  const labels = new Uint16Array(SIZE * SIZE);
  const toAlbers = gridMapper('EPSG:5070', mx0, my0, step, SIZE);
  for (let j = 0; j < SIZE; j++) for (let i = 0; i < SIZE; i++) {
    const [ax, ay] = toAlbers(i, j);
    const c = Math.floor((ax - grid.ox) / 30) - grid.px0, r = Math.floor((grid.oy - ay) / 30) - grid.py0;
    if (c >= 0 && r >= 0 && c < grid.w && r < grid.h) labels[j * SIZE + i] = grid.labels[r * grid.w + c];
  }
  const [w, n] = mercatorToLonLat(mx0, my0), [e, sth] = mercatorToLonLat(mx0 + 2 * half, my0 - 2 * half);
  m = { mx0, my0, step, labels, bounds: [[sth, w], [n, e]] };
  labelMaps.set(s, m);
  return m;
}

const BAD_SCL = new Set([0, 1, 3, 8, 9, 10, 11]); // no data, saturated, shadow, cloud (medium/high), cirrus, snow

export async function renderNdvi(s: Surroundings, scene: Scene, signal?: AbortSignal): Promise<NdviResult> {
  const lm = labelMap(s);
  const epsg = Number(scene.item.properties['proj:epsg']);
  const code = utmCode(epsg);
  const offset = parseFloat(String(scene.item.properties['s2:processing_baseline'] ?? '0')) >= 4 ? 1000 : 0; // L2A baseline >= 04.00 adds +1000 to DN

  const [b4, b8, scl] = await Promise.all(['B04', 'B08', 'SCL'].map(async (a) => fromUrl(await signed('sentinel-2-l2a', scene.item.assets[a].href))));
  const i4 = await b4.getImage();
  const [ox, oy] = i4.getOrigin();

  // where does every output pixel fall in the Sentinel-2 grid?
  const toUtm = gridMapper(code, lm.mx0, lm.my0, lm.step, SIZE);
  const cols = new Int32Array(SIZE * SIZE), rows = new Int32Array(SIZE * SIZE);
  let cmin = Infinity, cmax = -Infinity, rmin = Infinity, rmax = -Infinity;
  for (let j = 0; j < SIZE; j++) for (let i = 0; i < SIZE; i++) {
    const [x, y] = toUtm(i, j);
    const c = Math.floor((x - ox) / 10), r = Math.floor((oy - y) / 10), k = j * SIZE + i;
    cols[k] = c; rows[k] = r;
    if (c < cmin) cmin = c; if (c > cmax) cmax = c; if (r < rmin) rmin = r; if (r > rmax) rmax = r;
  }
  const W = i4.getWidth(), H = i4.getHeight();
  const c0 = Math.max(0, cmin), r0 = Math.max(0, rmin), c1 = Math.min(W, cmax + 1), r1 = Math.min(H, rmax + 1);
  if (c1 <= c0 || r1 <= r0) throw new Error('This Sentinel-2 scene does not cover the fields.');
  const ww = c1 - c0;
  const sc0 = c0 >> 1, sr0 = r0 >> 1, sc1 = (c1 >> 1) + 1, sr1 = (r1 >> 1) + 1;
  const sclImg = await scl.getImage();
  const sw = Math.min(sclImg.getWidth(), sc1) - sc0; // row stride of the SCL window actually read
  const [red, nir, cls] = await Promise.all([
    b4.readRasters({ window: [c0, r0, c1, r1], signal }),
    b8.readRasters({ window: [c0, r0, c1, r1], signal }),
    scl.readRasters({ window: [sc0, sr0, Math.min(sclImg.getWidth(), sc1), Math.min(sclImg.getHeight(), sr1)], signal }),
  ]) as unknown as [ArrayLike<number>[], ArrayLike<number>[], ArrayLike<number>[]];
  const R = red[0], N = nir[0], C = cls[0];

  const canvas = document.createElement('canvas');
  canvas.width = canvas.height = SIZE;
  const ctx = canvas.getContext('2d')!;
  const img = ctx.createImageData(SIZE, SIZE);
  const sum = new Float64Array(s.fields.length + 1), cnt = new Uint32Array(s.fields.length + 1), tot = new Uint32Array(s.fields.length + 1);
  for (let k = 0; k < SIZE * SIZE; k++) {
    const c = cols[k] - c0, r = rows[k] - r0;
    const lab = lm.labels[k];
    if (lab) tot[lab]++;
    if (c < 0 || r < 0 || c >= ww || r >= r1 - r0) continue;
    const sclv = C[((rows[k] >> 1) - sr0) * sw + ((cols[k] >> 1) - sc0)];
    if (BAD_SCL.has(sclv)) continue;
    const red_ = R[r * ww + c] - offset, nir_ = N[r * ww + c] - offset;
    if (R[r * ww + c] === 0 || nir_ + red_ <= 0) continue;
    const v = Math.max(-1, Math.min(1, (nir_ - red_) / (nir_ + red_)));
    const [cr, cg, cb] = ndviRgb(v);
    img.data.set([cr, cg, cb, 255], k * 4);
    if (lab) { sum[lab] += v; cnt[lab]++; }
  }
  ctx.putImageData(img, 0, 0);

  // clip to the smooth field outlines
  const clip = document.createElement('canvas');
  clip.width = clip.height = SIZE;
  const cctx = clip.getContext('2d')!;
  cctx.beginPath();
  for (const f of s.fields) {
    f.ring.forEach(([lat, lon], i) => {
      const [mx, my] = lonLatToMercator(lon, lat);
      const x = (mx - lm.mx0) / lm.step, y = (lm.my0 - my) / lm.step;
      if (i) cctx.lineTo(x, y); else cctx.moveTo(x, y);
    });
    cctx.closePath();
  }
  cctx.fillStyle = '#000';
  cctx.fill();
  ctx.globalCompositeOperation = 'destination-in';
  ctx.drawImage(clip, 0, 0);

  const means: Record<string, number | null> = {};
  s.fields.forEach((f, n) => { const l = n + 1; means[f.id] = cnt[l] && cnt[l] / (tot[l] || 1) >= 0.3 ? sum[l] / cnt[l] : null; });
  return { url: canvas.toDataURL('image/png'), bounds: lm.bounds, means, scene };
}
