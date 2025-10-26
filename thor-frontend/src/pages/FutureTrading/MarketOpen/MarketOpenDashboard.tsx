import { useEffect, useState } from 'react';
import { Box, Typography, Paper, Chip, Grid, CircularProgress, Alert, FormControl, InputLabel, Select, MenuItem } from '@mui/material';
import axios from 'axios';
import './MarketOpenDashboard.css';

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
}

const MarketOpenDashboard = () => {
  const [sessions, setSessions] = useState<MarketOpenSession[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  // Placeholder filter state (not wired yet)
  const [marketFilter, setMarketFilter] = useState<string>('all');
  const [outcomeFilter, setOutcomeFilter] = useState<string>('all');
  const [dateFilter, setDateFilter] = useState<string>('today');

  useEffect(() => {
    const fetchTodaySessions = async () => {
      try {
        setLoading(true);
        const response = await axios.get(
          'http://127.0.0.1:8000/api/futures/market-opens/today/'
        );
        // Backend returns array directly, not wrapped in {sessions: [...]}
        const data = Array.isArray(response.data) ? response.data : [];
        setSessions(data);
        setError(null);
      } catch (err) {
        console.error('Error fetching market open sessions:', err);
        // Don't show error for empty data - just show empty state
        setSessions([]);
        setError(null);
      } finally {
        setLoading(false);
      }
    };

    fetchTodaySessions();
    
    // Refresh every 5 seconds
    const interval = setInterval(fetchTodaySessions, 5000);
    return () => clearInterval(interval);
  }, []);

  // Dedicated header with future filter controls
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

  const getStatusColor = (status: string): "success" | "error" | "warning" | "default" => {
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

  const getSignalColor = (signal: string): "success" | "error" | "warning" | "default" => {
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
      maximumFractionDigits: 2 
    });
  };

  const formatTime = (timestamp: string) => {
    return new Date(timestamp).toLocaleTimeString('en-US', {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit'
    });
  };

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
    return (
      <div className="market-open-dashboard">
        <Header />
        <Box p={3} textAlign="center">
          <Typography variant="body1" color="text.secondary" gutterBottom>
            No market open sessions captured today
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Sessions will appear here when a market opens and data is captured
          </Typography>
        </Box>
      </div>
    );
  }

  return (
    <div className="market-open-dashboard">
      <Header />
      
      <Grid container spacing={2}>
        {sessions.map((session) => (
          <Grid size={{ xs: 12, sm: 6, md: 4, lg: 3 }} key={session.id}>
            <Paper className="market-open-card">
              {/* Header: Market & Time */}
              <div className="market-open-card-header">
                <Typography variant="h6" className="market-open-market-name">
                  {session.country}
                </Typography>
                <Typography variant="caption" className="market-open-time">
                  {formatTime(session.captured_at)}
                </Typography>
              </div>

              {/* Signal Badge */}
              <div className="market-open-signal-badge">
                <Chip
                  label={session.total_signal}
                  color={getSignalColor(session.total_signal)}
                  size="small"
                  className="signal-chip"
                />
              </div>

              {/* YM Trade Details */}
              <div className="market-open-trade-details">
                <div className="trade-detail-row">
                  <span className="trade-label">Entry:</span>
                  <span className="trade-value">{formatPrice(session.ym_entry_price)}</span>
                </div>
                <div className="trade-detail-row">
                  <span className="trade-label">Target:</span>
                  <span className="trade-value trade-target">{formatPrice(session.ym_high_dynamic)}</span>
                </div>
                <div className="trade-detail-row">
                  <span className="trade-label">Stop:</span>
                  <span className="trade-value trade-stop">{formatPrice(session.ym_low_dynamic)}</span>
                </div>
              </div>

              {/* Outcome Status */}
              <div className="market-open-outcome">
                <Chip
                  label={session.fw_nwdw}
                  color={getStatusColor(session.fw_nwdw)}
                  size="small"
                  className="outcome-chip"
                />
                {session.fw_exit_value && (
                  <Typography variant="caption" className="exit-value">
                    Exit: {formatPrice(session.fw_exit_value)}
                  </Typography>
                )}
              </div>
            </Paper>
          </Grid>
        ))}
      </Grid>
    </div>
  );
};

export default MarketOpenDashboard;
