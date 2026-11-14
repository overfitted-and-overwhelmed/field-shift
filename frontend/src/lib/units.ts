export type Units = 'in' | 'mm';
export const inToUnit = (inches: number, u: Units) => (u === 'in' ? inches : inches * 25.4);
export const fmtWater = (inches: number, u: Units) => (u === 'in' ? `${inches.toFixed(1)} in` : `${Math.round(inches * 25.4)} mm`);
export const fmtWaterNum = (inches: number, u: Units) => (u === 'in' ? inches.toFixed(1) : String(Math.round(inches * 25.4)));
export const fmtMm = (mm: number, u: Units) => (u === 'in' ? `${(mm / 25.4).toFixed(1)} in` : `${Math.round(mm)} mm`);
