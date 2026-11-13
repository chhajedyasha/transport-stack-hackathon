import React from 'react';
import { AlertCircle, Database } from 'lucide-react';
import ProvenanceBadge from './ProvenanceBadge';

export default function DemoBanner({ meta }) {
  const isDemo = meta?.data_mode !== 'organizer';

  return (
    <aside aria-label="Dataset Mode and Data Provenance" className="bg-brand-navy text-white text-xs px-4 py-2 border-b border-slate-700/60 shadow-inner">
      <div className="max-w-7xl mx-auto flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          {isDemo ? (
            <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded bg-amber-500/20 text-amber-300 font-semibold border border-amber-500/30">
              <AlertCircle className="w-3.5 h-3.5" />
              DEMO MODE
            </span>
          ) : (
            <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-300 font-semibold border border-emerald-500/30">
              <Database className="w-3.5 h-3.5" />
              LIVE DATA
            </span>
          )}
          <span className="text-slate-300">
            {isDemo
              ? 'Displaying synthetic passenger demand calibrated to Delhi bus schedules. Timetable is scheduled static GTFS.'
              : 'Active with production ETM ticket telemetry from Delhi Transport Stack.'}
          </span>
        </div>

        <div className="flex items-center gap-2">
          <ProvenanceBadge tier="real_public" label="GTFS Timetable" size="xs" />
          <ProvenanceBadge
            tier={isDemo ? 'demo_synthetic' : 'organizer'}
            label={isDemo ? 'Simulated Demand' : 'Live ETM'}
            size="xs"
          />
          <ProvenanceBadge tier="estimated" label="ML Crowding" size="xs" />
        </div>
      </div>
    </aside>
  );
}

