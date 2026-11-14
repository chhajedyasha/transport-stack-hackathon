import React from 'react';
import RouteBadge from './RouteBadge';
import CrowdIndicator from './CrowdIndicator';
import { useTranslation } from '../../i18n/LanguageContext';

export default function CompareTable({
  options = [],
  selectedOptionIndex = 0,
  onSelectOption,
  className = '',
}) {
  const { t, lang } = useTranslation();

  if (!options || options.length === 0) return null;

  const topOptions = options.slice(0, 3);

  // Identify fastest and least crowded among top options
  const fastestIndex = topOptions.reduce(
    (minIdx, cur, idx, arr) =>
      (cur.total_duration_minutes || 999) < (arr[minIdx].total_duration_minutes || 999) ? idx : minIdx,
    0
  );

  const leastCrowdedIndex = topOptions.reduce(
    (minIdx, cur, idx, arr) =>
      (cur.avg_rci || 50) < (arr[minIdx].avg_rci || 50) ? idx : minIdx,
    0
  );

  const getConfidenceWord = (conf) => {
    const c = String(conf || '').toLowerCase();
    if (c === 'high') return lang === 'hi' ? 'उच्च' : 'A lot of data';
    if (c === 'medium') return lang === 'hi' ? 'मध्यम' : 'Some data';
    return lang === 'hi' ? 'कम' : 'Little data';
  };

  const getBusiestZone = (opt) => {
    if (opt.zone_forecasts && opt.zone_forecasts.length > 0) {
      const maxZone = [...opt.zone_forecasts].sort((a, b) => (b.rci || 0) - (a.rci || 0))[0];
      return maxZone?.zone_name || (lang === 'hi' ? 'मध्य स्टॉप' : 'Midway stretch');
    }
    return lang === 'hi' ? 'सामान्य' : 'Typical stretch';
  };

  const metrics = [
    {
      key: 'total_time',
      label: lang === 'hi' ? 'कुल समय' : 'Total time',
      render: (opt) => (
        <span className="font-bold text-navy text-sm tabular-nums">
          {opt.total_duration_minutes || 45} {t('results.min')}
        </span>
      ),
    },
    {
      key: 'walk',
      label: lang === 'hi' ? 'पैदल' : 'Walk',
      render: (opt) => (
        <span className="tabular-nums text-tx-muted">
          {opt.walk_time_minutes || 0} {t('results.min')}
        </span>
      ),
    },
    {
      key: 'wait',
      label: lang === 'hi' ? 'इंतज़ार' : 'Wait',
      render: (opt) => (
        <span className="tabular-nums text-tx-muted">
          {opt.wait_time_minutes || 5} {t('results.min')}
        </span>
      ),
    },
    {
      key: 'ride',
      label: lang === 'hi' ? 'सवारी' : 'Ride',
      render: (opt) => (
        <span className="tabular-nums font-medium text-navy">
          {opt.ride_time_minutes || opt.total_duration_minutes || 40} {t('results.min')}
        </span>
      ),
    },
    {
      key: 'crowd_origin',
      label: lang === 'hi' ? 'आपके स्टॉप पर भीड़' : 'Crowd at your stop',
      render: (opt) => (
        <CrowdIndicator category={opt.crowd_category || 'low'} size="sm" />
      ),
    },
    {
      key: 'busiest',
      label: lang === 'hi' ? 'सबसे व्यस्त हिस्सा' : 'Busiest part of ride',
      render: (opt) => (
        <span className="text-xs text-tx truncate block max-w-[130px] mx-auto">
          {getBusiestZone(opt)}
        </span>
      ),
    },
    {
      key: 'confidence',
      label: lang === 'hi' ? 'डेटा विश्वसनीयता' : 'Data confidence',
      render: (opt) => (
        <span className="text-xs text-tx-muted font-medium">
          {getConfidenceWord(opt.confidence)}
        </span>
      ),
    },
    {
      key: 'transfers',
      label: lang === 'hi' ? 'ट्रांसफर (बदलना)' : 'Transfers',
      render: (opt) => (
        <span className="text-xs font-semibold text-navy">
          {opt.transfers ? `${opt.transfers}` : (lang === 'hi' ? 'सीधी बस (0)' : 'Direct bus (0)')}
        </span>
      ),
    },
  ];

  return (
    <div className={`border border-border rounded-[var(--radius-panel)] bg-surface overflow-hidden ${className}`}>
      <div className="p-3 bg-surface-bg border-b border-border flex items-center justify-between">
        <h4 className="text-xs font-bold text-navy uppercase tracking-wider">
          {lang === 'hi' ? 'शीर्ष 3 विकल्पों की तुलना' : 'Compare Top 3 Options'}
        </h4>
        <span className="text-[11px] text-tx-muted">
          {topOptions.length} {lang === 'hi' ? 'विकल्प' : 'options'}
        </span>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs border-collapse">
          <thead>
            <tr className="border-b border-border bg-surface">
              <th className="py-2.5 px-3 font-semibold text-tx-muted sticky left-0 bg-surface z-10 min-w-[110px] sm:min-w-[130px] border-r border-border/50">
                {lang === 'hi' ? 'मापदंड' : 'Metric'}
              </th>
              {topOptions.map((opt, idx) => {
                const isSelected = selectedOptionIndex === idx;
                const routeNum = opt.route_short_name || opt.route_id;
                const isFastest = idx === fastestIndex;
                const isLeastCrowded = idx === leastCrowdedIndex && !isFastest;

                return (
                  <th
                    key={opt.trip_id || idx}
                    onClick={() => onSelectOption && onSelectOption(idx)}
                    className={`py-2.5 px-3 text-center cursor-pointer min-w-[120px] transition-colors ${
                      isSelected ? 'bg-teal/10 font-bold text-teal' : 'hover:bg-surface-bg text-navy'
                    }`}
                  >
                    <div className="flex flex-col items-center gap-1">
                      {isFastest && (
                        <span className="text-[9.5px] font-bold px-1.5 py-0.5 rounded-[2px] bg-navy text-white leading-none">
                          {lang === 'hi' ? 'सबसे तेज़' : 'Fastest'}
                        </span>
                      )}
                      {isLeastCrowded && (
                        <span className="text-[9.5px] font-bold px-1.5 py-0.5 rounded-[2px] bg-teal text-white leading-none">
                          {lang === 'hi' ? 'कम भीड़' : 'Least crowded'}
                        </span>
                      )}
                      <RouteBadge routeNumber={routeNum} size="sm" />
                      <span className="text-[11px] block text-tx-muted font-normal">
                        Option {idx + 1}
                      </span>
                    </div>
                  </th>
                );
              })}
            </tr>
          </thead>
          <tbody className="divide-y divide-border/50">
            {metrics.map((m) => (
              <tr key={m.key} className="hover:bg-surface-bg/40 transition-colors">
                <td className="py-2.5 px-3 font-medium text-navy sticky left-0 bg-surface z-10 border-r border-border/50">
                  {m.label}
                </td>
                {topOptions.map((opt, idx) => {
                  const isSelected = selectedOptionIndex === idx;
                  return (
                    <td
                      key={opt.trip_id || idx}
                      onClick={() => onSelectOption && onSelectOption(idx)}
                      className={`py-2.5 px-3 text-center cursor-pointer ${
                        isSelected ? 'bg-teal/5 font-semibold' : ''
                      }`}
                    >
                      {m.render(opt)}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
