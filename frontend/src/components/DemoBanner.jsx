import React from 'react';
import { Database, Info } from 'lucide-react';
import { useTranslation } from '../i18n/LanguageContext';

export default function DemoBanner({ meta }) {
  const { lang, t } = useTranslation();

  const isDemo = meta?.data_mode === 'demo' || meta?.active_tier === 'synthetic';
  const dateRange = meta?.date_range
    ? `${meta.date_range.start || '2026-10-01'} to ${meta.date_range.end || '2026-10-31'}`
    : 'Oct 01 – Oct 31, 2026';

  return (
    <aside
      aria-label="Dataset Provenance and Authenticity Banner"
      className="bg-navy text-white text-xs px-3 sm:px-4 py-1.5 border-b border-navy/20 select-none"
    >
      <div className="max-w-7xl mx-auto flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          {isDemo ? (
            <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded-[3px] bg-[#F2B01E] text-navy font-bold text-[10px] uppercase">
              Simulated Data
            </span>
          ) : (
            <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded-[3px] bg-teal text-white font-bold text-[10px] uppercase">
              Official Data
            </span>
          )}

          <span className="text-white/90 text-xs font-normal">
            {lang === 'hi'
              ? `दिल्ली परिवहन टिकट डेटा (${dateRange}) पर आधारित ऐतिहासिक अनुमान। यह लाइव जीपीएस ट्रैकिंग नहीं है।`
              : `Historical estimates derived from official ticketing data (${dateRange}). Not live GPS tracking.`}
          </span>
        </div>

        <div className="hidden md:flex items-center gap-3 text-[11px] text-white/70">
          <span>GTFS Timetables</span>
          <span>·</span>
          <span>ETM Ticketing</span>
          <span>·</span>
          <span>Offline ML Estimates</span>
        </div>
      </div>
    </aside>
  );
}
