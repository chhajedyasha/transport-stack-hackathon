import React from 'react';
import { Bus, AlertCircle, RefreshCw } from 'lucide-react';
import Button from './Button';
import { useTranslation } from '../../i18n/LanguageContext';

export function EmptyState({
  title = null,
  description = null,
  actionLabel = null,
  onAction = null,
  className = '',
}) {
  const { t } = useTranslation();

  return (
    <div
      className={`p-6 sm:p-8 bg-white border border-transit-border rounded-panel text-center flex flex-col items-center justify-center gap-3 ${className}`}
    >
      <div className="w-12 h-12 rounded-full bg-transit-bg flex items-center justify-center text-transit-textMuted">
        <Bus className="w-6 h-6" />
      </div>
      <div className="space-y-1 max-w-sm">
        <h3 className="text-base font-semibold text-navy">
          {title || t('results.no_route_title')}
        </h3>
        <p className="text-sm text-transit-textMuted">
          {description || t('results.no_route_desc')}
        </p>
      </div>
      {actionLabel && onAction && (
        <div className="pt-2">
          <Button variant="secondary" size="sm" onClick={onAction}>
            {actionLabel}
          </Button>
        </div>
      )}
    </div>
  );
}

export function ErrorState({
  title = null,
  description = null,
  onRetry = null,
  className = '',
}) {
  const { t } = useTranslation();

  return (
    <div
      className={`p-6 bg-white border border-crowd-highBorder rounded-panel text-center flex flex-col items-center justify-center gap-3 ${className}`}
      role="alert"
    >
      <div className="w-10 h-10 rounded-full bg-crowd-highBg flex items-center justify-center text-crowd-high">
        <AlertCircle className="w-5 h-5" />
      </div>
      <div className="space-y-1 max-w-md">
        <h3 className="text-sm font-semibold text-navy">
          {title || 'Network error'}
        </h3>
        <p className="text-sm text-transit-textMuted">
          {description || t('results.error_loading')}
        </p>
      </div>
      {onRetry && (
        <div className="pt-1">
          <Button variant="secondary" size="sm" onClick={onRetry} className="gap-2">
            <RefreshCw className="w-3.5 h-3.5" />
            <span>{t('results.retry')}</span>
          </Button>
        </div>
      )}
    </div>
  );
}
