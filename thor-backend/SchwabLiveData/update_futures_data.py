"""
Dynamic JSON Data Updater for SchwabLiveData

This script continuously updates the futures_data.json file with realistic
market data variations every 2 seconds. It maintains 10 different data sets
for each future and rotates through them to simulate real market movement.

Usage:
    python update_futures_data.py
    python update_futures_data.py --interval 5  # Update every 5 seconds
    python update_futures_data.py --static      # Generate static variations only
"""

import json
import time
import random
import argparse
import os
from datetime import datetime
from typing import Dict, List, Any

# Base data templates for each future (10 variations per future)
FUTURES_DATA_SETS = {
    "/YM": [
        {"base_price": 317.92, "signal": "BUY", "stat_value": 10.000, "volume_base": 218245},
        {"base_price": 319.45, "signal": "STRONG_BUY", "stat_value": 12.500, "volume_base": 235680},
        {"base_price": 315.78, "signal": "HOLD", "stat_value": 0.000, "volume_base": 198750},
        {"base_price": 312.34, "signal": "SELL", "stat_value": -8.750, "volume_base": 245890},
        {"base_price": 321.56, "signal": "STRONG_BUY", "stat_value": 15.000, "volume_base": 267430},
        {"base_price": 316.89, "signal": "BUY", "stat_value": 8.250, "volume_base": 203560},
        {"base_price": 314.23, "signal": "HOLD", "stat_value": 2.500, "volume_base": 189340},
        {"base_price": 318.67, "signal": "BUY", "stat_value": 11.750, "volume_base": 224870},
        {"base_price": 313.45, "signal": "SELL", "stat_value": -6.250, "volume_base": 256780},
        {"base_price": 320.12, "signal": "STRONG_BUY", "stat_value": 13.750, "volume_base": 287650}
    ],
    "/ES": [
        {"base_price": 300.18, "signal": "BUY", "stat_value": 1.000, "volume_base": 232173},
        {"base_price": 302.45, "signal": "STRONG_BUY", "stat_value": 1.250, "volume_base": 248960},
        {"base_price": 298.76, "signal": "HOLD", "stat_value": 0.000, "volume_base": 215340},
        {"base_price": 296.34, "signal": "SELL", "stat_value": -0.875, "volume_base": 267890},
        {"base_price": 304.67, "signal": "STRONG_BUY", "stat_value": 1.500, "volume_base": 289750},
        {"base_price": 299.89, "signal": "BUY", "stat_value": 0.825, "volume_base": 201450},
        {"base_price": 297.56, "signal": "HOLD", "stat_value": 0.250, "volume_base": 187620},
        {"base_price": 301.23, "signal": "BUY", "stat_value": 1.175, "volume_base": 239870},
        {"base_price": 295.78, "signal": "SELL", "stat_value": -0.625, "volume_base": 278340},
        {"base_price": 303.45, "signal": "STRONG_BUY", "stat_value": 1.375, "volume_base": 254680}
    ],
    "/NQ": [
        {"base_price": 307.35, "signal": "BUY", "stat_value": 2.500, "volume_base": 139395},
        {"base_price": 310.78, "signal": "STRONG_BUY", "stat_value": 3.125, "volume_base": 156780},
        {"base_price": 304.23, "signal": "HOLD", "stat_value": 0.000, "volume_base": 128450},
        {"base_price": 301.56, "signal": "SELL", "stat_value": -2.187, "volume_base": 167890},
        {"base_price": 313.89, "signal": "STRONG_BUY", "stat_value": 3.750, "volume_base": 178230},
        {"base_price": 306.67, "signal": "BUY", "stat_value": 2.062, "volume_base": 134670},
        {"base_price": 303.45, "signal": "HOLD", "stat_value": 0.625, "volume_base": 121890},
        {"base_price": 309.12, "signal": "BUY", "stat_value": 2.937, "volume_base": 145230},
        {"base_price": 300.78, "signal": "SELL", "stat_value": -1.562, "volume_base": 189450},
        {"base_price": 312.34, "signal": "STRONG_BUY", "stat_value": 3.437, "volume_base": 167820}
    ],
    "RTY": [
        {"base_price": 358.03, "signal": "SELL", "stat_value": -2.500, "volume_base": 134579},
        {"base_price": 361.45, "signal": "BUY", "stat_value": 1.875, "volume_base": 145890},
        {"base_price": 355.78, "signal": "HOLD", "stat_value": 0.000, "volume_base": 127340},
        {"base_price": 352.34, "signal": "STRONG_SELL", "stat_value": -3.125, "volume_base": 156780},
        {"base_price": 364.67, "signal": "STRONG_BUY", "stat_value": 2.812, "volume_base": 167890},
        {"base_price": 359.23, "signal": "BUY", "stat_value": 1.562, "volume_base": 139450},
        {"base_price": 356.89, "signal": "SELL", "stat_value": -1.875, "volume_base": 148670},
        {"base_price": 362.78, "signal": "BUY", "stat_value": 2.187, "volume_base": 152340},
        {"base_price": 354.12, "signal": "STRONG_SELL", "stat_value": -2.812, "volume_base": 171230},
        {"base_price": 360.45, "signal": "HOLD", "stat_value": 0.625, "volume_base": 143890}
    ],
    "CL": [
        {"base_price": 245.67, "signal": "BUY", "stat_value": 0.050, "volume_base": 85375},
        {"base_price": 247.23, "signal": "STRONG_BUY", "stat_value": 0.062, "volume_base": 92450},
        {"base_price": 243.89, "signal": "HOLD", "stat_value": 0.000, "volume_base": 78690},
        {"base_price": 241.45, "signal": "SELL", "stat_value": -0.043, "volume_base": 98760},
        {"base_price": 249.78, "signal": "STRONG_BUY", "stat_value": 0.075, "volume_base": 104320},
        {"base_price": 246.34, "signal": "BUY", "stat_value": 0.041, "volume_base": 81230},
        {"base_price": 244.12, "signal": "HOLD", "stat_value": 0.012, "volume_base": 76540},
        {"base_price": 248.56, "signal": "BUY", "stat_value": 0.058, "volume_base": 89670},
        {"base_price": 242.78, "signal": "SELL", "stat_value": -0.031, "volume_base": 107890},
        {"base_price": 247.89, "signal": "STRONG_BUY", "stat_value": 0.067, "volume_base": 95430}
    ],
    "SI": [
        {"base_price": 258.47, "signal": "STRONG_BUY", "stat_value": 0.060, "volume_base": 121341},
        {"base_price": 261.23, "signal": "STRONG_BUY", "stat_value": 0.075, "volume_base": 134560},
        {"base_price": 256.78, "signal": "BUY", "stat_value": 0.045, "volume_base": 108790},
        {"base_price": 254.34, "signal": "HOLD", "stat_value": 0.000, "volume_base": 145230},
        {"base_price": 263.89, "signal": "STRONG_BUY", "stat_value": 0.090, "volume_base": 156870},
        {"base_price": 259.67, "signal": "BUY", "stat_value": 0.052, "volume_base": 117450},
        {"base_price": 255.45, "signal": "SELL", "stat_value": -0.037, "volume_base": 139680},
        {"base_price": 262.12, "signal": "STRONG_BUY", "stat_value": 0.082, "volume_base": 128340},
        {"base_price": 253.78, "signal": "STRONG_SELL", "stat_value": -0.045, "volume_base": 167890},
        {"base_price": 260.34, "signal": "BUY", "stat_value": 0.067, "volume_base": 142570}
    ],
    "HG": [
        {"base_price": 245.02, "signal": "STRONG_SELL", "stat_value": -0.012, "volume_base": 81929},
        {"base_price": 247.45, "signal": "BUY", "stat_value": 0.008, "volume_base": 89450},
        {"base_price": 243.78, "signal": "SELL", "stat_value": -0.009, "volume_base": 76320},
        {"base_price": 241.23, "signal": "STRONG_SELL", "stat_value": -0.015, "volume_base": 95670},
        {"base_price": 249.67, "signal": "STRONG_BUY", "stat_value": 0.011, "volume_base": 104380},
        {"base_price": 246.34, "signal": "HOLD", "stat_value": 0.000, "volume_base": 78560},
        {"base_price": 244.56, "signal": "SELL", "stat_value": -0.007, "volume_base": 87940},
        {"base_price": 248.12, "signal": "BUY", "stat_value": 0.009, "volume_base": 91230},
        {"base_price": 242.89, "signal": "STRONG_SELL", "stat_value": -0.013, "volume_base": 108760},
        {"base_price": 247.78, "signal": "BUY", "stat_value": 0.006, "volume_base": 85430}
    ],
    "GC": [
        {"base_price": 240.50, "signal": "STRONG_SELL", "stat_value": -3.000, "volume_base": 98395},
        {"base_price": 243.78, "signal": "BUY", "stat_value": 2.250, "volume_base": 108760},
        {"base_price": 238.23, "signal": "SELL", "stat_value": -2.437, "volume_base": 89450},
        {"base_price": 235.67, "signal": "STRONG_SELL", "stat_value": -3.750, "volume_base": 124580},
        {"base_price": 246.34, "signal": "STRONG_BUY", "stat_value": 2.812, "volume_base": 145230},
        {"base_price": 241.89, "signal": "HOLD", "stat_value": 0.000, "volume_base": 92340},
        {"base_price": 239.45, "signal": "SELL", "stat_value": -1.875, "volume_base": 117680},
        {"base_price": 244.67, "signal": "BUY", "stat_value": 2.625, "volume_base": 103450},
        {"base_price": 237.12, "signal": "STRONG_SELL", "stat_value": -3.375, "volume_base": 136790},
        {"base_price": 245.23, "signal": "STRONG_BUY", "stat_value": 2.437, "volume_base": 118560}
    ],
    "VX": [
        {"base_price": 276.13, "signal": "HOLD", "stat_value": 0.000, "volume_base": 206096},
        {"base_price": 279.45, "signal": "BUY", "stat_value": 0.075, "volume_base": 234560},
        {"base_price": 273.78, "signal": "SELL", "stat_value": -0.062, "volume_base": 189340},
        {"base_price": 271.23, "signal": "STRONG_SELL", "stat_value": -0.087, "volume_base": 267890},
        {"base_price": 282.67, "signal": "STRONG_BUY", "stat_value": 0.100, "volume_base": 289750},
        {"base_price": 277.89, "signal": "BUY", "stat_value": 0.050, "volume_base": 198450},
        {"base_price": 274.34, "signal": "HOLD", "stat_value": 0.025, "volume_base": 178620},
        {"base_price": 280.12, "signal": "BUY", "stat_value": 0.087, "volume_base": 245870},
        {"base_price": 272.56, "signal": "SELL", "stat_value": -0.075, "volume_base": 298340},
        {"base_price": 281.78, "signal": "STRONG_BUY", "stat_value": 0.112, "volume_base": 256680}
    ],
    "DX": [
        {"base_price": 256.99, "signal": "BUY", "stat_value": 5.000, "volume_base": 185237},
        {"base_price": 259.45, "signal": "STRONG_BUY", "stat_value": 6.250, "volume_base": 203450},
        {"base_price": 254.78, "signal": "HOLD", "stat_value": 0.000, "volume_base": 167890},
        {"base_price": 252.34, "signal": "SELL", "stat_value": -4.375, "volume_base": 218760},
        {"base_price": 261.67, "signal": "STRONG_BUY", "stat_value": 7.500, "volume_base": 245680},
        {"base_price": 258.23, "signal": "BUY", "stat_value": 4.125, "volume_base": 178340},
        {"base_price": 255.89, "signal": "HOLD", "stat_value": 1.250, "volume_base": 156790},
        {"base_price": 260.12, "signal": "BUY", "stat_value": 5.875, "volume_base": 192450},
        {"base_price": 253.45, "signal": "SELL", "stat_value": -3.125, "volume_base": 234670},
        {"base_price": 259.78, "signal": "STRONG_BUY", "stat_value": 6.875, "volume_base": 209830}
    ],
    "ZB": [
        {"base_price": 257.38, "signal": "HOLD", "stat_value": 0.000, "volume_base": 98949},
        {"base_price": 259.78, "signal": "BUY", "stat_value": 3.750, "volume_base": 108760},
        {"base_price": 255.23, "signal": "SELL", "stat_value": -3.125, "volume_base": 89340},
        {"base_price": 252.67, "signal": "STRONG_SELL", "stat_value": -4.687, "volume_base": 124580},
        {"base_price": 261.45, "signal": "STRONG_BUY", "stat_value": 4.375, "volume_base": 145230},
        {"base_price": 258.89, "signal": "BUY", "stat_value": 2.812, "volume_base": 92340},
        {"base_price": 256.12, "signal": "HOLD", "stat_value": 0.937, "volume_base": 87680},
        {"base_price": 260.34, "signal": "BUY", "stat_value": 4.062, "volume_base": 103450},
        {"base_price": 254.78, "signal": "SELL", "stat_value": -2.500, "volume_base": 136790},
        {"base_price": 259.56, "signal": "STRONG_BUY", "stat_value": 3.437, "volume_base": 118560}
    ]
}

def generate_realistic_fields(base_data: Dict, variation_factor: float = 0.1) -> Dict:
    """
    Generate realistic market data fields based on base data.
    
    Args:
        base_data: Base data containing price, signal, stat_value, volume_base
        variation_factor: How much to vary from base (0.1 = 10% variation)
    
    Returns:
        Complete futures data dictionary
    """
    base_price = base_data["base_price"]
    
    # Generate realistic bid/ask with appropriate spreads
    spreads = {
        "/YM": 1.0, "/ES": 0.25, "/NQ": 0.5, "RTY": 0.1,
        "CL": 0.01, "SI": 0.005, "HG": 0.0005, "GC": 0.1,
        "VX": 0.05, "DX": 0.005, "ZB": 0.015
    }
    
    # Price variation
    price_change = random.uniform(-variation_factor, variation_factor) * base_price
    current_price = base_price + price_change
    
    # Calculate OHLC
    daily_range = base_price * random.uniform(0.02, 0.08)  # 2-8% daily range
    high_price = current_price + (daily_range * random.uniform(0.3, 0.7))
    low_price = current_price - (daily_range * random.uniform(0.3, 0.7))
    open_price = random.uniform(low_price, high_price)
    previous_close = random.uniform(low_price * 0.98, high_price * 1.02)
    
    # Bid/Ask
    spread = spreads.get(base_data.get("symbol", ""), 0.5)
    bid = current_price - (spread / 2)
    ask = current_price + (spread / 2)
    
    # Sizes
    bid_size = random.randint(10, 100)
    ask_size = random.randint(10, 100)
    
    # VWAP (between bid and ask, closer to last)
    vwap = (bid + ask + current_price) / 3
    
    # Volume
    volume_variation = random.uniform(0.7, 1.4)  # 70% to 140% of base
    volume = int(base_data["volume_base"] * volume_variation)
    
    return {
        "base_price": round(current_price, 4),
        "signal": base_data["signal"],
        "stat_value": base_data["stat_value"],
        "bid": round(bid, 4),
        "ask": round(ask, 4),
        "bid_size": bid_size,
        "ask_size": ask_size,
        "vwap": round(vwap, 4),
        "spread": round(ask - bid, 4),
        "open_price": round(open_price, 4),
        "previous_close": round(previous_close, 4),
        "difference": round(current_price - previous_close, 4),
        "high_price": round(high_price, 4),
        "low_price": round(low_price, 4),
        "volume": volume
    }

def create_futures_json(data_set_index: int, json_file_path: str):
    """
    Create a complete futures JSON file using the specified data set index.
    
    Args:
        data_set_index: Which data set to use (0-9)
        json_file_path: Path to the JSON file to create/update
    """
    futures_list = []
    
    # Static data for each future
    futures_info = {
        "/YM": {"name": "Dow Jones Mini Futures", "exchange": "CME", "contract_weight": 1.5},
        "/ES": {"name": "S&P 500 Mini Futures", "exchange": "CME", "contract_weight": 1.2},
        "/NQ": {"name": "Nasdaq Mini Futures", "exchange": "CME", "contract_weight": 1.8},
        "RTY": {"name": "Russell 2000 Mini Futures", "exchange": "CME", "contract_weight": 1.1},
        "CL": {"name": "Crude Oil Futures", "exchange": "NYMEX", "contract_weight": 1.3},
        "SI": {"name": "Silver Futures", "exchange": "COMEX", "contract_weight": 1.0},
        "HG": {"name": "Copper Futures", "exchange": "COMEX", "contract_weight": 0.8},
        "GC": {"name": "Gold Futures", "exchange": "COMEX", "contract_weight": 1.4},
        "VX": {"name": "VIX Futures", "exchange": "CFE", "contract_weight": 0.9},
        "DX": {"name": "US Dollar Index Futures", "exchange": "ICE", "contract_weight": 1.2},
        "ZB": {"name": "30-Year Treasury Bond Futures", "exchange": "CBOT", "contract_weight": 1.1}
    }
    
    descriptions = {
        "/YM": "E-mini Dow Jones Industrial Average futures",
        "/ES": "E-mini S&P 500 futures",
        "/NQ": "E-mini Nasdaq-100 futures", 
        "RTY": "E-mini Russell 2000 futures",
        "CL": "Light Sweet Crude Oil futures",
        "SI": "Silver futures",
        "HG": "High Grade Copper futures",
        "GC": "Gold futures",
        "VX": "CBOE Volatility Index futures",
        "DX": "US Dollar Index futures",
        "ZB": "30-Year US Treasury Bond futures"
    }
    
    for symbol, data_sets in FUTURES_DATA_SETS.items():
        base_data = data_sets[data_set_index % len(data_sets)]
        base_data["symbol"] = symbol
        
        # Generate all the realistic fields
        market_data = generate_realistic_fields(base_data)
        
        # Build complete future entry
        future_entry = {
            "symbol": symbol,
            "name": futures_info[symbol]["name"],
            "exchange": futures_info[symbol]["exchange"],
            "contract_weight": futures_info[symbol]["contract_weight"],
            "description": descriptions[symbol],
            **market_data
        }
        
        futures_list.append(future_entry)
    
    # Create complete JSON structure
    json_data = {
        "futures": futures_list,
        "metadata": {
            "last_updated": datetime.now().isoformat(),
            "data_source": "dynamic_mock_generator",
            "description": f"Dynamic mock futures data (set {data_set_index + 1}/10) - will be replaced with Schwab API",
            "total_instruments": len(futures_list),
            "market_status": "OPEN",
            "data_set_index": data_set_index,
            "fields_included": [
                "base_price", "bid", "ask", "bid_size", "ask_size", "vwap", "spread",
                "open_price", "previous_close", "difference", "high_price", "low_price", 
                "volume", "signal", "stat_value", "contract_weight"
            ],
            "notes": [
                f"Using data set variation {data_set_index + 1} of 10",
                "Data updates automatically every 2 seconds",
                "All fields match the futures card display format",
                "Realistic price movements and market data simulation",
                "This file can be easily replaced when Schwab API integration is complete"
            ]
        }
    }
    
    # Write to file
    with open(json_file_path, 'w') as f:
        json.dump(json_data, f, indent=2)
    
    return json_data

def main():
    parser = argparse.ArgumentParser(description="Dynamic futures data updater")
    parser.add_argument("--interval", type=int, default=2, help="Update interval in seconds")
    parser.add_argument("--static", action="store_true", help="Generate static variations only")
    parser.add_argument("--json-file", type=str, help="Path to JSON file")
    
    args = parser.parse_args()
    
    # Determine JSON file path - default to current directory (SchwabLiveData)
    if args.json_file:
        json_file_path = args.json_file
    else:
        # Use current directory (should be SchwabLiveData)
        json_file_path = os.path.join(os.getcwd(), "futures_data.json")
    
    print(f"Dynamic Futures Data Updater")
    print(f"JSON file: {json_file_path}")
    print(f"Update interval: {args.interval} seconds")
    print(f"Static mode: {args.static}")
    print("-" * 60)
    
    if args.static:
        # Generate all 10 static variations
        print("Generating 10 static data variations...")
        for i in range(10):
            output_file = json_file_path.replace(".json", f"_variation_{i+1}.json")
            create_futures_json(i, output_file)
            print(f"Created: {output_file}")
        print("Static variations generated!")
        return
    
    # Dynamic mode - continuous updates
    data_set_index = 0
    
    try:
        while True:
            # Create new data using current data set
            json_data = create_futures_json(data_set_index, json_file_path)
            
            timestamp = datetime.now().strftime("%H:%M:%S")
            print(f"[{timestamp}] Updated with data set {data_set_index + 1}/10")
            
            # Show sample data for first future
            if json_data["futures"]:
                sample = json_data["futures"][0]
                print(f"  {sample['symbol']}: {sample['base_price']} ({sample['signal']}) "
                      f"Vol: {sample['volume']:,}")
            
            # Move to next data set (cycle through 0-9)
            data_set_index = (data_set_index + 1) % 10
            
            # Wait for next update
            time.sleep(args.interval)
            
    except KeyboardInterrupt:
        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Stopped by user")
        print("Final JSON file preserved.")

if __name__ == "__main__":
    main()