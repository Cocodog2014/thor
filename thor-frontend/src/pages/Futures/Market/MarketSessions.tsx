import React from "react";
import { CONTROL_MARKETS } from "./marketSessionTypes.ts";
import { normalizeCountry } from "./marketSessionUtils.ts";
import { useMarketSessions } from "./useMarketSessions.ts";
import MarketSessionCard from "./MarketSessionCard.tsx";
import "./MarketSessions.css";

const MarketSessions: React.FC<{ apiUrl?: string }> = ({ apiUrl }) => {
  const { liveStatus,  selected, setSelected, byCountry } =
    useMarketSessions(apiUrl);

  return (
    <div className="market-dashboard">
      <div className="market-dashboard-header">
        <h3 className="market-open-header-title">📊 Market Open Sessions</h3>
        <div className="text-xs subtitle-text">
          Shows all control markets with their own TOTAL
        </div>
      </div>

      <div className="market-grid">
        {CONTROL_MARKETS.map((m) => {
          const countryKey = normalizeCountry(m.country);
          const rows = byCountry.get(countryKey) || [];

          const selectedSymbol = selected[m.key];
          const handleSelectedChange = (symbol: string) =>
            setSelected((prev: Record<string, string>) => ({
              ...prev,
              [m.key]: symbol,
            }));

          return (
            <MarketSessionCard
              key={m.key}
              market={m}
              rows={rows}
              status={liveStatus[m.country]}
              selectedSymbol={selectedSymbol}
              onSelectedSymbolChange={handleSelectedChange}
            />
          );
        })}
      </div>
    </div>
  );
};

export default MarketSessions;
