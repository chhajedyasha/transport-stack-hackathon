import React from 'react';
import { Link } from 'react-router-dom';
import { Bus, Home, Search } from 'lucide-react';
import { useTranslation } from '../i18n/LanguageContext';

export default function NotFoundPage() {
  const { lang, t } = useTranslation();

  return (
    <div className="py-16 flex flex-col items-center justify-center text-center px-4">
      <div className="w-16 h-16 rounded-full bg-transit-bg border border-transit-border flex items-center justify-center text-transit-textMuted mb-4">
        <Bus className="w-8 h-8 text-teal" />
      </div>

      <div className="space-y-2 max-w-sm">
        <span className="text-3xl font-extrabold text-navy tabular-nums">404</span>
        <h1 className="text-lg font-bold text-navy">
          {lang === 'hi' ? 'पृष्ठ नहीं मिला' : 'Page not found'}
        </h1>
        <p className="text-xs text-transit-textMuted">
          {lang === 'hi'
            ? 'आप जिस बस रूट या पृष्ठ की तलाश कर रहे हैं वह मौजूद नहीं है।'
            : 'The route or page you are looking for does not exist or has moved.'}
        </p>
      </div>

      <div className="flex items-center gap-3 mt-6">
        <Link
          to="/"
          className="inline-flex items-center gap-2 px-4 py-2 text-xs font-semibold rounded-[4px] bg-teal text-white hover:bg-tealHover transition-colors min-h-[44px]"
        >
          <Home className="w-4 h-4" />
          <span>{lang === 'hi' ? 'यात्रा योजना पर जाएं' : 'Plan a journey'}</span>
        </Link>
      </div>
    </div>
  );
}
