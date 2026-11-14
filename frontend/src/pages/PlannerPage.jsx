import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowDownUp, Search, Compass, AlertCircle, History } from 'lucide-react';
import StopCombobox from '../components/primitives/StopCombobox';
import DateTimeField from '../components/primitives/DateTimeField';
import SegmentedControl from '../components/primitives/SegmentedControl';
import Button from '../components/primitives/Button';
import { useTranslation } from '../i18n/LanguageContext';

const RECENT_SEARCHES_KEY = 'crowdwise_recent_searches';
const PREF_KEY = 'crowdwise_pref';

export default function PlannerPage() {
  const navigate = useNavigate();
  const { t, lang } = useTranslation();

  // Search form state
  const [originQuery, setOriginQuery] = useState('');
  const [originStop, setOriginStop] = useState(null);

  const [destQuery, setDestQuery] = useState('');
  const [destStop, setDestStop] = useState(null);

  const [departureTime, setDepartureTime] = useState('now');
  const [preference, setPreference] = useState(() => {
    try {
      return localStorage.getItem(PREF_KEY) || 'balanced';
    } catch {
      return 'balanced';
    }
  });

  const [recentSearches, setRecentSearches] = useState(() => {
    try {
      const saved = localStorage.getItem(RECENT_SEARCHES_KEY);
      return saved ? JSON.parse(saved) : [];
    } catch {
      return [];
    }
  });

  const [formError, setFormError] = useState('');

  // Persist preference choice
  const handlePrefChange = (newPref) => {
    setPreference(newPref);
    try {
      localStorage.setItem(PREF_KEY, newPref);
    } catch {}
  };

  // Swap origin and destination
  const handleSwap = () => {
    const tempQuery = originQuery;
    const tempStop = originStop;
    setOriginQuery(destQuery);
    setOriginStop(destStop);
    setDestQuery(tempQuery);
    setDestStop(tempStop);
  };

  // Quick fill Anand Vihar -> Connaught Place
  const handleQuickShowcase = () => {
    setOriginQuery('Anand Vihar ISBT Terminal');
    setOriginStop({ stop_id: '8256', stop_name: 'Anand Vihar ISBT Terminal' });
    setDestQuery('Shivaji Stadium Terminal ( Connaught Place )');
    setDestStop({ stop_id: '365', stop_name: 'Shivaji Stadium Terminal ( Connaught Place )' });
    setDepartureTime('18:00');
    setFormError('');
  };

  // Clear recent searches
  const handleClearRecent = () => {
    setRecentSearches([]);
    try {
      localStorage.removeItem(RECENT_SEARCHES_KEY);
    } catch {}
  };

  // Submit search
  const handleSubmit = (e) => {
    e.preventDefault();
    setFormError('');

    const originId = originStop?.stop_id || originQuery.trim();
    const destId = destStop?.stop_id || destQuery.trim();

    if (!originId || !destId) {
      setFormError(
        lang === 'hi'
          ? 'कृपया प्रस्थान और गंतव्य दोनों स्टॉप चुनें।'
          : 'Please select both an origin and a destination stop.'
      );
      return;
    }

    if (originId === destId) {
      setFormError(
        lang === 'hi'
          ? 'प्रस्थान और गंतव्य स्टॉप एक ही नहीं हो सकते।'
          : 'Origin and destination stops cannot be the same.'
      );
      return;
    }

    // Save search to recents
    const searchItem = {
      origin_id: originId,
      origin_name: originStop?.stop_name || originQuery,
      dest_id: destId,
      dest_name: destStop?.stop_name || destQuery,
      timestamp: Date.now(),
    };
    const updatedRecents = [
      searchItem,
      ...recentSearches.filter((s) => s.origin_id !== originId || s.dest_id !== destId),
    ].slice(0, 5);
    setRecentSearches(updatedRecents);
    try {
      localStorage.setItem(RECENT_SEARCHES_KEY, JSON.stringify(updatedRecents));
    } catch {}

    const formattedTime = departureTime === 'now' ? '18:00' : departureTime;
    const params = new URLSearchParams({
      origin_id: originId,
      origin_name: originStop?.stop_name || originQuery,
      dest_id: destId,
      dest_name: destStop?.stop_name || destQuery,
      departure_time: formattedTime,
      preference,
    });

    navigate(`/results?${params.toString()}`);
  };

  return (
    <div className="py-4 sm:py-8 max-w-xl mx-auto">
      {/* Tool Header */}
      <div className="mb-4 sm:mb-6">
        <h1 className="text-xl sm:text-2xl font-bold text-navy tracking-tight">
          {t('planner.title')}
        </h1>
        <p className="text-xs text-transit-textMuted mt-1">
          {t('app.historicalNote')}
        </p>
      </div>

      {/* Main Tool Form */}
      <form
        onSubmit={handleSubmit}
        className="bg-white border border-transit-border rounded-panel p-4 sm:p-5 space-y-4"
      >
        {formError && (
          <div
            role="alert"
            className="p-3 bg-crowd-highBg border border-crowd-highBorder rounded-[4px] text-xs text-crowd-high flex items-center gap-2"
          >
            <AlertCircle className="w-4 h-4 shrink-0" />
            <span>{formError}</span>
          </div>
        )}

        {/* Stacked Stops with Connector Line and Swap */}
        <div className="relative space-y-3">
          {/* Origin Stop */}
          <div>
            <StopCombobox
              id="origin-stop"
              label={t('planner.fromLabel')}
              placeholder={t('planner.fromPlaceholder')}
              value={originQuery}
              selectedStop={originStop}
              onChange={(val) => {
                setOriginQuery(val);
                setOriginStop(null);
                setFormError('');
              }}
              onSelectStop={(stop) => {
                setOriginStop(stop);
                setOriginQuery(stop.stop_name);
                setFormError('');
              }}
              recentSearches={recentSearches.map((s) => ({
                stop_id: s.origin_id,
                stop_name: s.origin_name,
              }))}
              t={t}
              required
            />
          </div>

          {/* Swap Button (Centered between inputs) */}
          <div className="flex justify-end -my-1 pr-2">
            <button
              type="button"
              onClick={handleSwap}
              className="inline-flex items-center gap-1 px-2.5 py-1 text-xs font-semibold text-transit-textMuted hover:text-navy hover:bg-transit-bg border border-transit-border rounded-[4px] transition-colors min-h-[36px]"
              aria-label={t('planner.swap')}
            >
              <ArrowDownUp className="w-3.5 h-3.5" />
              <span>{t('planner.swap')}</span>
            </button>
          </div>

          {/* Destination Stop */}
          <div>
            <StopCombobox
              id="dest-stop"
              label={t('planner.toLabel')}
              placeholder={t('planner.toPlaceholder')}
              value={destQuery}
              selectedStop={destStop}
              onChange={(val) => {
                setDestQuery(val);
                setDestStop(null);
                setFormError('');
              }}
              onSelectStop={(stop) => {
                setDestStop(stop);
                setDestQuery(stop.stop_name);
                setFormError('');
              }}
              recentSearches={recentSearches.map((s) => ({
                stop_id: s.dest_id,
                stop_name: s.dest_name,
              }))}
              t={t}
              required
            />
          </div>
        </div>

        {/* Departure Time */}
        <div className="pt-1">
          <DateTimeField
            value={departureTime}
            onChange={(val) => setDepartureTime(val)}
            t={t}
          />
        </div>

        {/* Priority Segmented Control */}
        <div className="space-y-1.5 pt-1">
          <label className="block text-xs font-semibold text-navy">
            {t('planner.preference')}
          </label>
          <SegmentedControl
            options={[
              { value: 'fastest', label: t('planner.fastest') },
              { value: 'balanced', label: t('planner.balanced') },
              { value: 'least_crowded', label: t('planner.leastCrowded') },
            ]}
            value={preference}
            onChange={handlePrefChange}
          />
        </div>

        {/* Primary Search Button (Always visible on mobile 360x640 above keyboard) */}
        <div className="pt-2">
          <Button
            type="submit"
            variant="primary"
            size="lg"
            className="w-full justify-center text-sm font-semibold min-h-[44px]"
          >
            <Search className="w-4 h-4 mr-2" />
            <span>{t('planner.search')}</span>
          </Button>
        </div>
      </form>

      {/* Quick Corridor Shortcut */}
      <div className="mt-4 text-center">
        <button
          type="button"
          onClick={handleQuickShowcase}
          className="text-xs font-semibold text-teal hover:underline inline-flex items-center gap-1.5 py-1 px-2 rounded-[4px] hover:bg-teal/5 transition-colors min-h-[44px]"
        >
          <Compass className="w-4 h-4" />
          <span>{t('planner.showcaseButton')}</span>
        </button>
      </div>

      {/* Recent Searches Drawer / List */}
      {recentSearches.length > 0 && (
        <div className="mt-6 border border-transit-border rounded-panel bg-white p-3.5 space-y-2">
          <div className="flex items-center justify-between text-xs text-transit-textMuted">
            <span className="font-semibold text-navy flex items-center gap-1.5">
              <History className="w-3.5 h-3.5" />
              {t('planner.recent')}
            </span>
            <button
              type="button"
              onClick={handleClearRecent}
              className="text-[11px] text-transit-textMuted hover:text-crowd-high transition-colors"
            >
              {t('planner.clearRecent')}
            </button>
          </div>

          <div className="divide-y divide-transit-borderSubtle">
            {recentSearches.map((item, idx) => (
              <div
                key={idx}
                onClick={() => {
                  setOriginQuery(item.origin_name);
                  setOriginStop({ stop_id: item.origin_id, stop_name: item.origin_name });
                  setDestQuery(item.dest_name);
                  setDestStop({ stop_id: item.dest_id, stop_name: item.dest_name });
                }}
                className="py-2 flex items-center justify-between text-xs text-transit-text hover:bg-transit-bg px-1 rounded-[3px] cursor-pointer transition-colors"
              >
                <span className="truncate">
                  {item.origin_name} → {item.dest_name}
                </span>
                <span className="text-[10px] text-transit-textMuted shrink-0 ml-2">
                  Use
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
