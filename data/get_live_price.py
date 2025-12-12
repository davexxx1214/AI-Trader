"""
Live Price Fetcher - 实时价格数据获取模块

从 AlphaVantage API 获取最新的小时级股票数据，并增量更新到本地文件。
设计用于实时交易场景，只获取最近的数据而不是全量历史数据。
"""

import os
import json
import sys
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any

import requests
from dotenv import load_dotenv

load_dotenv()

# 将项目根目录加入 Python 路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from tools.trading_calendar import get_eastern_now, is_market_hours, format_eastern_time

# AlphaVantage API 配置
APIKEY = os.getenv("ALPHAADVANTAGE_API_KEY")
FUNCTION = "TIME_SERIES_INTRADAY"
INTERVAL = "60min"
BASE_DIR = Path(__file__).resolve().parent

# 纳斯达克 100 成分股
all_nasdaq_100_symbols = [
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
]


def fetch_latest_price(symbol: str) -> Optional[Dict[str, Any]]:
    """
    从 AlphaVantage 获取指定股票的最新小时级数据
    
    Args:
        symbol: 股票代码
        
    Returns:
        API 返回的 JSON 数据，失败返回 None
    """
    if not APIKEY:
        print(f"❌ ALPHAADVANTAGE_API_KEY 未设置")
        return None
    
    params = {
        "function": FUNCTION,
        "symbol": symbol,
        "interval": INTERVAL,
        "outputsize": "compact",  # 只获取最近 100 条数据
        "apikey": APIKEY,
        "entitlement": "delayed",
        "extended_hours": "false",
    }
    
    url = "https://www.alphavantage.co/query"
    
    try:
        response = requests.get(url, params=params, timeout=15)  # 减少超时时间
        response.raise_for_status()
        data = response.json()
        
        # 检查 API 错误
        if data.get("Note"):
            print(f"⚠️ {symbol}: API 限制 - {data['Note']}")
            return None
        if data.get("Information"):
            print(f"⚠️ {symbol}: {data['Information']}")
            return None
        if "Error Message" in data:
            print(f"❌ {symbol}: {data['Error Message']}")
            return None
            
        return data
    
    except requests.exceptions.Timeout:
        print(f"⚠️ {symbol}: 请求超时，跳过")
        return None
    except requests.exceptions.ConnectionError:
        print(f"⚠️ {symbol}: 连接失败，跳过")
        return None
    except requests.exceptions.RequestException as e:
        print(f"❌ {symbol}: 网络请求失败 - {e}")
        return None
    except json.JSONDecodeError as e:
        print(f"❌ {symbol}: JSON 解析失败 - {e}")
        return None


def update_local_file(symbol: str, new_data: Dict[str, Any]) -> bool:
    """
    将新数据增量更新到本地 JSON 文件
    
    Args:
        symbol: 股票代码
        new_data: 从 API 获取的新数据
        
    Returns:
        是否更新成功
    """
    file_path = BASE_DIR / f"daily_prices_{symbol}.json"
    
    try:
        # 获取新数据的时间序列
        new_ts = new_data.get("Time Series (60min)", {})
        if not new_ts:
            print(f"⚠️ {symbol}: 无时间序列数据")
            return False
        
        # 如果本地文件存在，合并数据
        if file_path.exists():
            with file_path.open('r', encoding='utf-8') as f:
                old_data = json.load(f)
            
            old_ts = old_data.get("Time Series (60min)", {})
            # 合并：新数据覆盖旧数据
            merged_ts = {**old_ts, **new_ts}
            
            merged_data = new_data.copy()
            merged_data["Time Series (60min)"] = merged_ts
            
            # 保留旧的 Meta Data 如果新数据没有
            if "Meta Data" not in merged_data and "Meta Data" in old_data:
                merged_data["Meta Data"] = old_data["Meta Data"]
        else:
            merged_data = new_data
        
        # 写入文件
        with file_path.open('w', encoding='utf-8') as f:
            json.dump(merged_data, f, ensure_ascii=False, indent=4)
        
        # 统计新增的数据点
        new_count = len(new_ts)
        total_count = len(merged_data.get("Time Series (60min)", {}))
        print(f"✅ {symbol}: 获取 {new_count} 条新数据，总计 {total_count} 条")
        
        return True
        
    except Exception as e:
        print(f"❌ {symbol}: 更新文件失败 - {e}")
        return False


def run_merge_jsonl() -> bool:
    """
    运行 merge_jsonl.py 合并所有数据到 merged.jsonl
    
    Returns:
        是否执行成功
    """
    merge_script = BASE_DIR / "merge_jsonl.py"
    
    if not merge_script.exists():
        print(f"❌ merge_jsonl.py 不存在")
        return False
    
    try:
        result = subprocess.run(
            [sys.executable, str(merge_script)],
            cwd=str(BASE_DIR),
            capture_output=True,
            text=True,
            timeout=60
        )
        
        if result.returncode != 0:
            print(f"❌ merge_jsonl.py 执行失败: {result.stderr}")
            return False
        
        print("✅ merged.jsonl 已更新")
        return True
        
    except subprocess.TimeoutExpired:
        print("❌ merge_jsonl.py 执行超时")
        return False
    except Exception as e:
        print(f"❌ merge_jsonl.py 执行异常: {e}")
        return False


def fetch_all_symbols(symbols: Optional[List[str]] = None, 
                      delay_between_requests: float = 0.8) -> Dict[str, bool]:
    """
    获取所有股票的最新数据
    
    Args:
        symbols: 要获取的股票列表，默认为纳斯达克 100
        delay_between_requests: 请求间隔（秒），避免 API 限制
        
    Returns:
        每个股票的获取结果
    """
    import time
    
    if symbols is None:
        symbols = all_nasdaq_100_symbols
    
    results = {}
    total = len(symbols)
    success_count = 0
    consecutive_failures = 0  # 连续失败计数
    
    print(f"📡 开始获取 {total} 只股票的实时数据...")
    print(f"⏰ 当前美东时间: {format_eastern_time()}")
    print(f"💡 提示: 如果遇到 API 限制，会自动增加等待时间")
    
    for i, symbol in enumerate(symbols, 1):
        print(f"[{i}/{total}] 获取 {symbol}...", end=" ", flush=True)
        
        data = fetch_latest_price(symbol)
        if data:
            success = update_local_file(symbol, data)
            results[symbol] = success
            if success:
                success_count += 1
                consecutive_failures = 0  # 重置失败计数
        else:
            results[symbol] = False
            consecutive_failures += 1
            
            # 如果连续失败超过 3 次，可能是 API 限制，增加等待时间
            if consecutive_failures >= 3:
                wait_time = 60  # 等待 60 秒
                print(f"⚠️ 检测到可能的 API 限制，等待 {wait_time} 秒...")
                time.sleep(wait_time)
                consecutive_failures = 0
        
        # 请求间隔，避免 API 限速
        if i < total:
            time.sleep(delay_between_requests)
    
    print(f"\n📊 获取完成: {success_count}/{total} 成功")
    
    return results


def fetch_and_merge(symbols: Optional[List[str]] = None) -> bool:
    """
    获取所有数据并合并到 merged.jsonl
    这是实时交易调度器的主入口
    
    Args:
        symbols: 要获取的股票列表，默认为纳斯达克 100
        
    Returns:
        是否全部成功
    """
    print("=" * 60)
    print(f"🚀 开始实时数据更新 - {format_eastern_time()}")
    print("=" * 60)
    
    # 检查是否在交易时间
    if not is_market_hours():
        print("⚠️ 当前不在美股交易时间内")
        # 仍然继续执行，因为可能需要获取收盘后的最终数据
    
    # 获取所有股票数据
    results = fetch_all_symbols(symbols)
    
    # 合并到 merged.jsonl
    merge_success = run_merge_jsonl()
    
    # 统计结果
    success_count = sum(1 for v in results.values() if v)
    total_count = len(results)
    
    print("=" * 60)
    print(f"📈 数据更新完成")
    print(f"   - 股票获取: {success_count}/{total_count}")
    print(f"   - 数据合并: {'✅ 成功' if merge_success else '❌ 失败'}")
    print("=" * 60)
    
    return success_count > 0 and merge_success


def fetch_single_symbol(symbol: str) -> bool:
    """
    获取单只股票的数据（用于测试或单独更新）
    
    Args:
        symbol: 股票代码
        
    Returns:
        是否成功
    """
    print(f"📡 获取 {symbol} 的实时数据...")
    
    data = fetch_latest_price(symbol)
    if not data:
        return False
    
    success = update_local_file(symbol, data)
    if success:
        run_merge_jsonl()
    
    return success


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="获取美股实时价格数据")
    parser.add_argument("--symbol", "-s", help="获取单只股票（默认获取全部纳斯达克100）")
    parser.add_argument("--no-merge", action="store_true", help="不执行合并操作")
    
    args = parser.parse_args()
    
    if args.symbol:
        # 获取单只股票
        success = fetch_single_symbol(args.symbol.upper())
        sys.exit(0 if success else 1)
    else:
        # 获取全部股票
        results = fetch_all_symbols()
        
        if not args.no_merge:
            run_merge_jsonl()
        
        # 返回退出码
        success_count = sum(1 for v in results.values() if v)
        sys.exit(0 if success_count > 0 else 1)

