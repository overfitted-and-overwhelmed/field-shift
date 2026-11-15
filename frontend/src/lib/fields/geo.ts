import proj4 from 'proj4';

/** USDA CDL tiles use NAD83 / Conus Albers (EPSG:5070). Sentinel-2 uses WGS84 / UTM north (EPSG:326zz). */
proj4.defs('EPSG:5070', '+proj=aea +lat_0=23 +lon_0=-96 +lat_1=29.5 +lat_2=45.5 +x_0=0 +y_0=0 +datum=NAD83 +units=m +no_defs');

export type XY = [number, number];

export const toAlbers = (lon: number, lat: number) => proj4('EPSG:4326', 'EPSG:5070', [lon, lat]) as XY;
export const fromAlbers = (x: number, y: number) => proj4('EPSG:5070', 'EPSG:4326', [x, y]) as XY; // -> [lon, lat]

/** Registers (once) and returns the proj4 code of a UTM-north EPSG number such as 32614. */
export function utmCode(epsg: number): string {
  const code = `EPSG:${epsg}`;
  if (!(proj4 as unknown as { defs: (c: string) => unknown }).defs(code)) {
    if (epsg < 32601 || epsg > 32660) throw new Error(`Unsupported Sentinel-2 projection ${code}`);
    proj4.defs(code, `+proj=utm +zone=${epsg - 32600} +datum=WGS84 +units=m +no_defs`);
  }
  return code;
}

export const mercatorTo = (code: string, x: number, y: number) => proj4('EPSG:3857', code, [x, y]) as XY;
export const lonLatToMercator = (lon: number, lat: number) => proj4('EPSG:4326', 'EPSG:3857', [lon, lat]) as XY;
export const mercatorToLonLat = (x: number, y: number) => proj4('EPSG:3857', 'EPSG:4326', [x, y]) as XY;

/**
 * Maps pixels of a square Web-Mercator output grid (origin mx0/my0, `step` metres, `size` px) to another projection.
 * proj4 runs exactly on a coarse lattice and the pixels in between are interpolated bilinearly: the error stays in the
 * centimetre range over a few kilometres and it is ~100x faster than a proj4 call per pixel.
 */
export function gridMapper(code: string, mx0: number, my0: number, step: number, size: number, n = 32): (i: number, j: number) => XY {
  const k = n + 1, xs = new Float64Array(k * k), ys = new Float64Array(k * k);
  for (let a = 0; a < k; a++) for (let b = 0; b < k; b++) {
    const [x, y] = mercatorTo(code, mx0 + ((b * size) / n) * step, my0 - ((a * size) / n) * step);
    xs[a * k + b] = x; ys[a * k + b] = y;
  }
  return (i, j) => {
    const u = ((i + 0.5) * n) / size, v = ((j + 0.5) * n) / size;
    const b = Math.min(n - 1, Math.floor(u)), a = Math.min(n - 1, Math.floor(v)), fu = u - b, fv = v - a, o = a * k + b;
    const lerp = (g: Float64Array) => (g[o] * (1 - fu) + g[o + 1] * fu) * (1 - fv) + (g[o + k] * (1 - fu) + g[o + k + 1] * fu) * fv;
    return [lerp(xs), lerp(ys)];
  };
}
