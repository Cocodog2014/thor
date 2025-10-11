import { Fragment, useState } from 'react';
import { Paper, Typography, Box } from '@mui/material';
import OrderModal from '../Orders/Order';
import ReviewModal from '../Orders/Review';
import FinalModal from '../Orders/Final';
import type { WatchListSymbol, ReviewOrderDetails } from '../Orders/types';

const Positions = () => {
  const columns = [
    { key: 'symbol', label: 'Symbol', align: 'left' as const },
    { key: 'plDay', label: 'P/L Day', align: 'right' as const },
    { key: 'marketChange', label: 'Market\nChange', align: 'right' as const },
    { key: 'mark', label: 'Mark', align: 'right' as const },
    { key: 'tradePrice', label: 'Trade\nPrice', align: 'right' as const },
    { key: 'plOpen', label: 'P/L Open', align: 'right' as const },
    { key: 'plPercent', label: 'P/L %', align: 'right' as const },
    { key: 'plYtd', label: 'P/L YTD', align: 'right' as const },
    { key: 'margin', label: 'Margin', align: 'right' as const },
    { key: 'delta', label: 'Delta', align: 'right' as const },
    { key: 'ask', label: 'Ask', align: 'right' as const },
    { key: 'bid', label: 'Bid', align: 'right' as const },
  ] as const;

  type ColumnKey = (typeof columns)[number]['key'];

  type MetricTone = 'gain' | 'loss' | 'neutral';

  type MetricValue = {
    text: string;
    tone?: MetricTone;
  };

  type PositionRow = {
    symbol: string;
    size?: string;
    fields: Record<ColumnKey, MetricValue>;
  };

  type AccountSection = {
    name: string;
    summary?: Record<ColumnKey, MetricValue>;
    rows: PositionRow[];
    subtotal: Record<ColumnKey, MetricValue>;
  };

  const accountSections: AccountSection[] = [
    {
      name: 'Joint Tenant',
      summary: {
        symbol: { text: 'Account' },
        plDay: { text: '($37.80)', tone: 'loss' },
        marketChange: { text: '-0.28', tone: 'loss' },
        mark: { text: '1.37' },
        tradePrice: { text: '-' },
        plOpen: { text: '($316.91)', tone: 'loss' },
        plPercent: { text: '-63.15%', tone: 'loss' },
        plYtd: { text: '($316.91)', tone: 'loss' },
        margin: { text: '$0.00' },
        delta: { text: '-0.12', tone: 'loss' },
        ask: { text: '3.73' },
        bid: { text: '3.71' },
      },
      rows: [
        {
          symbol: 'CGC',
          size: '+135',
          fields: {
            symbol: { text: 'CGC' },
            plDay: { text: '($37.80)', tone: 'loss' },
            marketChange: { text: '-0.28', tone: 'loss' },
            mark: { text: '1.37' },
            tradePrice: { text: '3.72' },
            plOpen: { text: '($316.91)', tone: 'loss' },
            plPercent: { text: '-63.15%', tone: 'loss' },
            plYtd: { text: '($316.91)', tone: 'loss' },
            margin: { text: '$0.00' },
            delta: { text: '-0.12', tone: 'loss' },
            ask: { text: '3.73' },
            bid: { text: '3.71' },
          },
        },
      ],
      subtotal: {
        symbol: { text: 'Subtotals:' },
        plDay: { text: '($37.80)', tone: 'loss' },
        marketChange: { text: '-0.28', tone: 'loss' },
  mark: { text: '1.37' },
        tradePrice: { text: '-' },
        plOpen: { text: '($316.91)', tone: 'loss' },
        plPercent: { text: '-63.15%', tone: 'loss' },
        plYtd: { text: '($316.91)', tone: 'loss' },
        margin: { text: '$0.00' },
        delta: { text: '-0.12', tone: 'loss' },
        ask: { text: '-' },
        bid: { text: '-' },
      },
    },
    {
      name: 'Rollover IRA',
      summary: {
        symbol: { text: 'Account' },
        plDay: { text: '($9,092.28)', tone: 'loss' },
        marketChange: { text: '-0.34', tone: 'loss' },
        mark: { text: '1.06' },
        tradePrice: { text: '-' },
        plOpen: { text: '($61,506.22)', tone: 'loss' },
        plPercent: { text: '-63.17%', tone: 'loss' },
        plYtd: { text: '$61,823.13', tone: 'gain' },
        margin: { text: '$28,500.00', tone: 'neutral' },
        delta: { text: '+0.45', tone: 'gain' },
        ask: { text: '0.87' },
        bid: { text: '0.83' },
      },
      rows: [
        {
          symbol: 'VFF',
          size: '+26000',
          fields: {
            symbol: { text: 'VFF' },
            plDay: { text: '($8,840.00)', tone: 'loss' },
            marketChange: { text: '-0.34', tone: 'loss' },
            mark: { text: '0.86' },
            tradePrice: { text: '0.85' },
            plOpen: { text: '$63,940.20', tone: 'gain' },
            plPercent: { text: '+289.06%', tone: 'gain' },
            plYtd: { text: '$63,940.20', tone: 'gain' },
            margin: { text: '$20,400.00' },
            delta: { text: '+0.32', tone: 'gain' },
            ask: { text: '0.86' },
            bid: { text: '0.84' },
          },
        },
        {
          symbol: 'CGC',
          size: '+901',
          fields: {
            symbol: { text: 'CGC' },
            plDay: { text: '($252.28)', tone: 'loss' },
            marketChange: { text: '-0.28', tone: 'loss' },
            mark: { text: '1.37' },
            tradePrice: { text: '3.71' },
            plOpen: { text: '($2,117.07)', tone: 'loss' },
            plPercent: { text: '-63.17%', tone: 'loss' },
            plYtd: { text: '($2,117.07)', tone: 'loss' },
            margin: { text: '$8,100.00' },
            delta: { text: '+0.13', tone: 'gain' },
            ask: { text: '3.72' },
            bid: { text: '3.69' },
          },
        },
      ],
      subtotal: {
        symbol: { text: 'Subtotals:' },
        plDay: { text: '($9,092.28)', tone: 'loss' },
        marketChange: { text: '-', tone: 'neutral' },
  mark: { text: '1.06', tone: 'neutral' },
        tradePrice: { text: '-' },
        plOpen: { text: '$61,823.13', tone: 'gain' },
        plPercent: { text: '+242.72%', tone: 'gain' },
        plYtd: { text: '$61,823.13', tone: 'gain' },
        margin: { text: '$28,500.00' },
        delta: { text: '+0.45', tone: 'gain' },
        ask: { text: '-' },
        bid: { text: '-' },
      },
    },
  ];

  const overallTotals: Record<ColumnKey, MetricValue> = {
    symbol: { text: 'Overall Totals:' },
    plDay: { text: '($9,130.08)', tone: 'loss' },
    marketChange: { text: '-', tone: 'neutral' },
    mark: { text: '1.12' },
    tradePrice: { text: '-' },
    plOpen: { text: '$61,506.22', tone: 'gain' },
    plPercent: { text: '+236.81%', tone: 'gain' },
    plYtd: { text: '$61,823.13', tone: 'gain' },
    margin: { text: '$28,500.00' },
    delta: { text: '+0.33', tone: 'gain' },
    ask: { text: '-' },
    bid: { text: '-' },
  };

  const toWatchListSymbol = (row: PositionRow, accountName: string): WatchListSymbol => {
    const mark = row.fields.mark?.text ?? '-';
    const marketChange = row.fields.marketChange?.text ?? '0.00';
    const tradePrice = row.fields.tradePrice?.text ?? '-';
    const bid = row.fields.bid?.text ?? '-';
    const ask = row.fields.ask?.text ?? '-';
    const size = row.size ?? '-';
    const tone = row.fields.marketChange?.tone;
    const quoteTrend: WatchListSymbol['quoteTrend'] = tone === 'gain' ? 'up' : tone === 'loss' ? 'down' : 'flat';

    return {
      symbol: row.symbol,
      description: `${accountName} · ${size !== '-' ? `${size} position` : 'Open position'}`,
      last: mark,
      netChange: marketChange,
      open: tradePrice,
      bid,
      ask,
      size,
      volume: row.fields.plOpen?.text ?? '--',
      high: mark,
      low: mark,
      fiftyTwoWeekHigh: mark,
      fiftyTwoWeekLow: mark,
      quoteTrend,
      bidX: `Bid: ${bid}`,
      askX: `Ask: ${ask}`,
      lastX: `Mark: ${mark}`,
    };
  };

  const [selectedSymbol, setSelectedSymbol] = useState<WatchListSymbol | null>(null);
  const [orderOpen, setOrderOpen] = useState(false);
  const [reviewOpen, setReviewOpen] = useState(false);
  const [reviewSide, setReviewSide] = useState<'buy' | 'sell'>('buy');
  const [finalOpen, setFinalOpen] = useState(false);
  const [finalDetails, setFinalDetails] = useState<ReviewOrderDetails | null>(null);

  const handlePositionClick = (row: PositionRow, accountName: string) => {
    setSelectedSymbol(toWatchListSymbol(row, accountName));
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
    setFinalDetails(null);
    setReviewOpen(true);
  };

  const handleFinalConfirm = () => {
    handleOrderClose();
  };

  const footerMetrics = [
    { label: 'P/L Day', value: '($9,130.08)', tone: 'loss' as MetricTone },
    { label: 'P/L Open', value: '$61,506.22', tone: 'gain' as MetricTone },
    { label: 'Net Liq', value: '$87,779.32', tone: 'gain' as MetricTone },
    { label: 'Available Dollars', value: '$300.00', tone: 'gain' as MetricTone },
    { label: 'Position Equity', value: '$63,940.20', tone: 'gain' as MetricTone },
  ];

  const getToneColor = (tone?: MetricTone) => {
    if (tone === 'gain') return 'success.main';
    if (tone === 'loss') return 'error.main';
    return undefined;
  };

  const getAlignClass = (align: (typeof columns)[number]['align']) =>
    align === 'right' ? 'positions-align-right' : 'positions-align-left';

  return (
    <Paper elevation={0} className="positions-panel">
      <Box className="positions-header">
        <Typography variant="h5" className="positions-title">
          Positions
        </Typography>
        <Typography variant="body2" className="positions-subtitle">
          Daily P/L and account breakdown
        </Typography>
      </Box>

      <Box className="positions-table-scroll">
        <table className="positions-table">
          <thead>
            <tr>
              {columns.map((column) => (
                <th key={column.key} className={getAlignClass(column.align)} scope="col">
                  {column.label.split('\n').map((part, index, parts) => (
                    <span key={`${column.key}-label-${index}`} className="positions-header-line">
                      {part}
                      {index < parts.length - 1 ? <br /> : null}
                    </span>
                  ))}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {accountSections.map((account) => (
              <Fragment key={account.name}>
                {account.summary && (
                  <tr className="positions-account-header">
                    {columns.map((column) => (
                      <td
                        key={column.key}
                        className={`${getAlignClass(column.align)} ${column.key === 'symbol' ? 'positions-account-label positions-symbol-cell' : 'positions-cell'}`.trim()}
                      >
                        {column.key === 'symbol' ? (
                          <Box className="positions-account-label-wrapper">
                            <Typography
                              variant="subtitle2"
                              className="positions-account-label-title"
                              color={getToneColor(account.summary?.[column.key]?.tone)}
                            >
                              {account.summary?.[column.key]?.text ?? 'Account'}
                            </Typography>
                            <Typography variant="caption" className="positions-account-label-subtext">
                              {account.name}
                            </Typography>
                          </Box>
                        ) : (
                          <Typography
                            variant="subtitle2"
                            color={getToneColor(account.summary?.[column.key]?.tone)}
                          >
                            {account.summary?.[column.key]?.text ?? '-'}
                          </Typography>
                        )}
                      </td>
                    ))}
                  </tr>
                )}

                {account.rows.map((row) => (
                  <tr key={`${account.name}-${row.symbol}`} className="positions-row">
                    {columns.map((column) => {
                      const field = row.fields[column.key];
                      if (column.key === 'symbol') {
                        return (
                          <td
                            key={`${row.symbol}-${column.key}`}
                            className={`positions-symbol-cell ${getAlignClass(column.align)}`}
                          >
                            <button
                              type="button"
                              className="positions-symbol-button"
                              onClick={() => handlePositionClick(row, account.name)}
                              aria-label={`Open order modal for ${row.symbol}`}
                            >
                              <Box className="positions-symbol">
                                <Typography variant="body2" className="positions-symbol-text">
                                  {field?.text ?? row.symbol}
                                </Typography>
                                {row.size && (
                                  <Typography
                                    variant="caption"
                                    className="positions-symbol-size"
                                    color={row.size.startsWith('-') ? 'error.main' : 'success.main'}
                                  >
                                    {row.size}
                                  </Typography>
                                )}
                              </Box>
                            </button>
                          </td>
                        );
                      }

                      return (
                        <td
                          key={`${row.symbol}-${column.key}`}
                          className={`positions-cell ${getAlignClass(column.align)}`}
                        >
                          <Typography variant="body2" color={getToneColor(field?.tone)}>
                            {field?.text ?? '-'}
                          </Typography>
                        </td>
                      );
                    })}
                  </tr>
                ))}

                <tr className="positions-subtotal">
                  {columns.map((column) => (
                    <td
                      key={`${account.name}-subtotal-${column.key}`}
                      className={`${column.key === 'symbol' ? 'positions-subtotal-label positions-symbol-cell' : 'positions-cell'} ${getAlignClass(column.align)}`.trim()}
                    >
                      <Typography variant="body2" color={getToneColor(account.subtotal[column.key]?.tone)}>
                        {account.subtotal[column.key]?.text ?? (column.key === 'symbol' ? 'Subtotals:' : '-')}
                      </Typography>
                    </td>
                  ))}
                </tr>
              </Fragment>
            ))}

            <tr className="positions-overall">
              {columns.map((column) => (
                <td
                  key={`overall-${column.key}`}
                  className={`${column.key === 'symbol' ? 'positions-overall-label positions-symbol-cell' : 'positions-cell'} ${getAlignClass(column.align)}`.trim()}
                >
                  <Typography variant="body2" color={getToneColor(overallTotals[column.key]?.tone)}>
                    {overallTotals[column.key]?.text ?? (column.key === 'symbol' ? 'Overall Totals:' : '-')}
                  </Typography>
                </td>
              ))}
            </tr>
          </tbody>
        </table>
      </Box>

      <Box className="positions-footer">
        {footerMetrics.map((metric) => (
          <Box key={metric.label} className="positions-footer-row">
            <Typography variant="body2" className="positions-footer-label">
              {metric.label}
            </Typography>
            <Typography
              variant="body2"
              className="positions-align-right"
              color={getToneColor(metric.tone)}
            >
              {metric.value}
            </Typography>
          </Box>
        ))}
      </Box>

      {orderOpen && !reviewOpen && !finalOpen && (
        <OrderModal
          open={orderOpen}
          symbol={selectedSymbol}
          onClose={handleOrderClose}
          onSelectAction={handleSelectAction}
        />
      )}
      {reviewOpen && !finalOpen && (
        <ReviewModal
          open={reviewOpen}
          symbol={selectedSymbol}
          initialSide={reviewSide}
          onClose={handleReviewClose}
          onReview={handleReviewComplete}
        />
      )}
      {finalOpen && (
        <FinalModal
          open={finalOpen}
          symbol={selectedSymbol}
          details={finalDetails}
          onClose={handleFinalClose}
          onConfirm={handleFinalConfirm}
        />
      )}
    </Paper>
  );
};

export default Positions;
