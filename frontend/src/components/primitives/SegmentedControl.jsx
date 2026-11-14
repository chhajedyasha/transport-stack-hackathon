import React from 'react';

export default function SegmentedControl({
  options = [],
  value,
  onChange,
  className = '',
  name = 'segmented-control',
}) {
  return (
    <div
      role="radiogroup"
      className={`
        inline-flex p-1 bg-transit-bg border border-transit-border rounded-control w-full
        ${className}
      `}
    >
      {options.map((opt) => {
        const isSelected = value === opt.value;
        return (
          <button
            key={opt.value}
            type="button"
            role="radio"
            aria-checked={isSelected}
            onClick={() => onChange && onChange(opt.value)}
            className={`
              flex-1 min-h-[38px] px-3 py-1.5 text-xs font-semibold rounded-[3px] transition-all select-none
              focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-teal
              ${
                isSelected
                  ? 'bg-navy text-white shadow-none'
                  : 'text-transit-textMuted hover:text-transit-text hover:bg-white/60'
              }
            `}
          >
            {opt.label}
          </button>
        );
      })}
    </div>
  );
}
