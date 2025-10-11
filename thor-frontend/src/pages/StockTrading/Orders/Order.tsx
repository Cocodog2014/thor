import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Typography,
  Box,
  Divider,
  Button,
} from '@mui/material';
import type { WatchListSymbol } from './types';

interface OrderModalProps {
  open: boolean;
  symbol: WatchListSymbol | null;
  onClose: () => void;
  onSelectAction: (side: 'buy' | 'sell') => void;
}

const OrderModal = ({ open, symbol, onClose, onSelectAction }: OrderModalProps) => {
  if (!symbol) {
    return null;
  }

  return (
    <Dialog
      open={open}
      onClose={onClose}
      maxWidth="sm"
      fullWidth
      PaperProps={{ className: 'orders-order-dialog' }}
    >
      <DialogTitle className="orders-order-title">
        <Box className="orders-order-title-row">
          <Typography variant="h6" className="orders-order-symbol">
            {symbol.symbol}
          </Typography>
          <Typography variant="subtitle2" className="orders-order-description">
            {symbol.description}
          </Typography>
        </Box>
      </DialogTitle>
      <DialogContent dividers className="orders-order-content">
        <Box className="orders-order-price-row">
          <Typography variant="h4" className="orders-order-price">
            {symbol.last}
          </Typography>
          <Typography
            variant="subtitle1"
            className={`orders-order-change ${symbol.netChange.startsWith('-') ? 'orders-order-change-negative' : 'orders-order-change-positive'}`}
          >
            {symbol.netChange}
          </Typography>
        </Box>
        <Typography variant="body2" className="orders-order-note">
          Mini snapshot; full chart module coming soon.
        </Typography>
        <Divider className="orders-order-divider" />
        <Box className="orders-order-grid">
          <dl>
            <div className="orders-order-detail">
              <dt>Open</dt>
              <dd>{symbol.open}</dd>
            </div>
            <div className="orders-order-detail">
              <dt>Bid</dt>
              <dd>{symbol.bid}</dd>
            </div>
            <div className="orders-order-detail">
              <dt>Ask</dt>
              <dd>{symbol.ask}</dd>
            </div>
            <div className="orders-order-detail">
              <dt>Volume</dt>
              <dd>{symbol.volume}</dd>
            </div>
          </dl>
          <dl>
            <div className="orders-order-detail">
              <dt>High</dt>
              <dd>{symbol.high}</dd>
            </div>
            <div className="orders-order-detail">
              <dt>Low</dt>
              <dd>{symbol.low}</dd>
            </div>
            <div className="orders-order-detail">
              <dt>52 High</dt>
              <dd>{symbol.fiftyTwoWeekHigh}</dd>
            </div>
            <div className="orders-order-detail">
              <dt>52 Low</dt>
              <dd>{symbol.fiftyTwoWeekLow}</dd>
            </div>
          </dl>
        </Box>
        <Box className="orders-order-chart">
          <Typography variant="body2">Chart preview placeholder</Typography>
        </Box>
      </DialogContent>
      <DialogActions className="orders-order-actions">
        <Button onClick={onClose} color="inherit">
          Close
        </Button>
        <Box className="orders-order-buttons">
          <Button
            variant="contained"
            color="error"
            className="orders-order-button orders-order-button-sell"
            onClick={() => onSelectAction('sell')}
          >
            <span className="orders-order-button-label">Sell @ {symbol.bid}</span>
            <span className="orders-order-button-sub">Bid Size: {symbol.bidX}</span>
          </Button>
          <Button
            variant="contained"
            color="success"
            className="orders-order-button orders-order-button-buy"
            onClick={() => onSelectAction('buy')}
          >
            <span className="orders-order-button-label">Buy @ {symbol.ask}</span>
            <span className="orders-order-button-sub">Ask Size: {symbol.askX}</span>
          </Button>
        </Box>
      </DialogActions>
    </Dialog>
  );
};

export default OrderModal;
