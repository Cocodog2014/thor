import { useEffect, useState } from 'react';
import { Alert, Box, CircularProgress, FormControl, InputLabel, MenuItem, Select, Typography } from '@mui/material';
import axios from 'axios';
import './MarketOpenDashboard.css';

interface FutureSnapshot {
  id: number;
  symbol: string;
  last_price: string | null;
  change: string | null;
  change_percent: string | null;
  bid: string | null;
  bid_size: number | null;
  ask: string | null;
  ask_size: number | null;
  volume: number | null;
  vwap: string | null;
  spread: string | null;
  open: string | null;
  close: string | null;
  open_vs_prev_number: string | null;
  open_vs_prev_percent: string | null;
  day_24h_low: string | null;
  day_24h_high: string | null;
  range_high_low: string | null;
  range_percent: string | null;
  week_52_low: string | null;
  week_52_high: string | null;
  week_52_range_high_low: string | null;
  week_52_range_percent: string | null;
  entry_price: string | null;
  high_dynamic: string | null;
  low_dynamic: string | null;
  weighted_average: string | null;
  signal: string | null;
  weight: number | null;
  sum_weighted: string | null;
  instrument_count: number | null;
  status: string | null;
  outcome: string;
  exit_price: string | null;
  exit_time: string | null;
  created_at: string;
}

interface MarketOpenSession {
  id: number;
  session_number: number;
  year: number;
  month: number;
  date: number;
  day: string;
  captured_at: string;
  country: string;
  total_signal: string;
  ym_entry_price: string | null;
  ym_high_dynamic: string | null;
  ym_low_dynamic: string | null;
  fw_nwdw: string;
  fw_exit_value: string | null;
  fw_exit_percent: string | null;
  created_at: string;
  futures?: FutureSnapshot[];
}

const MarketOpenDashboard = () => {
  const [sessions, setSessions] = useState<MarketOpenSession[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [marketFilter, setMarketFilter] = useState<string>('all');
  const [outcomeFilter, setOutcomeFilter] = useState<string>('all');
  const [dateFilter, setDateFilter] = useState<string>('today');

  useEffect(() => {
    const fetchTodaySessions = async () => {
      try {
        setLoading(true);
        const response = await axios.get('http://127.0.0.1:8000/api/futures/market-opens/today/');
        const data = Array.isArray(response.data) ? response.data : [];
        setSessions(data);
        setError(null);
      } catch (err) {
        console.error('Error fetching market open sessions:', err);
        setSessions([]);
        setError(null);
      } finally {
        setLoading(false);
      }
    };

    fetchTodaySessions();
    const interval = setInterval(fetchTodaySessions, 5000);
    return () => clearInterval(interval);
  }, []);

  const getStatusColor = (status: string): 'success' | 'error' | 'warning' | 'default' => {
    switch (status) {
      case 'WORKED':
        return 'success';
      case 'DIDNT_WORK':
        return 'error';
      case 'PENDING':
        return 'warning';
      default:
        return 'default';
    }
  };

  const getSignalColor = (signal: string): 'success' | 'error' | 'warning' | 'default' => {
    switch (signal) {
      case 'BUY':
      case 'STRONG_BUY':
        return 'success';
      case 'SELL':
      case 'STRONG_SELL':
        return 'error';
      case 'HOLD':
        return 'warning';
      default:
        return 'default';
    }
  };

  const formatPrice = (price: string | null) => {
    if (!price) return '—';
    return parseFloat(price).toLocaleString('en-US', {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    });
  };

  const formatTime = (timestamp: string) =>
    new Date(timestamp).toLocaleTimeString('en-US', {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    });

  const Header = () => (
    <div className="market-open-header">
      <Typography variant="h6" className="market-open-header-title">
        📊 Market Open Sessions
      </Typography>
      <div className="market-open-header-filters">
        <FormControl size="small" className="mo-filter">
          <InputLabel id="mo-market-label">Market</InputLabel>
          <Select
            labelId="mo-market-label"
            label="Market"
            value={marketFilter}
            onChange={(e) => setMarketFilter(String(e.target.value))}
          >
            <MenuItem value="all">All</MenuItem>
            <MenuItem value="asia">Asia</MenuItem>
            <MenuItem value="europe">Europe</MenuItem>
            <MenuItem value="americas">Americas</MenuItem>
          </Select>
        </FormControl>

        <FormControl size="small" className="mo-filter">
          <InputLabel id="mo-outcome-label">Outcome</InputLabel>
          <Select
            labelId="mo-outcome-label"
            label="Outcome"
            value={outcomeFilter}
            onChange={(e) => setOutcomeFilter(String(e.target.value))}
          >
            <MenuItem value="all">All</MenuItem>
            <MenuItem value="worked">Worked</MenuItem>
            <MenuItem value="didnt_work">Didn't Work</MenuItem>
            <MenuItem value="pending">Pending</MenuItem>
          </Select>
        </FormControl>

        <FormControl size="small" className="mo-filter">
          <InputLabel id="mo-date-label">Date</InputLabel>
          <Select
            labelId="mo-date-label"
            label="Date"
            value={dateFilter}
            onChange={(e) => setDateFilter(String(e.target.value))}
          >
            <MenuItem value="today">Today</MenuItem>
            <MenuItem value="yesterday">Yesterday</MenuItem>
            <MenuItem value="last7">Last 7 days</MenuItem>
          </Select>
        </FormControl>
      </div>
    </div>
  );

  if (loading) {
    return (
      <div className="market-open-dashboard">
        <Header />
        <Box display="flex" justifyContent="center" alignItems="center" p={4}>
          <CircularProgress />
        </Box>
      </div>
    );
  }

  if (error) {
    return (
      <div className="market-open-dashboard">
        <Header />
        <Alert severity="error" sx={{ m: 2 }}>
          {error}
        </Alert>
      </div>
    );
  }

  if (sessions.length === 0) {
    // Show placeholder raw containers to match real-time cards layout
    const placeholders = Array.from({ length: 3 }, (_, i) => i);
    return (
      <div className="market-open-dashboard">
        <Header />
        <div className="mo-cards">
          {placeholders.map((i) => (
            <div key={`placeholder-${i}`} className="mo-session-card">
              <div className="mo-card-header">
                <div className="mo-card-title">Session</div>
                <div className="mo-card-badges">
                  <span className={`mo-chip default`}>—</span>
                  <span className={`mo-chip default`}>—</span>
                  <span className={`mo-chip default`}>—</span>
                  <span className="mo-time">—</span>
                </div>
              </div>
              <div className="mo-card-body">
                <div className="mo-field">
                  <label>Entry</label>
                  <span>—</span>
                </div>
                <div className="mo-field success">
                  <label>Target</label>
                  <span>—</span>
                </div>
                <div className="mo-field danger">
                  <label>Stop</label>
                  <span>—</span>
                </div>
                <div className="mo-divider" />
                <div className="mo-field">
                  <label>Exit</label>
                  <span>—</span>
                </div>
                <div className="mo-field">
                  <label>Exit %</label>
                  <span>—</span>
                </div>
                <div className="mo-field">
                  <label>Status</label>
                  <span>—</span>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="market-open-dashboard">
      <Header />
      <div className="mo-cards">
        {sessions.map((s) => (
          <div key={s.id} className="mo-rt-card">
            {/* Header chips row similar to futures real-time */}
            <div className="mo-rt-header">
              <span className="mo-rt-chip sym">{s.country || '—'}</span>
              <span className={`mo-rt-chip ${getSignalColor(s.total_signal)}`}>{s.total_signal || '—'}</span>
              <span className={`mo-rt-chip ${getStatusColor(s.fw_nwdw)}`}>{s.fw_nwdw || '—'}</span>
              <span className="mo-rt-chip">Wgt: —</span>
              <span className="mo-rt-chip">Δ —</span>
              <span className="mo-rt-chip">—%</span>
              <span className="mo-rt-time">{formatTime(s.captured_at)}</span>
            </div>

            <div className="mo-rt-body">
              {/* Top row: Last + Change */}
              <div className="mo-rt-top">
                <div className="mo-rt-last">
                  <div className="val">{formatPrice(s.ym_entry_price)}</div>
                  <div className="label">Last</div>
                </div>
                <div className="mo-rt-change">
                  <div className="val">—</div>
                  <div className="pct">—%</div>
                  <div className="label">Change</div>
                </div>
              </div>

              {/* BID / ASK tiles */}
              <div className="mo-rt-bbo">
                <div className="tile bid">
                  <div className="t-head">BID</div>
                  <div className="t-main">—</div>
                  <div className="t-sub">Size —</div>
                </div>
                <div className="tile ask">
                  <div className="t-head">ASK</div>
                  <div className="t-main">—</div>
                  <div className="t-sub">Size —</div>
                </div>
              </div>

              {/* Stats grid */}
              <div className="mo-rt-stats">
                <div className="stat"><div className="label">Volume</div><div className="value">—</div></div>
                <div className="stat"><div className="label">VWAP</div><div className="value">—</div></div>
                <div className="stat"><div className="label">Close</div><div className="value">—</div></div>
                <div className="stat"><div className="label">Open</div><div className="value">—</div></div>
                <div className="stat"><div className="label">Open vs Prev</div><div className="value">— <span className="sub">—%</span></div></div>
                <div className="stat"><div className="label">24h Low</div><div className="value">—</div></div>
                <div className="stat"><div className="label">24h High</div><div className="value">—</div></div>
                <div className="stat"><div className="label">24h Range</div><div className="value">— <span className="sub">—%</span></div></div>
                <div className="stat"><div className="label">52W Low</div><div className="value">—</div></div>
                <div className="stat"><div className="label">52W High</div><div className="value">—</div></div>
                <div className="stat"><div className="label">From 52W High</div><div className="value">— <span className="sub">—%</span></div></div>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default MarketOpenDashboard;
