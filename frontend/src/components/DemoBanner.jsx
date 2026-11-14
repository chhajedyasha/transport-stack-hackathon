import React from 'react';
import { Database, ShieldCheck, Calendar } from 'lucide-react';
import ProvenanceBadge from './ProvenanceBadge';

export default function DemoBanner({ meta }) {
  const dateRange = meta?.date_range
    ? `${meta.date_range.start || '2026-10-01'} to ${meta.date_range.end || '2026-10-31'}`
    : 'Oct 01 – Oct 31, 2026';

  return (
    <aside aria-label="Dataset Provenance and Authenticity Banner" className="bg-slate-900 text-white text-xs px-4 py-2 border-b border-slate-800 shadow-sm">
      <div className="max-w-7xl mx-auto flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-emerald-500/20 text-emerald-400 font-semibold border border-emerald-500/30">
            <Database className="w-3.5 h-3.5" />
            ORGANIZER ETM DATA
          </span>
          <span className="text-slate-300 hidden sm:inline">
            Estimates derived from 2.56M official organizer ticketing records ({dateRange}). Historical patterns, not live GPS.
          </span>
          <span className="text-slate-300 sm:hidden">
            2.56M official organizer tickets ({dateRange}).
          </span>
        </div>

        <div className="flex items-center gap-2">
          <ProvenanceBadge tier="real_public" label="GTFS Timetable" size="xs" />
          <ProvenanceBadge tier="organizer" label="Organizer ETM" size="xs" />
          <ProvenanceBadge tier="estimated" label="ML Crowding" size="xs" />
        </div>
      </div>
    </aside>
  );
}

