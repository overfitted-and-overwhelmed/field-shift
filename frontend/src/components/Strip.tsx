import { cropColor, cropLabel } from '../config/crops';
import type { Rotation } from '../types';

const short = (iso: string) => new Date(`${iso}T00:00:00`).toLocaleDateString('en-US', { month: 'short', year: 'numeric' });

/** The rotation as one block per season: crop color on top, name and harvest year below. Double crops share a year. */
export function Strip({ r }: { r: Rotation }) {
  return (
    <ol className="strip" style={{ gridTemplateColumns: `repeat(${r.sequence.length}, minmax(0, 1fr))` }}>
      {r.sequence.map((s, i) => (
        <li key={i} data-tip={`${cropLabel(s.crop)}: planted ${short(s.plant_date)}, harvested ${short(s.harvest_date)}${s.cover ? `, then ${cropLabel(s.cover).toLowerCase()} cover` : ''}`}>
          <i style={{ background: cropColor(s.crop) }} />
          <b>{cropLabel(s.crop)}</b>
          <span>{s.year}{s.cover ? ' · + cover' : ''}</span>
        </li>
      ))}
    </ol>
  );
}
