import React, { useState, useEffect } from 'react';
import { NavLink, Link } from 'react-router-dom';
import { Bus, MapPin, BarChart2, ShieldCheck, Activity, Github } from 'lucide-react';
import { checkHealth } from '../api';

export default function Navbar() {
  const [backendOk, setBackendOk] = useState(null);

  useEffect(() => {
    checkHealth()
      .then((res) => setBackendOk(res.ok))
      .catch(() => setBackendOk(false));
  }, []);

  const navLinkClass = ({ isActive }) =>
    `inline-flex items-center gap-1.5 px-3 py-2 text-sm font-medium rounded-lg transition-colors ${
      isActive
        ? 'bg-brand-teal/10 text-brand-teal font-semibold'
        : 'text-slate-600 hover:text-brand-navy hover:bg-slate-100'
    }`;

  return (
    <header className="bg-white border-b border-slate-200 sticky top-0 z-30 shadow-sm">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        {/* Brand Logo */}
        <Link to="/" className="flex items-center gap-3 group">
          <div className="w-10 h-10 rounded-xl bg-brand-navy flex items-center justify-center text-white shadow-md group-hover:bg-brand-teal transition-colors">
            <Bus className="w-5 h-5 text-teal-300 group-hover:text-white" />
          </div>
          <div>
            <div className="flex items-center gap-1.5">
              <span className="font-extrabold text-lg tracking-tight text-brand-navy">CrowdWise</span>
              <span className="text-[10px] font-bold px-1.5 py-0.2 bg-teal-50 text-brand-teal border border-teal-200 rounded">
                DELHI
              </span>
            </div>
            <p className="text-[11px] text-slate-500 font-medium">Crowdedness-Aware Bus Planner</p>
          </div>
        </Link>

        {/* Navigation Links */}
        <nav className="hidden md:flex items-center gap-1">
          <NavLink to="/" end className={navLinkClass}>
            <MapPin className="w-4 h-4" />
            <span>Plan Journey</span>
          </NavLink>
          <NavLink to="/route/101UP" className={navLinkClass}>
            <Bus className="w-4 h-4" />
            <span>Route Corridors</span>
          </NavLink>
          <NavLink to="/analytics" className={navLinkClass}>
            <BarChart2 className="w-4 h-4" />
            <span>Network Analytics</span>
          </NavLink>
          <NavLink to="/about" className={navLinkClass}>
            <ShieldCheck className="w-4 h-4" />
            <span>Methodology</span>
          </NavLink>
        </nav>

        {/* Right Status & GitHub */}
        <div className="flex items-center gap-3">
          <div
            className={`hidden sm:inline-flex items-center gap-1.5 text-xs px-2.5 py-1 rounded-full border ${
              backendOk === true
                ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                : backendOk === false
                ? 'bg-red-50 text-red-700 border-red-200'
                : 'bg-slate-50 text-slate-500 border-slate-200'
            }`}
            title="API Backend Status"
          >
            <Activity className="w-3.5 h-3.5 animate-pulse" />
            <span>{backendOk === true ? 'API Live' : backendOk === false ? 'Offline' : 'Connecting...'}</span>
          </div>

          <a
            href="https://github.com/rajnyx/transport-stack-hackathon"
            target="_blank"
            rel="noreferrer"
            className="p-2 text-slate-500 hover:text-brand-navy hover:bg-slate-100 rounded-lg transition-colors"
            title="GitHub Repository"
          >
            <Github className="w-5 h-5" />
          </a>
        </div>
      </div>
    </header>
  );
}

