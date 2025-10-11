import { Paper, Typography, Box } from '@mui/material';

const watchListRows = [
  {
    symbol: 'SPY',
    description: 'S&P 500 ETF',
    last: '$429.10',
    change: '+1.35',
    changePercent: '+0.32%',
    mark: '$429.05',
    volume: '32.5M',
  },
  {
    symbol: 'QQQ',
    description: 'Nasdaq 100 ETF',
    last: '$356.42',
    change: '-2.18',
    changePercent: '-0.61%',
    mark: '$356.38',
    volume: '21.1M',
  },
  {
    symbol: 'AAPL',
    description: 'Apple Inc.',
    last: '$182.91',
    change: '+0.72',
    changePercent: '+0.40%',
    mark: '$182.80',
    volume: '54.0M',
  },
  {
    symbol: 'TSLA',
    description: 'Tesla, Inc.',
    last: '$243.17',
    change: '-6.41',
    changePercent: '-2.57%',
    mark: '$242.95',
    volume: '65.8M',
  },
];

const WatchList = () => {
  return (
    <Paper elevation={0} className="watchlist-panel">
      <Box className="watchlist-header">
        <Typography variant="h5" className="watchlist-title">
          Watch List
        </Typography>
        <Typography variant="body2" className="watchlist-subtitle">
          Quick quotes for priority symbols
        </Typography>
      </Box>

      <Box className="watchlist-table" component="table">
        <Box component="thead" className="watchlist-table-head">
          <Box component="tr">
            <Typography component="th" className="watchlist-col watchlist-col-symbol">
              Symbol
            </Typography>
            <Typography component="th" className="watchlist-col">Last</Typography>
            <Typography component="th" className="watchlist-col">Change</Typography>
            <Typography component="th" className="watchlist-col">P/L %</Typography>
            <Typography component="th" className="watchlist-col">Mark</Typography>
            <Typography component="th" className="watchlist-col">Volume</Typography>
          </Box>
        </Box>
        <Box component="tbody">
          {watchListRows.map((row) => (
            <Box component="tr" key={row.symbol} className="watchlist-row">
              <Typography component="td" className="watchlist-cell watchlist-col-symbol">
                <span className="watchlist-symbol">{row.symbol}</span>
                <span className="watchlist-description">{row.description}</span>
              </Typography>
              <Typography component="td" className="watchlist-cell">
                {row.last}
              </Typography>
              <Typography
                component="td"
                className="watchlist-cell"
                color={row.change.startsWith('-') ? 'error.main' : 'success.main'}
              >
                {row.change}
              </Typography>
              <Typography
                component="td"
                className="watchlist-cell"
                color={row.changePercent.startsWith('-') ? 'error.main' : 'success.main'}
              >
                {row.changePercent}
              </Typography>
              <Typography component="td" className="watchlist-cell">
                {row.mark}
              </Typography>
              <Typography component="td" className="watchlist-cell">
                {row.volume}
              </Typography>
            </Box>
          ))}
        </Box>
      </Box>
    </Paper>
  );
};

export default WatchList;
