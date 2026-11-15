import { fromUrl } from 'geotiff';
import type { LatLon } from '../request';
import { isCrop } from './cdl';
import { fromAlbers, toAlbers, type XY } from './geo';
import { sasToken, signed, stacSearch } from './stac';

/**
 * Fields around a coordinate, from real data: the USDA NASS Cropland Data Layer (30 m crop map, one per year) read straight from
 * Planetary Computer. A field is a connected patch of one crop in the latest year; its outline is traced from the raster and smoothed.
 * Every field also carries its crop in each earlier year (majority of its pixels), which is the observed rotation history.
 * Limit: the CDL knows crops per pixel, not legal parcels. Two neighbouring fields of the same crop in the same year merge into one patch.
 */
const RADIUS_PX = 100; // 100 px * 30 m = 3 km around the point
const MIN_PIXELS = 30; // ~2.7 ha; smaller patches are edge noise or farmsteads
const PX = 30; // CDL pixel size in metres

export interface FieldYear { year: number; cls: number }
export interface Field {
  id: string;
  label: string; // "Your field", "Field 2", …
  ring: [number, number][]; // [lat, lon] outline
  cls: number; // CDL class in `Surroundings.year`
  ha: number;
  labelPos: [number, number]; // [lat, lon] spot inside the field for a label
  distM: number; // from the picked point to the nearest pixel of the field
  own: boolean; // contains the picked point
  history: FieldYear[]; // oldest first
  pixels: number;
}

export interface Surroundings {
  center: LatLon;
  year: number; // CDL year used for the field patches
  years: number[]; // all CDL years read
  fields: Field[];
  ownId: string | null;
  pointClass: number | null; // CDL class at the picked point, in `year`
  /** Raster geometry, needed to relate other rasters (Sentinel-2) to the field patches. */
  grid: { px0: number; py0: number; w: number; h: number; ox: number; oy: number; labels: Uint16Array };
}

type Raster = Uint8Array & { width?: number };

async function readYear(href: string, win: [number, number, number, number], signal?: AbortSignal): Promise<Uint8Array> {
  const tif = await fromUrl(await signed('usda-cdl', href), { allowFullFile: false });
  const r = (await tif.readRasters({ window: win, signal, interleave: false })) as unknown as Raster[];
  return Uint8Array.from(r[0]);
}

export async function loadSurroundings(center: LatLon, signal?: AbortSignal): Promise<Surroundings> {
  void sasToken('usda-cdl').catch(() => {}); // start the token request now, in parallel with the search
  const items = await stacSearch({
    collections: ['usda-cdl'], intersects: { type: 'Point', coordinates: [center.lon, center.lat] }, limit: 60,
  }, signal);
  const byYear = new Map<number, string>();
  for (const it of items) {
    const y = Number(/cropland_(\d{4})_/.exec(it.id)?.[1]);
    if (y && it.assets.cropland) byYear.set(y, it.assets.cropland.href);
  }
  if (!byYear.size) throw new Error('No USDA Cropland Data Layer coverage for this location (it covers the contiguous United States).');
  const years = [...byYear.keys()].sort((a, b) => a - b);
  const year = years[years.length - 1];

  // geometry from the latest tile; all years share the same tile grid
  const first = await fromUrl(await signed('usda-cdl', byYear.get(year)!));
  const img = await first.getImage();
  const [ox, oy] = img.getOrigin();
  const W = img.getWidth(), H = img.getHeight();
  const [ax, ay] = toAlbers(center.lon, center.lat);
  const cx = Math.floor((ax - ox) / PX), cy = Math.floor((oy - ay) / PX);
  const x0 = Math.max(0, cx - RADIUS_PX), x1 = Math.min(W, cx + RADIUS_PX + 1);
  const y0 = Math.max(0, cy - RADIUS_PX), y1 = Math.min(H, cy + RADIUS_PX + 1);
  const w = x1 - x0, h = y1 - y0;
  if (w < 5 || h < 5) throw new Error('This location is at the edge of the data tile.');

  const grids = new Map<number, Uint8Array>();
  await Promise.all(years.map(async (y) => { grids.set(y, await readYear(byYear.get(y)!, [x0, y0, x1, y1], signal)); }));
  const latest = grids.get(year)!;

  const cls = denoise(latest, w, h);
  const { labels, sizes } = label(cls, w, h);
  splitTouching(labels, sizes, w);
  const keep = sizes.map((n, i) => (i > 0 && n >= MIN_PIXELS ? i : 0));
  const px = cx - x0, py = cy - y0;
  const pointClass = px >= 0 && py >= 0 && px < w && py < h ? latest[py * w + px] : null;
  const pointLabel = px >= 0 && py >= 0 && px < w && py < h ? labels[py * w + px] : 0;

  // group pixels by kept label
  const pix = new Map<number, number[]>();
  for (let i = 0; i < labels.length; i++) { const l = labels[i]; if (keep[l]) (pix.get(l) ?? pix.set(l, []).get(l)!).push(i); }

  const raw = [...pix.entries()].map(([l, idx]) => {
    let best = Infinity;
    for (const i of idx) { const dx = (i % w) - px, dy = Math.floor(i / w) - py; best = Math.min(best, Math.hypot(dx, dy)); }
    return { l, idx, dist: l === pointLabel ? 0 : Math.max(0, best - 0.5) * PX };
  }).sort((a, b) => a.dist - b.dist);

  const outLabels = new Uint16Array(w * h);
  const fields: Field[] = raw.map(({ l, idx, dist }, n) => {
    const own = l === pointLabel;
    for (const i of idx) outLabels[i] = n + 1;
    const ring = trace(idx, w).map(([c, r]) => fromAlbers(ox + (x0 + c) * PX, oy - (y0 + r) * PX)).map(([lo, la]) => [la, lo] as [number, number]);
    const lp = labelSpot(idx, w);
    const [llo, lla] = fromAlbers(ox + (x0 + lp[0]) * PX, oy - (y0 + lp[1]) * PX);
    const history = years.map((y) => ({ year: y, cls: mode(grids.get(y)!, idx) }));
    return {
      id: `f${n + 1}`, label: own ? 'Your field' : `Field ${n + 1}`, ring, cls: cls[idx[0]], ha: (idx.length * PX * PX) / 10000,
      labelPos: [lla, llo], distM: dist, own, history, pixels: idx.length,
    };
  });
  // the field with the picked point first, then by distance; numbering follows that order
  let k = 0;
  for (const f of fields) if (!f.own) f.label = `Field ${++k}`;

  return {
    center, year, years, fields, ownId: fields.find((f) => f.own)?.id ?? null, pointClass,
    grid: { px0: x0, py0: y0, w, h, ox, oy, labels: outLabels },
  };
}

/** Removes isolated pixels (mixed pixels at edges). A pixel with at least two like neighbours is kept, so one-pixel roads and field boundaries survive. */
function denoise(src: Uint8Array, w: number, h: number): Uint8Array {
  const out = Uint8Array.from(src);
  const counts = new Map<number, number>();
  for (let y = 1; y < h - 1; y++) for (let x = 1; x < w - 1; x++) {
    counts.clear();
    for (let dy = -1; dy <= 1; dy++) for (let dx = -1; dx <= 1; dx++) { const v = src[(y + dy) * w + x + dx]; counts.set(v, (counts.get(v) ?? 0) + 1); }
    const me = src[y * w + x];
    if ((counts.get(me) ?? 0) >= 3) continue;
    let bv = me, bn = 0;
    for (const [v, n] of counts) if (n > bn) { bv = v; bn = n; }
    if (bn >= 5) out[y * w + x] = bv;
  }
  return out;
}

/** 4-connected components of equal crop class; non-crop pixels get label 0. */
function label(cls: Uint8Array, w: number, h: number) {
  const labels = new Uint16Array(w * h);
  const sizes: number[] = [0];
  let next = 0;
  const stack: number[] = [];
  for (let s = 0; s < cls.length; s++) {
    if (labels[s] || !isCrop(cls[s])) continue;
    next++;
    let n = 0;
    labels[s] = next; stack.push(s);
    while (stack.length) {
      const i = stack.pop()!;
      n++;
      const x = i % w, y = (i - x) / w;
      if (x > 0 && !labels[i - 1] && cls[i - 1] === cls[s]) { labels[i - 1] = next; stack.push(i - 1); }
      if (x < w - 1 && !labels[i + 1] && cls[i + 1] === cls[s]) { labels[i + 1] = next; stack.push(i + 1); }
      if (y > 0 && !labels[i - w] && cls[i - w] === cls[s]) { labels[i - w] = next; stack.push(i - w); }
      if (y < h - 1 && !labels[i + w] && cls[i + w] === cls[s]) { labels[i + w] = next; stack.push(i + w); }
    }
    sizes.push(n);
  }
  return { labels, sizes };
}

function mode(grid: Uint8Array, idx: number[]): number {
  const c = new Map<number, number>();
  for (const i of idx) { const v = grid[i]; if (v) c.set(v, (c.get(v) ?? 0) + 1); }
  let bv = 0, bn = 0;
  for (const [v, n] of c) if (n > bn) { bv = v; bn = n; }
  return bv;
}

/** Pixel inside the patch that is farthest from its boundary, so labels sit in the middle even for odd shapes. */
function labelSpot(idx: number[], w: number): XY {
  const { d, bw, x0, y0, at } = distanceField(idx, w);
  let best = -1, bk = at(idx[0]);
  for (const i of idx) { const k = at(i); if (d[k] > best) { best = d[k]; bk = k; } }
  return [(bk % bw) + x0 - 1 + 0.5, Math.floor(bk / bw) + y0 - 1 + 0.5];
}

/** Outer boundary of a pixel patch as a smoothed ring of [col,row] corner coordinates. */
function trace(idx: number[], w: number): XY[] {
  const set = new Set(idx);
  const has = (x: number, y: number) => set.has(y * w + x);
  const stride = w + 2;
  const key = (x: number, y: number) => y * stride + x;
  const out = new Map<number, [number, number][]>(); // vertex -> list of [toX,toY]
  const add = (ax: number, ay: number, bx: number, by: number) => { const k = key(ax, ay); (out.get(k) ?? out.set(k, []).get(k)!).push([bx, by]); };
  for (const i of idx) {
    const x = i % w, y = (i - x) / w;
    if (!has(x, y - 1)) add(x, y, x + 1, y); // top: left -> right (clockwise on screen)
    if (!has(x + 1, y)) add(x + 1, y, x + 1, y + 1);
    if (!has(x, y + 1)) add(x + 1, y + 1, x, y + 1);
    if (!has(x - 1, y)) add(x, y + 1, x, y);
  }
  const loops: XY[][] = [];
  while (out.size) {
    const startKey = out.keys().next().value as number;
    const sx = startKey % stride, sy = (startKey - sx) / stride;
    const loop: XY[] = [[sx, sy]];
    let cx = sx, cy = sy;
    for (let guard = 0; guard < 200000; guard++) {
      const k = key(cx, cy);
      const nexts = out.get(k);
      if (!nexts || !nexts.length) break;
      const [nx, ny] = nexts.pop()!;
      if (!nexts.length) out.delete(k);
      cx = nx; cy = ny;
      if (cx === sx && cy === sy) break;
      loop.push([cx, cy]);
    }
    if (loop.length >= 4) loops.push(loop);
  }
  const area = (r: XY[]) => Math.abs(r.reduce((s, p, i) => { const q = r[(i + 1) % r.length]; return s + p[0] * q[1] - q[0] * p[1]; }, 0) / 2);
  const outer = loops.sort((a, b) => area(b) - area(a))[0] ?? [];
  return simplify(chaikin(chaikin(outer)), 0.12);
}

function chaikin(r: XY[]): XY[] {
  const o: XY[] = [];
  for (let i = 0; i < r.length; i++) {
    const p = r[i], q = r[(i + 1) % r.length];
    o.push([0.75 * p[0] + 0.25 * q[0], 0.75 * p[1] + 0.25 * q[1]], [0.25 * p[0] + 0.75 * q[0], 0.25 * p[1] + 0.75 * q[1]]);
  }
  return o;
}

/** Douglas–Peucker on a closed ring (split at the two points farthest apart so the ring stays closed). */
function simplify(r: XY[], tol: number): XY[] {
  if (r.length < 8) return r;
  const half = Math.floor(r.length / 2);
  const dp = (pts: XY[]): XY[] => {
    if (pts.length < 3) return pts;
    const [a, b] = [pts[0], pts[pts.length - 1]];
    let md = 0, mi = 0;
    for (let i = 1; i < pts.length - 1; i++) {
      const d = Math.abs((b[0] - a[0]) * (a[1] - pts[i][1]) - (a[0] - pts[i][0]) * (b[1] - a[1])) / (Math.hypot(b[0] - a[0], b[1] - a[1]) || 1);
      if (d > md) { md = d; mi = i; }
    }
    return md > tol ? [...dp(pts.slice(0, mi + 1)).slice(0, -1), ...dp(pts.slice(mi))] : [a, b];
  };
  const p1 = dp(r.slice(0, half + 1)), p2 = dp([...r.slice(half), r[0]]);
  return [...p1.slice(0, -1), ...p2.slice(0, -1)];
}

/**
 * Neighbouring fields of the same crop (typically touching centre-pivot circles) form one connected patch. Split such patches with a
 * distance-transform watershed: every field is a "hill" of distance-to-edge; two hills stay separate only if the pass between them is
 * clearly lower than the smaller hill (a long rectangle has no such pass and stays whole).
 */
const MIN_PEAK_PX = 7; // smallest field radius that may be split off: 7 px = 210 m
const PASS_RATIO = 0.7;

function splitTouching(labels: Uint16Array, sizes: number[], w: number) {
  const groups = new Map<number, number[]>();
  for (let i = 0; i < labels.length; i++) if (labels[i]) (groups.get(labels[i]) ?? groups.set(labels[i], []).get(labels[i])!).push(i);
  for (const [lab, idx] of groups) {
    if (idx.length < 600) continue;
    const parts = splitBlob(idx, w);
    for (let k = 1; k < parts.length; k++) {
      const nl = sizes.length;
      sizes.push(parts[k].length);
      for (const i of parts[k]) labels[i] = nl;
    }
    sizes[lab] = parts[0].length;
  }
}

/** Distance of every pixel of a patch to the nearest outside pixel (3-4 chamfer), on the patch's bounding box plus a one-pixel border. */
function distanceField(idx: number[], W: number) {
  let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
  for (const i of idx) { const x = i % W, y = (i - x) / W; if (x < x0) x0 = x; if (x > x1) x1 = x; if (y < y0) y0 = y; if (y > y1) y1 = y; }
  const bw = x1 - x0 + 3, bh = y1 - y0 + 3;
  const at = (i: number) => ((Math.floor(i / W) - y0 + 1) * bw) + (i % W) - x0 + 1;
  const inside = new Uint8Array(bw * bh);
  for (const i of idx) inside[at(i)] = 1;
  const d = new Float32Array(bw * bh);
  for (let k = 0; k < d.length; k++) d[k] = inside[k] ? 1e6 : 0;
  for (let y = 1; y < bh - 1; y++) for (let x = 1; x < bw - 1; x++) { const k = y * bw + x; if (inside[k]) d[k] = Math.min(d[k], d[k - 1] + 3, d[k - bw] + 3, d[k - bw - 1] + 4, d[k - bw + 1] + 4); }
  for (let y = bh - 2; y >= 1; y--) for (let x = bw - 2; x >= 1; x--) { const k = y * bw + x; if (inside[k]) d[k] = Math.min(d[k], d[k + 1] + 3, d[k + bw] + 3, d[k + bw + 1] + 4, d[k + bw - 1] + 4); }
  for (let k = 0; k < d.length; k++) d[k] /= 3;
  return { d, inside, bw, bh, x0, y0, at };
}

function splitBlob(idx: number[], W: number): number[][] {
  const { d, inside, bw, bh, at } = distanceField(idx, W);
  const cells = idx.map(at).sort((a, b) => d[b] - d[a]);
  const peaks: number[] = [];
  for (const k of cells) {
    if (d[k] < MIN_PEAK_PX) break;
    const x = k % bw, y = (k - x) / bw;
    if (peaks.every((q) => Math.hypot((q % bw) - x, Math.floor(q / bw) - y) >= d[q])) peaks.push(k);
  }
  if (peaks.length < 2) return [idx];

  // flood from the peaks, highest distance first
  const reg = new Int16Array(bw * bh).fill(-1);
  const heap: number[] = [];
  const push = (k: number) => { heap.push(k); let c = heap.length - 1; while (c > 0) { const p = (c - 1) >> 1; if (d[heap[p]] >= d[heap[c]]) break; [heap[p], heap[c]] = [heap[c], heap[p]]; c = p; } };
  const pop = () => { const top = heap[0], last = heap.pop()!; if (heap.length) { heap[0] = last; let c = 0; for (;;) { const l = 2 * c + 1, r = l + 1; let m = c; if (l < heap.length && d[heap[l]] > d[heap[m]]) m = l; if (r < heap.length && d[heap[r]] > d[heap[m]]) m = r; if (m === c) break; [heap[m], heap[c]] = [heap[c], heap[m]]; c = m; } } return top; };
  peaks.forEach((k, r) => { reg[k] = r; push(k); });
  while (heap.length) {
    const k = pop();
    for (const n of [k - 1, k + 1, k - bw, k + bw]) if (inside[n] && reg[n] < 0) { reg[n] = reg[k]; push(n); }
  }

  // merge hills whose pass is almost as high as the smaller hill
  const peakH = peaks.map((k) => d[k]);
  const parent = peaks.map((_, r) => r);
  const find = (r: number): number => (parent[r] === r ? r : (parent[r] = find(parent[r])));
  const pass = new Map<number, number>();
  const n = peaks.length;
  for (const k of cells) for (const q of [k + 1, k + bw]) {
    if (inside[q] && reg[q] !== reg[k]) { const a = Math.min(reg[k], reg[q]), b = Math.max(reg[k], reg[q]), key = a * n + b; pass.set(key, Math.max(pass.get(key) ?? 0, Math.min(d[k], d[q]))); }
  }
  for (;;) {
    let best = 0, bi = -1, bj = -1;
    const agg = new Map<number, number>();
    for (const [key, v] of pass) { const a = find(Math.floor(key / n)), b = find(key % n); if (a !== b) { const kk = Math.min(a, b) * n + Math.max(a, b); agg.set(kk, Math.max(agg.get(kk) ?? 0, v)); } }
    for (const [kk, v] of agg) { const a = Math.floor(kk / n), b = kk % n, ratio = v / Math.min(peakH[a], peakH[b]); if (ratio > best) { best = ratio; bi = a; bj = b; } }
    if (best < PASS_RATIO) break;
    parent[bj] = bi; peakH[bi] = Math.max(peakH[bi], peakH[bj]);
  }

  const out = new Map<number, number[]>();
  for (const i of idx) { const r = find(reg[at(i)]); (out.get(r) ?? out.set(r, []).get(r)!).push(i); }
  return [...out.values()].sort((a, b) => b.length - a.length);
}
