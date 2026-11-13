import React, { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import {
  Bus,
  Clock,
  MapPin,
  Calendar,
  ArrowRight,
  TrendingUp,
  AlertCircle,
  Activity,
  Layers,
  ChevronRight,
} from 'lucide-react';
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';
import { getRouteDetails, getRouteCrowdProfile } from '../api';
import ProvenanceBadge from '../components/ProvenanceBadge';
import CrowdBadge from '../components/CrowdBadge';
import CorridorHeatStrip from '../components/CorridorHeatStrip';
import LeafletRouteMap from '../components/LeafletRouteMap';

export default function RouteDetailsPage() {
  const { id: routeId = '101UP' } = useParams();

  const [routeInfo, setRouteInfo] = useState(null);
  const [profileData, setProfileData] = useState(null);
  const [dayType, setDayType] = useState('WEEKDAY');
  const [selectedDirection, setSelectedDirection] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let isMounted = true;
    setLoading(true);
    setError(null);

    Promise.all([
      getRouteDetails(routeId).catch((err) => ({ ok: false, error: err })),
      getRouteCrowdProfile(routeId, dayType).catch((err) => ({ ok: false, error: err })),
    ])
      .then(([routeRes, profileRes]) => {
        if (!isMounted) return;
        if (routeRes.ok && routeRes.data) {
          setRouteInfo(routeRes.data);
        }
        if (profileRes.ok && profileRes.data) {
          setProfileData(profileRes.data);
        }
        setLoading(false);
      })
      .catch((err) => {
        if (!isMounted) return;
        setError(err.message || 'Failed to load route details.');
        setLoading(false);
      });

    return () => {
      isMounted = false;
    };
  }, [routeId, dayType]);

  // Format 24-hour chart data
  const chartData = (profileData?.hourly_profile || []).map((h) => ({
    hour: `${h.hour}:00`,
    hourNum: h.hour,
    mean_load: Math.round(h.mean_load || 0),
    max_load: Math.round(h.max_load || 0),
    rci: Math.round(h.rci || 0),
    category: h.crowd_category || 'Seats Available',
  }));

  const stops = routeInfo?.stops || [];
  const patterns = routeInfo?.patterns || [];

  return (
    <div className="space-y-6 py-6">
      {/* Route Header Banner */}
      <div className="bg-white rounded-2xl p-6 border border-slate-200 shadow-sm space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="flex items-center gap-4">
            <div className="w-14 h-14 rounded-2xl bg-brand-navy text-white flex flex-col items-center justify-center font-black shadow-md">
              <Bus className="w-5 h-5 text-teal-300" />
              <span className="text-sm mt-0.5">{routeInfo?.route_short_name || routeId}</span>
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-2xl font-black text-brand-navy">
                  {routeInfo?.route_long_name || `Bus Route ${routeId}`}
                </h1>
                <ProvenanceBadge tier="real_public" label="GTFS Route" size="xs" />
              </div>
              <p className="text-xs text-slate-500 mt-1">
                Agency: {routeInfo?.agency_name || 'DTC Delhi'} • Pattern ID: {routeInfo?.pattern_id || 'PAT_01'} •{' '}
                {stops.length} stops mapped
              </p>
            </div>
          </div>

          {/* Quick Route Selector */}
          <div className="flex items-center gap-2">
            <span className="text-xs text-slate-400 font-semibold">Demo Routes:</span>
            {['101UP', '101DN', '8UP'].map((r) => (
              <Link
                key={r}
                to={`/route/${r}`}
                className={`px-2.5 py-1 rounded-lg text-xs font-bold transition-all ${
                  routeId === r
                    ? 'bg-brand-teal text-white shadow-sm'
                    : 'bg-slate-100 hover:bg-slate-200 text-slate-600'
                }`}
              >
                {r}
              </Link>
            ))}
          </div>
        </div>

        {/* Day Type and Direction Selectors */}
        <div className="flex flex-wrap items-center justify-between gap-3 pt-3 border-t border-slate-100 text-xs">
          <div className="flex items-center gap-2">
            <span className="font-semibold text-slate-500">Day Type:</span>
            <div className="flex bg-slate-100 p-1 rounded-xl font-bold">
              {['WEEKDAY', 'SATURDAY', 'SUNDAY'].map((dt) => (
                <button
                  key={dt}
                  onClick={() => setDayType(dt)}
                  className={`px-3 py-1 rounded-lg capitalize transition-all ${
                    dayType === dt
                      ? 'bg-brand-navy text-white shadow-sm'
                      : 'text-slate-600 hover:text-brand-navy'
                  }`}
                >
                  {dt.toLowerCase()}
                </button>
              ))}
            </div>
          </div>

          <div className="flex items-center gap-2 text-slate-500">
            <Activity className="w-4 h-4 text-brand-teal" />
            <span>Peak window: <strong>08:00–10:00 AM &amp; 17:00–20:00 PM</strong></span>
          </div>
        </div>
      </div>

      {loading ? (
        <div className="bg-white rounded-2xl p-12 text-center space-y-4 border border-slate-200">
          <div className="w-10 h-10 border-4 border-brand-teal border-t-transparent rounded-full animate-spin mx-auto"></div>
          <p className="text-sm font-semibold text-slate-600">Loading route corridor telemetry...</p>
        </div>
      ) : error ? (
        <div className="bg-white rounded-2xl p-8 text-center text-red-600 border border-red-200">
          <p className="font-bold">{error}</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          {/* Left Column: Heat Strip & 24h Chart (7 cols) */}
          <div className="lg:col-span-7 space-y-6">
            {/* 8-Zone Corridor Heat Strip */}
            <div className="bg-white rounded-2xl p-6 border border-slate-200 shadow-sm space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="font-bold text-base text-brand-navy">8-Zone Corridor Heat Distribution</h3>
                  <p className="text-xs text-slate-500">Aggregated passenger loads along stop stretches</p>
                </div>
                <ProvenanceBadge tier="estimated" label="ML Model" size="xs" />
              </div>

              <CorridorHeatStrip zones={profileData?.zone_profiles || []} />
            </div>

            {/* 24-Hour Diurnal Crowding Profile Chart */}
            <div className="bg-white rounded-2xl p-6 border border-slate-200 shadow-sm space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="font-bold text-base text-brand-navy">24-Hour Crowding Diurnal Profile</h3>
                  <p className="text-xs text-slate-500">
                    Predicted passenger load across hours ({dayType.toLowerCase()})
                  </p>
                </div>
                <div className="flex items-center gap-2 text-xs">
                  <span className="flex items-center gap-1">
                    <span className="w-3 h-3 rounded-full bg-teal-500"></span> Mean Load
                  </span>
                </div>
              </div>

              <div className="h-64 w-full">
                {chartData.length > 0 ? (
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={chartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                      <defs>
                        <linearGradient id="loadGradient" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="#0FA3A3" stopOpacity={0.4} />
                          <stop offset="95%" stopColor="#0FA3A3" stopOpacity={0.0} />
                        </linearGradient>
                      </defs>
                      <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#E2E8F0" />
                      <XAxis dataKey="hour" tick={{ fontSize: 10, fill: '#64748B' }} interval={2} />
                      <YAxis tick={{ fontSize: 10, fill: '#64748B' }} />
                      <Tooltip
                        content={({ active, payload }) => {
                          if (active && payload && payload.length) {
                            const d = payload[0].payload;
                            return (
                              <div className="bg-slate-900 text-white p-3 rounded-xl text-xs space-y-1 shadow-xl">
                                <p className="font-bold">{d.hour} ({d.category})</p>
                                <p className="text-teal-300">Mean Load: {d.mean_load} passengers</p>
                                <p className="text-slate-300">Peak Load: {d.max_load}</p>
                                <p className="text-amber-300">RCI: {d.rci} / 100</p>
                              </div>
                            );
                          }
                          return null;
                        }}
                      />
                      <Area
                        type="monotone"
                        dataKey="mean_load"
                        stroke="#0FA3A3"
                        strokeWidth={2.5}
                        fillOpacity={1}
                        fill="url(#loadGradient)"
                      />
                    </AreaChart>
                  </ResponsiveContainer>
                ) : (
                  <div className="h-full flex items-center justify-center text-xs text-slate-400">
                    No hourly profile points recorded.
                  </div>
                )}
              </div>
            </div>

            {/* Scheduled Stops Sequence */}
            <div className="bg-white rounded-2xl p-6 border border-slate-200 shadow-sm space-y-4">
              <h3 className="font-bold text-base text-brand-navy">Scheduled Stops Sequence ({stops.length} stops)</h3>
              <div className="max-h-72 overflow-y-auto divide-y divide-slate-100 pr-2">
                {stops.map((s, idx) => {
                  const zoneIdx = Math.min(7, Math.floor((8 * idx) / Math.max(stops.length, 1)));
                  return (
                    <div key={s.stop_id || idx} className="py-2.5 flex items-center justify-between text-xs hover:bg-slate-50 px-2 rounded-lg">
                      <div className="flex items-center gap-3">
                        <span className="w-5 h-5 rounded-full bg-slate-100 text-slate-600 font-bold flex items-center justify-center text-[10px]">
                          {idx + 1}
                        </span>
                        <div>
                          <p className="font-bold text-slate-800">{s.stop_name}</p>
                          <p className="text-[10px] text-slate-400 font-mono">{s.stop_id}</p>
                        </div>
                      </div>
                      <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-slate-100 text-slate-600">
                        Zone {zoneIdx}
                      </span>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>

          {/* Right Column: Interactive Map (5 cols) */}
          <div className="lg:col-span-5 space-y-6 lg:sticky lg:top-20">
            <div className="bg-white rounded-2xl p-5 border border-slate-200 shadow-sm space-y-3">
              <div className="flex items-center justify-between text-xs">
                <span className="font-bold text-slate-700">Route Geometry &amp; Alignment</span>
                <span className="text-slate-400 font-mono">{stops.length} Stops</span>
              </div>

              <LeafletRouteMap
                stops={stops}
                shapePoints={routeInfo?.shape_points || []}
                height="450px"
              />

              <div className="pt-2 flex items-center justify-between text-[11px] text-slate-500 border-t border-slate-100">
                <span className="flex items-center gap-1">
                  <span className="w-2.5 h-2.5 rounded-full bg-emerald-500"></span> First Stop
                </span>
                <span className="flex items-center gap-1">
                  <span className="w-2.5 h-2.5 rounded-full bg-red-500"></span> Terminal Stop
                </span>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

