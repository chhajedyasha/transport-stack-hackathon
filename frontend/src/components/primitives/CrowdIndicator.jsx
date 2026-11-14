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

/**
 * CrowdIndicator — 3-level crowdedness indicator adhering strictly to Transport Stack data honesty rules.
 *
 * Rules:
 * 1. Default demand-based wording: Low -> "Not crowded", Moderate -> "Fairly crowded", High -> "Very crowded", Unknown -> "Not enough data"
 * 2. Label-style switch driven by API: Only if `hasVerifiedCapacity` is true may seat-style wording ("Seats available" / "Standing room" / "Crowded") be used.
 * 3. 3-level discrete pictogram / segmented bar (1/2/3 active) + plain-language text label. Never colour alone.
 * 4. Tabular numerals and occupancy % only when the API supplies it.
 */
export default function CrowdIndicator({
  category = 'low',
  hasVerifiedCapacity = false,
  occupancyPercent = null,
  showLabel = true,
  qualifier = null,
  size = 'md',
  className = '',
}) {
  const { lang, t } = useTranslation();
  const normalized = normalizeCrowdCategory(category);

  // Meter configuration: 3 discrete segments
  const configs = {
    low: {
      activeCount: 1,
      fillColor: 'bg-crowd-low',
      textColor: 'text-crowd-low',
      tintBg: 'bg-crowd-low-tint',
      demandLabelEn: 'Not crowded',
      demandLabelHi: 'कम भीड़',
      capacityLabelEn: 'Seats available',
      capacityLabelHi: 'सीटें उपलब्ध',
    },
    moderate: {
      activeCount: 2,
      fillColor: 'bg-crowd-mod',
      textColor: 'text-crowd-mod-text',
      tintBg: 'bg-crowd-mod-tint',
      demandLabelEn: 'Fairly crowded',
      demandLabelHi: 'मध्यम भीड़',
      capacityLabelEn: 'Standing room',
      capacityLabelHi: 'खड़े होने की जगह',
    },
    high: {
      activeCount: 3,
      fillColor: 'bg-crowd-high',
      textColor: 'text-crowd-high',
      tintBg: 'bg-crowd-high-tint',
      demandLabelEn: 'Very crowded',
      demandLabelHi: 'ज़्यादा भीड़',
      capacityLabelEn: 'Crowded',
      capacityLabelHi: 'भीड़भाड़',
    },
    unknown: {
      activeCount: 0,
      fillColor: 'bg-crowd-unknown',
      textColor: 'text-tx-muted',
      tintBg: 'bg-crowd-unknown-tint',
      demandLabelEn: 'Not enough data',
      demandLabelHi: 'पर्याप्त डेटा नहीं',
      capacityLabelEn: 'Not enough data',
      capacityLabelHi: 'पर्याप्त डेटा नहीं',
    },
  };

  const current = configs[normalized] || configs.unknown;

  // Label style switch: seat wording only when verified capacity supplied
  const labelText = hasVerifiedCapacity
    ? (lang === 'hi' ? current.capacityLabelHi : current.capacityLabelEn)
    : (lang === 'hi' ? current.demandLabelHi : current.demandLabelEn);

  const segmentWidth = size === 'sm' ? 'w-2.5 h-2' : size === 'lg' ? 'w-4 h-3' : 'w-3.5 h-2.5';

  return (
    <div className={`inline-flex items-center gap-2 select-none ${className}`}>
      {/* 3-Level Discrete Pictogram Meter (Accessible non-color dependency) */}
      <div
        className="flex items-center gap-1"
        role="meter"
        aria-label={`Crowd estimate: ${labelText}`}
        aria-valuenow={current.activeCount}
        aria-valuemin={0}
        aria-valuemax={3}
      >
        {[1, 2, 3].map((segIndex) => {
          const isActive = segIndex <= current.activeCount;
          return (
            <span
              key={segIndex}
              className={`
                rounded-[1px] transition-colors
                ${segmentWidth}
                ${isActive ? current.fillColor : 'bg-[#DDE2E3]'}
              `}
            />
          );
        })}
      </div>

      {/* High-Contrast Plain-Language Text Label */}
      {showLabel && (
        <span
          className={`
            font-semibold inline-flex items-center gap-1
            ${size === 'sm' ? 'text-xs' : size === 'lg' ? 'text-base' : 'text-sm'}
            ${current.textColor}
          `}
        >
          <span>{labelText}</span>
          {qualifier && (
            <span className="font-normal text-tx-muted text-xs">
              · {qualifier}
            </span>
          )}
          {occupancyPercent != null && (
            <span className="font-normal tabular-nums text-xs opacity-90">
              ({Math.round(occupancyPercent)}%)
            </span>
          )}
        </span>
      )}
    </div>
  );
}
