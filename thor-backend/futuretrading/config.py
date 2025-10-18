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

# Data range: Basic quote data (columns A-M, includes headers in row 1)
# - Row 1: Headers (Symbol, Close, Open, NetChange, World High, World Low, Volume, Bid, Last, Ask, BidSize, AskSize)
# - Rows 2-11: 10 futures instruments with live RTD data
TOS_EXCEL_RANGE = "A1:M11"

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
]
