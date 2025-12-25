from __future__ import annotations
"""TOS Excel RTD data source configuration."""

# Excel file with TOS RTD feed - using simpler RTD_TOS.xlsm to avoid conflicts
TOS_EXCEL_FILE = r"A:\Thor\RTD_TOS.xlsm"

# Sheet containing futures data
TOS_EXCEL_SHEET = "LiveData"

# Data range: Basic quote data (columns A-N, includes headers in row 1)
# - Row 1: Headers (Symbol, Close, Open, NetChange, 24High, 24Low, 52WkHigh,
#   52WkLow, Volume, Bid, Last, Ask, BidSize, AskSize)
#   Backward compatible with legacy headers 'World High'/'World Low'.
# - Rows 2-13: 12 futures instruments with live RTD data
TOS_EXCEL_RANGE = "A1:N13"

# Expected futures symbols (for validation and fallback)
TOS_EXPECTED_FUTURES = [
	"YM",   # Dow Jones E-mini
	"ES",   # S&P 500 E-mini
	"NQ",   # Nasdaq 100 E-mini
	"RTY",  # Russell 2000 E-mini
	"CL",   # Crude Oil
	"SI",   # Silver
	"HG",   # Copper
	"GC",   # Gold
	"VX",   # VIX Futures
	"DX",   # Dollar Index
	"ZB",   # 30-Year Treasury Bond
]

# Backwards compatibility for callers expecting EXPECTED_FUTURES
EXPECTED_FUTURES = TOS_EXPECTED_FUTURES

__all__ = [
	"TOS_EXCEL_FILE",
	"TOS_EXCEL_SHEET",
	"TOS_EXCEL_RANGE",
	"TOS_EXPECTED_FUTURES",
	"EXPECTED_FUTURES",
]