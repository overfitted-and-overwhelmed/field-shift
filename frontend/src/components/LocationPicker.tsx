import 'leaflet/dist/leaflet.css';
import { CircleMarker, LayersControl, MapContainer, TileLayer, useMapEvents } from 'react-leaflet';
import type { LatLon } from '../lib/request';

/** Where the map opens when nothing is picked yet: southwest Kansas (GMD 3). */
const DEFAULT_CENTER: LatLon = { lat: 38.02511, lon: -101.126084 };

function ClickToPick({ onPick }: { onPick: (p: LatLon) => void }) {
  useMapEvents({ click: (e) => onPick({ lat: e.latlng.lat, lon: e.latlng.lng }) });
  return null;
}

/**
 * Leaflet map to pick the field position with a click. No API key: satellite tiles from Esri World Imagery,
 * street map from OpenStreetMap (both need the attribution in the corner).
 * A CircleMarker avoids Leaflet's image icons, which Vite does not bundle.
 */
export function LocationPicker({ value, onChange }: { value: LatLon | null; onChange: (p: LatLon) => void }) {
  const start = value ?? DEFAULT_CENTER;
  return (
    <div className="map">
      <MapContainer center={[start.lat, start.lon]} zoom={value ? 13 : 9} scrollWheelZoom={false} style={{ height: '100%', width: '100%' }}>
        <LayersControl position="topright">
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
        <ClickToPick onPick={onChange} />
        {value && <CircleMarker center={[value.lat, value.lon]} radius={9} pathOptions={{ color: '#fff', weight: 2, fillColor: '#2d6a4a', fillOpacity: 1 }} />}
      </MapContainer>
    </div>
  );
}
