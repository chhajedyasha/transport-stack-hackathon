import React from 'react';
import { Armchair, UserCheck, Users } from 'lucide-react';

export default function CrowdBadge({ label, rci, confidence, showRci = true, size = 'md' }) {
  const normLabel = (label || '').toLowerCase();

  let config = {
    bg: 'bg-emerald-50 text-emerald-800 border-emerald-300',
    icon: Armchair,
    text: 'Seats Available',
    dot: 'bg-emerald-500',
  };

  if (normLabel.includes('standing') || (rci >= 50 && rci < 85)) {
    config = {
      bg: 'bg-amber-50 text-amber-800 border-amber-300',
      icon: UserCheck,
      text: 'Standing Room',
      dot: 'bg-amber-500',
    };
  } else if (normLabel.includes('crowd') || normLabel.includes('crushed') || rci >= 85) {
    config = {
      bg: 'bg-red-50 text-red-800 border-red-300',
      icon: Users,
      text: 'Crowded',
      dot: 'bg-red-500',
    };
  }

  const Icon = config.icon;
  const isSmall = size === 'sm';

  return (
    <div className="inline-flex items-center gap-2">
      <span
        className={`inline-flex items-center gap-1.5 font-semibold rounded-lg border ${config.bg} ${
          isSmall ? 'text-xs px-2 py-0.5' : 'text-sm px-2.5 py-1'
        }`}
      >
        <Icon className={isSmall ? 'w-3.5 h-3.5' : 'w-4 h-4'} />
        <span>{config.text}</span>
      </span>

      {showRci && rci !== undefined && (
        <span
          className={`inline-flex items-center gap-1 font-mono text-slate-600 bg-slate-100 rounded border border-slate-200 ${
            isSmall ? 'text-[10px] px-1.5 py-0.5' : 'text-xs px-2 py-0.5'
          }`}
          title={`Relative Crowding Index: ${Math.round(rci)}/100`}
        >
          <span className="text-slate-400 font-sans">RCI</span>
          <strong>{Math.round(rci)}</strong>
        </span>
      )}

      {confidence && (
        <span
          className={`text-[10px] uppercase font-bold tracking-wider px-1.5 py-0.5 rounded ${
            confidence === 'high'
              ? 'bg-emerald-100 text-emerald-800'
              : confidence === 'medium'
              ? 'bg-sky-100 text-sky-800'
              : 'bg-slate-100 text-slate-600'
          }`}
          title={`Estimation Confidence: ${confidence}`}
        >
          {confidence} conf
        </span>
      )}
    </div>
  );
}

