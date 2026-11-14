import React from 'react';

/**
 * Accessible Transit Button
 * - 44px minimum touch target height
 * - High contrast (teal/navy/white)
 * - 2px focus-visible ring token
 * - States: default, hover, active, focus-visible, disabled, loading
 */
export default function Button({
  children,
  variant = 'primary', // 'primary' | 'secondary' | 'ghost' | 'navy'
  size = 'md',        // 'sm' | 'md' | 'lg'
  type = 'button',
  disabled = false,
  loading = false,
  onClick,
  className = '',
  icon: Icon,
  ariaLabel,
  ...props
}) {
  const base = 'inline-flex items-center justify-center font-bold tracking-tight transition-all select-none rounded-full focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-teal focus-visible:ring-offset-2';
  
  const sizes = {
    sm: 'min-h-[38px] px-4 py-1.5 text-xs gap-1.5',
    md: 'min-h-[44px] px-5 py-2.5 text-sm gap-2',
    lg: 'min-h-[48px] px-6 py-3 text-base gap-2.5 font-bold shadow-sm',
  };

  const variants = {
    primary: 'bg-teal text-white hover:bg-teal-hover active:bg-[#00605E] disabled:bg-[#DDE2E3] disabled:text-[#8A949B]',
    navy: 'bg-navy text-white hover:bg-navy-dark active:bg-[#0A1620] disabled:bg-[#DDE2E3] disabled:text-[#8A949B]',
    secondary: 'bg-white text-navy border border-border hover:bg-surface-bg active:bg-[#EAE4E0] disabled:border-[#DDE2E3] disabled:text-[#8A949B]',
    ghost: 'bg-transparent text-tx hover:bg-surface-bg active:bg-[#EAE4E0] disabled:text-[#8A949B]',
  };

  const stateClass = disabled || loading ? 'cursor-not-allowed opacity-60' : 'cursor-pointer';

  return (
    <button
      type={type}
      disabled={disabled || loading}
      onClick={onClick}
      aria-label={ariaLabel}
      aria-busy={loading}
      className={`${base} ${sizes[size]} ${variants[variant]} ${stateClass} ${className}`}
      {...props}
    >
      {loading ? (
        <span className="inline-block w-4 h-4 border-2 border-current border-t-transparent rounded-full animate-spin" />
      ) : Icon ? (
        <Icon className="w-4 h-4 shrink-0" strokeWidth={1.75} />
      ) : null}
      {children}
    </button>
  );
}
