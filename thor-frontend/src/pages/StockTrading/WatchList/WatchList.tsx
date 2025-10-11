import { useState } from 'react';
import { Paper, Typography, Box, IconButton, Tooltip } from '@mui/material';
import { KeyboardArrowUp, KeyboardArrowDown, DragHandle } from '@mui/icons-material';
import SearchOutlinedIcon from '@mui/icons-material/SearchOutlined';
import OrderModal from '../Orders/Order';
import ReviewModal from '../Orders/Review';
import FinalModal from '../Orders/Final';
import type { WatchListSymbol, ReviewOrderDetails } from '../Orders/types';

const watchListRows: WatchListSymbol[] = [
  {
    symbol: 'SPY',
    description: 'S&P 500 ETF',
    last: '$429.10',
    netChange: '+1.35',
    open: '$427.40',
    bid: '$429.05',
    ask: '$429.15',
    size: '1.2K',
    volume: '32.5M',
    high: '$430.22',
    low: '$426.80',
    fiftyTwoWeekHigh: '$451.20',
    fiftyTwoWeekLow: '$389.15',
    quoteTrend: 'up',
    bidX: 'ARCA x 800',
    askX: 'BATS x 600',
    lastX: 'ARCA x 400',
  },
  {
    symbol: 'QQQ',
    description: 'Nasdaq 100 ETF',
    last: '$356.42',
    netChange: '-2.18',
    open: '$358.90',
    bid: '$356.35',
    ask: '$356.48',
    size: '980',
    volume: '21.1M',
    high: '$359.75',
    low: '$354.90',
    fiftyTwoWeekHigh: '$387.45',
    fiftyTwoWeekLow: '$309.25',
    quoteTrend: 'down',
    bidX: 'NSDQ x 500',
    askX: 'NSDQ x 420',
    lastX: 'EDGX x 380',
  },
  {
    symbol: 'AAPL',
    description: 'Apple Inc.',
    last: '$182.91',
    netChange: '+0.72',
    open: '$181.60',
    bid: '$182.84',
    ask: '$182.93',
    size: '2.1K',
    volume: '54.0M',
    high: '$183.65',
    low: '$181.42',
    fiftyTwoWeekHigh: '$199.62',
    fiftyTwoWeekLow: '$164.08',
    quoteTrend: 'flat',
    bidX: 'NSDQ x 1200',
    askX: 'NSDQ x 1100',
    lastX: 'NSDQ x 950',
  },
  {
    symbol: 'TSLA',
    description: 'Tesla, Inc.',
    last: '$243.17',
    netChange: '-6.41',
    open: '$248.60',
    bid: '$243.05',
    ask: '$243.30',
    size: '1.5K',
    volume: '65.8M',
    high: '$249.14',
    low: '$241.80',
    fiftyTwoWeekHigh: '$299.29',
    fiftyTwoWeekLow: '$207.30',
    quoteTrend: 'down',
    bidX: 'NSDQ x 880',
    askX: 'NSDQ x 910',
    lastX: 'NSDQ x 700',
  },
  {
    symbol: 'MMM',
    description: '3M Company',
    last: '$96.42',
    netChange: '+0.18',
    open: '$95.70',
    bid: '$96.38',
    ask: '$96.45',
    size: '640',
    volume: '2.8M',
    high: '$97.10',
    low: '$95.20',
    fiftyTwoWeekHigh: '$113.02',
    fiftyTwoWeekLow: '$84.20',
    quoteTrend: 'up',
    bidX: 'NYSE x 320',
    askX: 'NYSE x 340',
    lastX: 'NYSE x 300',
  },
];

type WatchListRow = WatchListSymbol;

const WatchList = () => {
  const [selectedSymbol, setSelectedSymbol] = useState<WatchListSymbol | null>(null);
  const [orderOpen, setOrderOpen] = useState(false);
  const [reviewOpen, setReviewOpen] = useState(false);
  const [reviewSide, setReviewSide] = useState<'buy' | 'sell'>('buy');
  const [finalOpen, setFinalOpen] = useState(false);
  const [finalDetails, setFinalDetails] = useState<ReviewOrderDetails | null>(null);

  const getTrendIcon = (trend: WatchListRow['quoteTrend']) => {
    if (trend === 'up') {
      return <KeyboardArrowUp fontSize="inherit" />;
    }
    if (trend === 'down') {
      return <KeyboardArrowDown fontSize="inherit" />;
    }
    return <DragHandle fontSize="inherit" />;
  };

  const handleAddSymbol = () => {
    console.info('Open add-to-watchlist dialog');
  };

  const handleSymbolClick = (row: WatchListRow) => {
    setSelectedSymbol(row);
    setOrderOpen(true);
  };

  const handleOrderClose = () => {
    setOrderOpen(false);
    setSelectedSymbol(null);
    setReviewOpen(false);
    setFinalOpen(false);
    setFinalDetails(null);
    setReviewSide('buy');
  };

  const handleSelectAction = (side: 'buy' | 'sell') => {
    setReviewSide(side);
    setReviewOpen(true);
    setOrderOpen(false);
  };

  const handleReviewClose = () => {
    setReviewOpen(false);
    setOrderOpen(true);
  };

  const handleReviewComplete = (details: ReviewOrderDetails) => {
    setReviewOpen(false);
    setReviewSide(details.side);
    setFinalDetails(details);
    setFinalOpen(true);
  };

  const handleFinalClose = () => {
    setFinalOpen(false);
    if (finalDetails) {
      setReviewSide(finalDetails.side);
    }
    setReviewOpen(true);
    setFinalDetails(null);
  };

  const handleFinalConfirm = () => {
    handleOrderClose();
  };

  return (
    <Paper elevation={0} className="watchlist-panel">
      <Box className="watchlist-header">
        <Box className="watchlist-header-row">
          <Typography variant="h5" className="watchlist-title">
            Watch List
          </Typography>
          <Tooltip title="Add symbol">
            <IconButton
              size="small"
              onClick={handleAddSymbol}
              className="watchlist-search-button"
              aria-label="Add symbol to watch list"
            >
              <SearchOutlinedIcon fontSize="inherit" />
            </IconButton>
          </Tooltip>
        </Box>
        <Typography variant="body2" className="watchlist-subtitle">
          Quick quotes for priority symbols
        </Typography>
      </Box>

      <Box className="watchlist-table-scroll">
        <table className="watchlist-table">
          <thead>
            <tr>
              <th className="watchlist-col watchlist-col-symbol">Symbol</th>
              <th className="watchlist-col">Last</th>
              <th className="watchlist-col">Net Chg</th>
              <th className="watchlist-col">Open</th>
              <th className="watchlist-col">Bid</th>
              <th className="watchlist-col">Ask</th>
              <th className="watchlist-col">Size</th>
              <th className="watchlist-col">Volume</th>
              <th className="watchlist-col">High</th>
              <th className="watchlist-col">Low</th>
              <th className="watchlist-col">52 High</th>
              <th className="watchlist-col">52 Low</th>
              <th className="watchlist-col watchlist-col-trend">Quote Trend</th>
              <th className="watchlist-col">Bid X</th>
              <th className="watchlist-col">Ask X</th>
              <th className="watchlist-col">Last X</th>
            </tr>
          </thead>
          <tbody>
            {watchListRows.map((row) => {
              const isNegative = row.netChange.startsWith('-');
              return (
                <tr key={row.symbol} className="watchlist-row">
                  <td className="watchlist-cell watchlist-col-symbol">
                    <button
                      type="button"
                      className="watchlist-symbol-button"
                      onClick={() => handleSymbolClick(row)}
                    >
                      <span className="watchlist-symbol">{row.symbol}</span>
                      <span className="watchlist-description">{row.description}</span>
                    </button>
                  </td>
                  <td className="watchlist-cell watchlist-align-right">{row.last}</td>
                  <td
                    className={`watchlist-cell watchlist-align-right ${isNegative ? 'watchlist-change-negative' : 'watchlist-change-positive'}`}
                  >
                    {row.netChange}
                  </td>
                  <td className="watchlist-cell watchlist-align-right">{row.open}</td>
                  <td className="watchlist-cell watchlist-align-right">{row.bid}</td>
                  <td className="watchlist-cell watchlist-align-right">{row.ask}</td>
                  <td className="watchlist-cell watchlist-align-right">{row.size}</td>
                  <td className="watchlist-cell watchlist-align-right">{row.volume}</td>
                  <td className="watchlist-cell watchlist-align-right">{row.high}</td>
                  <td className="watchlist-cell watchlist-align-right">{row.low}</td>
                  <td className="watchlist-cell watchlist-align-right">{row.fiftyTwoWeekHigh}</td>
                  <td className="watchlist-cell watchlist-align-right">{row.fiftyTwoWeekLow}</td>
                  <td className="watchlist-cell watchlist-align-center watchlist-col-trend">
                    <span className={`watchlist-trend watchlist-trend-${row.quoteTrend}`}>
                      {getTrendIcon(row.quoteTrend)}
                    </span>
                  </td>
                  <td className="watchlist-cell watchlist-align-right">{row.bidX}</td>
                  <td className="watchlist-cell watchlist-align-right">{row.askX}</td>
                  <td className="watchlist-cell watchlist-align-right">{row.lastX}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </Box>

      <OrderModal
        open={orderOpen}
        symbol={selectedSymbol}
        onClose={handleOrderClose}
        onSelectAction={handleSelectAction}
      />
      <ReviewModal
        open={reviewOpen}
        symbol={selectedSymbol}
        initialSide={reviewSide}
        onClose={handleReviewClose}
        onReview={handleReviewComplete}
      />
      <FinalModal
        open={finalOpen}
        symbol={selectedSymbol}
        details={finalDetails}
        onClose={handleFinalClose}
        onConfirm={handleFinalConfirm}
      />
    </Paper>
  );
};

export default WatchList;
