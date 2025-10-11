import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Typography,
  Box,
  Button,
  Divider,
} from '@mui/material';
import type { WatchListSymbol, ReviewOrderDetails } from './types';

interface FinalModalProps {
  open: boolean;
  symbol: WatchListSymbol | null;
  details: ReviewOrderDetails | null;
  onClose: () => void;
  onConfirm: () => void;
}

const FinalModal = ({ open, symbol, details, onClose, onConfirm }: FinalModalProps) => {
  if (!symbol || !details) {
    return null;
  }

  const formatter = new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' });
  const formattedNotional = details.notional < 0
    ? `(${formatter.format(Math.abs(details.notional))})`
    : formatter.format(details.notional);

  return (
    <Dialog
      open={open}
      onClose={onClose}
      maxWidth="xs"
      fullWidth
      PaperProps={{ className: 'orders-final-dialog' }}
    >
      <DialogTitle className="orders-final-title">
        <Typography variant="subtitle1" className="orders-final-heading">
          {details.side === 'sell' ? 'Confirm Sell' : 'Confirm Buy'}
        </Typography>
      </DialogTitle>
      <DialogContent dividers className="orders-final-content">
        <Box className="orders-final-symbol">
          <Typography variant="h5" className="orders-final-symbol-text">
            {symbol.symbol}
          </Typography>
          <Typography variant="body2" className="orders-final-description">
            {symbol.description}
          </Typography>
        </Box>
        <Divider className="orders-final-divider" />
        <Box className="orders-final-summary">
          <div>
            <span>Order Type</span>
            <strong>{details.orderType.toUpperCase()}</strong>
          </div>
          <div>
            <span>Time in Force</span>
            <strong>{details.timeInForce.toUpperCase()}</strong>
          </div>
          <div>
            <span>Limit Price</span>
            <strong>{formatter.format(details.limitPrice)}</strong>
          </div>
          <div>
            <span>Shares</span>
            <strong>{details.side === 'sell' ? -details.shares : details.shares}</strong>
          </div>
          <div>
            <span>Estimated Total</span>
            <strong>{formattedNotional}</strong>
          </div>
        </Box>
        <Typography variant="caption" className="orders-final-note">
          This is a mock confirmation screen for design alignment. Execution wiring coming later.
        </Typography>
      </DialogContent>
      <DialogActions className="orders-final-actions">
        <Button onClick={onClose} color="inherit">
          Back
        </Button>
        <Button
          variant="contained"
          color={details.side === 'sell' ? 'error' : 'success'}
          onClick={onConfirm}
        >
          Submit Order
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default FinalModal;
