import React, { useMemo, useState } from 'react';
import type { SchwabHealth } from './bannerTypes';

interface SchwabHealthCardProps {
  health: SchwabHealth | null;
}

const formatSeconds = (seconds?: number) => {
  if (seconds === undefined || seconds === null) {
    return '—';
  }
  if (seconds <= 0) {
    return 'expired';
  }
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  const secs = Math.floor(seconds % 60);

  if (hours > 0) {
    return `${hours}h ${minutes}m`;
  }
  if (minutes > 0) {
    return `${minutes}m ${secs}s`;
  }
  return `${secs}s`;
};

const SchwabHealthCard: React.FC<SchwabHealthCardProps> = ({ health }) => {
  const [expanded, setExpanded] = useState(true);

  const summary = useMemo(() => {
    if (!health) {
      return 'No Schwab data';
    }

    const parts = [
      health.connected ? 'Connected' : 'Not connected',
      health.token_expired ? 'Token expired' : 'Token active',
    ];

    if (health.seconds_until_expiry !== undefined && health.seconds_until_expiry !== null) {
      parts.push(`${formatSeconds(health.seconds_until_expiry)} left`);
    }

    return parts.filter(Boolean).join(' • ');
  }, [health]);

  if (!health) {
    return null;
  }

  const stats = [
    {
      label: 'Connected',
      value: health.connected ? 'Yes' : 'No',
      variant: health.connected ? 'ok' : 'warn',
    },
    {
      label: 'Approval',
      value: (health.approval_state ?? 'unknown').replace('_', ' '),
      variant: health.approval_state === 'trading_enabled' ? 'ok' : undefined,
    },
    {
      label: 'Token',
      value: health.token_expired ? 'Expired' : 'Active',
      variant: health.token_expired ? 'warn' : 'ok',
    },
    {
      label: 'Time left',
      value: formatSeconds(health.seconds_until_expiry),
    },
    {
      label: 'Trading',
      value: health.trading_enabled ? 'Enabled' : 'Disabled',
      variant: health.trading_enabled ? 'ok' : undefined,
    },
    {
      label: 'Last error',
      value: health.last_error ?? '—',
      variant: health.last_error ? 'warn' : undefined,
    },
  ];


  const bodyId = 'schwab-health-card-body';

  return (
    <div className="schwab-health-card" aria-live="polite">
      <button
        type="button"
        className="schwab-health-card__header"
        onClick={() => setExpanded((prev) => !prev)}
        aria-expanded={expanded ? 'true' : 'false'}
        aria-controls={bodyId}
      >
        <span className="schwab-health-card__toggle" aria-hidden="true">
          {expanded ? '▾' : '▸'}
        </span>
        <span className="schwab-health-card__title">Schwab Health</span>
        <span className="schwab-health-card__summary">{summary}</span>
      </button>

      <div
        id={bodyId}
        className="schwab-health-card__body"
        hidden={!expanded}
        aria-hidden={expanded ? 'false' : 'true'}
      >
        <div className="schwab-health-row">
          {stats.map(({ label, value, variant }) => (
            <div className="schwab-health-stat" key={label}>
              <span className="schwab-health-stat__label">{label}</span>
              <span className={`schwab-health-stat__value ${variant ?? ''}`}>{value}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default SchwabHealthCard;
