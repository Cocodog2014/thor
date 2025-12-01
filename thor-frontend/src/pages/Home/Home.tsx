// src/pages/Home/Home.tsx
import React, { useRef } from "react";
// Ribbon now global; local import removed.
import GlobalMarkets from "../GlobalMarkets/GlobalMarkets";

const Home: React.FC = () => {
  const topStripRef = useRef<HTMLDivElement | null>(null);

  // Pure flex layout: no dynamic height calc needed.

  return (
    <div className="home-screen">
      {/* BODY: now just the tiles; banner & ribbon are global */}
      <main className="home-content">
        <div className="home-grid">
          {[
            { id: "global", title: "", hint: "" },
            { id: "pl", title: "RTD", hint: "Real Time Data" },
            { id: "news", title: "Schwab Network / News", hint: "Video / headlines" },
            { id: "watchlist", title: "Heat Map / Watchlist", hint: "Top movers, sectors" },
            { id: "events", title: "Today’s Events", hint: "Economic calendar / orders" },
            { id: "system", title: "System Status", hint: "Feeds, jobs, alerts" },
          ].map((tile, idx) => (
            <section key={tile.id} className={`home-tile home-tile-${idx + 1}`}>
              <header className="home-tile-header">
                <span className="home-tile-title">{tile.title}</span>
                {tile.id !== "global" && (<span className="home-tile-slot">Slot {idx + 1}</span>)}
              </header>
              <div className="home-tile-body">
                {tile.id === "global" ? (
                  <GlobalMarkets />
                ) : (
                  <p className="home-tile-hint">{tile.hint}</p>
                )}
              </div>
            </section>
          ))}
        </div>
        {/* Ribbon globally mounted; removed local instance */}
      </main>
    </div>
  );
};

export default Home;
