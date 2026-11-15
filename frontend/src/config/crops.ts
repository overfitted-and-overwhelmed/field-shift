/**
 * Crop labels and colors. New crop ids from the scorer need no change: the label is derived from the id,
 * the color is a fallback. To fix a color, define --c-<id> in styles/tokens.css.
 */
export const CROP_LABELS: Record<string, string> = {
  corn: 'Corn', soybean: 'Soybean', winter_wheat: 'Winter wheat', sorghum: 'Sorghum', sunflower: 'Sunflower', triticale: 'Triticale',
};
/** The cover crop the API accepts in a rotation key ("+triticale"). The data names it in `crops[id].is_cover`. */
export const COVER_CROP = 'triticale';
/** The cover crop of the loaded data (the first crop with is_cover), else COVER_CROP. */
export const coverCropOf = (crops: Record<string, { is_cover: boolean }> | undefined) =>
  Object.keys(crops ?? {}).find((id) => crops![id].is_cover) ?? COVER_CROP;

/**
 * The scorer's rotation rule (crop_scorer/scoring/score_rotations.py, NDSU A1995 p. 46): at most one Sclerotinia
 * (white mold) host per three-year pass. Rotations that break it are still scored but ranked behind all others.
 */
export const SCLEROTINIA_HOSTS = ['sunflower', 'soybean'];
export const MAX_SCLEROTINIA_HOSTS = 1;
/** Index of every year whose crop is one host too many (the second host and later); empty if the rule holds. */
export const sclerotiniaExcess = (crops: string[]) => {
  const at = crops.map((c, i) => (SCLEROTINIA_HOSTS.includes(c) ? i : -1)).filter((i) => i >= 0);
  return at.slice(MAX_SCLEROTINIA_HOSTS);
};

const FALLBACK = ['#8c6d1f', '#5a7d9a', '#a05a8a', '#6b8e4e', '#b0643c', '#4f7f7a'];
export const humanize = (id: string) => { const s = id.replace(/_/g, ' '); return s.charAt(0).toUpperCase() + s.slice(1); };
export const cropLabel = (id: string | null | undefined) => (id ? (CROP_LABELS[id] ?? humanize(id)) : '');
const hash = (s: string) => [...s].reduce((a, c) => (a * 31 + c.charCodeAt(0)) >>> 0, 7);
export const cropColor = (id: string) => `var(--c-${id}, ${FALLBACK[hash(id) % FALLBACK.length]})`;
