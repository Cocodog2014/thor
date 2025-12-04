import React from "react";
import { FUTURE_OPTIONS } from "./marketSessionTypes.ts";
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
  selectedSymbol: string;
  onSelectedSymbolChange: (symbol: string) => void;
};

const MarketTotalCard: React.FC<MarketTotalCardProps> = ({
  market: m,
  snap,
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
