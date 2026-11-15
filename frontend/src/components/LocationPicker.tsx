import 'leaflet/dist/leaflet.css';
import { useEffect, useRef, useState, type ReactNode } from 'react';
import type { CircleMarker as LeafletCircleMarker } from 'leaflet';
import { CircleMarker, LayersControl, MapContainer, Popup, TileLayer, Tooltip, useMapEvents } from 'react-leaflet';
import { DEFAULT_LOCATION, type LatLon } from '../lib/request';

const fmt = (p: LatLon) => `${p.lat.toFixed(5)}, ${p.lon.toFixed(5)}`;

/** Places the marker on a map click, but only while there is none: an existing marker is removed via its menu. */
function ClickToPick({ enabled, onPick }: { enabled: boolean; onPick: (p: LatLon) => void }) {
  useMapEvents({ click: (e) => { if (enabled) onPick({ lat: e.latlng.lat, lon: e.latlng.lng }); } });
  return null;
}

/** Field marker: hover shows the coordinates, click or right-click opens a menu with the coordinates and "Remove". */
function FieldMarker({ value, onRemove }: { value: LatLon; onRemove: () => void }) {
  const ref = useRef<LeafletCircleMarker>(null);
  return (
    <CircleMarker
      ref={ref}
      center={[value.lat, value.lon]}
      radius={9}
      bubblingMouseEvents={false}
      pathOptions={{ color: '#fff', weight: 2, fillColor: '#3cd6bf', fillOpacity: 1 }}
      eventHandlers={{ contextmenu: (e) => { e.originalEvent.preventDefault(); ref.current?.openPopup(); } }}
    >
      <Tooltip direction="top" offset={[0, -10]}>{fmt(value)}</Tooltip>
      <Popup offset={[0, -6]}>
        <div className="pin-menu">
          <span className="pin-label">Field location</span>
          <b>{fmt(value)}</b>
          <button type="button" onClick={(e) => { e.stopPropagation(); ref.current?.closePopup(); onRemove(); }}>Remove marker</button>
        </div>
      </Popup>
    </CircleMarker>
  );
}

/**
 * Leaflet map to pick the field position with a click (only while no marker is set). No API key: satellite tiles from Esri World Imagery,
 * street map from OpenStreetMap (both need the attribution in the corner).
 * A CircleMarker avoids Leaflet's image icons, which Vite does not bundle.
 */
/** Modal "are you sure?" before the marker is removed. Native <dialog>: Escape and the backdrop cancel. */
function ConfirmRemove({ value, onConfirm, onCancel }: { value: LatLon; onConfirm: () => void; onCancel: () => void }) {
  const ref = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    const d = ref.current;
    if (d && !d.open) d.showModal();
    return () => d?.close();
  }, []);
  return (
    <dialog ref={ref} className="confirm" aria-labelledby="confirm-h" onCancel={(e) => { e.preventDefault(); onCancel(); }}
      onClick={(e) => { if (e.target === e.currentTarget) onCancel(); }}>
      <h2 id="confirm-h">Remove the marker?</h2>
      <p>The field location <b>{fmt(value)}</b> will be removed. You can then click on the map to set a new one.</p>
      <div className="confirm-actions">
        <button type="button" onClick={onCancel} autoFocus>Cancel</button>
        <button type="button" className="danger" onClick={onConfirm}>Remove</button>
      </div>
    </dialog>
  );
}

/** `scrollWheelZoom={false}` when the map sits inside a long page, so scrolling the page does not zoom the map. */
export function LocationPicker({ value, onChange, children, scrollWheelZoom = true }: { value: LatLon | null; onChange: (p: LatLon | null) => void; children?: ReactNode; scrollWheelZoom?: boolean }) {
  const start = value ?? DEFAULT_LOCATION;
  const [confirming, setConfirming] = useState(false);
  return (
    <div className={value ? 'map' : 'map picking'}>
      <MapContainer center={[start.lat, start.lon]} zoom={value ? 13 : 9} scrollWheelZoom={scrollWheelZoom} style={{ height: '100%', width: '100%' }}>
        <LayersControl position="topleft">
          <LayersControl.BaseLayer checked name="Satellite">
            <TileLayer
              url="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
              attribution="Imagery © Esri, Maxar, Earthstar Geographics"
              maxZoom={18}
            />
          </LayersControl.BaseLayer>
          <LayersControl.BaseLayer name="Map">
            <TileLayer
              url="https://tile.openstreetmap.org/{z}/{x}/{y}.png"
              attribution='© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
              maxZoom={19}
            />
          </LayersControl.BaseLayer>
        </LayersControl>
        <ClickToPick enabled={!value} onPick={onChange} />
        {children}
        {value && <FieldMarker value={value} onRemove={() => setConfirming(true)} />}
      </MapContainer>
      {confirming && value && <ConfirmRemove value={value} onCancel={() => setConfirming(false)} onConfirm={() => { setConfirming(false); onChange(null); }} />}
    </div>
  );
}
