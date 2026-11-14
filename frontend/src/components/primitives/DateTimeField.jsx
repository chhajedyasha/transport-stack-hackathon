import React, { useState, useEffect, useRef } from 'react';
import { Clock, Calendar, ChevronDown } from 'lucide-react';

/**
 * DateTimeField — Custom Accessible Transit Departure Selector
 * - Defaults to "Leave now"
 * - Toggleable to "Leave at" with clean 12-hour (hh:mm am/pm) and Day picker
 * - No unstyled browser native inputs
 */
export default function DateTimeField({
  value, // "18:00" or null for "now"
  onChange,
  t,
  className = '',
}) {
  const [isLeaveNow, setIsLeaveNow] = useState(!value || value === 'now');
  const [isOpen, setIsOpen] = useState(false);
  
  // Parse incoming value or current time
  const parseTime = (timeStr) => {
    if (!timeStr || timeStr === 'now') {
      const now = new Date();
      let h = now.getHours();
      const m = Math.floor(now.getMinutes() / 5) * 5;
      const period = h >= 12 ? 'pm' : 'am';
      h = h % 12 || 12;
      return { hour: h, minute: m < 10 ? `0${m}` : `${m}`, period };
    }
    const [h24, m] = timeStr.split(':');
    const hNum = parseInt(h24, 10);
    const period = hNum >= 12 ? 'pm' : 'am';
    const hour = hNum % 12 || 12;
    return { hour, minute: m || '00', period };
  };

  const [timeState, setTimeState] = useState(() => parseTime(value));
  const containerRef = useRef(null);

  useEffect(() => {
    function handleClickOutside(e) {
      if (containerRef.current && !containerRef.current.contains(e.target)) {
        setIsOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleToggleMode = (nowMode) => {
    setIsLeaveNow(nowMode);
    if (nowMode) {
      setIsOpen(false);
      if (onChange) onChange('now');
    } else {
      setIsOpen(true);
      emitTime(timeState);
    }
  };

  const emitTime = ({ hour, minute, period }) => {
    let h24 = parseInt(hour, 10);
    if (period === 'pm' && h24 < 12) h24 += 12;
    if (period === 'am' && h24 === 12) h24 = 0;
    const hStr = h24 < 10 ? `0${h24}` : `${h24}`;
    const time24 = `${hStr}:${minute}`;
    if (onChange) onChange(time24);
  };

  const handleHourChange = (e) => {
    const updated = { ...timeState, hour: parseInt(e.target.value, 10) };
    setTimeState(updated);
    emitTime(updated);
  };

  const handleMinuteChange = (e) => {
    const updated = { ...timeState, minute: e.target.value };
    setTimeState(updated);
    emitTime(updated);
  };

  const handlePeriodChange = (p) => {
    const updated = { ...timeState, period: p };
    setTimeState(updated);
    emitTime(updated);
  };

  const displayString = isLeaveNow
    ? (t ? t('planner.leaveNow') : 'Leave now')
    : `${timeState.hour}:${timeState.minute} ${timeState.period.toUpperCase()}`;

  return (
    <div ref={containerRef} className={`relative flex flex-col gap-1 text-left ${className}`}>
      <label className="text-sm font-medium text-tx">
        {t ? t('planner.departure') : 'Departure'}
      </label>

      {/* Main trigger button */}
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className="w-full min-h-[44px] px-3 py-2.5 bg-surface border border-border rounded-[var(--radius-control)] text-base flex items-center justify-between text-tx hover:border-teal transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-teal"
        aria-haspopup="dialog"
        aria-expanded={isOpen}
      >
        <div className="flex items-center gap-2">
          <Clock className="w-4 h-4 text-teal shrink-0" strokeWidth={1.75} />
          <span className="font-medium tabular-nums">{displayString}</span>
        </div>
        <ChevronDown className="w-4 h-4 text-tx-muted" />
      </button>

      {/* Popover dialog */}
      {isOpen && (
        <div className="absolute z-40 top-full left-0 right-0 mt-1 p-3 bg-surface border border-border rounded-[var(--radius-panel)] shadow-[var(--shadow-overlay)] flex flex-col gap-3">
          {/* Segmented Mode Toggle: Leave Now vs Leave At */}
          <div className="flex p-0.5 bg-[#EDF0F0] rounded-[var(--radius-control)] text-xs font-medium">
            <button
              type="button"
              onClick={() => handleToggleMode(true)}
              className={`flex-1 py-1.5 rounded-[calc(var(--radius-control)-1px)] transition-all ${
                isLeaveNow ? 'bg-surface text-navy font-semibold shadow-sm' : 'text-tx-muted hover:text-tx'
              }`}
            >
              {t ? t('planner.leaveNow') : 'Leave now'}
            </button>
            <button
              type="button"
              onClick={() => handleToggleMode(false)}
              className={`flex-1 py-1.5 rounded-[calc(var(--radius-control)-1px)] transition-all ${
                !isLeaveNow ? 'bg-surface text-navy font-semibold shadow-sm' : 'text-tx-muted hover:text-tx'
              }`}
            >
              {t ? t('planner.leaveAt') : 'Leave at'}
            </button>
          </div>

          {!isLeaveNow && (
            <div className="flex items-center justify-center gap-2 pt-1">
              {/* Hour Dropdown */}
              <div className="flex flex-col gap-1 items-center">
                <label className="text-[11px] text-tx-muted uppercase font-semibold">Hour</label>
                <select
                  value={timeState.hour}
                  onChange={handleHourChange}
                  className="min-h-[40px] px-2 py-1 bg-surface border border-border rounded-[var(--radius-control)] text-base font-semibold tabular-nums text-tx focus-visible:ring-2 focus-visible:ring-teal"
                >
                  {Array.from({ length: 12 }, (_, i) => i + 1).map((h) => (
                    <option key={h} value={h}>{h}</option>
                  ))}
                </select>
              </div>

              <span className="text-xl font-bold text-tx-muted pt-4">:</span>

              {/* Minute Dropdown (5-min intervals) */}
              <div className="flex flex-col gap-1 items-center">
                <label className="text-[11px] text-tx-muted uppercase font-semibold">Min</label>
                <select
                  value={timeState.minute}
                  onChange={handleMinuteChange}
                  className="min-h-[40px] px-2 py-1 bg-surface border border-border rounded-[var(--radius-control)] text-base font-semibold tabular-nums text-tx focus-visible:ring-2 focus-visible:ring-teal"
                >
                  {['00', '05', '10', '15', '20', '25', '30', '35', '40', '45', '50', '55'].map((m) => (
                    <option key={m} value={m}>{m}</option>
                  ))}
                </select>
              </div>

              {/* AM / PM Toggle */}
              <div className="flex flex-col gap-1 items-center">
                <label className="text-[11px] text-tx-muted uppercase font-semibold">AM/PM</label>
                <div className="flex border border-border rounded-[var(--radius-control)] overflow-hidden">
                  <button
                    type="button"
                    onClick={() => handlePeriodChange('am')}
                    className={`min-h-[40px] px-2.5 text-xs font-bold transition-colors ${
                      timeState.period === 'am' ? 'bg-navy text-white' : 'bg-surface text-tx hover:bg-[#F1F3F4]'
                    }`}
                  >
                    AM
                  </button>
                  <button
                    type="button"
                    onClick={() => handlePeriodChange('pm')}
                    className={`min-h-[40px] px-2.5 text-xs font-bold transition-colors ${
                      timeState.period === 'pm' ? 'bg-navy text-white' : 'bg-surface text-tx hover:bg-[#F1F3F4]'
                    }`}
                  >
                    PM
                  </button>
                </div>
              </div>
            </div>
          )}

          <div className="pt-2 border-t border-border flex justify-end">
            <button
              type="button"
              onClick={() => setIsOpen(false)}
              className="text-xs font-semibold text-teal hover:underline py-1 px-2"
            >
              Done
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
