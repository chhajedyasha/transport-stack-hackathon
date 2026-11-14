import React, { useState } from 'react';
import { 
  Clock, 
  MapPin, 
  Navigation, 
  ChevronDown, 
  ChevronUp, 
  Bus, 
  ShieldCheck, 
  Gauge, 
  ArrowRight,
  Info
} from 'lucide-react';
import RouteBadge from './primitives/RouteBadge';
import CrowdIndicator from './primitives/CrowdIndicator';
import { useTranslation } from '../i18n/LanguageContext';

/**
 * JourneyItinerary — Detailed Moovit-style Step-by-Step Stop Timeline & Route Inspector
 * Depicts:
 * - Route distance (km) and total duration
 * - Scheduled departure and arrival times
 * - Step-by-step stops timeline with approximate arrival time at each stop
 * - Distance from departure for each stop
 * - Boarding & Alighting highlights
 */
export default function JourneyItinerary({
  option,
  className = '',
  onStopClick = null,
}) {
  const { t, lang } = useTranslation();
  const [showAllStops, setShowAllStops] = useState(true);

  if (!option) return null;

  const stops = option.stops || [];
  const routeNum = option.route_short_name || option.route_id || 'Route';
  const totalDurationMin = option.total_duration_minutes || option.timing?.total_duration_min || 40;
  const distanceKm = option.distance_km || option.timing?.distance_km || 12.0;
  const depTime = option.scheduled_departure ? option.scheduled_departure.slice(0, 5) : '18:00';
  const arrTime = option.scheduled_arrival ? option.scheduled_arrival.slice(0, 5) : '18:40';
  const operator = option.operator || 'DTC';
  const crowdCategory = option.crowd_category || 'Standing Room';

  // Format 24h string to 12h AM/PM
  const formatTime12h = (tStr) => {
    if (!tStr) return '';
    const parts = tStr.split(':');
    let h = parseInt(parts[0], 10);
    const m = parts[1] || '00';
    if (isNaN(h)) return tStr;
    const period = h >= 12 ? 'pm' : 'am';
    h = h % 12 || 12;
    return `${h}:${m} ${period}`;
  };

  const dep12h = formatTime12h(depTime);
  const arr12h = formatTime12h(arrTime);

  const originStop = stops.length > 0 ? stops[0] : option.origin_stop;
  const destStop = stops.length > 1 ? stops[stops.length - 1] : option.destination_stop;
  const intermediateStops = stops.length > 2 ? stops.slice(1, -1) : [];

  return (
    <div className={`bg-white border border-border rounded-2xl shadow-sm overflow-hidden ${className}`}>
      {/* Header Bar: Route Badge, Timespan, Distance & Duration */}
      <div className="p-4 bg-[#F8F5F2] border-b border-border">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <RouteBadge routeNumber={routeNum} size="lg" />
            <div>
              <div className="flex items-center gap-2 text-sm font-extrabold text-navy">
                <span>{dep12h} – {arr12h}</span>
                <span className="text-tx-muted font-normal">·</span>
                <span className="text-teal font-black">{totalDurationMin} min</span>
              </div>
              <div className="text-xs text-tx-muted flex items-center gap-2 mt-0.5">
                <span className="font-semibold text-navy">{operator}</span>
                <span>·</span>
                <span className="font-semibold text-navy">{distanceKm} km route</span>
                <span>·</span>
                <span>{stops.length} stops</span>
              </div>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <div className="text-right">
              <div className="text-[10px] uppercase font-bold text-tx-muted tracking-wider">
                {lang === 'hi' ? 'भीड़ का स्तर' : 'Crowd Level'}
              </div>
              <CrowdIndicator
                category={crowdCategory}
                occupancyPercent={option.occupancy_percent || null}
                size="sm"
              />
            </div>
          </div>
        </div>
      </div>

      {/* Main Stop-by-Stop Timeline */}
      <div className="p-3 sm:p-4 space-y-0">
        <div className="text-xs font-bold text-navy uppercase tracking-wider mb-3 flex items-center justify-between">
          <span>{lang === 'hi' ? 'स्टॉप यात्रा क्रम' : 'Journey Stops & Schedule'}</span>
          <span className="text-[11px] font-normal text-transit-textMuted">
            {distanceKm} km corridor
          </span>
        </div>

        {/* 1. Origin / Boarding Stop */}
        <div className="flex items-start gap-3 group">
          <div className="flex flex-col items-center shrink-0 w-6">
            <div className="w-5 h-5 rounded-full bg-teal border-2 border-navy flex items-center justify-center text-white shadow-sm mt-0.5">
              <div className="w-1.5 h-1.5 rounded-full bg-white" />
            </div>
            <div className="w-0.5 bg-teal/40 h-10 grow" />
          </div>

          <div className="flex-1 pb-3 pt-0.5">
            <div className="flex items-center justify-between gap-2">
              <span className="font-bold text-xs sm:text-sm text-navy">
                {originStop?.stop_name || 'Origin Stop'}
              </span>
              <span className="font-mono text-xs font-bold text-teal tabular-nums bg-teal/10 px-1.5 py-0.5 rounded">
                {originStop?.arrival_time_12h || dep12h}
              </span>
            </div>
            <div className="flex items-center gap-2 text-[11px] text-transit-textMuted mt-0.5">
              <span className="font-medium text-teal uppercase font-bold text-[10px]">
                ● {lang === 'hi' ? 'प्रस्थान / बोर्डिंग' : 'Board Here'}
              </span>
              <span>·</span>
              <span>0.0 km</span>
              {originStop?.stop_id && (
                <>
                  <span>·</span>
                  <span className="font-mono text-[10px]">Stop ID: {originStop.stop_id}</span>
                </>
              )}
            </div>
          </div>
        </div>

        {/* 2. Intermediate Stops Rail & Expander */}
        {intermediateStops.length > 0 && (
          <div className="space-y-0">
            {/* Intermediate summary header */}
            <div className="flex items-center gap-3 py-1.5">
              <div className="flex flex-col items-center shrink-0 w-6">
                <div className="w-0.5 bg-transit-border h-4" />
                <button
                  type="button"
                  onClick={() => setShowAllStops(!showAllStops)}
                  className="w-4 h-4 rounded-full border border-transit-border bg-white hover:bg-transit-bg flex items-center justify-center text-navy shadow-xs transition-colors"
                  title={showAllStops ? 'Collapse stops' : 'Expand all stops'}
                  aria-label="Toggle intermediate stops"
                >
                  {showAllStops ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
                </button>
                <div className="w-0.5 bg-transit-border h-4" />
              </div>

              <button
                type="button"
                onClick={() => setShowAllStops(!showAllStops)}
                className="flex-1 flex items-center justify-between p-1.5 rounded hover:bg-transit-bg text-left transition-colors cursor-pointer"
              >
                <span className="text-xs font-medium text-navy">
                  {intermediateStops.length} {lang === 'hi' ? 'रास्ते के स्टॉप' : 'intermediate stops'}
                </span>
                <span className="text-[11px] text-teal font-semibold flex items-center gap-1">
                  <span>{showAllStops ? (lang === 'hi' ? 'छिपाएं' : 'Hide stops') : (lang === 'hi' ? 'सभी स्टॉप देखें' : 'View all stops')}</span>
                  {showAllStops ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
                </span>
              </button>
            </div>

            {/* Expanded List of Intermediate Stops with approx arrival times */}
            {showAllStops && (
              <div className="space-y-0 animate-fade-in pl-0">
                {intermediateStops.map((stop, i) => (
                  <div
                    key={stop.stop_id ? `${stop.stop_id}_${i}` : i}
                    onClick={() => onStopClick && onStopClick(stop)}
                    className="flex items-start gap-3 hover:bg-teal-tint/30 transition-colors rounded px-1 -mx-1 cursor-default"
                  >
                    <div className="flex flex-col items-center shrink-0 w-6">
                      <div className="w-0.5 bg-transit-border h-2" />
                      <div className="w-2.5 h-2.5 rounded-full bg-white border-2 border-navy shrink-0 my-0.5" />
                      <div className="w-0.5 bg-transit-border h-6 grow" />
                    </div>

                    <div className="flex-1 py-1 border-b border-transit-border/30 flex items-center justify-between text-xs">
                      <div className="min-w-0 pr-2">
                        <span className="font-medium text-transit-text text-xs truncate block">
                          <span className="text-[10px] font-mono text-transit-textMuted mr-1.5 font-bold">
                            #{i + 2}
                          </span>
                          {stop.stop_name}
                        </span>
                        <div className="text-[10px] text-transit-textMuted">
                          +{stop.distance_km || stop.dist_from_origin_km || '—'} km
                        </div>
                      </div>

                      <div className="text-right shrink-0">
                        <span className="font-mono text-xs font-semibold text-navy tabular-nums">
                          {stop.arrival_time_12h || stop.arrival_time || '—'}
                        </span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* 3. Destination / Alighting Stop */}
        <div className="flex items-start gap-3 pt-1">
          <div className="flex flex-col items-center shrink-0 w-6">
            <div className="w-0.5 bg-teal/40 h-3" />
            <div className="w-5 h-5 rounded-full bg-navy border-2 border-white flex items-center justify-center text-white shadow-sm">
              <div className="w-1.5 h-1.5 rounded-full bg-teal" />
            </div>
          </div>

          <div className="flex-1 pt-1 pb-1">
            <div className="flex items-center justify-between gap-2">
              <span className="font-bold text-xs sm:text-sm text-navy">
                {destStop?.stop_name || 'Destination Stop'}
              </span>
              <span className="font-mono text-xs font-bold text-navy tabular-nums bg-navy/10 px-1.5 py-0.5 rounded">
                {destStop?.arrival_time_12h || arr12h}
              </span>
            </div>
            <div className="flex items-center gap-2 text-[11px] text-transit-textMuted mt-0.5">
              <span className="font-medium text-navy uppercase font-bold text-[10px]">
                ■ {lang === 'hi' ? 'गंतव्य / उतरें' : 'Alight Here'}
              </span>
              <span>·</span>
              <span className="font-semibold text-navy">{distanceKm} km</span>
              {destStop?.stop_id && (
                <>
                  <span>·</span>
                  <span className="font-mono text-[10px]">Stop ID: {destStop.stop_id}</span>
                </>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Footer Advisory & Speed Note */}
      <div className="px-3 py-2 bg-[#F7F8F6] border-t border-transit-border flex items-center justify-between text-[11px] text-transit-textMuted">
        <div className="flex items-center gap-1.5">
          <Gauge className="w-3.5 h-3.5 text-teal shrink-0" />
          <span>{lang === 'hi' ? 'औसत गति ~18 किमी/घंटा' : 'Corridor speed ~18 km/h'}</span>
        </div>
        <div className="flex items-center gap-1 text-[10px]">
          <ShieldCheck className="w-3 h-3 text-teal" />
          <span>{lang === 'hi' ? 'डीटीसी पास मान्य' : 'DTC Daily / Pink Pass valid'}</span>
        </div>
      </div>
    </div>
  );
}
