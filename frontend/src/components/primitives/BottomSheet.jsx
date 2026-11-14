import React, { useState, useEffect, useRef } from 'react';
import { ChevronUp, ChevronDown } from 'lucide-react';

export default function BottomSheet({
  children,
  snapPoint = 'half', // 'peek' | 'half' | 'full'
  onSnapChange,
  className = '',
}) {
  const [currentSnap, setCurrentSnap] = useState(snapPoint);
  const sheetRef = useRef(null);

  // Sync snapPoint
  useEffect(() => {
    setCurrentSnap(snapPoint);
  }, [snapPoint]);

  // Back button closes open sheet before leaving page
  useEffect(() => {
    const handlePopState = (e) => {
      if (currentSnap === 'full' || currentSnap === 'half') {
        setCurrentSnap('peek');
        if (onSnapChange) onSnapChange('peek');
        e.preventDefault();
      }
    };
    window.addEventListener('popstate', handlePopState);
    return () => window.removeEventListener('popstate', handlePopState);
  }, [currentSnap, onSnapChange]);

  const snapClasses = {
    peek: 'h-[140px]',
    half: 'h-[52vh]',
    full: 'h-[92vh]',
  };

  const handleNextSnap = () => {
    let next = 'half';
    if (currentSnap === 'peek') next = 'half';
    else if (currentSnap === 'half') next = 'full';
    else if (currentSnap === 'full') next = 'half';
    setCurrentSnap(next);
    if (onSnapChange) onSnapChange(next);
  };

  return (
    <div
      ref={sheetRef}
      className={`
        fixed bottom-0 left-0 right-0 z-40 bg-white border-t border-transit-border
        rounded-t-[8px] shadow-sheet transition-all duration-[280ms] ease-transit flex flex-col
        ${snapClasses[currentSnap] || snapClasses.half}
        ${className}
      `}
    >
      {/* Drag & Header Bar */}
      <div
        onClick={handleNextSnap}
        className="w-full pt-2 pb-1.5 px-4 flex flex-col items-center justify-center cursor-pointer select-none bg-white hover:bg-transit-bg/50 transition-colors"
      >
        <div className="w-10 h-1 rounded-full bg-transit-border mb-1" />
        <div className="flex items-center gap-1 text-[11px] font-semibold text-transit-textMuted uppercase tracking-wider">
          <span>{currentSnap === 'full' ? 'Pull down for map' : 'Tap or drag for routes'}</span>
          {currentSnap === 'full' ? (
            <ChevronDown className="w-3.5 h-3.5" />
          ) : (
            <ChevronUp className="w-3.5 h-3.5" />
          )}
        </div>
      </div>

      {/* Scrollable Content */}
      <div className="flex-1 overflow-y-auto px-4 pb-6">{children}</div>
    </div>
  );
}
