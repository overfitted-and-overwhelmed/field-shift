/** USDA NASS Cropland Data Layer class codes (the ones that occur on the High Plains plus the usual rest) and the colours used on the map. */
const NAMES: Record<number, string> = {
  1: 'Corn', 2: 'Cotton', 3: 'Rice', 4: 'Sorghum', 5: 'Soybeans', 6: 'Sunflower', 10: 'Peanuts', 11: 'Tobacco', 12: 'Sweet corn', 13: 'Popcorn',
  14: 'Mint', 21: 'Barley', 22: 'Durum wheat', 23: 'Spring wheat', 24: 'Winter wheat', 25: 'Other small grains', 26: 'Wheat / soybean (double)',
  27: 'Rye', 28: 'Oats', 29: 'Millet', 30: 'Speltz', 31: 'Canola', 32: 'Flaxseed', 33: 'Safflower', 34: 'Rape seed', 35: 'Mustard', 36: 'Alfalfa',
  37: 'Other hay', 38: 'Camelina', 39: 'Buckwheat', 41: 'Sugarbeets', 42: 'Dry beans', 43: 'Potatoes', 44: 'Other crops', 45: 'Sugarcane',
  46: 'Sweet potatoes', 47: 'Misc. vegetables', 48: 'Watermelons', 49: 'Onions', 50: 'Cucumbers', 51: 'Chickpeas', 52: 'Lentils', 53: 'Peas',
  54: 'Tomatoes', 56: 'Hops', 57: 'Herbs', 58: 'Clover', 59: 'Sod / grass seed', 60: 'Switchgrass', 61: 'Fallow / idle',
  176: 'Grass / pasture', 205: 'Triticale', 225: 'Winter wheat / corn (double)', 226: 'Oats / corn (double)', 236: 'Winter wheat / sorghum (double)',
  237: 'Barley / corn (double)', 238: 'Winter wheat / cotton (double)', 239: 'Soybeans / cotton (double)', 240: 'Soybeans / oats (double)',
  241: 'Corn / soybeans (double)', 254: 'Barley / soybeans (double)', 227: 'Lettuce', 228: 'Triticale / corn (double)', 229: 'Pumpkins', 234: 'Durum wheat / sorghum (double)', 235: 'Barley / sorghum (double)',
  242: 'Blueberries', 243: 'Cabbage', 244: 'Cauliflower', 245: 'Celery', 246: 'Radishes', 247: 'Turnips', 248: 'Eggplants', 249: 'Gourds', 250: 'Cranberries', 204: 'Pistachios',
  111: 'Open water', 121: 'Developed (open)', 122: 'Developed (low)', 123: 'Developed (medium)', 124: 'Developed (high)', 131: 'Barren',
  141: 'Deciduous forest', 142: 'Evergreen forest', 143: 'Mixed forest', 152: 'Shrubland', 190: 'Woody wetlands', 195: 'Herbaceous wetlands',
};

/** Colours follow the app's crop palette (config/crops.ts, styles.css) so a crop looks the same everywhere. */
const COLORS: Record<number, string> = {
  1: '#e0a82a', 5: '#5a9a4a', 24: '#8a7bbd', 4: '#c65f36', 6: '#2b9a86', 205: '#d9829f',
  36: '#8fc46a', 37: '#8fc46a', 61: '#b9b48a', 26: '#a99bd0', 225: '#cdb35a', 236: '#b88a6a',
};
const OTHER = '#7f8b96';

export const cdlName = (v: number) => NAMES[v] ?? `CDL class ${v}`;
export const cdlColor = (v: number) => COLORS[v] ?? OTHER;

/** App crop id (config/crops.ts) for a CDL class, or null when the scorer does not model it. */
export function cdlAppCrop(v: number): string | null {
  return ({ 1: 'corn', 5: 'soybean', 24: 'winter_wheat', 4: 'sorghum', 6: 'sunflower', 205: 'triticale' } as Record<number, string>)[v] ?? null;
}

/** Cropland (incl. fallow, hay, orchards and specialty crops). Pasture, forest, water and developed land are not fields here. */
export const isCrop = (v: number) => (v >= 1 && v <= 61) || (v >= 66 && v <= 77) || (v >= 204 && v <= 254);
