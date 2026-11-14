import React from 'react';

/**
 * High-Contrast Accessible Text Field
 */
export default function TextField({
  id,
  label,
  value,
  onChange,
  placeholder,
  error,
  helperText,
  icon: Icon,
  rightElement,
  disabled = false,
  required = false,
  className = '',
  inputClassName = '',
  ...props
}) {
  const inputId = id || (label ? label.toLowerCase().replace(/\s+/g, '-') : undefined);

  return (
    <div className={`flex flex-col gap-1 text-left ${className}`}>
      {label && (
        <label htmlFor={inputId} className="text-sm font-medium text-tx flex items-center justify-between">
          <span>{label} {required && <span className="text-[#C8372D]">*</span>}</span>
        </label>
      )}
      <div className="relative flex items-center">
        {Icon && (
          <div className="absolute left-3 text-tx-muted pointer-events-none">
            <Icon className="w-4 h-4" strokeWidth={1.75} />
          </div>
        )}
        <input
          id={inputId}
          value={value}
          onChange={onChange}
          placeholder={placeholder}
          disabled={disabled}
          required={required}
          className={`w-full min-h-[44px] px-3 py-2 bg-surface border text-tx placeholder:text-tx-muted rounded-[var(--radius-control)] text-base transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-teal focus-visible:border-teal disabled:bg-[#F1F3F4] disabled:text-[#8A949B] ${
            Icon ? 'pl-9' : ''
          } ${rightElement ? 'pr-10' : ''} ${
            error ? 'border-[#C8372D] focus-visible:ring-[#C8372D]' : 'border-border'
          } ${inputClassName}`}
          {...props}
        />
        {rightElement && (
          <div className="absolute right-2 flex items-center">
            {rightElement}
          </div>
        )}
      </div>
      {error ? (
        <p className="text-xs text-[#C8372D] font-medium mt-0.5">{error}</p>
      ) : helperText ? (
        <p className="text-xs text-tx-muted mt-0.5">{helperText}</p>
      ) : null}
    </div>
  );
}
