import React, { useEffect, useMemo, useState } from 'react';
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

const trimSlash = (value: string) => value.replace(/\/+$/, '');

const buildRibbonUrls = () => {
  const urls: string[] = [];
  const explicit = import.meta.env.VITE_RIBBON_API_URL;
  const base = import.meta.env.VITE_API_BASE_URL;
  const fallbackBase = import.meta.env.VITE_FALLBACK_API_BASE_URL || import.meta.env.VITE_BACKEND_BASE_URL;

  if (explicit) urls.push(trimSlash(explicit));
  if (base) urls.push(`${trimSlash(base)}/quotes/ribbon`);
  if (fallbackBase) urls.push(`${trimSlash(fallbackBase)}/api/quotes/ribbon`);
  urls.push('/api/quotes/ribbon'); // final relative fallback (Vite proxy/nginx)

  // Deduplicate while preserving order
  const seen = new Set<string>();
  return urls.filter((u) => {
    if (seen.has(u)) return false;
    seen.add(u);
    return true;
  });
};

// Footer ribbon component that displays live market data from any source
// Note: Currently uses Futures endpoint, but TradingInstrument model
// supports all asset classes (futures, stocks, crypto, forex, etc)
const FooterRibbon: React.FC = () => {
  const [ribbonData, setRibbonData] = useState<RibbonSymbol[]>([]);
  const [error, setError] = useState<string | null>(null);
  const MIN_SYMBOLS_FOR_LOOP = 20;
  const ribbonUrls = useMemo(buildRibbonUrls, []);

  useEffect(() => {
    const fetchRibbonData = async () => {
      let lastErr: any = null;
      for (const url of ribbonUrls) {
        try {
          const response = await fetch(url);
          if (!response.ok) {
            lastErr = new Error(`Failed to fetch ribbon data: ${response.status} (${url})`);
            continue;
          }
          const data: RibbonData = await response.json();
          setRibbonData(data.symbols);
          setError(null);
          return;
        } catch (err) {
          lastErr = err;
          continue;
        }
      }
      console.error('Error fetching ribbon data:', lastErr);
      setError(lastErr instanceof Error ? lastErr.message : 'Unknown error');
    };

    // Fetch immediately
    fetchRibbonData();

    // Poll every 2 seconds
    const interval = setInterval(fetchRibbonData, 2000);

    return () => clearInterval(interval);
  }, []);

  const extendedRibbonData = useMemo(() => {
    if (!ribbonData.length) {
      return [];
    }

    const loops = Math.max(1, Math.ceil(MIN_SYMBOLS_FOR_LOOP / ribbonData.length));
    if (loops === 1) {
      return ribbonData;
    }

    return Array.from({ length: loops }, () => ribbonData).flat();
  }, [ribbonData]);

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

    if (extendedRibbonData.length === 0) {
      return '📊 No symbols configured for ribbon display. Configure in admin panel. ';
    }

    return extendedRibbonData.map((item, idx) => {
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
