import React from 'react';

export default function CorridorHeatStrip({ zones, title = "8-Zone Corridor Heat Strip", activeZoneIndex = null }) {
  // If zones array is empty or less than 8, normalize to 8 zones
  const displayZones = Array.from({ length: 8 }).map((_, idx) => {
    const existing = zones?.find((z) => z.zone_id === idx) || zones?.[idx];
    if (existing) {
      return {
        zone_id: idx,
        mean_load: existing.mean_load || 0,
        rci: existing.rci !== undefined ? existing.rci : (existing.mean_load ? Math.min(100, existing.mean_load * 2) : 25),
        label: existing.crowd_category || (existing.mean_load > 35 ? 'Crowded' : existing.mean_load > 20 ? 'Standing Room' : 'Seats Available'),
      };
    }
    // Default placeholder
    return {
      zone_id: idx,
      mean_load: 0,
      rci: 20,
      label: 'Seats Available',
    };
  });

  const getZoneColor = (rci) => {
    if (rci >= 85) return 'bg-red-500 text-white';
    if (rci >= 50) return 'bg-amber-400 text-amber-950';
    return 'bg-emerald-500 text-white';
  };

  return (
    <div className="space-y-2">
      {title && (
        <div className="flex items-center justify-between text-xs text-slate-500">
          <span className="font-semibold text-slate-700">{title}</span>
          <span>Origin (Zone 0) → Terminal (Zone 7)</span>
        </div>
      )}

      {/* 8-segment strip */}
      <div className="grid grid-cols-8 gap-1 p-1 bg-slate-100 rounded-xl border border-slate-200">
        {displayZones.map((z, idx) => {
          const isSelected = activeZoneIndex === idx;
          return (
            <div
              key={idx}
              className={`h-10 rounded-lg flex flex-col items-center justify-center transition-all cursor-pointer relative group ${getZoneColor(
                z.rci
              )} ${isSelected ? 'ring-2 ring-brand-navy shadow-md scale-105 z-10' : 'hover:opacity-90'}`}
              title={`Zone ${idx}: Load ~${Math.round(z.mean_load)} pass. | RCI ${Math.round(z.rci)} (${z.label})`}
            >
              <span className="text-[10px] font-bold opacity-80">Z{idx}</span>
              <span className="text-xs font-black leading-none">{Math.round(z.mean_load)}</span>

              {/* Tooltip on hover */}
              <div className="absolute bottom-full mb-1 hidden group-hover:flex flex-col items-center px-2 py-1 bg-slate-900 text-white text-[10px] rounded shadow-lg whitespace-nowrap z-20 pointer-events-none">
                <span>Zone {idx} ({z.label})</span>
                <span>Load: {Math.round(z.mean_load)} | RCI: {Math.round(z.rci)}</span>
              </div>
            </div>
          );
        })}
      </div>

      <div className="flex items-center justify-between text-[11px] text-slate-500 px-1">
        <span className="flex items-center gap-1.5">
          <span className="w-2.5 h-2.5 rounded bg-emerald-500"></span> Seats Available (&lt;50)
        </span>
        <span className="flex items-center gap-1.5">
          <span className="w-2.5 h-2.5 rounded bg-amber-400"></span> Standing Room (50–85)
        </span>
        <span className="flex items-center gap-1.5">
          <span className="w-2.5 h-2.5 rounded bg-red-500"></span> Crowded (&gt;85)
        </span>
      </div>
    </div>
  );
}

