import { cropColor, cropLabel } from '../config/crops';
import type { Rotation } from '../types';

/** The rotation as one block per year: crop color on top, name and year below. */
export function Strip({ r }: { r: Rotation }) {
  return (
    <ol className="strip" style={{ gridTemplateColumns: `repeat(${r.sequence.length}, minmax(0, 1fr))` }}>
      {r.sequence.map((s) => (
        <li key={s.year}>
          <i style={{ background: cropColor(s.crop) }} />
          <b>{cropLabel(s.crop)}</b>
          <span>{s.year}{s.cover ? ' · + cover' : ''}</span>
        </li>
      ))}
    </ol>
  );
}
