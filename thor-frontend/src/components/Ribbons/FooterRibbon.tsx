import React, { useEffect, useState } from 'react';
import './FooterRibbon.css';

interface RibbonSymbol {
  symbol: string;
  name: string;
  price: number | null;
  last: number | null;
  change: number | null;
  change_percent: number | null;
  signal: string | null;
}

interface RibbonData {
  symbols: RibbonSymbol[];
  count: number;
  last_updated: string;
}

// Footer ribbon component that displays live market data from any source
// Note: Currently uses FutureTrading endpoint, but TradingInstrument model
// supports all asset classes (futures, stocks, crypto, forex, etc)
const FooterRibbon: React.FC = () => {
  const [ribbonData, setRibbonData] = useState<RibbonSymbol[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchRibbonData = async () => {
      try {
        const response = await fetch('/api/futuretrading/quotes/ribbon');
        if (!response.ok) {
          throw new Error(`Failed to fetch ribbon data: ${response.status}`);
        }
        const data: RibbonData = await response.json();
        setRibbonData(data.symbols);
        setError(null);
      } catch (err) {
        console.error('Error fetching ribbon data:', err);
        setError(err instanceof Error ? err.message : 'Unknown error');
      }
    };

    // Fetch immediately
    fetchRibbonData();

    // Poll every 2 seconds
    const interval = setInterval(fetchRibbonData, 2000);

    return () => clearInterval(interval);
  }, []);

  const formatPrice = (price: number | null) => {
    if (price === null || price === undefined) return '—';
    return price.toFixed(2);
  };

  const formatChange = (change: number | null, percent: number | null) => {
    if (change === null || percent === null) return '';
    const sign = change >= 0 ? '+' : '';
    return `${sign}${percent.toFixed(2)}%`;
  };

  const renderContent = () => {
    if (error) {
      return `⚠️ Error loading data: ${error} `;
    }

    if (ribbonData.length === 0) {
      return '📊 No symbols configured for ribbon display. Configure in admin panel. ';
    }

    return ribbonData.map((item, idx) => {
      const changeClass = (item.change ?? 0) >= 0 ? 'positive' : 'negative';
      return (
        <span key={`${item.symbol}-${idx}`} className="ribbon-item">
          <span className="ribbon-symbol">{item.symbol}</span>
          <span className="ribbon-price">{formatPrice(item.last || item.price)}</span>
          <span className={`ribbon-change ${changeClass}`}>
            {formatChange(item.change, item.change_percent)}
          </span>
          {' • '}
        </span>
      );
    }).join('');
  };

  return (
    <div className="footer-ribbon" aria-label="Market ticker ribbon">
      <div className="footer-ribbon-track">
        {renderContent()}
        {renderContent()} {/* Duplicate for seamless loop */}
      </div>
    </div>
  );
};

export default FooterRibbon;
