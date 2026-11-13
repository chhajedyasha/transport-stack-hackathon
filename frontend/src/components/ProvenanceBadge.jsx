import React from 'react';

export default function ProvenanceBadge({ tier, label, size = 'sm' }) {
  const getStyle = () => {
    switch (tier) {
      case 'real_public':
      case 'gtfs':
        return 'bg-slate-100 text-slate-700 border-slate-300';
      case 'demo_synthetic':
      case 'simulated':
        return 'bg-amber-50 text-amber-800 border-amber-300';
      case 'organizer':
        return 'bg-blue-50 text-blue-800 border-blue-300';
      case 'estimated':
      case 'ml':
      default:
        return 'bg-purple-50 text-purple-800 border-purple-300';
    }
  };

  const displayText = label || (
    tier === 'real_public' ? 'Timetable: GTFS' :
    tier === 'demo_synthetic' ? 'Simulated Tickets' :
    tier === 'organizer' ? 'Organizer ETM' :
    tier === 'estimated' ? 'Estimated Flow' : tier
  );

  const sizeClass = size === 'xs' ? 'text-[10px] px-1.5 py-0.5' : 'text-xs px-2.5 py-1';

  return (
    <span className={`inline-flex items-center font-medium rounded-full border ${getStyle()} ${sizeClass}`}>
      <span className="w-1.5 h-1.5 rounded-full mr-1.5 bg-current opacity-70"></span>
      {displayText}
    </span>
  );
}
