import React, { useEffect, useMemo } from 'react';
import { MapContainer, TileLayer, Polyline, CircleMarker, Popup, useMap } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';

// Helper component to auto-fit bounds
function ChangeView({ bounds }) {
  const map = useMap();
  useEffect(() => {
    if (bounds && bounds.length > 0) {
      try {
        map.fitBounds(bounds, { padding: [40, 40], maxZoom: 15 });
      } catch (e) {
        console.warn('Could not fit map bounds:', e);
      }
    }
  }, [bounds, map]);
  return null;
}

export default function LeafletRouteMap({
  stops = [],
  shapePoints = [],
  highlightOrigin = null,
  highlightDest = null,
  height = '360px',
}) {
  // Compute positions
  const polylineCoords = useMemo(() => {
    if (shapePoints && shapePoints.length > 0) {
      return shapePoints.map((pt) => [pt.shape_pt_lat || pt.lat, pt.shape_pt_lon || pt.lon]);
    }
    if (stops && stops.length > 0) {
      return stops.map((s) => [s.stop_lat || s.lat, s.stop_lon || s.lon]).filter((c) => c[0] && c[1]);
    }
    return [];
  }, [shapePoints, stops]);

  const bounds = useMemo(() => {
    if (polylineCoords.length > 0) return polylineCoords;
    if (stops.length > 0) {
      return stops.map((s) => [s.stop_lat || s.lat, s.stop_lon || s.lon]).filter((c) => c[0] && c[1]);
    }
    return [
      [28.5, 77.1],
      [28.7, 77.3],
    ];
  }, [polylineCoords, stops]);

  const defaultCenter = [28.6139, 77.2090]; // Delhi center

  return (
    <div style={{ height }} className="w-full rounded-2xl overflow-hidden border border-slate-200 shadow-inner relative">
      <MapContainer
        center={defaultCenter}
        zoom={12}
        scrollWheelZoom={false}
        className="w-full h-full"
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />

        {bounds.length > 0 && <ChangeView bounds={bounds} />}

        {/* Route Polyline */}
        {polylineCoords.length > 1 && (
          <Polyline
            positions={polylineCoords}
            pathOptions={{ color: '#0FA3A3', weight: 5, opacity: 0.85, lineJoin: 'round' }}
          />
        )}

        {/* Stops Markers */}
        {stops.map((stop, idx) => {
          const lat = stop.stop_lat || stop.lat;
          const lon = stop.stop_lon || stop.lon;
          if (!lat || !lon) return null;

          const isOrigin = highlightOrigin === stop.stop_id || idx === 0;
          const isDest = highlightDest === stop.stop_id || idx === stops.length - 1;

          let color = '#4A5568';
          let radius = 4;
          let fillColor = '#FFFFFF';

          if (isOrigin) {
            color = '#22A06B';
            fillColor = '#22A06B';
            radius = 7;
          } else if (isDest) {
            color = '#E5484D';
            fillColor = '#E5484D';
            radius = 7;
          }

          return (
            <CircleMarker
              key={stop.stop_id || idx}
              center={[lat, lon]}
              radius={radius}
              pathOptions={{ color, fillColor, fillOpacity: 0.9, weight: 2 }}
            >
              <Popup>
                <div className="text-xs space-y-1">
                  <p className="font-bold text-slate-800">{stop.stop_name || `Stop ${idx + 1}`}</p>
                  <p className="text-[11px] text-slate-500 font-mono">ID: {stop.stop_id}</p>
                  {isOrigin && <span className="inline-block px-1.5 py-0.5 rounded bg-emerald-100 text-emerald-800 font-bold text-[10px]">Origin</span>}
                  {isDest && <span className="inline-block px-1.5 py-0.5 rounded bg-red-100 text-red-800 font-bold text-[10px]">Destination</span>}
                </div>
              </Popup>
            </CircleMarker>
          );
        })}
      </MapContainer>
    </div>
  );
}
