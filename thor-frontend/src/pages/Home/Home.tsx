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

      {/* BLANK BODY – we’ll add widgets here later */}
      <main className="home-content">
        {/* Blank home canvas – widgets will be added here later */}
      </main>
    </div>
  );
};

export default Home;
