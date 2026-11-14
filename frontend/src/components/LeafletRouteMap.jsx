import React, { useEffect, useMemo } from 'react';
import { MapContainer, TileLayer, Polyline, CircleMarker, Popup, useMap } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';

// Auto-fit bounds component
function ChangeView({ bounds }) {
  const map = useMap();
  useEffect(() => {
    if (bounds && bounds.length > 0) {
      try {
        map.fitBounds(bounds, { padding: [30, 30], maxZoom: 15 });
      } catch (e) {
        // Ignore zoom errors when container is rendering
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
  className = '',
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
      [28.52, 77.10],
      [28.72, 77.32],
    ];
  }, [polylineCoords, stops]);

  const defaultCenter = [28.6139, 77.2090]; // Central Secretariat / CP

  return (
    <div
      style={{ height }}
      className={`w-full rounded-panel overflow-hidden border border-transit-border relative bg-transit-bg ${className}`}
    >
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

        {/* Selected journey: 5px navy casing with a 3px teal line */}
        {polylineCoords.length > 1 && (
          <>
            <Polyline
              positions={polylineCoords}
              pathOptions={{ color: '#142B3B', weight: 6, opacity: 0.9, lineJoin: 'round' }}
            />
            <Polyline
              positions={polylineCoords}
              pathOptions={{ color: '#147D78', weight: 3.5, opacity: 1, lineJoin: 'round' }}
            />
          </>
        )}

        {/* Stops as small white circles with a navy stroke */}
        {stops.map((stop, idx) => {
          const lat = stop.stop_lat || stop.lat;
          const lon = stop.stop_lon || stop.lon;
          if (!lat || !lon) return null;

          const isOrigin = highlightOrigin === stop.stop_id || idx === 0;
          const isDest = highlightDest === stop.stop_id || idx === stops.length - 1;

          let radius = 4;
          let color = '#142B3B'; // navy stroke
          let fillColor = '#FFFFFF'; // white fill
          let weight = 2;

          if (isOrigin) {
            radius = 6;
            color = '#142B3B';
            fillColor = '#147D78'; // Teal origin
            weight = 2.5;
          } else if (isDest) {
            radius = 6;
            color = '#142B3B';
            fillColor = '#142B3B'; // Navy destination
            weight = 2.5;
          }

          return (
            <CircleMarker
              key={stop.stop_id || idx}
              center={[lat, lon]}
              radius={radius}
              pathOptions={{
                color,
                fillColor,
                fillOpacity: 1,
                weight,
              }}
            >
              <Popup className="text-xs font-sans">
                <div className="font-semibold text-navy">{stop.stop_name || `Stop #${idx + 1}`}</div>
                {stop.stop_id && (
                  <div className="text-[10px] text-transit-textMuted font-mono">
                    ID: {stop.stop_id}
                  </div>
                )}
                {isOrigin && (
                  <div className="text-[10px] font-bold text-teal mt-0.5">Origin Stop</div>
                )}
                {isDest && (
                  <div className="text-[10px] font-bold text-navy mt-0.5">Destination Stop</div>
                )}
              </Popup>
            </CircleMarker>
          );
        })}
      </MapContainer>
    </div>
  );
}
