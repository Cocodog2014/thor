// src/pages/AccountStatements/AccountStatements.tsx
import React from 'react';

const AccountStatements: React.FC = () => {
  return (
    <div className="account-statements-page">
      <header className="account-statements-header">
        <h1>Account Statements</h1>
        <p className="account-statements-subtitle">
          View and download monthly and daily statements for your selected account.
        </p>
      </header>

      <section className="account-statements-filters">
        <div className="filter-group">
          <label htmlFor="statement-account">Account</label>
          {/* later we can wire this to the banner-selected account */}
          <select id="statement-account" className="account-statements-select">
            <option>Use banner account (coming soon)</option>
          </select>
        </div>

        <div className="filter-group">
          <label htmlFor="statement-range">Date Range</label>
          <select id="statement-range" className="account-statements-select">
            <option value="30d">Last 30 days</option>
            <option value="90d">Last 90 days</option>
            <option value="ytd">Year to date</option>
            <option value="1y">Last 12 months</option>
          </select>
        </div>

        <div className="filter-group">
          <label htmlFor="statement-type">Statement Type</label>
          <select id="statement-type" className="account-statements-select">
            <option value="all">All</option>
            <option value="monthly">Monthly</option>
            <option value="daily">Daily</option>
            <option value="tax">Tax</option>
          </select>
        </div>

        <button
          type="button"
          className="account-statements-apply-btn"
        >
          Apply Filters
        </button>
      </section>

      <section className="account-statements-results">
        <div className="account-statements-results-header">
          <h2>Available Statements</h2>
          <span className="account-statements-count">
            (Coming soon – wiring to backend)
          </span>
        </div>

        <div className="account-statements-table-wrapper">
          <table className="account-statements-table">
            <thead>
              <tr>
                <th>Date</th>
                <th>Statement Type</th>
                <th>Account</th>
                <th>Format</th>
                <th>Download</th>
              </tr>
            </thead>
            <tbody>
              {/* placeholder rows for now */}
              <tr>
                <td>—</td>
                <td>—</td>
                <td>—</td>
                <td>—</td>
                <td>
                  <button
                    type="button"
                    className="account-statements-download-btn"
                    disabled
                  >
                    Download
                  </button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
};

export default AccountStatements;
