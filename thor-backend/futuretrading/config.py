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

# Data range: columns T:BJ, rows 4:13
# - Row 3 contains headers (symbol names, field labels)
# - Rows 4-13 contain data for 10 futures instruments
# - Columns T-BJ contain all fields (Time, Num, Perc, OHLC, Volume, Bid/Ask, etc.)
TOS_EXCEL_RANGE = "T4:BJ13"

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
