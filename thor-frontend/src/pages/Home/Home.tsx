// src/pages/Home/Home.tsx
import React, { useLayoutEffect, useRef } from "react";
import HomeRibbon from "./HomeRibbon";
import GlobalMarkets from "../GlobalMarkets/GlobalMarkets";

const Home: React.FC = () => {
  const topStripRef = useRef<HTMLDivElement | null>(null);

  // Restore dynamic top strip height measurement for calc() based layout.
  useLayoutEffect(() => {
    const setVar = () => {
      if (topStripRef.current) {
        const h = topStripRef.current.offsetHeight;
        document.documentElement.style.setProperty("--home-top-strip-h", h + "px");
      }
    };
    setVar();
    window.addEventListener("resize", setVar);
    return () => window.removeEventListener("resize", setVar);
  }, []);

  return (
    <div className="home-screen">
      {/* TOP STRIP NAV (Thinkorswim / Schwab-style) */}
      <div className="home-top-strip" ref={topStripRef}>
        {/* ROW 1: Connection + account + quick links */}
        <div className="home-top-row">
          {/* LEFT SIDE */}
          <div className="home-top-left">
            <span className="home-connection">
              <span className="home-connection-dot" />
              Connected
            </span>
            <span className="home-connection-details">Realtime data</span>
            <span className="home-account-id">739954815CHW (Rollover IRA)</span>
          </div>

          {/* RIGHT SIDE: email + links */}
          <div className="home-top-right">
            <a href="mailto:admin@360edu.org" className="home-contact-link">
              <span>📧</span>
              admin@360edu.org
            </a>

            <button className="home-quick-link" type="button">
              <span>🏠</span>Home
            </button>
            <button className="home-quick-link" type="button">
              <span>💬</span>Messages
            </button>
            <button className="home-quick-link" type="button">
              <span>🛟</span>Support
            </button>
            <button className="home-quick-link" type="button">
              <span>💭</span>Chat Rooms
            </button>
            <button className="home-quick-link" type="button">
              <span>⚙️</span>Setup
            </button>
          </div>
        </div>

        {/* ROW 2: Buying power / balances */}
        <div className="home-balances">
          <span>
            Option Buying Power:
            <span className="home-balance-value">$6,471.41</span>
          </span>
          <span>
            Stock Buying Power:
            <span className="home-balance-value">$6,471.41</span>
          </span>
          <span>
            Net Liq:
            <span className="home-balance-value">$105,472.85</span>
          </span>
        </div>

        {/* ROW 3: Tabs */}
        <nav className="home-nav">
          {["Home", "Futures", "Global", "Account", "Activity", "Research", "Settings"].map(
            (tab, idx) => (
              <button
                key={tab}
                type="button"
                className={`home-nav-button${idx === 0 ? " active" : ""}`}
              >
                {tab}
              </button>
            )
          )}
        </nav>
      </div>

      {/* BODY: grid + ribbon row (original layout) */}
      <main className="home-content">
        <div className="home-grid">
          {[
            { id: "global", title: "", hint: "" },
            { id: "pl", title: "P/L Open", hint: "Account profit / loss summary" },
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
        <HomeRibbon />
      </main>
    </div>
  );
};

export default Home;
