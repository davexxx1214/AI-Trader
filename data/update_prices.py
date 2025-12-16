#!/usr/bin/env python3
"""
Auto-update US stock hourly price data.

Features:
1. Automatically detects the latest timestamp in existing data
2. Fetches data from the latest timestamp to now
3. If no local data exists, fetches the last month's data by default

Usage:
    cd data
    python update_prices.py
    
    # Or with custom lookback days (default: 30)
    python update_prices.py --days 60
"""

import os
import sys
import json
import argparse
from datetime import datetime, timedelta
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv()

# Nasdaq-100 symbols + QQQ benchmark
ALL_SYMBOLS = [
    "NVDA", "MSFT", "AAPL", "GOOG", "GOOGL", "AMZN", "META", "AVGO", "TSLA", "NFLX",
    "PLTR", "COST", "ASML", "AMD", "CSCO", "AZN", "TMUS", "MU", "LIN", "PEP",
    "SHOP", "APP", "INTU", "AMAT", "LRCX", "PDD", "QCOM", "ARM", "INTC", "BKNG",
    "AMGN", "TXN", "ISRG", "GILD", "KLAC", "PANW", "ADBE", "HON", "CRWD", "CEG",
    "ADI", "ADP", "DASH", "CMCSA", "VRTX", "MELI", "SBUX", "CDNS", "ORLY", "SNPS",
    "MSTR", "MDLZ", "ABNB", "MRVL", "CTAS", "TRI", "MAR", "MNST", "CSX", "ADSK",
    "PYPL", "FTNT", "AEP", "WDAY", "REGN", "ROP", "NXPI", "DDOG", "AXON", "ROST",
    "IDXX", "EA", "PCAR", "FAST", "EXC", "TTWO", "XEL", "ZS", "PAYX", "WBD",
    "BKR", "CPRT", "CCEP", "FANG", "TEAM", "CHTR", "KDP", "MCHP", "GEHC", "VRSK",
    "CTSH", "CSGP", "KHC", "ODFL", "DXCM", "TTD", "ON", "BIIB", "LULU", "CDW", "GFS",
    "QQQ"  # Benchmark
]

BASE_DIR = Path(__file__).resolve().parent
APIKEY = os.getenv("ALPHAADVANTAGE_API_KEY")


def parse_datetime(dt_str: str) -> datetime | None:
    """Parse datetime string in various formats."""
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(dt_str, fmt)
        except ValueError:
            continue
    return None


def get_latest_timestamp_from_file(symbol: str) -> datetime | None:
    """Get the latest timestamp from existing price data file."""
    file_path = BASE_DIR / f"daily_prices_{symbol}.json"
    
    if not file_path.exists():
        return None
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        time_series = data.get("Time Series (60min)") or data.get("Time Series (Daily)")
        if not time_series:
            return None
        
        # Find the latest timestamp
        latest_ts = None
        for ts_str in time_series.keys():
            ts = parse_datetime(ts_str)
            if ts and (latest_ts is None or ts > latest_ts):
                latest_ts = ts
        
        return latest_ts
    except Exception as e:
        print(f"⚠️ Error reading {symbol} data: {e}")
        return None


def get_global_latest_timestamp() -> tuple[datetime | None, str | None]:
    """
    Scan all price files to find the global latest timestamp.
    Returns (latest_timestamp, symbol_name).
    """
    global_latest = None
    latest_symbol = None
    
    print("🔍 Scanning existing data files...")
    
    for symbol in ALL_SYMBOLS:
        ts = get_latest_timestamp_from_file(symbol)
        if ts and (global_latest is None or ts > global_latest):
            global_latest = ts
            latest_symbol = symbol
    
    return global_latest, latest_symbol


def month_range(start_dt: datetime, end_dt: datetime) -> list[str]:
    """Return list of YYYY-MM strings covering [start_dt, end_dt], inclusive."""
    cur = datetime(start_dt.year, start_dt.month, 1)
    end = datetime(end_dt.year, end_dt.month, 1)
    months = []
    while cur <= end:
        months.append(cur.strftime("%Y-%m"))
        if cur.month == 12:
            cur = datetime(cur.year + 1, 1, 1)
        else:
            cur = datetime(cur.year, cur.month + 1, 1)
    return months


def fetch_symbol_data(symbol: str, start_dt: datetime, end_dt: datetime) -> dict:
    """Fetch hourly data for a symbol within date range."""
    months = month_range(start_dt, end_dt)
    if not months:
        return {}
    
    merged_ts = {}
    meta_data = None
    
    for m in months:
        params = {
            "function": "TIME_SERIES_INTRADAY",
            "symbol": symbol,
            "interval": "60min",
            "outputsize": "full",
            "apikey": APIKEY,
            "entitlement": "delayed",
            "extended_hours": "false",
            "month": m
        }
        
        try:
            url = "https://www.alphavantage.co/query"
            r = requests.get(url, params=params, timeout=30)
            data = r.json()
            
            # Check for API errors
            if data.get("Note") or data.get("Information"):
                print(f"  ⚠️ {symbol} month={m}: {data.get('Note') or data.get('Information')}")
                continue
            
            ts = data.get("Time Series (60min)")
            if not ts:
                print(f"  ⚠️ {symbol} month={m}: no data")
                continue
            
            # Filter by date range
            for ts_str, values in ts.items():
                ts_dt = parse_datetime(ts_str)
                if ts_dt and start_dt <= ts_dt <= end_dt:
                    merged_ts[ts_str] = values
            
            if meta_data is None and data.get("Meta Data"):
                meta_data = data["Meta Data"]
            
            print(f"  ✓ {symbol} month={m}: {len(ts)} records")
            
        except Exception as e:
            print(f"  ❌ {symbol} month={m}: {e}")
    
    return {
        "Meta Data": meta_data or {},
        "Time Series (60min)": merged_ts
    }


def update_local_file(symbol: str, new_data: dict):
    """Update local JSON file with new data."""
    file_path = BASE_DIR / f"daily_prices_{symbol}.json"
    
    new_ts = new_data.get("Time Series (60min)", {})
    if not new_ts:
        return
    
    try:
        if file_path.exists():
            with open(file_path, 'r', encoding='utf-8') as f:
                old_data = json.load(f)
            
            old_ts = old_data.get("Time Series (60min)", {})
            # Merge: new data overwrites old data for same timestamps
            merged_ts = {**old_ts, **new_ts}
            
            merged_data = {
                "Meta Data": new_data.get("Meta Data") or old_data.get("Meta Data", {}),
                "Time Series (60min)": merged_ts
            }
        else:
            merged_data = new_data
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(merged_data, f, ensure_ascii=False, indent=4)
        
        # Special handling for QQQ
        if symbol == "QQQ":
            qqq_path = BASE_DIR / f"Adaily_prices_{symbol}.json"
            with open(qqq_path, 'w', encoding='utf-8') as f:
                json.dump(merged_data, f, ensure_ascii=False, indent=4)
        
        print(f"  💾 Saved {symbol}: {len(new_ts)} new records")
        
    except Exception as e:
        print(f"  ❌ Error saving {symbol}: {e}")


def main():
    parser = argparse.ArgumentParser(
        description='Auto-update US stock hourly price data',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        '--days', '-d',
        type=int,
        default=30,
        help='Default lookback days when no local data exists (default: 30)'
    )
    parser.add_argument(
        '--force', '-f',
        action='store_true',
        help='Force re-fetch all data within the date range'
    )
    
    args = parser.parse_args()
    
    if not APIKEY:
        print("❌ Error: ALPHAADVANTAGE_API_KEY not set in environment")
        print("   Please set it in .env file or environment variable")
        sys.exit(1)
    
    print()
    print("=" * 60)
    print("📊 US Stock Price Data Auto-Updater")
    print("=" * 60)
    
    # Get current time (US Eastern approximation)
    now = datetime.now()
    
    # Detect latest local data timestamp
    latest_ts, latest_symbol = get_global_latest_timestamp()
    
    if latest_ts:
        print(f"\n📅 Latest local data: {latest_ts.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"   (from {latest_symbol})")
        
        # Start from the day after the latest data
        start_dt = latest_ts + timedelta(hours=1)
        
        # Check if we need to update
        if start_dt >= now:
            print("\n✅ Data is already up to date!")
            return
        
        print(f"\n📥 Will fetch data from {start_dt.strftime('%Y-%m-%d %H:%M')} to {now.strftime('%Y-%m-%d %H:%M')}")
    else:
        print("\n📂 No existing data found")
        print(f"   Will fetch last {args.days} days of data")
        
        start_dt = now - timedelta(days=args.days)
    
    end_dt = now
    
    # Calculate how many months we need to fetch
    months = month_range(start_dt, end_dt)
    print(f"\n📆 Date range: {start_dt.strftime('%Y-%m-%d')} → {end_dt.strftime('%Y-%m-%d')}")
    print(f"   Months to fetch: {', '.join(months)}")
    print(f"   Total symbols: {len(ALL_SYMBOLS)}")
    
    # Confirm before proceeding
    estimated_calls = len(ALL_SYMBOLS) * len(months)
    print(f"\n⚠️  This will make approximately {estimated_calls} API calls")
    print("   (AlphaVantage free tier: 25 calls/day)")
    
    response = input("\nProceed? [y/N]: ").strip().lower()
    if response != 'y':
        print("Cancelled.")
        return
    
    print("\n" + "-" * 60)
    print("Starting data fetch...")
    print("-" * 60 + "\n")
    
    success_count = 0
    error_count = 0
    
    for i, symbol in enumerate(ALL_SYMBOLS, 1):
        print(f"\n[{i}/{len(ALL_SYMBOLS)}] Fetching {symbol}...")
        
        try:
            data = fetch_symbol_data(symbol, start_dt, end_dt)
            
            if data.get("Time Series (60min)"):
                update_local_file(symbol, data)
                success_count += 1
            else:
                print(f"  ⚠️ No data fetched for {symbol}")
                error_count += 1
                
        except Exception as e:
            print(f"  ❌ Error: {e}")
            error_count += 1
    
    print("\n" + "=" * 60)
    print("📊 Summary")
    print("=" * 60)
    print(f"   ✓ Success: {success_count}")
    print(f"   ✗ Errors:  {error_count}")
    print(f"   Total:     {len(ALL_SYMBOLS)}")
    
    if success_count > 0:
        print("\n💡 Tip: Run 'python merge_jsonl.py' to update merged.jsonl")
    
    print()


if __name__ == "__main__":
    main()

