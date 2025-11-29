# Data Contracts

Canonical schemas for Redis keys and API payloads.

Redis Latest (`quotes:latest:<symbol>`):
- Fields: `last`, `bid`, `ask`, `last_size`, `bid_size`, `ask_size`, `ts`, `source`

Redis Stream (`quotes:stream:unified`):
- Entry: `{ symbol, ts, last, bid, ask, sizes..., source }`

API: `/api/quotes/latest`
- Response: `{ symbol, last, bid, ask, extended_data: { 52w fields... } }`

API: Market Session list/detail
- Fields: `session_number`, `country`, `future`, local `year/month/date/day`, prices, targets, metrics

## Examples (Canonical)

### Redis Hash: `quotes:latest:YM`
```json
{
	"last": 47682.0,
	"bid": 47681.0,
	"ask": 47683.0,
	"last_size": 2,
	"bid_size": 1,
	"ask_size": 1,
	"ts": "2025-11-28T14:30:01.123Z",
	"source": "EXCEL"
}
```

### Redis Stream Entry: `quotes:stream:unified`
```json
{
	"id": "1732804201123-0",
	"symbol": "YM",
	"ts": "2025-11-28T14:30:01.123Z",
	"last": 47682.0,
	"bid": 47681.0,
	"ask": 47683.0,
	"last_size": 2,
	"bid_size": 1,
	"ask_size": 1,
	"source": "EXCEL"
}
```

### API: `/api/quotes/latest?symbol=YM`
```json
{
	"symbol": "YM",
	"last": 47682.0,
	"bid": 47681.0,
	"ask": 47683.0,
	"extended_data": {
		"high_52w": 47683.0,
		"low_52w": 47679.0,
		"dist_from_52w_high": 1.0,
		"dist_from_52w_low": 3.0
	}
}
```

### API: Market Session (list item)
```json
{
	"session_number": 42,
	"capture_group": 17,
	"country": "USA",
	"future": "YM",
	"year": 2025,
	"month": 11,
	"date": 28,
	"day": "Fri",
	"captured_at": "2025-11-28T14:30:05.000Z",
	"bhs": "BUY",
	"weight": 1,
	"wndw": "PENDING",
	"last_price": 47682.0,
	"bid_price": 47681.0,
	"ask_price": 47683.0,
	"bid_size": 1,
	"ask_size": 1,
	"spread": 2.0,
	"volume": 120,
	"entry_price": 47683.0,
	"target_high": 47733.0,
	"target_low": 47633.0,
	"prev_close_24h": 47600.0,
	"open_price_24h": 47610.0,
	"open_prev_diff_24h": 10.0,
	"open_prev_pct_24h": 0.0210,
	"low_24h": 47500.0,
	"high_24h": 47750.0,
	"range_diff_24h": 250.0,
	"range_pct_24h": 0.5250,
	"low_52w": 43000.0,
	"high_52w": 48000.0,
	"range_52w": 5000.0,
	"range_pct_52w": 10.48,
	"high_pct_52w": 0.26,
	"low_pct_52w": 10.34
}
```

### API: Market Session (TOTAL row)
```json
{
	"session_number": 42,
	"country": "USA",
	"future": "TOTAL",
	"instrument_count": 11,
	"weighted_average": -0.109,
	"bhs": "SELL",
	"weight": 11,
	"entry_price": 47681.0,
	"target_high": 47631.0,
	"target_low": 47731.0
}
```

Notes:
- Percent fields are stored with 4 decimal places.
- Local calendar fields (`year/month/date/day`) reflect market-local time.
- `session_number` is the primary grouping key for the 12-row snapshot.
