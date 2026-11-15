import L from 'leaflet';
import { useEffect, useMemo, useState } from 'react';
import { ImageOverlay, Marker, Pane, Polygon, Tooltip, useMap, useMapEvents } from 'react-leaflet';
import { cdlColor, cdlName } from '../lib/fields/cdl';
import type { NdviResult } from '../lib/fields/ndvi';
import type { Surroundings } from '../lib/fields/surroundings';

export type Layer = 'ndvi' | 'crop' | 'plain';

interface Props {
  data: Surroundings;
  layer: Layer;
  ndvi: NdviResult | null;
  selectedId: string | null;
  onSelect: (id: string) => void;
}

const labelIcon = (text: string, dark: boolean) => L.divIcon({ className: 'fl-label' + (dark ? ' dark' : ''), html: `<span>${text}</span>`, iconSize: undefined });
/** A value label needs room: the field must be at least this many screen pixels across, otherwise labels pile up. Small fields keep tooltip and list entry. */
const LABEL_MIN_PX = 46;
const short = (n: string) => n.replace(/ \(.*\)/, '').replace('Winter wheat', 'W. wheat');

/**
 * Surrounding fields on the Leaflet map. NDVI layer: a Sentinel-2 raster clipped to the outlines, value label per field.
 * Crop layer: flat colour per CDL crop. Plain: outlines only, over the satellite photo.
 */
export function FieldsLayer({ data, layer, ndvi, selectedId, onSelect }: Props) {
  const map = useMap();
  const [zoom, setZoom] = useState(() => map.getZoom());
  useMapEvents({ zoomend: () => setZoom(map.getZoom()) });
  const mPerPx = (40075016 * Math.cos((data.center.lat * Math.PI) / 180)) / (256 * 2 ** zoom);

  // frame all fields once per location; keep room for the list panel on the right on wide screens
  useEffect(() => {
    const pts = data.fields.flatMap((f) => f.ring);
    if (!pts.length) { map.setView([data.center.lat, data.center.lon], 13); return; }
    const wide = map.getContainer().clientWidth > 900;
    map.fitBounds(L.latLngBounds(pts), { paddingTopLeft: [24, 64], paddingBottomRight: [wide ? 360 : 24, 84], maxZoom: 15, animate: true });
  }, [map, data]);

  const labels = useMemo(() => data.fields.map((f) => {
    const v = ndvi?.means[f.id];
    if (layer === 'ndvi') return v == null ? '–' : v.toFixed(2);
    if (layer === 'crop') return short(cdlName(f.cls));
    return '';
  }), [data, layer, ndvi]);

  return (
    <>
      {layer === 'ndvi' && ndvi && (
        <Pane name="ndvi" style={{ zIndex: 380 }}>
          <ImageOverlay url={ndvi.url} bounds={ndvi.bounds} interactive={false} />
        </Pane>
      )}
      {data.fields.map((f) => {
        const sel = f.id === selectedId;
        const fill = layer === 'crop' ? cdlColor(f.cls) : '#ffffff';
        return (
          <Polygon
            key={f.id}
            positions={f.ring}
            bubblingMouseEvents={false}
            eventHandlers={{ click: () => onSelect(f.id) }}
            pathOptions={{
              color: sel ? '#ffffff' : f.own ? '#3cd6bf' : 'rgba(255,255,255,.85)',
              weight: sel ? 4 : f.own ? 3 : 1.5,
              fillColor: sel && layer !== 'crop' ? '#3cd6bf' : fill, fillOpacity: layer === 'crop' ? 0.78 : sel ? 0.22 : layer === 'plain' ? 0.04 : 0,
            }}
          >
            <Tooltip sticky direction="top">{f.label} · {cdlName(f.cls)} {data.year} · {f.ha.toFixed(1)} ha</Tooltip>
          </Polygon>
        );
      })}
      {layer !== 'plain' && data.fields.map((f, i) => Math.sqrt(f.ha * 1e4) / mPerPx >= LABEL_MIN_PX && (
        <Marker key={f.id + layer} position={f.labelPos} interactive={false} keyboard={false} icon={labelIcon(labels[i], true)} />
      ))}
    </>
  );
}
