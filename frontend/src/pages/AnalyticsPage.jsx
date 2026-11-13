import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import {
  BarChart2,
  TrendingUp,
  Bus,
  MapPin,
  Calendar,
  Users,
  Activity,
  Layers,
  ArrowRight,
  ShieldCheck,
} from 'lucide-react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  LineChart,
  Line,
} from 'recharts';
import { getAnalyticsSummary } from '../api';
import ProvenanceBadge from '../components/ProvenanceBadge';
import CrowdBadge from '../components/CrowdBadge';

export default function AnalyticsPage() {
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getAnalyticsSummary()
      .then((res) => {
        setSummary(res.data);
        setLoading(false);
      })
      .catch((err) => {
        console.error(err);
        setLoading(false);
      });
  }, []);

  // System stats fallback if backend summary is minimal
  const stats = [
    {
      title: 'Total Delhi Routes Mapped',
      value: summary?.total_routes || '18',
      desc: 'GTFS Scheduled Corridors',
      icon: Bus,
      color: 'bg-blue-50 text-brand-navy',
    },
    {
      title: 'Total Bus Stops Indexed',
      value: summary?.total_stops || '542',
      desc: 'cKDTree & Levenshtein Fuzzy Search',
      icon: MapPin,
      color: 'bg-emerald-50 text-emerald-800',
    },
    {
      title: 'October Ticketing Records',
      value: '2.56M',
      desc: 'Delhi Transport Stack ETM Dataset',
      icon: Users,
      color: 'bg-amber-50 text-amber-800',
    },
    {
      title: 'Peak Diurnal Ratio',
      value: '1.48×',
      desc: 'AM/PM Peak over Midday Baseline',
      icon: TrendingUp,
      color: 'bg-purple-50 text-purple-800',
    },
  ];

  // Network Diurnal Curve data
  const networkHourlyData = (summary?.hourly_network_curve || [
    { hour: '06:00', load: 12 },
    { hour: '07:00', load: 24 },
    { hour: '08:00', load: 46 },
    { hour: '09:00', load: 52 },
    { hour: '10:00', load: 48 },
    { hour: '11:00', load: 35 },
    { hour: '12:00', load: 30 },
    { hour: '13:00', load: 28 },
    { hour: '14:00', load: 32 },
    { hour: '15:00', load: 36 },
    { hour: '16:00', load: 42 },
    { hour: '17:00', load: 56 },
    { hour: '18:00', load: 60 },
    { hour: '19:00', load: 54 },
    { hour: '20:00', load: 38 },
    { hour: '21:00', load: 22 },
  ]);

  // Top Corridors
  const topCorridors = summary?.top_crowded_routes || [
    {
      route_id: '101UP',
      route_name: 'Anand Vihar to Connaught Place',
      peak_load: 64,
      avg_rci: 88,
      category: 'Crowded',
      peak_hour: '18:00',
    },
    {
      route_id: '8UP',
      route_name: 'ISBT Kashmiri Gate to Nehru Place',
      peak_load: 58,
      avg_rci: 82,
      category: 'Standing Room',
      peak_hour: '09:00',
    },
    {
      route_id: '101DN',
      route_name: 'Connaught Place to Anand Vihar',
      peak_load: 54,
      avg_rci: 76,
      category: 'Standing Room',
      peak_hour: '08:30',
    },
    {
      route_id: '429UP',
      route_name: 'Mehrauli Terminal to Old Delhi Railway Station',
      peak_load: 48,
      avg_rci: 71,
      category: 'Standing Room',
      peak_hour: '17:30',
    },
    {
      route_id: '502DN',
      route_name: 'Saket Crossing to Mori Gate Terminal',
      peak_load: 32,
      avg_rci: 44,
      category: 'Seats Available',
      peak_hour: '12:00',
    },
  ];

  return (
    <div className="space-y-8 py-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-3xl font-black text-brand-navy">Delhi Transit Network Analytics</h1>
            <ProvenanceBadge tier="estimated" label="System Overview" size="sm" />
          </div>
          <p className="text-xs text-slate-500 mt-1">
            Empirical passenger load insights, diurnal peak distributions, and corridor stress indicators.
          </p>
        </div>
      </div>

      {/* KPI Stats Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {stats.map((st, i) => {
          const Icon = st.icon;
          return (
            <div key={i} className="bg-white rounded-2xl p-5 border border-slate-200 shadow-sm space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold text-slate-500">{st.title}</span>
                <div className={`p-2 rounded-xl ${st.color}`}>
                  <Icon className="w-4 h-4" />
                </div>
              </div>
              <div>
                <p className="text-2xl font-black text-brand-navy leading-none">{st.value}</p>
                <p className="text-[11px] text-slate-400 mt-1">{st.desc}</p>
              </div>
            </div>
          );
        })}
      </div>

      {/* Network Diurnal Curve & Top Routes Table */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Network Diurnal Curve Chart (7 cols) */}
        <div className="lg:col-span-7 bg-white rounded-2xl p-6 border border-slate-200 shadow-sm space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="font-bold text-base text-brand-navy">Network Diurnal Passenger Load Curve</h3>
              <p className="text-xs text-slate-500">Hourly load profile showing twin AM &amp; PM commuter peaks</p>
            </div>
            <ProvenanceBadge tier="simulated" label="October Telemetry" size="xs" />
          </div>

          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={networkHourlyData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#E2E8F0" />
                <XAxis dataKey="hour" tick={{ fontSize: 10, fill: '#64748B' }} />
                <YAxis tick={{ fontSize: 10, fill: '#64748B' }} />
                <Tooltip
                  content={({ active, payload }) => {
                    if (active && payload && payload.length) {
                      const d = payload[0].payload;
                      return (
                        <div className="bg-slate-900 text-white p-2.5 rounded-xl text-xs space-y-1 shadow-lg">
                          <p className="font-bold">{d.hour}</p>
                          <p className="text-teal-300">Avg Passenger Load: {d.load}</p>
                        </div>
                      );
                    }
                    return null;
                  }}
                />
                <Bar dataKey="load" fill="#0FA3A3" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>

          <div className="p-3 bg-slate-50 rounded-xl text-xs text-slate-600 flex items-center justify-between">
            <span>
              <strong>Morning Peak:</strong> 08:00 – 10:00 (1.48× midday)
            </span>
            <span>
              <strong>Evening Peak:</strong> 17:00 – 20:00 (1.52× midday)
            </span>
          </div>
        </div>

        {/* Top 5 Most Crowded Routes (5 cols) */}
        <div className="lg:col-span-5 bg-white rounded-2xl p-6 border border-slate-200 shadow-sm space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="font-bold text-base text-brand-navy">Top Crowded Bus Corridors</h3>
              <p className="text-xs text-slate-500">Routes with highest peak passenger density</p>
            </div>
          </div>

          <div className="divide-y divide-slate-100">
            {topCorridors.map((c, i) => (
              <div key={i} className="py-3 flex items-center justify-between gap-3 text-xs">
                <div className="space-y-0.5">
                  <div className="flex items-center gap-1.5">
                    <span className="font-extrabold text-brand-navy">{c.route_id}</span>
                    <span className="text-[10px] text-slate-400">({c.peak_hour})</span>
                  </div>
                  <p className="text-slate-500 truncate max-w-[180px]">{c.route_name}</p>
                </div>

                <div className="flex items-center gap-2">
                  <div className="text-right">
                    <span className="font-black text-slate-800">{c.peak_load}</span>
                    <span className="text-[10px] text-slate-400 block">pass.</span>
                  </div>
                  <CrowdBadge label={c.category} rci={c.avg_rci} size="sm" showRci={false} />
                </div>
              </div>
            ))}
          </div>

          <div className="pt-2 text-center">
            <Link
              to="/route/101UP"
              className="inline-flex items-center gap-1.5 text-xs font-bold text-brand-teal hover:underline"
            >
              Explore individual route corridors <ArrowRight className="w-3.5 h-3.5" />
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}

