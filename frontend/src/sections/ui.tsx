import { cropColor, cropLabel } from '../config/crops';
import { TAG_HELP, TAG_LABELS, type Tag } from '../config/metrics';
import type { Rotation } from '../types';

/** Section header: small step label, title, optional lead text. */
export function SecHead({ id, eyebrow, title, lead }: { id?: string; eyebrow: string; title: string; lead?: string }) {
  return (
    <div className="sec-head">
      <p className="eyebrow">{eyebrow}</p>
      <h2 id={id}>{title}</h2>
      {lead && <p>{lead}</p>}
    </div>
  );
}

export const Badge = ({ tag }: { tag: Tag }) => <span className={`badge ${tag}`} data-tip={TAG_HELP[tag]}>{TAG_LABELS[tag]}</span>;

const month = (iso: string) => new Date(`${iso}T00:00:00`).toLocaleDateString('en-US', { month: 'short', year: 'numeric' });

/** The rotation as one block per season: crop color, name, harvest year, cover crop after it. Double crops share a year. */
export function Seq({ r }: { r: Rotation }) {
  return (
    <div className="seq" style={{ gridTemplateColumns: `repeat(${r.sequence.length}, minmax(0, 1fr))` }}>
      {r.sequence.map((s, i) => (
        <div className="yr" key={i} data-tip={`${cropLabel(s.crop)}: planted ${month(s.plant_date)}, harvested ${month(s.harvest_date)}${s.cover ? `, then ${cropLabel(s.cover).toLowerCase()} cover` : ''}`}>
          <span className="bar" style={{ background: cropColor(s.crop) }} />
          <span className="nm">{cropLabel(s.crop)}</span>
          <span className="ir">{s.year}</span>
          {s.cover && <span className="cv">+ cover</span>}
        </div>
      ))}
    </div>
  );
}
