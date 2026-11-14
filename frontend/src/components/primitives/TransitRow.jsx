import React, { useState } from 'react';
import { ChevronDown, ChevronUp, ArrowRight, Info } from 'lucide-react';
import { Link } from 'react-router-dom';
import RouteBadge from './RouteBadge';
import CrowdStrip from './CrowdStrip';
import TimeBreakdownBar from './TimeBreakdownBar';
import { useTranslation } from '../../i18n/LanguageContext';

export default function TransitRow({
  option,
  isRecommended = false,
  isSelected = false,
  preference = 'balanced',
  onSelect,
  onOpenWhyModal,
  className = '',
}) {
  const { t, lang } = useTranslation();
  const [isExpanded, setIsExpanded] = useState(false);

  // Confidence text in plain words (per prompt rule: "Based on a lot of data / some data / little data")
  const getConfidenceText = (conf) => {
    const c = String(conf || '').toLowerCase();
    if (c === 'high') {
      return lang === 'hi' ? 'पर्याप्त टिकट डेटा पर आधारित' : 'Based on a lot of historical data';
    }
    if (c === 'medium') {
      return lang === 'hi' ? 'कुछ टिकट डेटा पर आधारित' : 'Based on some historical data';
    }
    return lang === 'hi' ? 'कम डेटा पर आधारित (सावधानी रखें)' : 'Based on limited data';
  };

  // Convert "18:00" or raw string to 12-hour am/pm
  const formatTime12h = (timeStr) => {
    if (!timeStr) return '8:42 am';
    const [hStr, mStr] = timeStr.split(':');
    let h = parseInt(hStr, 10);
    const m = mStr || '00';
    if (isNaN(h)) return timeStr;
    const period = h >= 12 ? 'pm' : 'am';
    h = h % 12 || 12;
    return `${h}:${m} ${period}`;
  };

  const totalMin = option.total_duration_minutes || 45;
  const rideMin = option.ride_time_minutes || totalMin;
  const waitMin = option.wait_time_minutes || 0;
  const walkMin = option.walk_time_minutes || 0;
  const depTime = formatTime12h(option.departure_time || option.scheduled_departure);
  const routeNum = option.route_short_name || option.route_id || '73UP';
  const distKm = option.distance_km || option.timing?.distance_km;
  const stopsCount = option.stops_count || option.stops?.length;

  // Crowd text construction
  const crowdOrigin = option.crowd_category || 'low';
  const peakCrowd = option.peak_crowd_category || option.crowd_category || 'moderate';

  return (
    <div
      onClick={onSelect}
      className={`
        bg-white border rounded-[6px] transition-colors cursor-pointer select-none
        ${isRecommended ? 'border-l-[3px] border-l-teal' : 'border-transit-border'}
        ${isSelected ? 'ring-2 ring-teal border-teal' : 'hover:border-transit-textMuted/40'}
        ${className}
      `}
    >
      {/* Top recommendation indicator */}
      {isRecommended && (
        <div className="px-3 pt-2 pb-0.5 text-[11px] font-semibold text-teal flex items-center gap-1">
          <span>
            {lang === 'hi'
              ? `अनुशंसित विकल्प (${preference === 'balanced' ? 'संतुलित' : preference === 'least_crowded' ? 'कम भीड़' : 'सबसे तेज़'})`
              : `Recommended for ${preference.replace('_', ' ')}`}
          </span>
        </div>
      )}

      {/* Main scannable row */}
      <div className="p-3 sm:p-4 flex items-start justify-between gap-3">
        {/* Left: Route and Departure */}
        <div className="space-y-1.5 flex-1 min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <RouteBadge routeNumber={routeNum} size="md" />
            <span className="text-xs text-transit-textMuted font-medium">
              {lang === 'hi'
                ? `प्रस्थान ${depTime} · ${distKm ? `${distKm} किमी · ` : ''}${stopsCount ? `${stopsCount} स्टॉप` : 'निर्धारित'}`
                : `Leaves ${depTime} · ${distKm ? `${distKm} km · ` : ''}${stopsCount ? `${stopsCount} stops` : 'scheduled'}`}
            </span>
          </div>

          <div className="text-xs text-transit-text truncate">
            {option.route_long_name || `Delhi Bus Route ${routeNum}`}
          </div>

          {/* Crowd Strip signature element */}
          <div className="pt-0.5">
            <CrowdStrip
              category={crowdOrigin}
              occupancyPercent={option.occupancy_percent || null}
              size="sm"
            />
          </div>
        </div>

        {/* Right: Duration & Expand Toggle */}
        <div className="flex flex-col items-end justify-between self-stretch shrink-0">
          <div className="text-right">
            <span className="text-2xl font-bold text-navy tabular-nums leading-none">
              {totalMin}
            </span>
            <span className="text-xs text-transit-textMuted font-medium ml-1">
              {t('results.min')}
            </span>
          </div>

          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation();
              setIsExpanded(!isExpanded);
            }}
            className="p-1 text-transit-textMuted hover:text-navy hover:bg-transit-bg rounded-[4px] mt-2 transition-colors min-w-[32px] min-h-[32px] flex items-center justify-center"
            aria-label={isExpanded ? 'Collapse journey details' : 'Expand journey details'}
          >
            {isExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
          </button>
        </div>
      </div>

      {/* Inline Expander */}
      {isExpanded && (
        <div
          className="px-3 sm:px-4 pb-3 sm:pb-4 pt-2 border-t border-transit-border space-y-3 bg-transit-bg/40 text-xs"
          onClick={(e) => e.stopPropagation()}
        >
          {/* Time breakdown visual bar */}
          <div className="space-y-1">
            <span className="font-semibold text-navy">
              {lang === 'hi' ? 'समय का विभाजन' : 'Time breakdown'}
            </span>
            <TimeBreakdownBar
              walkMinutes={walkMin}
              waitMinutes={waitMin}
              rideMinutes={rideMin}
            />
          </div>

          {/* Confidence and Crowding explanation */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-transit-textMuted pt-1">
            <div className="p-2 bg-white border border-transit-border rounded-[4px]">
              <span className="block text-[10px] uppercase font-semibold text-transit-textMuted">
                {lang === 'hi' ? 'डेटा विश्वसनीयता' : 'Data confidence'}
              </span>
              <span className="text-transit-text font-medium text-xs">
                {getConfidenceText(option.confidence)}
              </span>
            </div>

            <div className="p-2 bg-white border border-transit-border rounded-[4px]">
              <span className="block text-[10px] uppercase font-semibold text-transit-textMuted">
                {lang === 'hi' ? 'सवारी के दौरान भीड़' : 'Journey crowd note'}
              </span>
              <span className="text-transit-text font-medium text-xs">
                {option.avg_rci && option.avg_rci > 80
                  ? (lang === 'hi' ? 'आगे के स्टॉप पर भीड़ बढ़ सकती है' : 'Crowd increases later on this ride')
                  : (lang === 'hi' ? 'पूरी यात्रा में आरामदायक रहने की संभावना' : 'Likely comfortable throughout ride')}
              </span>
            </div>
          </div>

          {/* Action links */}
          <div className="flex flex-wrap items-center justify-between gap-2 pt-1 border-t border-transit-border/50">
            {onOpenWhyModal && (
              <button
                type="button"
                onClick={() => onOpenWhyModal(option)}
                className="inline-flex items-center gap-1 text-teal hover:underline font-semibold text-xs min-h-[36px]"
              >
                <Info className="w-3.5 h-3.5" />
                <span>{lang === 'hi' ? 'यह विकल्प क्यों चुना गया?' : 'Why this option?'}</span>
              </button>
            )}

            <Link
              to={`/route/${encodeURIComponent(option.route_id)}`}
              className="inline-flex items-center gap-1 text-teal hover:underline font-semibold text-xs ml-auto min-h-[36px]"
            >
              <span>{lang === 'hi' ? '24 घंटे का रूट प्रोफाइल देखें' : 'View 24h route profile'}</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </Link>
          </div>
        </div>
      )}
    </div>
  );
}
