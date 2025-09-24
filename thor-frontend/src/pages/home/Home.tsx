import React from 'react';
import TimeZone from '../TimeZone/TimeZone.tsx';
import './Home.css';

// The Home.css file is the single source of truth for positioning/layout
// of all Home dashboard widgets (markets, charts, buttons, etc.).
// Add new sections here and place them via CSS grid in Home.css.
const Home: React.FC = () => {
  return (
    <div className="dashboard-grid">
      {/* Global Markets (World Clock) */}
      <section className="dashboard-card global-markets" aria-label="Global Markets">
        <TimeZone />
      </section>

      {/* Future widgets go here; keep structure, position via Home.css only */}
      {/* <section className="dashboard-card charts" aria-label="Charts">Charts TBD</section> */}
      {/* <section className="dashboard-card quick-actions" aria-label="Quick Actions">Buttons TBD</section> */}
    </div>
  );
};

export default Home;