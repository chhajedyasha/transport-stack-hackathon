import React from 'react';
import { X, Sparkles, Clock, Users, ArrowRight, ShieldCheck } from 'lucide-react';
import CrowdBadge from './CrowdBadge';

export default function WhyThisRouteModal({ option, fastestOption, preference = 'balanced', onClose }) {
  if (!option) return null;

  const tFastest = fastestOption?.total_duration_minutes || option.total_duration_minutes;
  const tOption = option.total_duration_minutes;
  const timePenalty = Math.max(0, (tOption - tFastest) / Math.max(tFastest, 10));
  const crowdPenalty = (option.avg_rci || 0) / 100.0;

  let wTime = 0.5;
  let wCrowd = 0.5;
  if (preference === 'fastest') {
    wTime = 1.0;
    wCrowd = 0.0;
  } else if (preference === 'least_crowded') {
    wTime = 0.2;
    wCrowd = 0.8;
  }

  const finalScore = (wTime * timePenalty + wCrowd * crowdPenalty).toFixed(3);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/50 backdrop-blur-sm animate-fade-in">
      <div className="bg-white rounded-2xl shadow-2xl max-w-lg w-full p-6 space-y-5 border border-slate-200">
        <div className="flex items-center justify-between border-b border-slate-100 pb-3">
          <div className="flex items-center gap-2">
            <div className="p-2 rounded-xl bg-teal-50 text-brand-teal">
              <Sparkles className="w-5 h-5" />
            </div>
            <div>
              <h3 className="font-bold text-lg text-brand-navy">Why this route was ranked</h3>
              <p className="text-xs text-slate-500">Transparent Multi-Objective Recommendation Engine</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 text-slate-400 hover:text-slate-600 rounded-lg hover:bg-slate-100 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="space-y-4 text-sm text-slate-700">
          <div className="flex items-center justify-between p-3 rounded-xl bg-slate-50 border border-slate-200">
            <div>
              <p className="text-xs text-slate-500">Route Candidate</p>
              <p className="font-bold text-base text-brand-navy">Bus {option.route_short_name || option.route_id}</p>
            </div>
            <CrowdBadge
              label={option.crowd_category}
              rci={option.avg_rci}
              confidence={option.confidence}
              size="sm"
            />
          </div>

          <div className="space-y-2">
            <h4 className="text-xs font-bold uppercase tracking-wider text-slate-500">Mathematical Optimization Formula</h4>
            <div className="p-3 rounded-lg bg-slate-900 text-slate-100 font-mono text-xs overflow-x-auto">
              Score = w<sub>time</sub> · ΔT<sub>norm</sub> + w<sub>crowd</sub> · RCI<sub>norm</sub>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3 text-xs">
            <div className="p-3 rounded-lg bg-blue-50/60 border border-blue-200 space-y-1">
              <span className="flex items-center gap-1 font-semibold text-blue-900">
                <Clock className="w-3.5 h-3.5" /> Time Weight ({wTime})
              </span>
              <p className="text-slate-600">Travel time: <strong>{tOption} min</strong></p>
              <p className="text-slate-500">Fastest baseline: {tFastest} min</p>
              <p className="text-blue-700 font-mono">ΔT<sub>norm</sub> = {timePenalty.toFixed(2)}</p>
            </div>

            <div className="p-3 rounded-lg bg-amber-50/60 border border-amber-200 space-y-1">
              <span className="flex items-center gap-1 font-semibold text-amber-900">
                <Users className="w-3.5 h-3.5" /> Crowd Weight ({wCrowd})
              </span>
              <p className="text-slate-600">Avg RCI: <strong>{Math.round(option.avg_rci || 0)} / 100</strong></p>
              <p className="text-slate-500">Seats comfort rank</p>
              <p className="text-amber-700 font-mono">RCI<sub>norm</sub> = {crowdPenalty.toFixed(2)}</p>
            </div>
          </div>

          <div className="p-3 rounded-xl bg-teal-50 border border-teal-200 text-xs text-teal-900 space-y-1">
            <p className="font-semibold flex items-center gap-1.5">
              <ShieldCheck className="w-4 h-4 text-brand-teal" />
              Detour Safeguard & Recommendation
            </p>
            <p className="text-slate-600">
              Under <strong>{preference}</strong> mode, this option scored <code className="font-bold text-teal-900">{finalScore}</code>.
              {tOption <= 1.5 * tFastest + 10 ? (
                <span> It satisfies the maximum allowed detour threshold of 1.5× + 10 minutes.</span>
              ) : (
                <span className="text-amber-700"> Note: High detour penalty applies.</span>
              )}
            </p>
          </div>
        </div>

        <div className="pt-2 flex justify-end">
          <button
            onClick={onClose}
            className="px-4 py-2 bg-brand-navy hover:bg-slate-800 text-white font-medium text-xs rounded-xl transition-colors"
          >
            Got it, close
          </button>
        </div>
      </div>
    </div>
  );
}
