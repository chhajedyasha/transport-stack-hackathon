import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  MapPin,
  Clock,
  ArrowRightLeft,
  Search,
  Sparkles,
  Zap,
  Sliders,
  ShieldCheck,
  Armchair,
  UserCheck,
  Users,
  Compass,
} from 'lucide-react';
import { searchStops } from '../api';
import ProvenanceBadge from '../components/ProvenanceBadge';

export default function PlannerPage() {
  const navigate = useNavigate();

  // Search form state
  const [originQuery, setOriginQuery] = useState('');
  const [originStop, setOriginStop] = useState(null);
  const [originSuggestions, setOriginSuggestions] = useState([]);
  const [showOriginDropdown, setShowOriginDropdown] = useState(false);

  const [destQuery, setDestQuery] = useState('');
  const [destStop, setDestStop] = useState(null);
  const [destSuggestions, setDestSuggestions] = useState([]);
  const [showDestDropdown, setShowDestDropdown] = useState(false);

  const [departureTime, setDepartureTime] = useState('18:00');
  const [preference, setPreference] = useState('balanced');
  const [isSearching, setIsSearching] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');

  const originRef = useRef(null);
  const destRef = useRef(null);

  // Debounced search for Origin
  useEffect(() => {
    if (!originQuery || originStop?.stop_name === originQuery) {
      setOriginSuggestions([]);
      return;
    }
    const timer = setTimeout(async () => {
      try {
        const matches = await searchStops(originQuery);
        setOriginSuggestions(matches);
        setShowOriginDropdown(true);
      } catch (e) {
        console.error(e);
      }
    }, 200);
    return () => clearTimeout(timer);
  }, [originQuery, originStop]);

  // Debounced search for Dest
  useEffect(() => {
    if (!destQuery || destStop?.stop_name === destQuery) {
      setDestSuggestions([]);
      return;
    }
    const timer = setTimeout(async () => {
      try {
        const matches = await searchStops(destQuery);
        setDestSuggestions(matches);
        setShowDestDropdown(true);
      } catch (e) {
        console.error(e);
      }
    }, 200);
    return () => clearTimeout(timer);
  }, [destQuery, destStop]);

  // Close dropdowns on click outside
  useEffect(() => {
    function handleClickOutside(event) {
      if (originRef.current && !originRef.current.contains(event.target)) {
        setShowOriginDropdown(false);
      }
      if (destRef.current && !destRef.current.contains(event.target)) {
        setShowDestDropdown(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Quick fill showcase route
  const handleQuickFillShowcase = () => {
    setOriginQuery('Anand Vihar ISBT Terminal');
    setOriginStop({ stop_id: '8256', stop_name: 'Anand Vihar ISBT Terminal' });
    setDestQuery('Shivaji Stadium Terminal ( Connaught Place )');
    setDestStop({ stop_id: '365', stop_name: 'Shivaji Stadium Terminal ( Connaught Place )' });
    setDepartureTime('18:00');
    setPreference('balanced');
  };

  const handleSwap = () => {
    const tempQ = originQuery;
    const tempStop = originStop;
    setOriginQuery(destQuery);
    setOriginStop(destStop);
    setDestQuery(tempQ);
    setDestStop(tempStop);
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    setErrorMsg('');

    const originId = originStop?.stop_id || originQuery;
    const destId = destStop?.stop_id || destQuery;

    if (!originId || !destId) {
      setErrorMsg('Please enter both an origin and a destination stop.');
      return;
    }

    setIsSearching(true);
    const params = new URLSearchParams({
      origin_id: originId,
      origin_name: originStop?.stop_name || originQuery,
      dest_id: destId,
      dest_name: destStop?.stop_name || destQuery,
      departure_time: departureTime,
      preference: preference,
    });
    navigate(`/results?${params.toString()}`);
  };

  return (
    <div className="space-y-12 py-6">
      {/* Hero & Planner Container */}
      <section className="relative overflow-hidden rounded-3xl bg-gradient-to-b from-brand-navy via-[#0c2445] to-slate-900 text-white p-6 sm:p-10 shadow-xl border border-slate-700/50">
        <div className="max-w-3xl mx-auto space-y-6 text-center">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-teal-500/10 border border-teal-500/30 text-teal-300 text-xs font-semibold">
            <Sparkles className="w-3.5 h-3.5" />
            Transport Stack Hackathon 2026 Showcase
          </div>

          <h1 className="text-3xl sm:text-5xl font-black tracking-tight leading-tight">
            Know how crowded your Delhi bus is <br className="hidden sm:inline" />
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-teal-300 to-emerald-400">
              before you board.
            </span>
          </h1>

          <p className="text-slate-300 text-sm sm:text-base max-w-2xl mx-auto">
            Traditional journey planners rank routes solely on travel time. CrowdWise models 4 weeks of Delhi ETM
            ticketing records to predict real-time bus crowdedness stretch-by-stretch.
          </p>

          {/* Quick Showcase Button */}
          <div className="pt-2">
            <button
              type="button"
              onClick={handleQuickFillShowcase}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-white/10 hover:bg-white/20 text-teal-200 hover:text-white border border-teal-400/30 text-xs font-semibold backdrop-blur-sm transition-all"
            >
              <Zap className="w-4 h-4 text-amber-400" />
              <span>Try Hackathon Showcase: Anand Vihar → Connaught Place (6:00 PM)</span>
            </button>
          </div>
        </div>

        {/* Planner Card */}
        <div className="mt-8 max-w-4xl mx-auto bg-white rounded-2xl p-6 sm:p-8 shadow-2xl text-slate-800 border border-slate-100">
          <form onSubmit={handleSubmit} className="space-y-6">
            {errorMsg && (
              <div className="p-3 rounded-xl bg-red-50 text-red-700 text-xs font-medium border border-red-200">
                {errorMsg}
              </div>
            )}

            <div className="grid grid-cols-1 md:grid-cols-12 gap-3 items-center">
              {/* Origin Stop */}
              <div ref={originRef} className="relative md:col-span-5">
                <label className="block text-xs font-bold text-slate-500 uppercase tracking-wider mb-1">
                  Origin Bus Stop
                </label>
                <div className="relative">
                  <MapPin className="absolute left-3.5 top-3.5 w-4 h-4 text-emerald-600 pointer-events-none" />
                  <input
                    type="text"
                    required
                    placeholder="e.g. Anand Vihar ISBT"
                    value={originQuery}
                    onChange={(e) => {
                      setOriginQuery(e.target.value);
                      setOriginStop(null);
                    }}
                    onFocus={() => setShowOriginDropdown(true)}
                    className="w-full pl-10 pr-4 py-3 rounded-xl border border-slate-300 focus:outline-none focus:ring-2 focus:ring-brand-teal focus:border-transparent text-sm font-medium"
                  />
                </div>

                {/* Autocomplete Dropdown */}
                {showOriginDropdown && originSuggestions.length > 0 && (
                  <ul className="absolute left-0 right-0 mt-1 bg-white border border-slate-200 rounded-xl shadow-xl max-h-56 overflow-y-auto z-40 divide-y divide-slate-100">
                    {originSuggestions.map((s) => (
                      <li
                        key={s.stop_id}
                        onClick={() => {
                          setOriginStop(s);
                          setOriginQuery(s.stop_name);
                          setShowOriginDropdown(false);
                        }}
                        className="p-3 hover:bg-slate-50 cursor-pointer text-xs flex items-center justify-between"
                      >
                        <div className="font-semibold text-slate-800">{s.stop_name}</div>
                        <span className="text-[10px] text-slate-400 font-mono">{s.stop_id}</span>
                      </li>
                    ))}
                  </ul>
                )}
              </div>

              {/* Swap Button */}
              <div className="flex justify-center md:col-span-2 pt-2 md:pt-4">
                <button
                  type="button"
                  onClick={handleSwap}
                  className="p-2.5 rounded-full bg-slate-100 hover:bg-slate-200 text-slate-600 transition-colors shadow-sm"
                  title="Swap Origin & Destination"
                >
                  <ArrowRightLeft className="w-4 h-4" />
                </button>
              </div>

              {/* Destination Stop */}
              <div ref={destRef} className="relative md:col-span-5">
                <label className="block text-xs font-bold text-slate-500 uppercase tracking-wider mb-1">
                  Destination Bus Stop
                </label>
                <div className="relative">
                  <MapPin className="absolute left-3.5 top-3.5 w-4 h-4 text-red-500 pointer-events-none" />
                  <input
                    type="text"
                    required
                    placeholder="e.g. Connaught Place"
                    value={destQuery}
                    onChange={(e) => {
                      setDestQuery(e.target.value);
                      setDestStop(null);
                    }}
                    onFocus={() => setShowDestDropdown(true)}
                    className="w-full pl-10 pr-4 py-3 rounded-xl border border-slate-300 focus:outline-none focus:ring-2 focus:ring-brand-teal focus:border-transparent text-sm font-medium"
                  />
                </div>

                {/* Autocomplete Dropdown */}
                {showDestDropdown && destSuggestions.length > 0 && (
                  <ul className="absolute left-0 right-0 mt-1 bg-white border border-slate-200 rounded-xl shadow-xl max-h-56 overflow-y-auto z-40 divide-y divide-slate-100">
                    {destSuggestions.map((s) => (
                      <li
                        key={s.stop_id}
                        onClick={() => {
                          setDestStop(s);
                          setDestQuery(s.stop_name);
                          setShowDestDropdown(false);
                        }}
                        className="p-3 hover:bg-slate-50 cursor-pointer text-xs flex items-center justify-between"
                      >
                        <div className="font-semibold text-slate-800">{s.stop_name}</div>
                        <span className="text-[10px] text-slate-400 font-mono">{s.stop_id}</span>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            </div>

            {/* Time & Preference Controls */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-2 border-t border-slate-100">
              <div>
                <label className="block text-xs font-bold text-slate-500 uppercase tracking-wider mb-1">
                  Departure Time
                </label>
                <div className="relative">
                  <Clock className="absolute left-3.5 top-3.5 w-4 h-4 text-slate-400 pointer-events-none" />
                  <input
                    type="time"
                    value={departureTime}
                    onChange={(e) => setDepartureTime(e.target.value)}
                    className="w-full pl-10 pr-4 py-2.5 rounded-xl border border-slate-300 text-sm font-medium focus:outline-none focus:ring-2 focus:ring-brand-teal"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-500 uppercase tracking-wider mb-1">
                  Commute Preference
                </label>
                <div className="grid grid-cols-3 gap-1.5 p-1 bg-slate-100 rounded-xl">
                  <button
                    type="button"
                    onClick={() => setPreference('fastest')}
                    className={`py-2 text-xs font-bold rounded-lg transition-all ${
                      preference === 'fastest'
                        ? 'bg-white text-brand-navy shadow-sm'
                        : 'text-slate-600 hover:text-brand-navy'
                    }`}
                  >
                    Fastest
                  </button>
                  <button
                    type="button"
                    onClick={() => setPreference('balanced')}
                    className={`py-2 text-xs font-bold rounded-lg transition-all ${
                      preference === 'balanced'
                        ? 'bg-white text-brand-navy shadow-sm'
                        : 'text-slate-600 hover:text-brand-navy'
                    }`}
                  >
                    Balanced
                  </button>
                  <button
                    type="button"
                    onClick={() => setPreference('least_crowded')}
                    className={`py-2 text-xs font-bold rounded-lg transition-all ${
                      preference === 'least_crowded'
                        ? 'bg-white text-brand-navy shadow-sm'
                        : 'text-slate-600 hover:text-brand-navy'
                    }`}
                  >
                    Least Crowded
                  </button>
                </div>
              </div>
            </div>

            {/* Submit Button */}
            <div className="pt-2">
              <button
                type="submit"
                disabled={isSearching}
                className="w-full py-4 rounded-xl bg-brand-teal hover:bg-brand-tealHover text-white font-bold text-base shadow-lg shadow-teal-500/20 hover:shadow-teal-500/30 transition-all flex items-center justify-center gap-2"
              >
                <Search className="w-5 h-5" />
                <span>{isSearching ? 'Finding Comfort Options...' : 'Find Crowdedness-Aware Routes'}</span>
              </button>
            </div>
          </form>
        </div>
      </section>

      {/* 3 Pillars Explanatory Cards */}
      <section className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="bg-white rounded-2xl p-6 border border-slate-200 shadow-sm space-y-3">
          <div className="w-10 h-10 rounded-xl bg-emerald-50 text-emerald-600 flex items-center justify-center font-bold">
            <Armchair className="w-5 h-5" />
          </div>
          <h2 className="text-base font-bold text-brand-navy">Tri-Level Comfort Taxonomy</h2>
          <p className="text-xs text-slate-600 leading-relaxed">
            Directly mapped to commuter reality: <strong>Seats Available</strong> (low),{' '}
            <strong>Standing Room</strong> (moderate), and <strong>Crowded</strong> (high), using calibrated Relative
            Crowding Index (RCI 0–100).
          </p>
        </div>

        <div className="bg-white rounded-2xl p-6 border border-slate-200 shadow-sm space-y-3">
          <div className="w-10 h-10 rounded-xl bg-amber-50 text-amber-600 flex items-center justify-center font-bold">
            <Sliders className="w-5 h-5" />
          </div>
          <h2 className="text-base font-bold text-brand-navy">Multi-Objective Trade-Offs</h2>
          <p className="text-xs text-slate-600 leading-relaxed">
            Choose whether to save 10 minutes or secure a seat. Our detour filter caps out-of-the-way options at 1.5×
            travel time so recommendations stay practical.
          </p>
        </div>

        <div className="bg-white rounded-2xl p-6 border border-slate-200 shadow-sm space-y-3">
          <div className="w-10 h-10 rounded-xl bg-blue-50 text-brand-teal flex items-center justify-center font-bold">
            <ShieldCheck className="w-5 h-5" />
          </div>
          <h2 className="text-base font-bold text-brand-navy">Empirical Data Provenance</h2>
          <p className="text-xs text-slate-600 leading-relaxed">
            Trained on 2.56M October 2026 Delhi ETM records. Anonymized under DPDP Act 2023 with salted HMAC-SHA-256
            hashes and transparent data provenance tiers.
          </p>
        </div>
      </section>
    </div>
  );
}

