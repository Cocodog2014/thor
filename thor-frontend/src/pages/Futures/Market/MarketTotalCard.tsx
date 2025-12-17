import React from "react";
import { FUTURE_OPTIONS, type IntradayHealth } from "./marketSessionTypes.ts";
import {
  formatNum,
  isZero,
  formatNumOrDash,
  getSessionDateKey,
} from "./marketSessionUtils.ts";

import "./MarketTotalCard.css";

type MarketTotalCardProps = {
  market: any;
  snap: any;
  health?: IntradayHealth;
  selectedSymbol: string;
  onSelectedSymbolChange: (symbol: string) => void;
};

const MarketTotalCard: React.FC<MarketTotalCardProps> = ({
  market: m,
  snap,
  health,
  selectedSymbol,
  onSelectedSymbolChange,
}) => {
  const captureTime = snap?.captured_at
    ? new Date(snap.captured_at).toLocaleTimeString()
    : "—";

  const selectId = `future-select-${m.key}`;

  // 1) Weighted Avg
  const weightedAvgDisplay =
    formatNum(snap?.weighted_average, 3) ??
    (isZero(snap?.weighted_average) ? 0 : "—");

  // 2) Sum Weighted (wire this to your real field later)
  const sumWeightedDisplay =
    formatNum(snap?.weighted_sum) ??
    formatNum(snap?.weighted_average_sum) ??
    "—";

  // 3) Composite Signal
  const compositeSignal = snap?.bhs || "—";

  // 4) Worked / Didn’t Work (placeholder wiring – adjust to your data later)
  const workedDisplay =
    snap?.worked_label ||
    formatNumOrDash(snap?.signal_weight) ||
    "—";

  const instrumentsCount = snap?.instrument_count ?? 0;
  const sessionDateLabel = getSessionDateKey(snap) ?? "—";

  const healthStatus = health?.status || "unknown";
  const healthClass =
    healthStatus === "green" ? "chip success" : healthStatus === "red" ? "chip error" : "chip default";
  const lastBarLocal = health?.last_bar_utc ? new Date(health.last_bar_utc).toLocaleTimeString() : "—";
  const lagLabel =
    typeof health?.lag_minutes === "number"
      ? `${health.lag_minutes.toFixed(1)}m lag`
      : "No bars yet";

  return (
    <div className="total-card">
      {/* Header */}
      <div className="total-card-header">
        <div className="total-card-header-left">
          <span className="total-card-header-title">TOTAL</span>
          <span className="total-card-header-market">{m.label}</span>
        </div>

        <div className="total-card-header-right">
          <span className="total-card-header-count">
            {instrumentsCount} Futures
          </span>

          <div className="total-card-header-select">
            <label htmlFor={selectId}>Future</label>
            <select
              id={selectId}
              value={selectedSymbol}
              onChange={(e) => onSelectedSymbolChange(e.target.value)}
            >
              {FUTURE_OPTIONS.map((o) => (
                <option key={o.key} value={o.key}>
                  {o.label}
                </option>
              ))}
            </select>
          </div>
        </div>
      </div>

        <div className="total-card-health">
          <span className={healthClass}>
            Intraday {healthStatus === "green" ? "Live" : healthStatus === "red" ? "Stalled" : "Unknown"}
          </span>
          <span className="chip default">Last bar {lastBarLocal}</span>
          <span className="chip default">{lagLabel}</span>
        </div>

      {/* 2x2 grid – ONLY the four metrics */}
      <div className="total-card-grid">
        <div className="total-card-box">
          <div className="total-card-box-label">Weighted Avg</div>
          <div className="total-card-box-value">{weightedAvgDisplay}</div>
        </div>

        <div className="total-card-box">
          <div className="total-card-box-label">Sum Weighted</div>
          <div className="total-card-box-value">{sumWeightedDisplay}</div>
        </div>

        <div className="total-card-box">
          <div className="total-card-box-label">Composite Signal</div>
          <div className="total-card-box-pill">
            <span className="total-card-box-pill-label">{compositeSignal}</span>
          </div>
        </div>

        <div className="total-card-box">
          <div className="total-card-box-label">Worked / Didn&apos;t Work</div>
          <div className="total-card-box-value">{workedDisplay}</div>
        </div>
      </div>

      {/* Footer strip – optional but matches the screenshot vibe */}
      <div className="total-card-footer">
        <span className="total-card-footer-left">
          Updated {sessionDateLabel} • {captureTime}
        </span>
        <span className="total-card-footer-right">Composite</span>
      </div>
    </div>
  );
};

export default MarketTotalCard;
