import React from 'react';

/**
 * CrowdWise App Mark & Wordmark
 * Original, self-made SVG identity representing public bus transit with density intelligence.
 */
export function AppMark({ size = 28, className = '' }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 32 32"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={`shrink-0 ${className}`}
      aria-hidden="true"
    >
      {/* Structural Rounded Navy Badge */}
      <rect width="32" height="32" rx="7" fill="#142B3B" />

      {/* Stylized Bus Profile */}
      <rect x="7" y="6" width="18" height="18" rx="3.5" fill="#FFFFFF" />

      {/* Windshield */}
      <rect x="9.5" y="8.5" width="13" height="6.5" rx="1.5" fill="#142B3B" />

      {/* Headlights */}
      <circle cx="10.5" cy="18.5" r="1.5" fill="#00828A" />
      <circle cx="21.5" cy="18.5" r="1.5" fill="#00828A" />

      {/* Three Horizontal Density Indicator Notch Bars */}
      <rect x="13.5" y="17.5" width="5" height="1.5" rx="0.75" fill="#142B3B" />
      <rect x="13.5" y="20" width="5" height="1" rx="0.5" fill="#142B3B" opacity="0.6" />

      {/* Wheels */}
      <rect x="9" y="23.5" width="3.5" height="2" rx="1" fill="#142B3B" />
      <rect x="19.5" y="23.5" width="3.5" height="2" rx="1" fill="#142B3B" />
    </svg>
  );
}

export default function AppLogo({ markSize = 28, showTag = true, className = '' }) {
  return (
    <div className={`flex items-center gap-2 select-none group ${className}`}>
      <AppMark size={markSize} />
      <div className="flex items-center gap-1.5">
        <span className="font-extrabold text-xl tracking-tight text-navy leading-none">
          CrowdWise
        </span>
        {showTag && (
          <span className="text-[10px] font-bold px-1.5 py-0.5 bg-navy text-white rounded-[3px] tracking-wider uppercase leading-none">
            Delhi
          </span>
        )}
      </div>
    </div>
  );
}
