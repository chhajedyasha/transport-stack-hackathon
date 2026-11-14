import React from 'react';
import { useTranslation } from '../../i18n/LanguageContext';

export default function TimeBreakdownBar({
  walkMinutes = 0,
  waitMinutes = 5,
  rideMinutes = 35,
  className = '',
}) {
  const { t } = useTranslation();
  const total = Math.max(1, walkMinutes + waitMinutes + rideMinutes);

  const walkPct = (walkMinutes / total) * 100;
  const waitPct = (waitMinutes / total) * 100;
  const ridePct = (rideMinutes / total) * 100;

  return (
    <div className={`flex flex-col gap-1.5 w-full ${className}`}>
      {/* Visual Proportion Bar */}
      <div className="h-2 w-full flex rounded-full overflow-hidden bg-border/40">
        {walkMinutes > 0 && (
          <div
            style={{ width: `${walkPct}%` }}
            className="bg-tx-muted/40 transition-all"
            title={`${walkMinutes} min walk`}
          />
        )}
        <div
          style={{ width: `${waitPct}%` }}
          className="bg-crowd-mod transition-all"
          title={`${waitMinutes} min wait`}
        />
        <div
          style={{ width: `${ridePct}%` }}
          className="bg-teal transition-all"
          title={`${rideMinutes} min ride`}
        />
      </div>

      {/* Numerical Labels with Tabular Numerals */}
      <div className="flex items-center gap-3 text-xs text-tx-muted font-medium tabular-nums">
        {walkMinutes > 0 && (
          <span className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-tx-muted/50" />
            <span>{walkMinutes} {t('results.min')} {t('results.walk')}</span>
          </span>
        )}
        <span className="flex items-center gap-1">
          <span className="w-2 h-2 rounded-full bg-crowd-mod" />
          <span>{waitMinutes} {t('results.min')} {t('results.wait')}</span>
        </span>
        <span className="flex items-center gap-1 text-navy font-semibold">
          <span className="w-2 h-2 rounded-full bg-teal" />
          <span>{rideMinutes} {t('results.min')} {t('results.ride')}</span>
        </span>
      </div>
    </div>
  );
}
