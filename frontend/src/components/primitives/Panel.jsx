import React from 'react';

export default function Panel({
  children,
  className = '',
  border = true,
  padding = 'p-4 sm:p-5',
  as: Component = 'div',
  ...props
}) {
  return (
    <Component
      className={`
        bg-white rounded-panel transition-colors
        ${border ? 'border border-transit-border' : ''}
        ${padding}
        ${className}
      `}
      {...props}
    >
      {children}
    </Component>
  );
}
