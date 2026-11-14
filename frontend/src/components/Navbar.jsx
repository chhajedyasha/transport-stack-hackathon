import React from 'react';
import { NavLink, Link } from 'react-router-dom';
import { MapPin, BarChart2, BookOpen, Globe } from 'lucide-react';
import AppLogo from './AppLogo';
import { useTranslation } from '../i18n/LanguageContext';

export default function Navbar() {
  const { lang, toggleLang, t } = useTranslation();

  const navLinkClass = ({ isActive }) =>
    `inline-flex items-center gap-2 px-4 py-1.5 text-sm font-bold rounded-full transition-all ${
      isActive
        ? 'text-teal bg-teal-tint'
        : 'text-tx-muted hover:text-navy hover:bg-[#F3ECE8]'
    }`;

  const mobileNavLinkClass = ({ isActive }) =>
    `flex flex-col items-center justify-center flex-1 h-full min-h-[48px] py-1 text-xs select-none ${
      isActive ? 'text-teal font-bold' : 'text-transit-textMuted font-medium'
    }`;

  return (
    <>
      {/* 56px Top Header Bar */}
      <header className="bg-white border-b border-transit-border sticky top-0 z-30 h-14">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-full flex items-center justify-between">
          {/* Brand Wordmark & Original App Mark */}
          <Link to="/" className="focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-teal rounded" aria-label="CrowdWise Delhi Home">
            <AppLogo markSize={28} />
          </Link>

          {/* Desktop Navigation Links */}
          <nav className="hidden sm:flex items-center gap-2">
            <NavLink to="/" end className={navLinkClass}>
              <MapPin className="w-4 h-4" />
              <span>{t('nav.plan')}</span>
            </NavLink>
            <NavLink to="/analytics" className={navLinkClass}>
              <BarChart2 className="w-4 h-4" />
              <span>{t('nav.analytics')}</span>
            </NavLink>
            <NavLink to="/about" className={navLinkClass}>
              <BookOpen className="w-4 h-4" />
              <span>{t('nav.about')}</span>
            </NavLink>
          </nav>

          {/* Language Switcher (EN / हिन्दी) */}
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={toggleLang}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-bold rounded-full border border-border bg-white text-navy hover:border-teal hover:bg-teal-tint transition-all min-h-[36px] shadow-xs"
              aria-label={`Switch to ${lang === 'en' ? 'Hindi' : 'English'}`}
            >
              <Globe className="w-4 h-4 text-teal" />
              <span>{lang === 'en' ? 'हिन्दी' : 'English'}</span>
            </button>
          </div>
        </div>
      </header>

      {/* Mobile Bottom Tab Bar (< 600px) */}
      <nav
        aria-label="Mobile Navigation"
        className="sm:hidden fixed bottom-0 left-0 right-0 bg-white border-t border-transit-border z-30 h-14 flex items-center justify-around px-2"
      >
        <NavLink to="/" end className={mobileNavLinkClass}>
          <MapPin className="w-5 h-5 mb-0.5" />
          <span>{t('nav.plan')}</span>
        </NavLink>
        <NavLink to="/analytics" className={mobileNavLinkClass}>
          <BarChart2 className="w-5 h-5 mb-0.5" />
          <span>{t('nav.analytics')}</span>
        </NavLink>
        <NavLink to="/about" className={mobileNavLinkClass}>
          <BookOpen className="w-5 h-5 mb-0.5" />
          <span>{t('nav.about')}</span>
        </NavLink>
      </nav>
    </>
  );
}
