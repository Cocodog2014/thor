import { useEffect, useMemo, useState } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Typography,
  Box,
  Divider,
  ToggleButtonGroup,
  ToggleButton,
  IconButton,
  TextField,
  Slider,
  Button,
} from '@mui/material';
import AddCircleOutlineIcon from '@mui/icons-material/AddCircleOutline';
import RemoveCircleOutlineIcon from '@mui/icons-material/RemoveCircleOutline';
import type { WatchListSymbol, ReviewOrderDetails } from './types';

interface ReviewModalProps {
  open: boolean;
  symbol: WatchListSymbol | null;
  initialSide: 'buy' | 'sell';
  onClose: () => void;
  onReview: (details: ReviewOrderDetails) => void;
}

const toNumber = (value: string) => Number(value.replace(/[^0-9.\-]/g, '')) || 0;

const ReviewModal = ({ open, symbol, initialSide, onClose, onReview }: ReviewModalProps) => {
  const [side, setSide] = useState<'buy' | 'sell'>(initialSide);
  const [orderType, setOrderType] = useState<'limit' | 'market'>('limit');
  const [timeInForce, setTimeInForce] = useState<'day' | 'gtc'>('day');
  const [limitPrice, setLimitPrice] = useState(0);
  const [shares, setShares] = useState(100);

  useEffect(() => {
    setSide(initialSide);
  }, [initialSide]);

  useEffect(() => {
    if (!symbol) {
      return;
    }
    const startPrice = side === 'buy' ? toNumber(symbol.ask) : toNumber(symbol.bid);
    const fallback = toNumber(symbol.last);
    setLimitPrice(startPrice || fallback);
    setShares(100);
    setOrderType('limit');
    setTimeInForce('day');
  }, [symbol, side]);

  if (!symbol) {
    return null;
  }

  const handleLimitField = (event: React.ChangeEvent<HTMLInputElement>) => {
    const next = Number(event.target.value);
    if (!Number.isNaN(next)) {
      setLimitPrice(next);
    }
  };

  const handleLimitAdjust = (delta: number) => {
    setLimitPrice((prev) => Number((prev + delta).toFixed(2)));
  };

  const handleShareAdjust = (delta: number) => {
    setShares((prev) => Math.max(1, prev + delta));
  };

  const handleShareField = (event: React.ChangeEvent<HTMLInputElement>) => {
    const rawValue = Number(event.target.value);
    if (Number.isNaN(rawValue)) {
      return;
    }
    if (rawValue < 0) {
      setSide('sell');
      setShares(Math.max(1, Math.abs(rawValue)));
    } else {
      setSide('buy');
      setShares(Math.max(1, rawValue));
    }
  };

  const notional = useMemo(() => {
    const direction = side === 'sell' ? -1 : 1;
    return direction * limitPrice * shares;
  }, [limitPrice, shares, side]);

  const formattedNotional = useMemo(() => {
    if (!notional) {
      return '$0.00';
    }
    const formatter = new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' });
    if (notional < 0) {
      return `(${formatter.format(Math.abs(notional))})`;
    }
    return formatter.format(notional);
  }, [notional]);

  const dailyLow = toNumber(symbol.low);
  const dailyHigh = toNumber(symbol.high);
  const sliderMin = dailyLow ? Math.min(dailyLow, limitPrice * 0.9) : limitPrice * 0.9;
  const sliderMax = dailyHigh ? Math.max(dailyHigh, limitPrice * 1.1) : limitPrice * 1.1;

  const handleReview = () => {
    onReview({
      side,
      orderType,
      timeInForce,
      limitPrice,
      shares,
      notional,
    });
  };

  return (
    <Dialog
      open={open}
      onClose={onClose}
      maxWidth="sm"
      fullWidth
      PaperProps={{ className: `orders-review-dialog orders-review-dialog-${side}` }}
    >
      <DialogTitle className="orders-review-title">
        <Box className="orders-review-header">
          <Typography variant="subtitle1" className="orders-review-mode">
            {side === 'sell' ? 'Sell' : 'Buy'} {symbol.symbol}
          </Typography>
          <Typography variant="body2" className="orders-review-subtitle">
            {symbol.description}
          </Typography>
        </Box>
      </DialogTitle>
      <DialogContent dividers className="orders-review-content">
        <Box className="orders-review-price-summary">
          <Typography variant="h4" className="orders-review-last">
            {symbol.last}
          </Typography>
          <Typography
            variant="subtitle1"
            className={`orders-review-change ${symbol.netChange.startsWith('-') ? 'orders-review-change-negative' : 'orders-review-change-positive'}`}
          >
            {symbol.netChange}
          </Typography>
        </Box>
        <Box className="orders-review-price-grid">
          <div>
            <h4>Bid</h4>
            <p>{symbol.bid}</p>
            <span>{symbol.bidX}</span>
          </div>
          <div>
            <h4>Ask</h4>
            <p>{symbol.ask}</p>
            <span>{symbol.askX}</span>
          </div>
          <div>
            <h4>Last</h4>
            <p>{symbol.last}</p>
            <span>{symbol.lastX}</span>
          </div>
        </Box>
        <Divider className="orders-review-divider" />
        <Box className="orders-review-controls">
          <ToggleButtonGroup
            value={side}
            exclusive
            onChange={(_, value: 'buy' | 'sell' | null) => {
              if (value) {
                setSide(value);
              }
            }}
            className="orders-review-toggle orders-review-toggle-side"
          >
            <ToggleButton value="sell">Sell</ToggleButton>
            <ToggleButton value="buy">Buy</ToggleButton>
          </ToggleButtonGroup>
          <ToggleButtonGroup
            value={orderType}
            exclusive
            onChange={(_, value: 'limit' | 'market' | null) => {
              if (value) {
                setOrderType(value);
              }
            }}
            className="orders-review-toggle"
          >
            <ToggleButton value="limit">Limit</ToggleButton>
            <ToggleButton value="market">Market</ToggleButton>
          </ToggleButtonGroup>
          <ToggleButtonGroup
            value={timeInForce}
            exclusive
            onChange={(_, value: 'day' | 'gtc' | null) => {
              if (value) {
                setTimeInForce(value);
              }
            }}
            className="orders-review-toggle"
          >
            <ToggleButton value="day">Day</ToggleButton>
            <ToggleButton value="gtc">GTC</ToggleButton>
          </ToggleButtonGroup>
        </Box>
        <Box className="orders-review-limit">
          <Typography component="span">Limit</Typography>
          <Box className="orders-review-limit-inputs">
            <IconButton onClick={() => handleLimitAdjust(-0.05)} aria-label="Decrease price" size="small">
              <RemoveCircleOutlineIcon fontSize="inherit" />
            </IconButton>
            <TextField
              size="small"
              type="number"
              value={limitPrice.toFixed(2)}
              onChange={handleLimitField}
              inputProps={{ step: 0.01, min: 0 }}
            />
            <IconButton onClick={() => handleLimitAdjust(0.05)} aria-label="Increase price" size="small">
              <AddCircleOutlineIcon fontSize="inherit" />
            </IconButton>
          </Box>
        </Box>
        <Slider
          value={limitPrice}
          min={Math.max(0, sliderMin)}
          max={Math.max(sliderMax, sliderMin + 0.5)}
          step={0.01}
          onChange={(_, value) => {
            setLimitPrice(Array.isArray(value) ? value[0] : value);
          }}
          className="orders-review-slider"
        />
        <Box className="orders-review-shares">
          <Typography component="span">Shares</Typography>
          <Box className="orders-review-shares-controls">
            <IconButton onClick={() => handleShareAdjust(-1)} aria-label="Decrease shares" size="small">
              <RemoveCircleOutlineIcon fontSize="inherit" />
            </IconButton>
            <TextField
              size="small"
              type="number"
              value={side === 'sell' ? -shares : shares}
              onChange={handleShareField}
              inputProps={{ step: 1 }}
            />
            <IconButton onClick={() => handleShareAdjust(1)} aria-label="Increase shares" size="small">
              <AddCircleOutlineIcon fontSize="inherit" />
            </IconButton>
          </Box>
        </Box>
        <Box className="orders-review-summary">
          <div>
            <span>Cost of Trade</span>
            <strong>{formattedNotional}</strong>
          </div>
          <div>
            <span>Exchange</span>
            <strong>BEST</strong>
          </div>
          <div>
            <span>Instruction</span>
            <strong>None</strong>
          </div>
        </Box>
      </DialogContent>
      <DialogActions className="orders-review-actions">
        <Button onClick={onClose} color="inherit">
          Cancel
        </Button>
        <Box className="orders-review-footer-buttons">
          <Button variant="outlined" color="inherit">
            More
          </Button>
          <Button variant="contained" color={side === 'sell' ? 'error' : 'success'} onClick={handleReview}>
            Review
          </Button>
        </Box>
      </DialogActions>
    </Dialog>
  );
};

export default ReviewModal;
