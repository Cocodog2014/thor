import React from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import './GlobalBanner.css';

// Permanent banner under the AppBar, shows connection/account info + balances + tabs.
const GlobalBanner: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();

  // Parent (top) tabs
  const parentTabs: { label: string; path: string; key: string }[] = [
    { label: 'Home',     path: '/app/home',     key: 'home' },
    { label: 'Futures',  path: '/app/futures',  key: 'futures' },
    { label: 'Global',   path: '/app/global',   key: 'global' },
    { label: 'Account',  path: '/app/account',  key: 'account' },
    { label: 'Activity', path: '/app/activity', key: 'activity' },
    { label: 'Research', path: '/app/home',     key: 'research' },
    { label: 'Settings', path: '/app/home',     key: 'settings' },
  ];

  // Child tabs for each parent (generic placeholders for now)
  const childTabsByParent: Record<string, { label: string; path: string }[]> = {
    home: [
      { label: 'View 1', path: '/app/home' },
      { label: 'View 2', path: '/app/home' },
      { label: 'View 3', path: '/app/home' },
    ],
    futures: [
      { label: 'Option A', path: '/app/futures' },
      { label: 'Option B', path: '/app/futures' },
      { label: 'Option C', path: '/app/futures' },
    ],
    global: [
      { label: 'Tab 1', path: '/app/global' },
      { label: 'Tab 2', path: '/app/global' },
    ],
    account: [
      { label: 'Panel 1', path: '/app/account' },
      { label: 'Panel 2', path: '/app/account' },
    ],
    activity: [
      { label: 'Section A', path: '/app/activity' },
      { label: 'Section B', path: '/app/activity' },
    ],
  };

  // Figure out which parent tab is active
  const activeParent =
    parentTabs.find((tab) => location.pathname.startsWith(tab.path)) ??
    parentTabs[0];

  const childTabs = childTabsByParent[activeParent.key] ?? [];

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

      {/* Row 3 parent tabs */}
      <nav className="global-banner-tabs home-nav">
        {parentTabs.map((tab) => {
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

      {/* Row 4 child tabs (generic placeholders, not wired yet) */}
      {childTabs.length > 0 && (
        <nav className="global-banner-subtabs">
          {childTabs.map((child) => {
            const active = location.pathname === child.path;
            return (
              <button
                key={child.label}
                type="button"
                onClick={() => console.log('Child tab clicked:', child.label)}
                className={`home-nav-button-child${active ? ' active' : ''}`}
              >
                {child.label}
              </button>
            );
          })}
        </nav>
      )}
    </div>
  );
};

export default GlobalBanner;
