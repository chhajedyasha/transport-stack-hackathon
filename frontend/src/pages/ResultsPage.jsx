import React, { useState, useEffect } from 'react';
import { useLocation, useNavigate, Link } from 'react-router-dom';
import {
  ArrowLeft,
  Clock,
  MapPin,
  Sparkles,
  Sliders,
  ChevronDown,
  ChevronUp,
  Bus,
  ArrowRight,
  Info,
  CheckCircle2,
} from 'lucide-react';
import { planJourney } from '../api';
import CrowdBadge from '../components/CrowdBadge';
import ProvenanceBadge from '../components/ProvenanceBadge';
import CorridorHeatStrip from '../components/CorridorHeatStrip';
import LeafletRouteMap from '../components/LeafletRouteMap';
import WhyThisRouteModal from '../components/WhyThisRouteModal';

export default function ResultsPage() {
  const location = useLocation();
  const navigate = useNavigate();
  const queryParams = new URLSearchParams(location.search);

  const originId = queryParams.get('origin_id') || 'STOP_ANAND_VIHAR';
  const originName = queryParams.get('origin_name') || originId;
  const destId = queryParams.get('dest_id') || 'STOP_CONNAUGHT_PLACE';
  const destName = queryParams.get('dest_name') || destId;
  const departureTime = queryParams.get('departure_time') || '18:00';
  const initialPref = queryParams.get('preference') || 'balanced';

  const [preference, setPreference] = useState(initialPref);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [planData, setPlanData] = useState(null);
  const [selectedOptionIndex, setSelectedOptionIndex] = useState(0);
  const [expandedOptionIndex, setExpandedOptionIndex] = useState(null);
  const [modalOption, setModalOption] = useState(null);

  useEffect(() => {
    let isMounted = true;
    setLoading(true);
    setError(null);

    planJourney({
      originId,
      destId,
      departureTime,
      preference,
    })
      .then((res) => {
        if (isMounted) {
          setPlanData(res.data);
          setSelectedOptionIndex(0);
          setLoading(false);
        }
      })
      .catch((err) => {
        if (isMounted) {
          setError(err.message || 'Failed to compute journey options.');
          setLoading(false);
        }
      });

    return () => {
      isMounted = false;
    };
  }, [originId, destId, departureTime, preference]);

  const options = planData?.options || [];
  const selectedOption = options[selectedOptionIndex] || options[0];
  const fastestOption = planData?.fastest_baseline || options[0];

  return (
    <div className="space-y-6 py-6">
      {/* Top Navigation & Query Breadcrumb */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-white p-4 sm:p-6 rounded-2xl border border-slate-200 shadow-sm">
        <div className="flex items-center gap-4">
          <Link
            to="/"
            className="p-2 rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-700 transition-colors"
            title="Modify Search"
          >
            <ArrowLeft className="w-5 h-5" />
          </Link>
          <div>
            <div className="flex items-center gap-2 text-xs font-bold text-slate-500 uppercase tracking-wider">
              <span>{originName}</span>
              <ArrowRight className="w-3.5 h-3.5 text-brand-teal" />
              <span>{destName}</span>
            </div>
            <div className="flex items-center gap-3 mt-1 text-xs text-slate-600">
              <span className="flex items-center gap-1">
                <Clock className="w-3.5 h-3.5 text-slate-400" /> Departs {departureTime}
              </span>
              <span>•</span>
              <ProvenanceBadge tier={planData?.meta?.active_tier || 'estimated'} size="xs" />
            </div>
          </div>
        </div>

        {/* Preference Selector */}
        <div className="flex items-center gap-2">
          <span className="text-xs font-semibold text-slate-500">Ranking:</span>
          <div className="grid grid-cols-3 gap-1 bg-slate-100 p-1 rounded-xl text-xs font-bold">
            {['fastest', 'balanced', 'least_crowded'].map((p) => (
              <button
                key={p}
                onClick={() => setPreference(p)}
                className={`px-3 py-1.5 rounded-lg capitalize transition-all ${
                  preference === p
                    ? 'bg-brand-navy text-white shadow-sm'
                    : 'text-slate-600 hover:text-brand-navy'
                }`}
              >
                {p.replace('_', ' ')}
              </button>
            ))}
          </div>
        </div>
      </div>

      {loading ? (
        <div className="bg-white rounded-2xl p-12 text-center space-y-4 border border-slate-200 shadow-sm">
          <div className="w-12 h-12 border-4 border-brand-teal border-t-transparent rounded-full animate-spin mx-auto"></div>
          <p className="text-sm font-semibold text-slate-700">Estimating route crowding profiles...</p>
          <p className="text-xs text-slate-400">Loading GTFS patterns and executing Random Forest inference</p>
        </div>
      ) : error ? (
        <div className="bg-white rounded-2xl p-8 text-center space-y-3 border border-red-200 shadow-sm text-red-600">
          <p className="font-bold text-base">Journey Calculation Error</p>
          <p className="text-xs text-slate-600 max-w-md mx-auto">{error}</p>
          <Link
            to="/"
            className="inline-block mt-2 px-4 py-2 rounded-xl bg-slate-100 hover:bg-slate-200 text-xs font-bold text-slate-700"
          >
            Try another route
          </Link>
        </div>
      ) : options.length === 0 ? (
        <div className="bg-white rounded-2xl p-8 text-center space-y-2 border border-slate-200 shadow-sm">
          <p className="font-bold text-base text-slate-800">No direct bus routes found</p>
          <p className="text-xs text-slate-500">Try searching with nearby stops or check Anand Vihar showcase.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
          {/* Left Column: Route Option Cards (7 cols) */}
          <div className="lg:col-span-7 space-y-4">
            <div className="flex items-center justify-between text-xs text-slate-500 px-1">
              <span className="font-bold uppercase tracking-wider text-slate-600">
                Found {options.length} Journey Option{options.length > 1 ? 's' : ''}
              </span>
              <span>Sorted by {preference.replace('_', ' ')} score</span>
            </div>

            {/* Option Cards */}
            {options.map((opt, idx) => {
              const isSelected = selectedOptionIndex === idx;
              const isExpanded = expandedOptionIndex === idx;

              return (
                <div
                  key={opt.trip_id || idx}
                  className={`bg-white rounded-2xl p-5 border transition-all cursor-pointer relative ${
                    isSelected
                      ? 'border-brand-teal ring-2 ring-brand-teal/20 shadow-md'
                      : 'border-slate-200 hover:border-slate-300 shadow-sm'
                  }`}
                  onClick={() => setSelectedOptionIndex(idx)}
                >
                  {/* Top Badge: Recommendation */}
                  {idx === 0 && (
                    <div className="absolute -top-3 right-5 inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full bg-brand-teal text-white text-[10px] font-bold shadow-sm">
                      <Sparkles className="w-3 h-3" />
                      Recommended Option
                    </div>
                  )}

                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                    <div className="flex items-center gap-3">
                      <div className="w-12 h-12 rounded-xl bg-slate-100 border border-slate-200 flex flex-col items-center justify-center font-black text-brand-navy">
                        <Bus className="w-4 h-4 text-slate-500" />
                        <span className="text-xs leading-none mt-0.5">{opt.route_short_name || opt.route_id}</span>
                      </div>
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="font-extrabold text-base text-brand-navy">
                            {opt.route_long_name || `Bus Route ${opt.route_short_name || opt.route_id}`}
                          </span>
                        </div>
                        <p className="text-xs text-slate-500">
                          Departs ~{opt.departure_time || departureTime} • {opt.stops_count || 12} stops
                        </p>
                      </div>
                    </div>

                    <div className="flex sm:flex-col items-end justify-between sm:justify-center gap-1">
                      <div className="text-right">
                        <span className="text-2xl font-black text-brand-navy leading-none">
                          {opt.total_duration_minutes}
                        </span>
                        <span className="text-xs font-semibold text-slate-500 ml-1">min</span>
                      </div>
                      <div className="text-[11px] text-slate-400">
                        Ride: {opt.ride_time_minutes || opt.total_duration_minutes}m • Wait: {opt.wait_time_minutes || 0}m
                      </div>
                    </div>
                  </div>

                  {/* Crowdedness Status Row */}
                  <div className="mt-4 pt-3 border-t border-slate-100 flex flex-wrap items-center justify-between gap-2">
                    <CrowdBadge
                      label={opt.crowd_category}
                      rci={opt.avg_rci}
                      confidence={opt.confidence}
                      size="md"
                    />

                    <div className="flex items-center gap-2">
                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation();
                          setModalOption(opt);
                        }}
                        className="inline-flex items-center gap-1 text-xs font-semibold text-brand-teal hover:text-brand-tealHover bg-teal-50 px-2.5 py-1 rounded-lg border border-teal-200 transition-colors"
                      >
                        <Info className="w-3.5 h-3.5" />
                        Why this route?
                      </button>

                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation();
                          setExpandedOptionIndex(isExpanded ? null : idx);
                        }}
                        className="p-1 text-slate-400 hover:text-slate-600 rounded-lg hover:bg-slate-100"
                        title={isExpanded ? 'Collapse Details' : 'Expand Details'}
                      >
                        {isExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                      </button>
                    </div>
                  </div>

                  {/* 8-Zone Heat Strip inside option card */}
                  <div className="mt-3">
                    <CorridorHeatStrip zones={opt.zone_forecasts} title="" />
                  </div>

                  {/* Expanded Stop-by-Stop Breakdown */}
                  {isExpanded && (
                    <div className="mt-4 pt-4 border-t border-slate-100 space-y-3 text-xs animate-fade-in">
                      <h4 className="font-bold text-slate-700">Detailed Corridor Breakdown</h4>
                      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-slate-600">
                        <div className="p-2.5 bg-slate-50 rounded-lg">
                          <span className="text-[10px] text-slate-400 block uppercase">Peak Load</span>
                          <strong className="text-slate-800 text-sm">{Math.round(opt.peak_load || 0)} pass.</strong>
                        </div>
                        <div className="p-2.5 bg-slate-50 rounded-lg">
                          <span className="text-[10px] text-slate-400 block uppercase">Average RCI</span>
                          <strong className="text-slate-800 text-sm">{Math.round(opt.avg_rci || 0)} / 100</strong>
                        </div>
                        <div className="p-2.5 bg-slate-50 rounded-lg">
                          <span className="text-[10px] text-slate-400 block uppercase">Detour Ratio</span>
                          <strong className="text-slate-800 text-sm">
                            {(opt.total_duration_minutes / Math.max(fastestOption.total_duration_minutes, 1)).toFixed(2)}×
                          </strong>
                        </div>
                        <div className="p-2.5 bg-slate-50 rounded-lg">
                          <span className="text-[10px] text-slate-400 block uppercase">Seats Chance</span>
                          <strong className="text-slate-800 text-sm">
                            {opt.avg_rci < 50 ? 'High (>80%)' : opt.avg_rci < 85 ? 'Moderate (~40%)' : 'Low (<15%)'}
                          </strong>
                        </div>
                      </div>

                      <div className="pt-2">
                        <Link
                          to={`/route/${encodeURIComponent(opt.route_id)}`}
                          className="inline-flex items-center gap-1.5 text-xs font-bold text-brand-teal hover:underline"
                        >
                          View 24h Route Crowding Profile <ArrowRight className="w-3.5 h-3.5" />
                        </Link>
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>

          {/* Right Column: Interactive Map & Comparison Summary (5 cols) */}
          <div className="lg:col-span-5 space-y-4 lg:sticky lg:top-20">
            {/* Interactive Leaflet Map Preview */}
            <div className="bg-white rounded-2xl p-4 border border-slate-200 shadow-sm space-y-3">
              <div className="flex items-center justify-between text-xs">
                <span className="font-bold text-slate-700">
                  Route Preview: Bus {selectedOption?.route_short_name || selectedOption?.route_id}
                </span>
                <span className="text-slate-400 font-mono text-[11px]">{selectedOption?.route_id}</span>
              </div>

              <LeafletRouteMap
                stops={selectedOption?.stops || []}
                shapePoints={selectedOption?.shape_points || []}
                highlightOrigin={originId}
                highlightDest={destId}
                height="320px"
              />

              <div className="flex items-center justify-between text-[11px] text-slate-500 pt-1">
                <span className="flex items-center gap-1">
                  <span className="w-2.5 h-2.5 rounded-full bg-emerald-500"></span> Boarding
                </span>
                <span className="flex items-center gap-1">
                  <span className="w-2.5 h-2.5 rounded-full bg-red-500"></span> Alighting
                </span>
                <span className="flex items-center gap-1">
                  <span className="w-4 h-1 bg-brand-teal rounded"></span> Bus Path
                </span>
              </div>
            </div>

            {/* Side-by-Side Comparison Matrix */}
            <div className="bg-white rounded-2xl p-5 border border-slate-200 shadow-sm space-y-3">
              <h3 className="font-bold text-sm text-brand-navy">Comfort vs. Travel Time Matrix</h3>
              <p className="text-xs text-slate-500">Compare top alternatives at a glance:</p>

              <div className="divide-y divide-slate-100 text-xs">
                {options.slice(0, 3).map((opt, i) => (
                  <div key={i} className="py-2.5 flex items-center justify-between gap-2">
                    <div className="space-y-0.5">
                      <span className="font-bold text-slate-800">Bus {opt.route_short_name || opt.route_id}</span>
                      <p className="text-[11px] text-slate-400">{opt.total_duration_minutes} min</p>
                    </div>
                    <CrowdBadge label={opt.crowd_category} rci={opt.avg_rci} size="sm" showRci={false} />
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Why This Route Modal */}
      {modalOption && (
        <WhyThisRouteModal
          option={modalOption}
          fastestOption={fastestOption}
          preference={preference}
          onClose={() => setModalOption(null)}
        />
      )}
    </div>
  );
}
