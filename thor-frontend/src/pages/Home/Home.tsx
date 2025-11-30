// src/pages/Home/Home.tsx
import React from "react";

const Home: React.FC = () => {
  return (
    <div className="home-screen">
      {/* TOP STRIP NAV (Thinkorswim / Schwab-style) */}
      <div className="home-top-strip">
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

      {/* BODY: grid + bottom ticker ribbon */}
      <main className="home-content">
        <div className="home-grid">
          {[ 
            { id: "nyse", title: "NYSE Opens In", hint: "Countdown / session clock" },
            { id: "pl", title: "P/L Open", hint: "Account profit / loss summary" },
            { id: "news", title: "Schwab Network / News", hint: "Video / headlines" },
            { id: "watchlist", title: "Heat Map / Watchlist", hint: "Top movers, sectors" },
            { id: "events", title: "Today’s Events", hint: "Economic calendar / orders" },
            { id: "system", title: "System Status", hint: "Feeds, jobs, alerts" },
          ].map((tile, idx) => (
            <section key={tile.id} className={`home-tile home-tile-${idx + 1}`}>
              <header className="home-tile-header">
                <span className="home-tile-title">{tile.title}</span>
                <span className="home-tile-slot">Slot {idx + 1}</span>
              </header>
              <div className="home-tile-body">
                <p className="home-tile-hint">{tile.hint}</p>
              </div>
            </section>
          ))}
        </div>
        <div className="home-ticker" aria-label="Market ticker">
          <div className="home-ticker-track">
            {/* Placeholder scrolling content – replace with live data later */}
            🔔 Futures: ES +0.28% • NQ +0.34% • RTY +0.12% • CL -0.45% • GC +0.15% • DXY 104.6 • VIX 12.8 • BTC 98,450 • ETH 5,230 • AAPL 198.32 • MSFT 374.55 • NVDA 487.21 • TSLA 234.10 • AMZN 152.40 • META 328.02 • GOOG 138.25 • SPY 471.31 • QQQ 404.17 • IWM 186.42 • 10Y 4.27% • 2Y 4.52% •
            🔔 Futures: ES +0.28% • NQ +0.34% • RTY +0.12% • CL -0.45% • GC +0.15% • DXY 104.6 • VIX 12.8 • BTC 98,450 • ETH 5,230 • AAPL 198.32 • MSFT 374.55 • NVDA 487.21 • TSLA 234.10 • AMZN 152.40 • META 328.02 • GOOG 138.25 • SPY 471.31 • QQQ 404.17 • IWM 186.42 • 10Y 4.27% • 2Y 4.52% •
          </div>
        </div>
      </main>
    </div>
  );
};

export default Home;
