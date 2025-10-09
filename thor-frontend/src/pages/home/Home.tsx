import React, { useState } from 'react';
import TimeZone from '../TimeZone/TimeZone.tsx';
import './Home.css';

const Home: React.FC = () => {
  const [activeProvider, setActiveProvider] = useState(
    localStorage.getItem('selectedProvider') || 'excel_live'
  );
  
  const selectProvider = (provider: string) => {
    setActiveProvider(provider);
    localStorage.setItem('selectedProvider', provider);
    
    window.dispatchEvent(new CustomEvent('provider-changed', { 
      detail: { provider } 
    }));
  };
  
  return (
    <div className="dashboard-grid">
      {/* Global Markets (World Clock) */}
      <section className="dashboard-card global-markets" aria-label="Global Markets">
        <TimeZone />
      </section>

      {/* Provider Selection - Added from futures page */}
      <section className="dashboard-card data-source" aria-label="Data Source">
        <h2>Data Source</h2>
        <div className="provider-controls">
          <button 
            className={`btn excel-live-btn ${activeProvider === 'excel_live' ? 'active' : ''}`}
            onClick={() => selectProvider('excel_live')}
          >
            EXCEL LIVE
          </button>
          <button 
            className={`btn schwab-btn ${activeProvider === 'schwab' ? 'active' : ''}`}
            onClick={() => selectProvider('schwab')}
          > SCHWAB
          </button>
        </div>
        
      </section>
    </div>
  );
};

export default Home;