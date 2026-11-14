import React, { useEffect, useMemo } from 'react';
import { MapContainer, TileLayer, Polyline, CircleMarker, Popup, useMap } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';

// Auto-fit bounds component with reliable invalidation & focus
function ChangeView({ bounds }) {
  const map = useMap();
  useEffect(() => {
    if (!bounds || bounds.length === 0) return;

    const applyBounds = () => {
      try {
        map.invalidateSize();
        if (bounds.length === 1) {
          map.setView(bounds[0], 13);
        } else if (bounds.length > 1) {
          map.fitBounds(bounds, { padding: [45, 45], maxZoom: 15 });
        }
      } catch (e) {
        // Guard against race condition on unmount
      }
    };

    applyBounds();
    const timer = setTimeout(applyBounds, 150);
    return () => clearTimeout(timer);
  }, [bounds, map]);
  return null;
}

export default function LeafletRouteMap({
  stops = [],
  shapePoints = [],
  highlightOrigin = null,
  highlightDest = null,
  distanceKm = null,
  height = '360px',
  className = '',
}) {
  const totalDistKm = distanceKm || (stops.length > 0 ? stops[stops.length - 1]?.distance_km : null) || 12.0;
  // Compute polyline coordinates from shapePoints or stops sequence
  const polylineCoords = useMemo(() => {
    if (shapePoints && shapePoints.length > 0) {
      return shapePoints
        .map((pt) => [pt.shape_pt_lat || pt.lat, pt.shape_pt_lon || pt.lon])
        .filter((c) => c[0] && c[1]);
    }
    if (stops && stops.length > 0) {
      return stops
        .map((s) => [s.stop_lat || s.lat, s.stop_lon || s.lon])
        .filter((c) => c[0] && c[1]);
    }
    return [];
  }, [shapePoints, stops]);

  // Compute bounding box strictly focused on the route corridor
  const bounds = useMemo(() => {
    if (polylineCoords.length > 0) return polylineCoords;
    if (stops.length > 0) {
      const valid = stops
        .map((s) => [s.stop_lat || s.lat, s.stop_lon || s.lon])
        .filter((c) => c[0] && c[1]);
      if (valid.length > 0) return valid;
    }
    return [
      [28.61, 77.20],
      [28.66, 77.32],
    ];
  }, [polylineCoords, stops]);

  const defaultCenter = [28.635, 77.26]; // Central Delhi / Vikas Marg corridor

  return (
    <div
      style={{ height }}
      className={`w-full rounded-panel overflow-hidden border border-transit-border relative bg-transit-bg flex flex-col ${className}`}
    >
      <div className="flex-1 w-full relative">
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

          {/* Selected bus route track: 6px navy casing + 3.5px teal line */}
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

          {/* Scheduled bus stops along the track */}
          {stops.map((stop, idx) => {
            const lat = stop.stop_lat || stop.lat;
            const lon = stop.stop_lon || stop.lon;
            if (!lat || !lon) return null;

            const isOrigin =
              String(highlightOrigin) === String(stop.stop_id) || idx === 0;
            const isDest =
              String(highlightDest) === String(stop.stop_id) || idx === stops.length - 1;

            let radius = 4;
            let color = '#142B3B'; // navy stroke
            let fillColor = '#FFFFFF'; // white center
            let weight = 2;

            if (isOrigin) {
              radius = 7;
              color = '#142B3B';
              fillColor = '#147D78'; // Teal for origin
              weight = 2.5;
            } else if (isDest) {
              radius = 7;
              color = '#142B3B';
              fillColor = '#142B3B'; // Navy for destination
              weight = 2.5;
            }

            return (
              <CircleMarker
                key={stop.stop_id ? `${stop.stop_id}_${idx}` : idx}
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
                  <div className="font-bold text-navy text-sm">{stop.stop_name || `Stop #${idx + 1}`}</div>
                  <div className="flex items-center gap-2 mt-1 text-xs">
                    {stop.arrival_time_12h && (
                      <span className="font-mono font-bold text-teal bg-teal/10 px-1.5 py-0.5 rounded">
                        🕒 {stop.arrival_time_12h}
                      </span>
                    )}
                    {stop.distance_km != null && (
                      <span className="font-medium text-navy bg-transit-bg px-1.5 py-0.5 rounded border border-transit-border">
                        📍 {stop.distance_km} km
                      </span>
                    )}
                  </div>
                  {stop.stop_id && (
                    <div className="text-[10px] text-transit-textMuted font-mono mt-1">
                      Stop ID: {stop.stop_id} · Sequence: #{idx + 1}
                    </div>
                  )}
                  {isOrigin && (
                    <div className="text-[10px] font-bold text-teal mt-1 uppercase tracking-wide">
                      ● Boarding / Departure Stop
                    </div>
                  )}
                  {isDest && (
                    <div className="text-[10px] font-bold text-navy mt-1 uppercase tracking-wide">
                      ■ Alighting / Destination Stop
                    </div>
                  )}
                </Popup>
              </CircleMarker>
            );
          })}
        </MapContainer>
      </div>

      {/* Map Legend & Track Status Bar */}
      <div className="bg-white border-t border-transit-border px-3 py-1.5 flex flex-wrap items-center justify-between text-[11px] text-transit-textMuted select-none">
        <div className="flex items-center gap-3">
          <span className="flex items-center gap-1 font-medium text-navy">
            <span className="w-2.5 h-2.5 rounded-full bg-teal border border-navy" />
            <span>Boarding</span>
          </span>
          <span className="flex items-center gap-1 font-medium text-navy">
            <span className="w-2.5 h-2.5 rounded-full bg-navy border border-white" />
            <span>Alighting</span>
          </span>
          <span className="flex items-center gap-1">
            <span className="w-4 h-1.5 bg-teal border-y border-navy rounded-[1px]" />
            <span>Bus Track</span>
          </span>
        </div>
        <div className="font-semibold text-navy">
          <span>
            {stops.length > 0
              ? `${stops.length} stops · ${totalDistKm} km corridor`
              : 'Corridor track view'}
          </span>
        </div>
      </div>
    </div>
  );
}
