import React from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import './GlobalBanner.css';

// Permanent banner under the AppBar, shows connection/account info + balances + tabs.
const GlobalBanner: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();

  const tabs: { label: string; path: string }[] = [
    { label: 'Home', path: '/app/home' },
    { label: 'Futures', path: '/app/futures' },
    { label: 'Global', path: '/app/global' },
    { label: 'Account', path: '/app/account' },
    { label: 'Activity', path: '/app/activity' },
    { label: 'Research', path: '/app/home' }, // placeholder
    { label: 'Settings', path: '/app/home' }, // placeholder
  ];

  return (
    <div className="global-banner" role="navigation" aria-label="Primary navigation banner">
      {/* Row 1 */}
      <div className="global-banner-row global-banner-row-top">
        <div className="global-banner-left">
          <span className="home-connection">
            <span className="home-connection-dot" />
            Connected
          </span>
          <span className="home-connection-details">Realtime data</span>
          <span className="home-account-id">739954815CHW (Rollover IRA)</span>
        </div>
        <div className="global-banner-right">
          <a href="mailto:admin@360edu.org" className="home-contact-link">
            <span>📧</span> admin@360edu.org
          </a>
          <button className="home-quick-link" type="button" onClick={() => navigate('/app/home')}>
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

      {/* Row 2 balances */}
      <div className="global-banner-balances home-balances">
        <span>Option Buying Power:<span className="home-balance-value">$6,471.41</span></span>
        <span>Stock Buying Power:<span className="home-balance-value">$6,471.41</span></span>
        <span>Net Liq:<span className="home-balance-value">$105,472.85</span></span>
      </div>

      {/* Row 3 tabs */}
      <nav className="global-banner-tabs home-nav">
        {tabs.map((tab) => {
          const active = location.pathname === tab.path;
          return (
            <button
              key={tab.label}
              type="button"
              onClick={() => navigate(tab.path)}
              className={`home-nav-button${active ? ' active' : ''}`}
            >
              {tab.label}
            </button>
          );
        })}
      </nav>
    </div>
  );
};

export default GlobalBanner;
