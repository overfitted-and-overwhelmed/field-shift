import { useMemo } from 'react';
import { cdlColor, cdlName } from '../lib/fields/cdl';
import { ndviCss, type NdviResult } from '../lib/fields/ndvi';
import type { Field, Surroundings } from '../lib/fields/surroundings';
import type { Load } from '../lib/fields/useFieldData';
import type { Layer } from './FieldsLayer';

/** Little outline of the field, filled with its NDVI colour or crop colour (like the thumbnails in the list of a field-monitoring tool). */
function Shape({ f, fill }: { f: Field; fill: string }) {
  const d = useMemo(() => {
    const k = Math.cos((f.labelPos[0] * Math.PI) / 180);
    const pts = f.ring.map(([la, lo]) => [lo * k, -la] as const);
    const xs = pts.map((p) => p[0]), ys = pts.map((p) => p[1]);
    const x0 = Math.min(...xs), y0 = Math.min(...ys), s = Math.max(Math.max(...xs) - x0, Math.max(...ys) - y0) || 1;
    const sc = 40 / s, ox = (48 - (Math.max(...xs) - x0) * sc) / 2, oy = (48 - (Math.max(...ys) - y0) * sc) / 2;
    return pts.map(([x, y], i) => `${i ? 'L' : 'M'}${(ox + (x - x0) * sc).toFixed(1)} ${(oy + (y - y0) * sc).toFixed(1)}`).join('') + 'Z';
  }, [f]);
  return <svg viewBox="0 0 48 48" width="48" height="48" aria-hidden="true"><path d={d} fill={fill} stroke="rgba(0,0,0,.25)" strokeWidth="1" strokeLinejoin="round" /></svg>;
}

const km = (m: number) => (m < 950 ? `${Math.round(m / 10) * 10} m` : `${(m / 1000).toFixed(1)} km`);

function History({ f }: { f: Field }) {
  const counts = new Map<number, number>();
  for (const h of f.history) if (h.cls) counts.set(h.cls, (counts.get(h.cls) ?? 0) + 1);
  const top = [...counts.entries()].sort((a, b) => b[1] - a[1]).slice(0, 3);
  const first = f.history[0]?.year, last = f.history[f.history.length - 1]?.year;
  return (
    <div className="hist">
      <span className="k">Crop each year (USDA CDL)</span>
      <ol className="years" aria-label="Crop per year">
        {f.history.map((h) => <li key={h.year} style={{ background: h.cls ? cdlColor(h.cls) : 'var(--ln-line)' }} title={`${h.year}: ${h.cls ? cdlName(h.cls) : 'no data'}`} />)}
      </ol>
      <span className="ends"><span>{first}</span><span>{last}</span></span>
      <p className="sum">{top.map(([c, n]) => `${cdlName(c)} ${n}×`).join(' · ')} in {f.history.length} years</p>
    </div>
  );
}

interface Props {
  surr: Load<Surroundings>;
  ndvi: NdviResult | null;
  ndviLoading: boolean;
  layer: Layer;
  selectedId: string | null;
  onSelect: (id: string) => void;
}

export function FieldPanel({ surr, ndvi, ndviLoading, layer, selectedId, onSelect }: Props) {
  if (surr.status === 'idle') return <div className="hud fields"><header><h2>Fields nearby</h2></header><p className="msg">Click on the map to place your field. The fields around it appear here.</p></div>;
  if (surr.status === 'loading') return <div className="hud fields" aria-busy="true"><header><h2>Fields nearby</h2></header><ul className="cards skel" aria-label="Loading">{[0, 1, 2, 3].map((i) => <li key={i} />)}</ul><p className="msg">Reading the USDA Cropland Data Layer…</p></div>;
  if (surr.status === 'error') return <div className="hud fields"><header><h2>Fields nearby</h2></header><p className="msg err" role="alert">{surr.error}</p></div>;

  const { fields, year, pointClass, ownId } = surr.data;
  return (
    <div className="hud fields">
      <header>
        <h2>Fields nearby <span className="n">{fields.length}</span></h2>
        <p>Within 3 km · crops {year}</p>
      </header>
      {!ownId && <p className="msg warn">Your point is on <b>{pointClass ? cdlName(pointClass).toLowerCase() : 'land outside the map data'}</b> in {year}, not on cropland. These are the closest fields.</p>}
      {fields.length === 0 && <p className="msg">No cropland within 3 km of this point.</p>}
      <ul className="cards">
        {fields.map((f) => {
          const v = ndvi?.means[f.id];
          const sel = f.id === selectedId;
          const fill = layer === 'crop' || v == null ? cdlColor(f.cls) : ndviCss(v);
          return (
            <li key={f.id} className={(sel ? 'on ' : '') + (f.own ? 'own' : '')}>
              <button type="button" aria-pressed={sel} onClick={() => onSelect(f.id)}>
                <Shape f={f} fill={fill} />
                <span className="who">
                  <b>{f.label}</b>
                  <small>{f.ha.toFixed(1)} ha · {f.own ? 'your marker' : km(f.distM) + ' away'}</small>
                  <span className="crop"><i style={{ background: cdlColor(f.cls) }} />{cdlName(f.cls)}</span>
                </span>
                <span className="val">
                  <b>{v == null ? (ndviLoading ? '…' : '–') : v.toFixed(2)}</b>
                  <small>NDVI</small>
                </span>
              </button>
              {sel && <History f={f} />}
            </li>
          );
        })}
      </ul>
      <p className="src">
        Fields: USDA NASS Cropland Data Layer {year}, observed crop per 30 m pixel. NDVI: Copernicus Sentinel-2 L2A{ndvi ? `, ${ndvi.scene.date}` : ''}, 10 m, clouds masked. Data via Microsoft Planetary Computer.
      </p>
    </div>
  );
}
