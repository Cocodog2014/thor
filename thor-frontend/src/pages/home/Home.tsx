import React from 'react';
import TimeZone from '../TimeZone/TimeZone.tsx';
import './Home.css';

const Home: React.FC = () => {
  return (
    <div className="dashboard-grid">
      {/* Global Markets (World Clock) */}
      <section className="dashboard-card global-markets" aria-label="Global Markets">
        <TimeZone />
      </section>
    </div>
  );
};

export default Home;