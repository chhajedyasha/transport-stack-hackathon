import React from 'react';
import { ShieldCheck, ExternalLink, Heart } from 'lucide-react';

export default function Footer() {
  return (
    <footer className="bg-white border-t border-slate-200 mt-16 text-slate-600 text-xs py-8">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 space-y-4">
        <div className="flex flex-col md:flex-row justify-between items-center gap-4">
          <div className="space-y-1 text-center md:text-left">
            <p className="font-semibold text-brand-navy">
              CrowdWise — Delhi Transport Stack Hackathon 2026 (Problem 2)
            </p>
            <p className="text-slate-500">
              Crowdedness-aware bus journey planning with historical ETM ticket inference & machine learning.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-4 text-slate-500">
            <a
              href="https://delhi.transportstack.in"
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center gap-1 hover:text-brand-teal transition-colors"
            >
              Delhi Transport Stack <ExternalLink className="w-3 h-3" />
            </a>
            <span>•</span>
            <span className="inline-flex items-center gap-1 text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200">
              <ShieldCheck className="w-3.5 h-3.5" /> DPDP Act 2023 Compliant
            </span>
          </div>
        </div>

        <div className="pt-4 border-t border-slate-100 flex flex-col sm:flex-row justify-between items-center text-slate-400 gap-2">
          <p>© 2026 Team CrowdWise. Open source Apache 2.0.</p>
          <p className="flex items-center gap-1">
            Built with 100% test coverage & reproducible pipelines
          </p>
        </div>
      </div>
    </footer>
  );
}
