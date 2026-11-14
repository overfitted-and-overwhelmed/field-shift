/**
 * Crop labels and colors. New crop ids from the scorer need no change: the label is derived from the id,
 * the color is a fallback. To fix a color, define --c-<id> in styles/tokens.css.
 */
export const CROP_LABELS: Record<string, string> = {
  corn: 'Corn', soybean: 'Soybean', winter_wheat: 'Winter wheat', sorghum: 'Sorghum', sunflower: 'Sunflower', triticale: 'Triticale',
};
const FALLBACK = ['#8c6d1f', '#5a7d9a', '#a05a8a', '#6b8e4e', '#b0643c', '#4f7f7a'];
export const humanize = (id: string) => { const s = id.replace(/_/g, ' '); return s.charAt(0).toUpperCase() + s.slice(1); };
export const cropLabel = (id: string | null | undefined) => (id ? (CROP_LABELS[id] ?? humanize(id)) : '');
const hash = (s: string) => [...s].reduce((a, c) => (a * 31 + c.charCodeAt(0)) >>> 0, 7);
export const cropColor = (id: string) => `var(--c-${id}, ${FALLBACK[hash(id) % FALLBACK.length]})`;
