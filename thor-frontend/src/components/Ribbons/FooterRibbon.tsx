import React, { useEffect, useState } from 'react';
import './FooterRibbon.css';

interface RibbonSymbol {
  symbol: string;
  name: string;
  price: number | string | null;
  last: number | string | null;
  change: number | string | null;
  change_percent: number | string | null;
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
        const response = await fetch('/api/quotes/ribbon');
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

  const toNumber = (value: number | string | null | undefined) => {
    if (value === null || value === undefined) return null;
    const numeric = typeof value === 'string' ? Number(value) : value;
    return Number.isFinite(numeric) ? numeric : null;
  };

  const formatPrice = (price: number | string | null | undefined) => {
    const numericPrice = toNumber(price);
    if (numericPrice === null) return '—';
    return numericPrice.toFixed(2);
  };

  const formatChange = (
    change: number | string | null | undefined,
    percent: number | string | null | undefined,
  ) => {
    const numericChange = toNumber(change);
    const numericPercent = toNumber(percent);
    if (numericChange === null || numericPercent === null) return '';
    const sign = numericChange >= 0 ? '+' : '';
    return `${sign}${numericPercent.toFixed(2)}%`;
  };

  const renderContent = (dupIndex = 0) => {
    if (error) {
      return `⚠️ Error loading data: ${error} `;
    }

    if (ribbonData.length === 0) {
      return '📊 No symbols configured for ribbon display. Configure in admin panel. ';
    }

    return ribbonData.map((item, idx) => {
      const numericChange = toNumber(item.change);
      const changeClass = (numericChange ?? 0) >= 0 ? 'positive' : 'negative';
      return (
        <span key={`${item.symbol}-${dupIndex}-${idx}`} className="ribbon-item">
          <span className="ribbon-symbol">{item.symbol}</span>
          <span className="ribbon-price">{formatPrice(item.last ?? item.price)}</span>
          <span className={`ribbon-change ${changeClass}`}>
            {formatChange(item.change, item.change_percent)}
          </span>
          {' • '}
        </span>
      );
    });
  };

  return (
    <div className="footer-ribbon" aria-label="Market ticker ribbon">
      <div className="footer-ribbon-track">
        {renderContent(0)}
        {renderContent(1)} {/* Duplicate for seamless loop */}
      </div>
    </div>
  );
};

export default FooterRibbon;
