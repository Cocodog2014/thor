"""
FutureTrading Configuration

Data source configuration for futures trading dashboard.
This file contains application settings that should be version controlled.
"""

# ============================================================================
# TOS Excel RTD Data Source
# ============================================================================
# FutureTrading reads live futures data from TOS Excel RTD

# Excel file with TOS RTD feed
TOS_EXCEL_FILE = r"A:\Thor\CleanData.xlsm"

# Sheet containing futures data
TOS_EXCEL_SHEET = "Futures"

# Data range: Basic quote data (columns A-N, includes headers in row 1)
# - Row 1: Headers (Symbol, Close, Open, NetChange, 24High, 24Low, 52WkHigh, 52WkLow, Volume, Bid, Last, Ask, BidSize, AskSize)
#   Backward compatible with legacy headers 'World High'/'World Low'.
# - Rows 2-12: 11 futures instruments with live RTD data
TOS_EXCEL_RANGE = "A1:N12"

# Expected futures symbols (for validation and fallback)
EXPECTED_FUTURES = [
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
