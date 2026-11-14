import React from 'react';
import CrowdIndicator, { normalizeCrowdCategory } from './primitives/CrowdIndicator';

export default function CrowdBadge({ label, rci, confidence, showRci = false, size = 'md' }) {
  const norm = normalizeCrowdCategory(label);
  return (
    <CrowdIndicator
      category={norm}
      size={size}
      showLabel={true}
    />
  );
}
