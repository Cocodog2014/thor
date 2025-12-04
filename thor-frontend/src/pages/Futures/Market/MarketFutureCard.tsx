// MarketFutureCard.tsx
import React from "react";
import { FUTURE_OPTIONS } from "./marketSessionTypes.ts";
import {
  chipClass,
  formatNum,
  formatSignedValue,
  formatPercentValue,
  getDeltaClass,
  getTriangleClass,
  buildPercentCell,
  isZero,
  formatNumOrDash,
  formatIntradayValue,
} from "./marketSessionUtils.ts";

type MarketFutureCardProps = {
  market: any;
  snap: any;
  intradaySnap?: any;
  selectedSymbol: string;
  onSelectedSymbolChange: (symbol: string) => void;
};

const MarketFutureCard: React.FC<MarketFutureCardProps> = ({
  market: m,
  snap,
  intradaySnap,
  selectedSymbol,
  onSelectedSymbolChange,
}) => {
  const signal = snap?.bhs;
  const outcomeStatus = snap?.wndw;

  const captureTime = snap?.captured_at
    ? new Date(snap.captured_at).toLocaleTimeString()
    : "—";
  const selectId = `future-select-${m.key}`;

  const closeDeltaValue = formatSignedValue(snap?.market_close);
  const closeDeltaPercent = formatPercentValue(
    snap?.market_close_vs_open_pct
  );
  const closeDeltaClass = getDeltaClass(
    snap?.market_close ??
      snap?.market_close_vs_open_pct ??
      snap?.market_high_pct_close ??
      snap?.market_low_pct_close
  );

  const openDeltaMetric = {
    label: "Open Δ",
    primary: formatSignedValue(snap?.market_open),
    secondary: undefined as string | undefined,
    className: getDeltaClass(snap?.market_open),
  };

  const rangeColumnMetrics = [
    {
      label: "Low Δ",
      primary: formatSignedValue(snap?.market_low_open),
      secondary: formatPercentValue(snap?.market_low_pct_open),
      className: getDeltaClass(
        snap?.market_low_open ?? snap?.market_low_pct_open
      ),
    },
    {
      label: "High Δ",
      primary: formatSignedValue(snap?.market_high_open),
      secondary: formatPercentValue(snap?.market_high_pct_open),
      className: getDeltaClass(
        snap?.market_high_open ?? snap?.market_high_pct_open
      ),
    },
    {
      label: "Range Δ",
      primary: formatSignedValue(snap?.market_range),
      secondary: formatPercentValue(snap?.market_range_pct),
      className: getDeltaClass(
        snap?.market_range ?? snap?.market_range_pct
      ),
    },
  ] as const;

  const [lowMetric, highMetric, diffMetric] = rangeColumnMetrics;
  const showLowMetric = Boolean(lowMetric.primary || lowMetric.secondary);
  const showHighMetric = Boolean(highMetric.primary || highMetric.secondary);
  const showDiffMetric = Boolean(diffMetric.primary || diffMetric.secondary);

  const bidPriceDisplay = formatNumOrDash(snap?.bid_price);
  const bidSizeDisplay = formatNumOrDash(snap?.bid_size, 0);
  const askPriceDisplay = formatNumOrDash(snap?.ask_price);
  const askSizeDisplay = formatNumOrDash(snap?.ask_size, 0);

  const lastPriceDisplay =
    formatNum(snap?.last_price) ?? (isZero(snap?.last_price) ? 0 : "—");

  const openPrimary = openDeltaMetric.primary ?? "—";

  const sessionRangeValue = snap?.range_diff_24h
    ? `${formatNum(snap?.range_diff_24h)} (${
        formatNum(snap?.range_pct_24h) ?? "—"
      })`
    : "—";

  const detailedSessionStatsRows = [
    {
      key: "close",
      label: "Close",
      value: formatNumOrDash(snap?.prev_close_24h),
      triangleValue: snap?.market_close_vs_open_pct,
      percent: buildPercentCell(snap?.market_close_vs_open_pct),
    },
    {
      key: "open",
      label: "Open",
      value: formatNumOrDash(snap?.open_price_24h),
      triangleValue: snap?.market_open,
      percent: buildPercentCell(snap?.market_open),
    },
    {
      key: "low24",
      label: "24h Low",
      value: formatNumOrDash(snap?.low_24h),
      triangleValue: snap?.market_low_pct_open,
      percent: buildPercentCell(snap?.market_low_pct_open),
    },
    {
      key: "high24",
      label: "24h High",
      value: formatNumOrDash(snap?.high_24h),
      triangleValue: snap?.market_high_pct_open,
      percent: buildPercentCell(snap?.market_high_pct_open),
    },
    {
      key: "range24",
      label: "24h Range",
      value: sessionRangeValue,
      triangleValue: snap?.market_range_pct,
      percent: buildPercentCell(snap?.market_range_pct),
    },
    {
      key: "low52",
      label: "52w Low",
      value: formatNumOrDash(snap?.low_52w),
      triangleValue: null,
      percent: buildPercentCell(undefined, "--"),
    },
    {
      key: "high52",
      label: "52w High",
      value: formatNumOrDash(snap?.high_52w),
      triangleValue: null,
      percent: buildPercentCell(undefined, "--"),
    },
  ];

  const latestIntradaySnap = intradaySnap;

  return (
    <div className="mo-rt-card">
      <div className="mo-rt-left">
        {/* Shared header for futures */}
        <div className="mo-rt-header">
          <div className="mo-rt-header-chips">
            <span className="chip sym">{m.label}</span>
            <span className={chipClass("signal", signal || undefined)}>
              {signal || "—"}
            </span>
            <span className={chipClass("status", outcomeStatus || undefined)}>
              {outcomeStatus || "—"}
            </span>
            <span className="chip weight">Wgt: {snap?.weight ?? "—"}</span>
            <span className="chip default">Capture {captureTime}</span>
          </div>
          <div className="mo-rt-header-select">
            <label htmlFor={selectId} className="future-select-label">
              Future
            </label>
            <select
              id={selectId}
              className="future-select"
              value={selectedSymbol}
              onChange={(e) => onSelectedSymbolChange(e.target.value)}
              aria-label="Select future contract"
            >
              {FUTURE_OPTIONS.map((o) => (
                <option key={o.key} value={o.key}>
                  {o.label}
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* FUTURE (L1) layout */}
        <div className="mo-rt-top">
          <div className="mo-rt-last">
            <div className="val">{lastPriceDisplay}</div>
            <div className="label">Last</div>
          </div>
          <div className="mo-rt-change">
            <div className={`val ${closeDeltaClass}`}>
              {closeDeltaValue ?? (isZero(snap?.market_close) ? "0" : "—")}
            </div>
            <div className={`pct ${closeDeltaClass}`}>
              {closeDeltaPercent ??
                (isZero(snap?.market_close_vs_open_pct) ? "0%" : "—")}
            </div>
            <div className="label">Close Δ</div>
          </div>
        </div>

        <div className="mo-rt-deltas">
          <div className="delta-column">
            <div className="delta-card bbo-card">
              <div className="bbo-section">
                <div className="bbo-head bid">Bid</div>
                <div className="bbo-main">{bidPriceDisplay}</div>
                <div className="bbo-sub">Size {bidSizeDisplay}</div>
              </div>
              <div className="bbo-divider" aria-hidden="true" />
              <div className="bbo-section">
                <div className="bbo-head ask">Ask</div>
                <div className="bbo-main">{askPriceDisplay}</div>
                <div className="bbo-sub">Size {askSizeDisplay}</div>
              </div>
            </div>
          </div>

          {(openPrimary || showLowMetric || showHighMetric || showDiffMetric) && (
            <div className="delta-column">
              <div className="delta-row">
                <div className="delta-card" key="open-metric">
                  <div className="delta-label">{openDeltaMetric.label}</div>
                  <div className={`delta-value ${openDeltaMetric.className}`}>
                    {openPrimary}
                  </div>
                  {openDeltaMetric.secondary && (
                    <div className="delta-sub">
                      {openDeltaMetric.secondary}
                    </div>
                  )}
                </div>

                {showLowMetric && (
                  <div className="delta-card" key="low-metric">
                    <div className="delta-label">{lowMetric.label}</div>
                    <div className={`delta-value ${lowMetric.className}`}>
                      {lowMetric.primary ?? "—"}
                    </div>
                    {lowMetric.secondary && (
                      <div className="delta-sub">{lowMetric.secondary}</div>
                    )}
                  </div>
                )}

                {showHighMetric && (
                  <div className="delta-card" key="high-metric">
                    <div className="delta-label">{highMetric.label}</div>
                    <div className={`delta-value ${highMetric.className}`}>
                      {highMetric.primary ?? "—"}
                    </div>
                    {highMetric.secondary && (
                      <div className="delta-sub">{highMetric.secondary}</div>
                    )}
                  </div>
                )}
              </div>

              {showDiffMetric && (
                <div className="delta-card" key="range-metric">
                  <div className="delta-label">{diffMetric.label}</div>
                  <div className={`delta-value ${diffMetric.className}`}>
                    {diffMetric.primary ?? "—"}
                  </div>
                  {diffMetric.secondary && (
                    <div className="delta-sub">{diffMetric.secondary}</div>
                  )}
                </div>
              )}
            </div>
          )}
        </div>

        <div className="mo-rt-meta">
          <div className="meta">
            <div className="meta-label">Entry</div>
            <div className="meta-value">
              {formatNum(snap?.entry_price) ??
                (isZero(snap?.entry_price) ? 0 : "—")}
            </div>
          </div>
        </div>

        <div className="mo-rt-session-stats">
          <div className="session-stats-header">
            <span>Metric</span>
            <span>Value</span>
            <span>Δ</span>
            <span>Δ%</span>
          </div>
          {detailedSessionStatsRows.map((row) => (
            <div className="session-stats-row" key={row.key}>
              <span>{row.label}</span>
              <span>{row.value}</span>
              <span className="triangle-cell">
                <span className={getTriangleClass(row.triangleValue)} />
              </span>
              <span
                className={`triangle-percent ${row.percent.className}`}
              >
                {row.percent.text}
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* Right-side panel only for futures */}
      <div className="mo-rt-right">
        <div className="mo-rt-right-columns">
          <div className="session-stats-column">
            <div className="mo-rt-stats-title">Session Stats</div>
            <div className="mo-rt-stats">
              {/* stats cards – unchanged */}
              {/* ... */}
            </div>
          </div>

          <div className="intraday-column">
            <div className="intraday-title">Intraday 1m</div>
            <div className="intraday-grid">
              {[
                {
                  key: "open",
                  label: "Open",
                  value: formatIntradayValue(latestIntradaySnap?.open),
                },
                {
                  key: "low",
                  label: "Low",
                  value: formatIntradayValue(latestIntradaySnap?.low),
                },
                {
                  key: "high",
                  label: "High",
                  value: formatIntradayValue(latestIntradaySnap?.high),
                },
                {
                  key: "close",
                  label: "Close",
                  value: formatIntradayValue(latestIntradaySnap?.close),
                },
                {
                  key: "volume",
                  label: "Volume",
                  value: formatIntradayValue(
                    latestIntradaySnap?.volume,
                    0
                  ),
                },
                {
                  key: "spread",
                  label: "Spread",
                  value: formatIntradayValue(
                    latestIntradaySnap?.spread,
                    3
                  ),
                },
              ].map((item) => (
                <div className="intraday-card" key={item.key}>
                  <div className="intraday-label">{item.label}</div>
                  <div className="intraday-value">{item.value}</div>
                </div>
              ))}
            </div>
            {!latestIntradaySnap && (
              <div className="intraday-empty">Waiting for live data...</div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default MarketFutureCard;
