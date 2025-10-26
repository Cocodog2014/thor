import { useEffect, useState } from 'react';
import { Box, Typography, Paper, Chip, Grid, CircularProgress, Alert } from '@mui/material';
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

interface TodayResponse {
  date: string;
  count: number;
  sessions: MarketOpenSession[];
}

const MarketOpenDashboard = () => {
  const [sessions, setSessions] = useState<MarketOpenSession[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchTodaySessions = async () => {
      try {
        const response = await axios.get<TodayResponse>(
          'http://127.0.0.1:8000/api/futures/market-opens/today/'
        );
        setSessions(response.data.sessions);
        setError(null);
      } catch (err) {
        console.error('Error fetching market open sessions:', err);
        setError('Failed to load market open data');
      } finally {
        setLoading(false);
      }
    };

    fetchTodaySessions();
    
    // Refresh every 5 seconds
    const interval = setInterval(fetchTodaySessions, 5000);
    return () => clearInterval(interval);
  }, []);

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
      <Box display="flex" justifyContent="center" alignItems="center" p={4}>
        <CircularProgress />
      </Box>
    );
  }

  if (error) {
    return (
      <Alert severity="error" sx={{ m: 2 }}>
        {error}
      </Alert>
    );
  }

  if (sessions.length === 0) {
    return (
      <Box p={3}>
        <Typography variant="h6" color="text.secondary" align="center">
          No market open sessions captured today
        </Typography>
      </Box>
    );
  }

  return (
    <div className="market-open-dashboard">
      <Typography variant="h5" gutterBottom className="market-open-title">
        📊 Market Open Sessions - Today
      </Typography>
      
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
