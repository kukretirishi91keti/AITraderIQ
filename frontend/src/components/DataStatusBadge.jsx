/**
 * DataStatusBadge.jsx - FIXED
 * ============================
 * Location: frontend/src/components/DataStatusBadge.jsx
 *
 * FIXED: Added proper SystemStatusBar export
 */

import React, { useState } from 'react';

// =============================================================================
// CONFIGURATION
// =============================================================================

const STATUS_CONFIG = {
  LIVE: {
    bgColor: 'bg-green-100',
    textColor: 'text-green-800',
    borderColor: 'border-green-300',
    dotColor: 'bg-green-500',
    icon: '🟢',
    label: 'LIVE',
    description: 'Real-time data from market feed',
    pulse: true,
  },
  STALE: {
    bgColor: 'bg-yellow-100',
    textColor: 'text-yellow-800',
    borderColor: 'border-yellow-300',
    dotColor: 'bg-yellow-500',
    icon: '🟡',
    label: 'CACHED',
    description: 'Last-Known-Good data (provider temporarily unavailable)',
    pulse: false,
  },
  SIMULATED: {
    bgColor: 'bg-purple-100',
    textColor: 'text-purple-800',
    borderColor: 'border-purple-300',
    dotColor: 'bg-purple-500',
    icon: '🟣',
    label: 'SIMULATED',
    description: 'Modeled data (live feed unavailable)',
    pulse: false,
  },
};

const SOURCE_LABELS = {
  yfinance: 'Yahoo Finance',
  lkg: 'Last-Known-Good Cache',
  mme: 'Mock Market Engine',
};

// =============================================================================
// HELPERS
// =============================================================================

const formatDataAge = (seconds) => {
  if (!seconds || seconds < 0) return 'just now';
  if (seconds < 60) return `${Math.floor(seconds)}s ago`;
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
  if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
  return `${Math.floor(seconds / 86400)}d ago`;
};

const getStatusConfig = (dataQuality) => {
  return STATUS_CONFIG[dataQuality] || STATUS_CONFIG.SIMULATED;
};

// =============================================================================
// MAIN COMPONENT: DataStatusBadge
// =============================================================================

const DataStatusBadge = ({
  dataQuality = 'SIMULATED',
  source = 'mme',
  dataAge = 0,
  isAnchored = false,
  size = 'medium',
  onClick,
}) => {
  const [isExpanded, setIsExpanded] = useState(false);
  const config = getStatusConfig(dataQuality);

  const sizeClasses = {
    small: 'px-2 py-0.5 text-xs',
    medium: 'px-3 py-1 text-sm',
    large: 'px-4 py-2 text-base',
  };

  const dotSizes = {
    small: 'w-1.5 h-1.5',
    medium: 'w-2 h-2',
    large: 'w-3 h-3',
  };

  const handleClick = () => {
    if (onClick) {
      onClick();
    } else {
      setIsExpanded(!isExpanded);
    }
  };

  return (
    <div className="relative inline-block">
      {/* Main Badge */}
      <button
        onClick={handleClick}
        className={`
          inline-flex items-center gap-1.5 rounded-full font-medium
          border transition-all duration-200
          hover:shadow-md cursor-pointer
          ${config.bgColor} ${config.textColor} ${config.borderColor}
          ${sizeClasses[size]}
        `}
        title={config.description}
      >
        {/* Animated dot */}
        <span className="relative flex">
          <span
            className={`
            rounded-full ${config.dotColor} ${dotSizes[size]}
            ${config.pulse ? 'animate-ping absolute opacity-75' : ''}
          `}
          />
          <span
            className={`
            rounded-full ${config.dotColor} ${dotSizes[size]}
            relative
          `}
          />
        </span>

        {/* Label */}
        <span>{config.label}</span>

        {/* Age indicator */}
        {dataAge > 0 && size !== 'small' && (
          <span className="opacity-70">({formatDataAge(dataAge)})</span>
        )}

        {/* Anchored indicator */}
        {isAnchored && dataQuality === 'SIMULATED' && (
          <span title="Anchored to last known price">⚓</span>
        )}
      </button>

      {/* Expanded Details Panel */}
      {isExpanded && (
        <div className="absolute top-full left-0 mt-2 p-3 rounded-lg shadow-lg bg-white border border-gray-200 z-50 min-w-[250px]">
          <div className="space-y-2">
            <div className="flex items-center gap-2">
              <span className="text-lg">{config.icon}</span>
              <span className="font-semibold">{config.label}</span>
            </div>

            <p className="text-sm text-gray-600">{config.description}</p>

            <div className="pt-2 border-t border-gray-100 space-y-1 text-xs text-gray-500">
              <div className="flex justify-between">
                <span>Source:</span>
                <span className="font-medium">{SOURCE_LABELS[source] || source}</span>
              </div>
              <div className="flex justify-between">
                <span>Data Age:</span>
                <span className="font-medium">{formatDataAge(dataAge)}</span>
              </div>
              {isAnchored && (
                <div className="flex justify-between">
                  <span>Anchored:</span>
                  <span className="font-medium text-purple-600">Yes ⚓</span>
                </div>
              )}
            </div>

            {dataQuality !== 'LIVE' && (
              <div className="pt-2 border-t border-gray-100">
                <p className="text-xs text-gray-400 italic">
                  {dataQuality === 'STALE'
                    ? '💡 Showing last known real price while live feed reconnects'
                    : '💡 Prices are simulated while awaiting live data'}
                </p>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

// =============================================================================
// COMPACT VERSION: DataStatusDot
// =============================================================================

export const DataStatusDot = ({ dataQuality = 'SIMULATED', showLabel = false }) => {
  const config = getStatusConfig(dataQuality);

  return (
    <span
      className="inline-flex items-center gap-1"
      title={`${config.label}: ${config.description}`}
    >
      <span className="relative flex h-2 w-2">
        {config.pulse && (
          <span
            className={`
            animate-ping absolute inline-flex h-full w-full rounded-full opacity-75
            ${config.dotColor}
          `}
          />
        )}
        <span
          className={`
          relative inline-flex rounded-full h-2 w-2
          ${config.dotColor}
        `}
        />
      </span>
      {showLabel && (
        <span className={`text-xs font-medium ${config.textColor}`}>{config.label}</span>
      )}
    </span>
  );
};

// =============================================================================
// SYSTEM STATUS BAR (for dashboard header) - FIXED EXPORT
// =============================================================================

export const SystemStatusBar = ({
  dataQuality = 'SIMULATED',
  source = 'mme',
  dataAge = 0,
  isAnchored = false,
  health = null,
}) => {
  const config = getStatusConfig(dataQuality);

  // Circuit breaker status
  const breakerState = health?.yfinance?.breaker?.state || 'UNKNOWN';
  const breakerColor =
    {
      CLOSED: 'text-green-600',
      HALF_OPEN: 'text-yellow-600',
      OPEN: 'text-red-600',
    }[breakerState] || 'text-gray-600';

  return (
    <div
      className={`
      flex items-center justify-between px-4 py-2 rounded-lg
      ${config.bgColor} ${config.borderColor} border
    `}
    >
      <div className="flex items-center gap-4">
        {/* Main status */}
        <DataStatusBadge
          dataQuality={dataQuality}
          source={source}
          dataAge={dataAge}
          isAnchored={isAnchored}
          size="medium"
        />

        {/* Source */}
        <span className="text-sm text-gray-600">
          via <span className="font-medium">{SOURCE_LABELS[source] || source}</span>
        </span>
      </div>

      <div className="flex items-center gap-4 text-xs text-gray-500">
        {/* Circuit breaker */}
        {health && <span className={breakerColor}>Breaker: {breakerState}</span>}

        {/* LKG entries */}
        {health?.lkg && <span>Cache: {health.lkg.entries} entries</span>}

        {/* Last updated */}
        <span>Updated: {formatDataAge(dataAge)}</span>
      </div>
    </div>
  );
};

// =============================================================================
// EXPORTS - FIXED
// =============================================================================

export default DataStatusBadge;
