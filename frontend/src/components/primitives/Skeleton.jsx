import React from 'react';

export function SkeletonLine({ className = '', height = 'h-4', width = 'w-full' }) {
  return (
    <div
      className={`bg-transit-borderSubtle animate-pulse rounded-[2px] ${height} ${width} ${className}`}
      aria-hidden="true"
    />
  );
}

export function SkeletonRow({ className = '' }) {
  return (
    <div
      className={`p-4 bg-white border border-transit-border rounded-panel flex flex-col gap-3 ${className}`}
      aria-hidden="true"
    >
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <SkeletonLine width="w-16" height="h-7" className="rounded-[4px]" />
          <SkeletonLine width="w-24" height="h-4" />
        </div>
        <SkeletonLine width="w-16" height="h-6" />
      </div>
      <div className="flex items-center justify-between pt-1">
        <SkeletonLine width="w-36" height="h-4" />
        <SkeletonLine width="w-20" height="h-4" />
      </div>
    </div>
  );
}

export default function Skeleton({ count = 3, className = '' }) {
  return (
    <div className={`space-y-3 w-full ${className}`}>
      {Array.from({ length: count }).map((_, i) => (
        <SkeletonRow key={i} />
      ))}
    </div>
  );
}
