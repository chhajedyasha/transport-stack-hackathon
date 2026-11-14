import React, { useState } from 'react';
import { ChevronDown, ChevronUp, ArrowRight, HelpCircle } from 'lucide-react';
import { Link } from 'react-router-dom';
import RouteBadge from './RouteBadge';
import CrowdIndicator from './CrowdIndicator';
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

  // Confidence text in plain words per Transport Stack guidelines
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

  // Convert "18:00" to 12-hour format e.g. "6:00 pm"
  const formatTime12h = (timeStr) => {
    if (!timeStr) return '6:00 pm';
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
  const waitMin = option.wait_time_minutes || 5;
  const walkMin = option.walk_time_minutes || 0;
  const depTime = formatTime12h(option.departure_time || option.scheduled_departure);
  const routeNum = option.route_short_name || option.route_id || '73UP';
  const distKm = option.distance_km || option.timing?.distance_km;
  const stopsCount = option.stops_count || option.stops?.length;

  // Crowd categories
  const crowdOrigin = option.crowd_category || 'low';
  const peakCrowd = option.peak_crowd_category || option.crowd_category || 'moderate';

  const prefLabel =
    preference === 'fastest'
      ? (lang === 'hi' ? 'सबसे तेज़' : 'fastest')
      : preference === 'least_crowded'
      ? (lang === 'hi' ? 'कम भीड़' : 'least crowded')
      : (lang === 'hi' ? 'संतुलित' : 'balanced');

  return (
    <div
      onClick={onSelect}
      className={`
        bg-white border rounded-2xl transition-all duration-200 cursor-pointer select-none overflow-hidden
        ${
          isSelected
            ? 'border-teal ring-4 ring-teal/15 shadow-md'
            : 'border-border hover:border-teal/50 hover:shadow-sm'
        }
        ${className}
      `}
    >
      {/* Top recommendation indicator */}
      {isRecommended && (
        <div className="bg-teal/10 px-4 py-2 border-b border-teal/15 flex items-center justify-between text-xs font-bold text-teal">
          <div className="flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-teal animate-pulse" />
            <span>
              {lang === 'hi'
                ? `अनुशंसित विकल्प (${prefLabel})`
                : `Recommended for ${prefLabel}`}
            </span>
          </div>
          {onOpenWhyModal && (
            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation();
                onOpenWhyModal(option);
              }}
              className="inline-flex items-center gap-1 text-[11px] bg-white px-2 py-0.5 rounded-full border border-teal/30 hover:bg-teal hover:text-white transition-colors"
              title={lang === 'hi' ? 'स्कोरिंग विवरण' : 'Why this route'}
            >
              <HelpCircle className="w-3.5 h-3.5" />
              <span>{lang === 'hi' ? 'कारण' : 'Why'}</span>
            </button>
          )}
        </div>
      )}

      {/* Main Scannable Row */}
      <div className="p-4 sm:p-5 flex items-start justify-between gap-4">
        {/* Left: Route, Scheduled Time, and Destination */}
        <div className="space-y-2 flex-1 min-w-0">
          <div className="flex flex-wrap items-center gap-2.5">
            <RouteBadge routeNumber={routeNum} size="lg" />
            <div className="flex flex-col">
              <span className="text-xs sm:text-sm font-bold text-navy">
                {lang === 'hi'
                  ? `प्रस्थान ${depTime} · निर्धारित`
                  : `Leaves ${depTime} · scheduled`}
              </span>
              {distKm && (
                <span className="text-[11px] text-tx-muted font-medium">
                  {distKm} km {stopsCount ? `· ${stopsCount} stops` : ''}
                </span>
              )}
            </div>
          </div>

          <div className="text-xs text-tx-muted font-medium truncate">
            {option.route_long_name || `Delhi Bus Route ${routeNum}`}
          </div>

          {/* Crowding Indicators: Boarding stop + Busiest segment */}
          <div className="pt-1.5 flex flex-wrap items-center gap-x-5 gap-y-2 text-xs">
            <div className="flex items-center gap-1.5">
              <span className="text-[11px] text-tx-muted font-semibold">
                {lang === 'hi' ? 'स्टॉप पर:' : 'At stop:'}
              </span>
              <CrowdIndicator
                category={crowdOrigin}
                occupancyPercent={option.occupancy_percent || null}
                size="sm"
              />
            </div>

            <div className="flex items-center gap-1.5">
              <span className="text-[11px] text-tx-muted font-semibold">
                {lang === 'hi' ? 'अधिकतम भीड़:' : 'Busiest part:'}
              </span>
              <CrowdIndicator
                category={peakCrowd}
                size="sm"
              />
            </div>
          </div>
        </div>

        {/* Right: Duration (Bold Poster Number) & Expand Toggle */}
        <div className="flex flex-col items-end justify-between self-stretch shrink-0">
          <div className="text-right">
            <div className="text-3xl sm:text-4xl font-black text-navy tabular-nums leading-none tracking-tight">
              {totalMin}
            </div>
            <div className="text-[11px] font-bold text-tx-muted uppercase tracking-wider mt-0.5">
              {t('results.min')}
            </div>
          </div>

          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation();
              setIsExpanded(!isExpanded);
            }}
            className="p-1.5 text-tx-muted hover:text-navy hover:bg-[#F3ECE8] rounded-full mt-3 transition-colors min-w-[36px] min-h-[36px] flex items-center justify-center focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-teal"
            aria-label={isExpanded ? 'Collapse journey details' : 'Expand journey details'}
          >
            {isExpanded ? <ChevronUp className="w-5 h-5" /> : <ChevronDown className="w-5 h-5" />}
          </button>
        </div>
      </div>

      {/* Inline Expander (Time Breakdown, Transfers & Route Link) */}
      {isExpanded && (
        <div
          className="px-3.5 sm:px-4 pb-3.5 sm:pb-4 pt-2.5 border-t border-border space-y-3 bg-surface-bg/40 text-xs"
          onClick={(e) => e.stopPropagation()}
        >
          {/* Time breakdown visual bar */}
          <div className="space-y-1">
            <div className="flex items-center justify-between text-xs">
              <span className="font-semibold text-navy">
                {lang === 'hi' ? 'समय का विभाजन' : 'Time breakdown'}
              </span>
              <span className="text-tx-muted text-[11px]">
                {lang === 'hi' ? 'सीधा रूट (0 बदलाव)' : 'Direct route (0 transfers)'}
              </span>
            </div>
            <TimeBreakdownBar
              walkMinutes={walkMin}
              waitMinutes={waitMin}
              rideMinutes={rideMin}
            />
          </div>

          {/* Confidence and Crowding explanation */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-tx-muted pt-1">
            <div className="p-2.5 bg-surface border border-border rounded-[var(--radius-control)]">
              <span className="block text-[10px] uppercase font-semibold text-tx-muted">
                {lang === 'hi' ? 'डेटा विश्वसनीयता' : 'Data confidence'}
              </span>
              <span className="text-tx font-medium text-xs">
                {getConfidenceText(option.confidence)}
              </span>
            </div>

            <div className="p-2.5 bg-surface border border-border rounded-[var(--radius-control)]">
              <span className="block text-[10px] uppercase font-semibold text-tx-muted">
                {lang === 'hi' ? 'कॉरिडोर दूरी व स्टॉप' : 'Corridor stops'}
              </span>
              <span className="text-tx font-medium text-xs">
                {stopsCount ? `${stopsCount} ${lang === 'hi' ? 'स्टॉप' : 'stops'}` : 'Direct'} {distKm ? `· ${distKm} km` : ''}
              </span>
            </div>
          </div>

          {/* Action links */}
          <div className="flex flex-wrap items-center justify-between gap-2 pt-1 border-t border-border/50">
            {onOpenWhyModal && (
              <button
                type="button"
                onClick={() => onOpenWhyModal(option)}
                className="inline-flex items-center gap-1 text-teal hover:underline font-semibold text-xs min-h-[36px]"
              >
                <span>{lang === 'hi' ? 'स्कोरिंग विवरण देखें' : 'View scoring breakdown'}</span>
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
