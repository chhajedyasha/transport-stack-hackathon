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
        inline-flex p-1.5 bg-[#F0EAE6] border border-border rounded-full w-full
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
              flex-1 min-h-[38px] px-3.5 py-1.5 text-xs font-bold rounded-full transition-all select-none
              focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-teal
              ${
                isSelected
                  ? 'bg-navy text-white shadow-xs'
                  : 'text-tx-muted hover:text-navy hover:bg-white/60'
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
