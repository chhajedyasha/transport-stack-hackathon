import React from 'react';
import { useTranslation } from '../../i18n/LanguageContext';

export function normalizeCrowdCategory(rawCategory) {
  if (!rawCategory) return 'unknown';
  const c = String(rawCategory).toLowerCase();
  if (c.includes('seat') || c.includes('low') || c.includes('not crowded') || c.includes('कम')) {
    return 'low';
  }
  if (c.includes('stand') || c.includes('mod') || c.includes('fairly') || c.includes('मध्यम')) {
    return 'moderate';
  }
  if (c.includes('crowd') || c.includes('high') || c.includes('very') || c.includes('ज़्यादा')) {
    return 'high';
  }
  return 'unknown';
}

export default function CrowdStrip({
  category = 'low',
  occupancyPercent = null,
  showLabel = true,
  qualifier = null,
  size = 'md',
  className = '',
}) {
  const { t } = useTranslation();
  const normalized = normalizeCrowdCategory(category);

  // Meter configuration: 3 discrete segments representing Low, Moderate, High
  const meterStyles = {
    low: {
      activeSegments: 1,
      fillColor: 'bg-crowd-low',
      textColor: 'text-crowd-low',
      bgColor: 'bg-crowd-lowBg',
      borderColor: 'border-crowd-lowBorder',
      labelKey: 'crowd.low',
    },
    moderate: {
      activeSegments: 2,
      fillColor: 'bg-crowd-mod',
      textColor: 'text-crowd-modText',
      bgColor: 'bg-crowd-modBg',
      borderColor: 'border-crowd-modBorder',
      labelKey: 'crowd.moderate',
    },
    high: {
      activeSegments: 3,
      fillColor: 'bg-crowd-high',
      textColor: 'text-crowd-high',
      bgColor: 'bg-crowd-highBg',
      borderColor: 'border-crowd-highBorder',
      labelKey: 'crowd.high',
    },
    unknown: {
      activeSegments: 0,
      fillColor: 'bg-crowd-unknown',
      textColor: 'text-transit-textMuted',
      bgColor: 'bg-crowd-unknownBg',
      borderColor: 'border-crowd-unknownBorder',
      labelKey: 'crowd.unknown',
    },
  };

  const current = meterStyles[normalized] || meterStyles.unknown;
  const labelText = t(current.labelKey);

  return (
    <div className={`inline-flex items-center gap-2 select-none ${className}`}>
      {/* 3-Segment Horizontal Meter */}
      <div
        className="flex items-center gap-1"
        title={`Crowding level: ${labelText}`}
        aria-label={`Crowding level: ${labelText}`}
      >
        {[1, 2, 3].map((segIndex) => {
          const isActive = segIndex <= current.activeSegments;
          return (
            <span
              key={segIndex}
              className={`
                h-2.5 rounded-[1px] transition-colors
                ${size === 'sm' ? 'w-2.5 h-2' : 'w-3.5 h-2.5'}
                ${isActive ? current.fillColor : 'bg-[#DDE2E3]'}
              `}
            />
          );
        })}
      </div>

      {/* Plain Language Text Label */}
      {showLabel && (
        <span
          className={`
            font-semibold inline-flex items-center gap-1
            ${size === 'sm' ? 'text-xs' : 'text-sm'}
            ${current.textColor}
          `}
        >
          <span>{labelText}</span>
          {qualifier && (
            <span className="font-normal text-transit-textMuted text-xs">
              · {qualifier}
            </span>
          )}
          {occupancyPercent !== null && (
            <span className="font-normal tabular-nums text-xs opacity-90">
              ({Math.round(occupancyPercent)}%)
            </span>
          )}
        </span>
      )}
    </div>
  );
}
