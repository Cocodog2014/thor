import { FUTURE_OPTIONS } from "./marketSessionTypes.ts";
import {
  chipClass,
  formatNum,
  parseNumericValue,
  formatSignedValue,
  formatPercentValue,
  getDeltaClass,
  getTriangleClass,
  buildPercentCell,
  isZero,
  formatNumOrDash,
  getSessionDateKey,
  formatIntradayValue,
  isToday,
} from "./marketSessionUtils.ts";

type MarketSessionCardProps = {
  market: any;                 // one element from CONTROL_MARKETS
  rows: any[];                 // rows for this country
  status?: any;                // liveStatus[m.country]
  intradaySnap?: any;          // intradayLatest[m.key]
  selectedSymbol?: string;     // selected[m.key]
  onSelectedSymbolChange: (symbol: string) => void;
};

const MarketSessionCard: React.FC<MarketSessionCardProps> = ({
  market: m,
  rows,
  status,
  intradaySnap,
  selectedSymbol,
  onSelectedSymbolChange,
}) => {
  // ----- prior-day / open hiding logic -----
  const latestRow =
    rows.length > 0
      ? rows.reduce((latest, r) =>
          new Date(r.captured_at) > new Date(latest.captured_at) ? r : latest
        )
      : null;

  const seconds = status?.seconds_to_next_event ?? undefined;
  const nextEvent = status?.next_event;

  const sessionDateKey = latestRow ? getSessionDateKey(latestRow) : undefined;
  const marketDateKey = status?.local_date_key;

  let isPriorDay = false;
  if (sessionDateKey && marketDateKey) {
    isPriorDay = sessionDateKey !== marketDateKey;
  } else if (latestRow?.captured_at) {
    isPriorDay = !isToday(latestRow.captured_at);
  }

  const hidePriorNow =
    isPriorDay &&
    nextEvent === "open" &&
    typeof seconds === "number" &&
    seconds <= 300;

  if (hidePriorNow) {
    return (
      <div className="mo-rt-card">
        <div className="mo-rt-left">
          <div className="mo-rt-header">
            <div className="mo-rt-header-chips">
              <span className="chip sym">{m.label}</span>
              <span className="chip default">Awaiting market open…</span>
            </div>
          </div>
          <div className="mo-rt-placeholder">
            Prior capture hidden 5 minutes before today&apos;s open.
          </div>
        </div>
      </div>
    );
  }

  // ----- select / snapshot -----
  const defaultFuture = "TOTAL";
  const effectiveSelectedSymbol = selectedSymbol || defaultFuture;

  const snap =
    rows.find(
      (r) =>
        r.future &&
        r.future.toUpperCase() === effectiveSelectedSymbol.toUpperCase()
    ) || rows[0];

  const latestIntradaySnap = intradaySnap;

  if (!snap) {
    return (
      <div className="mo-rt-card">
        <div className="mo-rt-left">
          <div className="mo-rt-header">
            <div className="mo-rt-header-chips">
              <span className="chip sym">{m.label}</span>
              <span className="chip default">No capture yet</span>
            </div>
          </div>
          <div className="mo-rt-placeholder">
            No market capture has been recorded for this session yet.
          </div>
        </div>
      </div>
    );
  }

  // ----- derived values / metrics -----
  const signal = snap?.bhs;
  const outcomeStatus = snap?.wndw;
  const isTotalFuture =
    (snap.future || "").toUpperCase() === "TOTAL";

  const totalWeightedAverage =
    formatNum(snap?.weighted_average, 3) ??
    (isZero(snap?.weighted_average) ? 0 : "—");

  const totalInstrumentCount = snap?.instrument_count ?? 11;
  const sessionDateLabel = getSessionDateKey(snap) ?? "—";

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

  const captureTime = snap?.captured_at
    ? new Date(snap.captured_at).toLocaleTimeString()
    : "—";
  const selectId = `future-select-${m.key}`;

  const bidPriceDisplay = formatNumOrDash(snap?.bid_price);
  const bidSizeDisplay = formatNumOrDash(snap?.bid_size, 0);
  const askPriceDisplay = formatNumOrDash(snap?.ask_price);
  const askSizeDisplay = formatNumOrDash(snap?.ask_size, 0);

  const lastPriceDisplay =
    formatNum(snap?.last_price) ??
    (isZero(snap?.last_price) ? 0 : "—");

  const openPrimary = openDeltaMetric.primary ?? "—";

  const totalSummaryCards: Array<{
    key: string;
    label: string;
    value: string | number;
    subtitle?: string | number;
  }> = [
    {
      key: "bid",
      label: "Bid",
      value: `${bidPriceDisplay}`,
      subtitle: `Size ${bidSizeDisplay}`,
    },
    {
      key: "basket",
      label: "Futures in Basket",
      value: totalInstrumentCount,
    },
    {
      key: "total-avg",
      label: "Total Weighted Avg",
      value: totalWeightedAverage,
    },
    {
      key: "local-date",
      label: "Local Date",
      value: sessionDateLabel,
    },
  ];

  const totalSessionStatsRows = [
    {
      key: "market-open",
      label: "Market Open",
      value: formatNumOrDash(snap?.open_price_24h),
      triangleValue: snap?.market_open,
      percent: buildPercentCell(snap?.market_open),
    },
    {
      key: "market-high",
      label: "Market High",
      value: formatNumOrDash(snap?.high_24h),
      triangleValue: snap?.market_high_pct_open,
      percent: buildPercentCell(snap?.market_high_pct_open),
    },
    {
      key: "market-low",
      label: "Market Low",
      value: formatNumOrDash(snap?.low_24h),
      triangleValue: snap?.market_low_pct_open,
      percent: buildPercentCell(snap?.market_low_pct_open),
    },
    {
      key: "market-close",
      label: "Market Close",
      value: formatNumOrDash(snap?.prev_close_24h),
      triangleValue: snap?.market_close_vs_open_pct,
      percent: buildPercentCell(snap?.market_close_vs_open_pct),
    },
    {
      key: "range",
      label: "Range",
      value: formatNumOrDash(snap?.market_range),
      triangleValue: snap?.market_range_pct,
      percent: buildPercentCell(snap?.market_range_pct),
    },
    {
      key: "session-volume",
      label: "Session Volume",
      value: formatNumOrDash(snap?.volume, 0),
      triangleValue: null,
      percent: buildPercentCell(undefined, "--"),
    },
  ];

  const prevCloseNum = parseNumericValue(snap?.prev_close_24h);
  const low52Num = parseNumericValue(snap?.low_52w);
  const high52Num = parseNumericValue(snap?.high_52w);

  const low52DeltaPercent =
    prevCloseNum !== null &&
    low52Num !== null &&
    prevCloseNum !== 0
      ? ((prevCloseNum - low52Num) / prevCloseNum) * 100
      : null;

  const high52DeltaPercent =
    prevCloseNum !== null &&
    high52Num !== null &&
    prevCloseNum !== 0
      ? ((high52Num - prevCloseNum) / prevCloseNum) * 100
      : null;

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
      triangleValue: low52DeltaPercent,
      percent: buildPercentCell(low52DeltaPercent),
    },
    {
      key: "high52",
      label: "52w High",
      value: formatNumOrDash(snap?.high_52w),
      triangleValue: high52DeltaPercent,
      percent: buildPercentCell(high52DeltaPercent),
    },
  ];

  // ----- render -----
  return (
    <div className="mo-rt-card">
      <div className="mo-rt-left">
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
              value={effectiveSelectedSymbol}
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

        {isTotalFuture ? (
          <div className="total-session-card">
            <div className="mo-rt-top total">
              <div className="mo-rt-last">
                <div className="val">{lastPriceDisplay}</div>
                <div className="label">Last</div>
              </div>
              <div className="mo-rt-change">
                <div className={`val ${closeDeltaClass}`}>
                  {closeDeltaValue ??
                    (isZero(snap?.market_close) ? "0" : "—")}
                </div>
                <div className={`pct ${closeDeltaClass}`}>
                  {closeDeltaPercent ??
                    (isZero(snap?.market_close_vs_open_pct) ? "0%" : "—")}
                </div>
                <div className="label">Close Δ</div>
              </div>
            </div>

            <div className="session-summary-grid">
              {totalSummaryCards.map((card) => (
                <div className="session-summary-card" key={card.key}>
                  <div className="summary-label">{card.label}</div>
                  <div className="summary-value">{card.value}</div>
                  {card.subtitle && (
                    <div className="summary-sub">{card.subtitle}</div>
                  )}
                </div>
              ))}
            </div>

            <div className="mo-rt-session-stats">
              <div className="session-stats-header">
                <span>Metric</span>
                <span>Value</span>
                <span>Δ</span>
                <span>Δ%</span>
              </div>
              {totalSessionStatsRows.map((row) => (
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
        ) : (
          <>
            <div className="mo-rt-top">
              <div className="mo-rt-last">
                <div className="val">{lastPriceDisplay}</div>
                <div className="label">Last</div>
              </div>
              <div className="mo-rt-change">
                <div className={`val ${closeDeltaClass}`}>
                  {closeDeltaValue ??
                    (isZero(snap?.market_close) ? "0" : "—")}
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

              {(openPrimary ||
                showLowMetric ||
                showHighMetric ||
                showDiffMetric) && (
                <div className="delta-column">
                  <div className="delta-row">
                    <div className="delta-card" key="open-metric">
                      <div className="delta-label">
                        {openDeltaMetric.label}
                      </div>
                      <div
                        className={`delta-value ${openDeltaMetric.className}`}
                      >
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
                        <div
                          className={`delta-value ${lowMetric.className}`}
                        >
                          {lowMetric.primary ?? "—"}
                        </div>
                        {lowMetric.secondary && (
                          <div className="delta-sub">
                            {lowMetric.secondary}
                          </div>
                        )}
                      </div>
                    )}

                    {showHighMetric && (
                      <div className="delta-card" key="high-metric">
                        <div className="delta-label">
                          {highMetric.label}
                        </div>
                        <div
                          className={`delta-value ${highMetric.className}`}
                        >
                          {highMetric.primary ?? "—"}
                        </div>
                        {highMetric.secondary && (
                          <div className="delta-sub">
                            {highMetric.secondary}
                          </div>
                        )}
                      </div>
                    )}
                  </div>

                  {showDiffMetric && (
                    <div className="delta-card" key="range-metric">
                      <div className="delta-label">{diffMetric.label}</div>
                      <div
                        className={`delta-value ${diffMetric.className}`}
                      >
                        {diffMetric.primary ?? "—"}
                      </div>
                      {diffMetric.secondary && (
                        <div className="delta-sub">
                          {diffMetric.secondary}
                        </div>
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
          </>
        )}
      </div>

      {!isTotalFuture && (
        <div className="mo-rt-right">
          <div className="mo-rt-right-columns">
            <div className="session-stats-column">
              <div className="mo-rt-stats-title">Session Stats</div>
              <div className="mo-rt-stats">
                <div className="stat">
                  <div className="stat-label">Volume</div>
                  <div className="stat-value">
                    {snap?.volume !== undefined &&
                    snap?.volume !== null
                      ? formatNum(snap?.volume, 0)
                      : "—"}
                  </div>
                </div>
                <div className="stat">
                  <div className="stat-label">Prev Close (24h)</div>
                  <div className="stat-value">
                    {formatNum(snap?.prev_close_24h) ??
                      (isZero(snap?.prev_close_24h) ? 0 : "—")}
                  </div>
                </div>
                <div className="stat">
                  <div className="stat-label">Open (24h)</div>
                  <div className="stat-value">
                    {formatNum(snap?.open_price_24h) ??
                      (isZero(snap?.open_price_24h) ? 0 : "—")}
                  </div>
                </div>
                <div className="stat">
                  <div className="stat-label">24h Low</div>
                  <div className="stat-value">
                    {formatNum(snap?.low_24h) ??
                      (isZero(snap?.low_24h) ? 0 : "—")}
                  </div>
                </div>
                <div className="stat">
                  <div className="stat-label">24h High</div>
                  <div className="stat-value">
                    {formatNum(snap?.high_24h) ??
                      (isZero(snap?.high_24h) ? 0 : "—")}
                  </div>
                </div>
                <div className="stat">
                  <div className="stat-label">24h Range</div>
                  <div className="stat-value">
                    {snap?.range_diff_24h
                      ? `${formatNum(snap?.range_diff_24h)} (${
                          formatNum(snap?.range_pct_24h) ?? "—"
                        })`
                      : "—"}
                  </div>
                </div>
                <div className="stat">
                  <div className="stat-label">52W Low</div>
                  <div className="stat-value">
                    {formatNum(snap?.low_52w) ??
                      (isZero(snap?.low_52w) ? 0 : "—")}
                  </div>
                </div>
                <div className="stat">
                  <div className="stat-label">52W High</div>
                  <div className="stat-value">
                    {formatNum(snap?.high_52w) ??
                      (isZero(snap?.high_52w) ? 0 : "—")}
                  </div>
                </div>
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
                <div className="intraday-empty">
                  Waiting for live data...
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default MarketSessionCard;
