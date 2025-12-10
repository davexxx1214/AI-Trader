import os
import json
from datetime import datetime
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv()

all_nasdaq_100_symbols = [
    "NVDA",
    "MSFT",
    "AAPL",
    "GOOG",
    "GOOGL",
    "AMZN",
    "META",
    "AVGO",
    "TSLA",
    "NFLX",
    "PLTR",
    "COST",
    "ASML",
    "AMD",
    "CSCO",
    "AZN",
    "TMUS",
    "MU",
    "LIN",
    "PEP",
    "SHOP",
    "APP",
    "INTU",
    "AMAT",
    "LRCX",
    "PDD",
    "QCOM",
    "ARM",
    "INTC",
    "BKNG",
    "AMGN",
    "TXN",
    "ISRG",
    "GILD",
    "KLAC",
    "PANW",
    "ADBE",
    "HON",
    "CRWD",
    "CEG",
    "ADI",
    "ADP",
    "DASH",
    "CMCSA",
    "VRTX",
    "MELI",
    "SBUX",
    "CDNS",
    "ORLY",
    "SNPS",
    "MSTR",
    "MDLZ",
    "ABNB",
    "MRVL",
    "CTAS",
    "TRI",
    "MAR",
    "MNST",
    "CSX",
    "ADSK",
    "PYPL",
    "FTNT",
    "AEP",
    "WDAY",
    "REGN",
    "ROP",
    "NXPI",
    "DDOG",
    "AXON",
    "ROST",
    "IDXX",
    "EA",
    "PCAR",
    "FAST",
    "EXC",
    "TTWO",
    "XEL",
    "ZS",
    "PAYX",
    "WBD",
    "BKR",
    "CPRT",
    "CCEP",
    "FANG",
    "TEAM",
    "CHTR",
    "KDP",
    "MCHP",
    "GEHC",
    "VRSK",
    "CTSH",
    "CSGP",
    "KHC",
    "ODFL",
    "DXCM",
    "TTD",
    "ON",
    "BIIB",
    "LULU",
    "CDW",
    "GFS",
]


BASE_DIR = Path(__file__).resolve().parent
# 默认读取小时配置，可通过环境变量覆盖
DEFAULT_CONFIG_PATH = os.environ.get(
    "HOUR_CONFIG_PATH",
    str((BASE_DIR.parent / "configs" / "default_hour_config.json").resolve()),
)


def _parse_datetime(dt_str: str):
    """Support both date and datetime strings from AlphaVantage."""
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(dt_str, fmt)
        except ValueError:
            continue
    return None


def load_date_range(config_path: str = DEFAULT_CONFIG_PATH):
    """Load init_date and end_date from config; return (start_dt, end_dt)."""
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        dr = cfg.get("date_range", {})
        start = dr.get("init_date")
        end = dr.get("end_date")
        start_dt = _parse_datetime(start) if start else None
        end_dt = _parse_datetime(end) if end else None
        print(f"Using date range from config: {start} -> {end}")
        return start_dt, end_dt
    except Exception as e:
        print(f"⚠️ Failed to load date_range from {config_path}: {e}")
        return None, None


START_DT, END_DT = load_date_range()


def filter_time_series(ts: dict):
    """Filter time series by START_DT/END_DT."""
    if not ts or (START_DT is None and END_DT is None):
        return ts or {}
    filtered = {}
    for k, v in ts.items():
        dt = _parse_datetime(k)
        if dt is None:
            continue
        if START_DT and dt < START_DT:
            continue
        if END_DT and dt > END_DT:
            continue
        filtered[k] = v
    return filtered


def update_json(data: dict, SYMBOL: str):
    file_path = BASE_DIR / f"daily_prices_{SYMBOL}.json"
    
    try:
        if file_path.exists():
            with file_path.open('r', encoding='utf-8') as f:
                old_data = json.load(f)
            
            # 合并新旧的"Time Series (60min)"，新data优先（相同时间戳用新数据覆盖）
            old_ts_raw = old_data.get("Time Series (60min)", {})
            # 先把历史数据也按配置范围过滤，避免旧文件带入超范围数据
            old_ts = filter_time_series(old_ts_raw)
            new_ts = data.get("Time Series (60min)", {})
            merged_ts = {**old_ts, **new_ts}  # 新数据覆盖旧数据中相同的时间戳
            # 再次保险过滤一次
            merged_ts = filter_time_series(merged_ts)
            
            # 创建新的数据字典，避免直接修改传入的data
            merged_data = data.copy()
            merged_data["Time Series (60min)"] = merged_ts
            
            # 如果新数据没有Meta Data，保留旧的Meta Data
            if "Meta Data" not in merged_data and "Meta Data" in old_data:
                merged_data["Meta Data"] = old_data["Meta Data"]
            
            with file_path.open('w', encoding='utf-8') as f:
                json.dump(merged_data, f, ensure_ascii=False, indent=4)
        else:
            with file_path.open('w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
        
        # QQQ 特殊处理：同时保存到另一个文件
        if SYMBOL == "QQQ":
            file_path_qqq = BASE_DIR / f"Adaily_prices_{SYMBOL}.json"
            if file_path_qqq.exists():
                with file_path_qqq.open('r', encoding='utf-8') as f:
                    old_data = json.load(f)
                old_ts_raw = old_data.get("Time Series (60min)", {})
                old_ts = filter_time_series(old_ts_raw)
                new_ts = data.get("Time Series (60min)", {})
                merged_ts = {**old_ts, **new_ts}
                merged_ts = filter_time_series(merged_ts)
                merged_data = data.copy()
                merged_data["Time Series (60min)"] = merged_ts
                if "Meta Data" not in merged_data and "Meta Data" in old_data:
                    merged_data["Meta Data"] = old_data["Meta Data"]
                with file_path_qqq.open('w', encoding='utf-8') as f:
                    json.dump(merged_data, f, ensure_ascii=False, indent=4)
            else:
                with file_path_qqq.open('w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=4)
                    
    except (IOError, json.JSONDecodeError, KeyError) as e:
        print(f"Error when update {SYMBOL}: {e}")
        raise
         
FUNCTION = "TIME_SERIES_INTRADAY"
INTERVAL = "60min"
OUTPUTSIZE = 'full'
APIKEY = os.getenv("ALPHAADVANTAGE_API_KEY")


def _month_range(start_dt: datetime | None, end_dt: datetime | None):
    """Return list of YYYY-MM strings covering [start_dt, end_dt], inclusive."""
    if start_dt is None and end_dt is None:
        return []
    if start_dt is None:
        start_dt = end_dt
    if end_dt is None:
        end_dt = start_dt
    # normalize to first day of month
    cur = datetime(start_dt.year, start_dt.month, 1)
    end = datetime(end_dt.year, end_dt.month, 1)
    months = []
    while cur <= end:
        months.append(cur.strftime("%Y-%m"))
        # increment month
        if cur.month == 12:
            cur = datetime(cur.year + 1, 1, 1)
        else:
            cur = datetime(cur.year, cur.month + 1, 1)
    return months


def get_daily_price(SYMBOL: str):
    months = _month_range(START_DT, END_DT)
    # 如果没有日期范围，就用一次默认调用（最近30天）
    if not months:
        months = [None]

    merged_ts_all = {}
    meta_data = None
    for m in months:
        params = {
            "function": FUNCTION,
            "symbol": SYMBOL,
            "interval": INTERVAL,
            "outputsize": OUTPUTSIZE,
            "apikey": APIKEY,
            "entitlement": "delayed",
            "extended_hours": "false",
        }
        if m:
            params["month"] = m
        url = "https://www.alphavantage.co/query"
        r = requests.get(url, params=params)
        data = r.json()
        print(f"{SYMBOL} month={m}: status={r.status_code}")
        if data.get("Note") is not None or data.get("Information") is not None:
            print(f"Error: {data.get('Note') or data.get('Information')}")
            continue
        ts = data.get("Time Series (60min)") or data.get("Time Series (Daily)")
        if not ts:
            print(f"⚠️ {SYMBOL} month={m}: no time series returned")
            continue
        merged_ts_all.update(ts)
        if meta_data is None and data.get("Meta Data"):
            meta_data = data.get("Meta Data")

    if not merged_ts_all:
        print(f"⚠️ {SYMBOL}: no data fetched.")
        return

    filtered_ts = filter_time_series(merged_ts_all)
    data_filtered = {
        "Meta Data": meta_data or {},
        "Time Series (60min)": filtered_ts
    }

    if not filtered_ts:
        print(f"⚠️ {SYMBOL}: no data within the configured date range.")
    update_json(data_filtered, SYMBOL)


if __name__ == "__main__":
    for symbol in all_nasdaq_100_symbols:
        get_daily_price(symbol)

    get_daily_price("QQQ")
