import React from 'react';

export default function RouteBadge({
  routeNumber,
  size = 'md',
  operator = null,
  className = '',
}) {
  const sizeStyles = {
    sm: 'text-xs px-2 py-0.5 min-w-[40px]',
    md: 'text-sm px-2.5 py-1 min-w-[54px]',
    lg: 'text-base px-3 py-1.5 min-w-[64px]',
  };

  return (
    <div className={`inline-flex items-center gap-1.5 ${className}`}>
      <span
        className={`
          inline-flex items-center justify-center font-bold tracking-tight rounded-[4px]
          bg-navy text-white tabular-nums select-none border border-navy
          ${sizeStyles[size] || sizeStyles.md}
        `}
        title={`Delhi Bus Route ${routeNumber}`}
      >
        {routeNumber}
      </span>
      {operator && (
        <span className="text-[11px] font-medium text-transit-textMuted uppercase tracking-wider">
          {operator}
        </span>
      )}
    </div>
  );
}
