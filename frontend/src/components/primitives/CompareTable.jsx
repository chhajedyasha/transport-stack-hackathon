import React from 'react';
import RouteBadge from './RouteBadge';
import CrowdStrip from './CrowdStrip';
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

  const getConfidenceWord = (conf) => {
    const c = String(conf || '').toLowerCase();
    if (c === 'high') return lang === 'hi' ? 'उच्च' : 'A lot of data';
    if (c === 'medium') return lang === 'hi' ? 'मध्यम' : 'Some data';
    return lang === 'hi' ? 'कम' : 'Little data';
  };

  const getBusiestZone = (opt) => {
    if (opt.zone_forecasts && opt.zone_forecasts.length > 0) {
      const maxZone = [...opt.zone_forecasts].sort((a, b) => (b.rci || 0) - (a.rci || 0))[0];
      return maxZone?.zone_name || (lang === 'hi' ? 'मध्य स्टॉप' : 'Midway stops');
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
        <span className="tabular-nums">
          {opt.walk_time_minutes || 0} {t('results.min')}
        </span>
      ),
    },
    {
      key: 'wait',
      label: lang === 'hi' ? 'इंतज़ार' : 'Wait',
      render: (opt) => (
        <span className="tabular-nums">
          {opt.wait_time_minutes || 0} {t('results.min')}
        </span>
      ),
    },
    {
      key: 'ride',
      label: lang === 'hi' ? 'सवारी' : 'Ride',
      render: (opt) => (
        <span className="tabular-nums">
          {opt.ride_time_minutes || opt.total_duration_minutes || 40} {t('results.min')}
        </span>
      ),
    },
    {
      key: 'crowd_origin',
      label: lang === 'hi' ? 'आपके स्टॉप पर भीड़' : 'Crowd at your stop',
      render: (opt) => (
        <CrowdStrip category={opt.crowd_category || 'low'} size="sm" />
      ),
    },
    {
      key: 'busiest',
      label: lang === 'hi' ? 'सबसे व्यस्त हिस्सा' : 'Busiest part of ride',
      render: (opt) => (
        <span className="text-xs text-transit-text truncate block max-w-[120px]">
          {getBusiestZone(opt)}
        </span>
      ),
    },
    {
      key: 'confidence',
      label: lang === 'hi' ? 'डेटा विश्वसनीयता' : 'Data confidence',
      render: (opt) => (
        <span className="text-xs text-transit-textMuted font-medium">
          {getConfidenceWord(opt.confidence)}
        </span>
      ),
    },
    {
      key: 'transfers',
      label: lang === 'hi' ? 'ट्रांसफर (बदलना)' : 'Transfers',
      render: (opt) => (
        <span className="text-xs font-medium text-navy">
          {opt.transfers ? `${opt.transfers}` : (lang === 'hi' ? 'सीधी बस' : 'Direct bus')}
        </span>
      ),
    },
  ];

  return (
    <div className={`border border-transit-border rounded-panel bg-white overflow-hidden ${className}`}>
      <div className="p-3 bg-transit-bg border-b border-transit-border flex items-center justify-between">
        <h4 className="text-xs font-bold text-navy uppercase tracking-wider">
          {lang === 'hi' ? 'शीर्ष विकल्पों की तुलना' : 'Compare Top Options'}
        </h4>
        <span className="text-[11px] text-transit-textMuted">
          {topOptions.length} {lang === 'hi' ? 'विकल्प' : 'options'}
        </span>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs border-collapse">
          <thead>
            <tr className="border-b border-transit-border bg-white">
              <th className="py-2.5 px-3 font-semibold text-transit-textMuted sticky left-0 bg-white z-10 min-w-[110px] sm:min-w-[130px] border-r border-transit-borderSubtle">
                {lang === 'hi' ? 'मापदंड' : 'Metric'}
              </th>
              {topOptions.map((opt, idx) => {
                const isSelected = selectedOptionIndex === idx;
                const routeNum = opt.route_short_name || opt.route_id;
                return (
                  <th
                    key={opt.trip_id || idx}
                    onClick={() => onSelectOption && onSelectOption(idx)}
                    className={`py-2 px-3 text-center cursor-pointer min-w-[110px] transition-colors ${
                      isSelected ? 'bg-teal/5 font-bold text-teal' : 'hover:bg-transit-bg text-navy'
                    }`}
                  >
                    <div className="flex flex-col items-center gap-1">
                      <RouteBadge routeNumber={routeNum} size="sm" />
                      <span className="text-[11px] block text-transit-textMuted font-normal">
                        Option {idx + 1}
                      </span>
                    </div>
                  </th>
                );
              })}
            </tr>
          </thead>
          <tbody className="divide-y divide-transit-borderSubtle">
            {metrics.map((m) => (
              <tr key={m.key} className="hover:bg-transit-bg/30 transition-colors">
                <td className="py-2 px-3 font-medium text-navy sticky left-0 bg-white z-10 border-r border-transit-borderSubtle">
                  {m.label}
                </td>
                {topOptions.map((opt, idx) => {
                  const isSelected = selectedOptionIndex === idx;
                  return (
                    <td
                      key={opt.trip_id || idx}
                      onClick={() => onSelectOption && onSelectOption(idx)}
                      className={`py-2 px-3 text-center cursor-pointer ${
                        isSelected ? 'bg-teal/5' : ''
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
