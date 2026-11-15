import type { Rotation } from '../types';

/** Earliest first month and the number of months that cover all rotations, so their strips line up. */
export function calendarSpan(rs: Rotation[]): { start: string; months: number } {
  const ms = rs.filter((r) => r.monthly.length);
  if (!ms.length) return { start: '2027-01', months: 36 };
  const idx = (m: string) => Number(m.slice(0, 4)) * 12 + Number(m.slice(5, 7)) - 1;
  const lo = Math.min(...ms.map((r) => idx(r.monthly[0].m)));
  const hi = Math.max(...ms.map((r) => idx(r.monthly[r.monthly.length - 1].m)));
  const startIdx = lo - (lo % 12); // start at January so the years read cleanly
  return { start: `${Math.floor(startIdx / 12)}-01`, months: hi - startIdx + 1 };
}
