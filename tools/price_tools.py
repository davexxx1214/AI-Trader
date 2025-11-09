import os
from dotenv import load_dotenv
load_dotenv()
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
import sys

# 将项目根目录加入 Python 路径，便于从子目录直接运行本文件
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)
from tools.general_tools import get_config_value

all_nasdaq_100_symbols = [
    "NVDA", "MSFT", "AAPL", "GOOG", "GOOGL", "AMZN", "META", "AVGO", "TSLA",
    "NFLX", "PLTR", "COST", "ASML", "AMD", "CSCO", "AZN", "TMUS", "MU", "LIN",
    "PEP", "SHOP", "APP", "INTU", "AMAT", "LRCX", "PDD", "QCOM", "ARM", "INTC",
    "BKNG", "AMGN", "TXN", "ISRG", "GILD", "KLAC", "PANW", "ADBE", "HON",
    "CRWD", "CEG", "ADI", "ADP", "DASH", "CMCSA", "VRTX", "MELI", "SBUX",
    "CDNS", "ORLY", "SNPS", "MSTR", "MDLZ", "ABNB", "MRVL", "CTAS", "TRI",
    "MAR", "MNST", "CSX", "ADSK", "PYPL", "FTNT", "AEP", "WDAY", "REGN", "ROP",
    "NXPI", "DDOG", "AXON", "ROST", "IDXX", "EA", "PCAR", "FAST", "EXC", "TTWO",
    "XEL", "ZS", "PAYX", "WBD", "BKR", "CPRT", "CCEP", "FANG", "TEAM", "CHTR",
    "KDP", "MCHP", "GEHC", "VRSK", "CTSH", "CSGP", "KHC", "ODFL", "DXCM", "TTD",
    "ON", "BIIB", "LULU", "CDW", "GFS"
]

def get_yesterday_date(today_date: str) -> str:
    """
    获取昨日日期，考虑休市日。
    Args:
        today_date: 日期字符串，格式 YYYY-MM-DD，代表今天日期。

    Returns:
        yesterday_date: 昨日日期字符串，格式 YYYY-MM-DD。
    """
    # 计算昨日日期，考虑休市日
    today_dt = datetime.strptime(today_date, "%Y-%m-%d")
    yesterday_dt = today_dt - timedelta(days=1)
    
    # 如果昨日是周末，向前找到最近的交易日
    while yesterday_dt.weekday() >= 5:  # 5=Saturday, 6=Sunday
        yesterday_dt -= timedelta(days=1)
    
    yesterday_date = yesterday_dt.strftime("%Y-%m-%d")
    return yesterday_date

def get_open_prices(today_date: str, symbols: List[str], merged_path: Optional[str] = None) -> Dict[str, Optional[float]]:
    """从 data/merged.jsonl 中读取指定日期与标的的开盘价。

    Args:
        today_date: 日期字符串，格式 YYYY-MM-DD。
        symbols: 需要查询的股票代码列表。
        merged_path: 可选，自定义 merged.jsonl 路径；默认读取项目根目录下 data/merged.jsonl。

    Returns:
        {symbol_price: open_price 或 None} 的字典；若未找到对应日期或标的，则值为 None。
    """
    wanted = set(symbols)
    results: Dict[str, Optional[float]] = {}

    if merged_path is None:
        base_dir = Path(__file__).resolve().parents[1]
        merged_file = base_dir / "data" / "merged.jsonl"
    else:
        merged_file = Path(merged_path)

    if not merged_file.exists():
        return results

    with merged_file.open("r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            try:
                doc = json.loads(line)
            except Exception:
                continue
            meta = doc.get("Meta Data", {}) if isinstance(doc, dict) else {}
            sym = meta.get("2. Symbol")
            if sym not in wanted:
                continue
            series = doc.get("Time Series (Daily)", {})
            if not isinstance(series, dict):
                continue
            bar = series.get(today_date)
            if isinstance(bar, dict):
                open_val = bar.get("1. buy price")
                try:
                    results[f'{sym}_price'] = float(open_val) if open_val is not None else None
                except Exception:
                    results[f'{sym}_price'] = None

    return results

def get_yesterday_open_and_close_price(today_date: str, symbols: List[str], merged_path: Optional[str] = None) -> tuple[Dict[str, Optional[float]], Dict[str, Optional[float]]]:
    """从 data/merged.jsonl 中读取指定日期与股票的昨日买入价和卖出价。

    Args:
        today_date: 日期字符串，格式 YYYY-MM-DD，代表今天日期。
        symbols: 需要查询的股票代码列表。
        merged_path: 可选，自定义 merged.jsonl 路径；默认读取项目根目录下 data/merged.jsonl。

    Returns:
        (买入价字典, 卖出价字典) 的元组；若未找到对应日期或标的，则值为 None。
    """
    wanted = set(symbols)
    buy_results: Dict[str, Optional[float]] = {}
    sell_results: Dict[str, Optional[float]] = {}

    if merged_path is None:
        base_dir = Path(__file__).resolve().parents[1]
        merged_file = base_dir / "data" / "merged.jsonl"
    else:
        merged_file = Path(merged_path)

    if not merged_file.exists():
        return buy_results, sell_results

    yesterday_date = get_yesterday_date(today_date)

    with merged_file.open("r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            try:
                doc = json.loads(line)
            except Exception:
                continue
            meta = doc.get("Meta Data", {}) if isinstance(doc, dict) else {}
            sym = meta.get("2. Symbol")
            if sym not in wanted:
                continue
            series = doc.get("Time Series (Daily)", {})
            if not isinstance(series, dict):
                continue
            
            # 尝试获取昨日买入价和卖出价
            bar = series.get(yesterday_date)
            if isinstance(bar, dict):
                buy_val = bar.get("1. buy price")  # 买入价字段
                sell_val = bar.get("4. sell price")  # 卖出价字段
                
                try:
                    buy_price = float(buy_val) if buy_val is not None else None
                    sell_price = float(sell_val) if sell_val is not None else None
                    buy_results[f'{sym}_price'] = buy_price
                    sell_results[f'{sym}_price'] = sell_price
                except Exception:
                    buy_results[f'{sym}_price'] = None
                    sell_results[f'{sym}_price'] = None
            else:
                # 如果昨日没有数据，尝试向前查找最近的交易日
                today_dt = datetime.strptime(today_date, "%Y-%m-%d")
                yesterday_dt = today_dt - timedelta(days=1)
                current_date = yesterday_dt
                found_data = False
                
                # 最多向前查找5个交易日
                for _ in range(5):
                    current_date -= timedelta(days=1)
                    # 跳过周末
                    while current_date.weekday() >= 5:
                        current_date -= timedelta(days=1)
                    
                    check_date = current_date.strftime("%Y-%m-%d")
                    bar = series.get(check_date)
                    if isinstance(bar, dict):
                        buy_val = bar.get("1. buy price")
                        sell_val = bar.get("4. sell price")
                        
                        try:
                            buy_price = float(buy_val) if buy_val is not None else None
                            sell_price = float(sell_val) if sell_val is not None else None
                            buy_results[f'{sym}_price'] = buy_price
                            sell_results[f'{sym}_price'] = sell_price
                            found_data = True
                            break
                        except Exception:
                            continue
                
                if not found_data:
                    buy_results[f'{sym}_price'] = None
                    sell_results[f'{sym}_price'] = None

    return buy_results, sell_results

def get_yesterday_profit(today_date: str, yesterday_buy_prices: Dict[str, Optional[float]], yesterday_sell_prices: Dict[str, Optional[float]], yesterday_init_position: Dict[str, float]) -> Dict[str, float]:
    """
    获取今日开盘时持仓的收益，收益计算方式为：(昨日收盘价格 - 昨日开盘价格)*当前持仓。
    Args:
        today_date: 日期字符串，格式 YYYY-MM-DD，代表今天日期。
        yesterday_buy_prices: 昨日开盘价格字典，格式为 {symbol_price: price}
        yesterday_sell_prices: 昨日收盘价格字典，格式为 {symbol_price: price}
        yesterday_init_position: 昨日初始持仓字典，格式为 {symbol: weight}

    Returns:
        {symbol: profit} 的字典；若未找到对应日期或标的，则值为 0.0。
    """
    profit_dict = {}
    
    # 遍历所有股票代码
    for symbol in all_nasdaq_100_symbols:
        symbol_price_key = f'{symbol}_price'
        
        # 获取昨日开盘价和收盘价
        buy_price = yesterday_buy_prices.get(symbol_price_key)
        sell_price = yesterday_sell_prices.get(symbol_price_key)
        
        # 获取昨日持仓权重
        position_weight = yesterday_init_position.get(symbol, 0.0)
        
        # 计算收益：(收盘价 - 开盘价) * 持仓权重
        if buy_price is not None and sell_price is not None and position_weight > 0:
            profit = (sell_price - buy_price) * position_weight
            profit_dict[symbol] = round(profit, 4)  # 保留4位小数
        else:
            profit_dict[symbol] = 0.0
    
    return profit_dict

def get_today_init_position(today_date: str, modelname: str) -> Dict[str, float]:
    """
    获取今日开盘时的初始持仓（即文件中上一个交易日代表的持仓）。从../data/agent_data/{modelname}/position/position.jsonl中读取。
    如果同一日期有多条记录，选择id最大的记录作为初始持仓。
    如果找不到yesterday_date的数据，则查找position文件中最早的记录（用于处理从更早日期开始的情况）。
    
    Args:
        today_date: 日期字符串，格式 YYYY-MM-DD，代表今天日期。
        modelname: 模型名称，用于构建文件路径。

    Returns:
        {symbol: weight} 的字典；若未找到对应日期，则返回空字典。
    """
    base_dir = Path(__file__).resolve().parents[1]
    position_file = base_dir / "data" / "agent_data" / modelname / "position" / "position.jsonl"

    if not position_file.exists():
        print(f"Position file {position_file} does not exist")
        return {}
    
    yesterday_date = get_yesterday_date(today_date)
    max_id = -1
    latest_positions = {}
    
    # 用于存储所有记录，以便在找不到yesterday_date时使用最早的记录
    all_records = []
  
    with position_file.open("r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            try:
                doc = json.loads(line)
                all_records.append(doc)
                if doc.get("date") == yesterday_date:
                    current_id = doc.get("id", 0)
                    if current_id > max_id:
                        max_id = current_id
                        latest_positions = doc.get("positions", {})
            except Exception:
                continue
    
    # 如果找到了yesterday_date的数据，直接返回
    if latest_positions:
        return latest_positions
    
    # 如果找不到yesterday_date的数据，检查today_date是否早于position文件中的最早日期
    if all_records:
        # 先尝试查找id=0的记录（初始记录）
        initial_record = None
        for record in all_records:
            if record.get("id", -1) == 0:
                initial_record = record
                break
        
        # 按日期排序，找到最早的记录
        all_records.sort(key=lambda x: (x.get("date", ""), x.get("id", -1)))
        earliest_record = all_records[0]
        earliest_date = earliest_record.get("date", "")
        
        # 如果today_date早于position文件中的最早日期，说明是从更早的日期开始处理
        # 此时应该使用初始记录（id=0）的持仓，如果没有则使用最早的记录
        try:
            from datetime import datetime
            today_date_obj = datetime.strptime(today_date, "%Y-%m-%d")
            earliest_date_obj = datetime.strptime(earliest_date, "%Y-%m-%d")
            
            if today_date_obj < earliest_date_obj:
                # today_date早于position文件中的最早日期，使用初始记录或最早的记录
                if initial_record:
                    initial_positions = initial_record.get("positions", {})
                    if initial_positions:
                        print(f"ℹ️  {today_date} 早于position文件中的最早日期 ({earliest_date})，使用初始记录 (id=0) 的持仓")
                        return initial_positions
                
                # 如果没有初始记录，尝试从最早的记录中构建初始持仓
                earliest_positions = earliest_record.get("positions", {})
                if earliest_positions:
                    # 从最早的记录中获取所有股票代码（排除CASH）
                    stock_symbols = [sym for sym in earliest_positions.keys() if sym != "CASH"]
                    # 如果最早的记录中没有股票代码，使用默认的股票列表
                    if not stock_symbols:
                        stock_symbols = all_nasdaq_100_symbols
                    
                    # 检查最早的记录是否有持仓（非零股票）
                    has_positions = any(earliest_positions.get(sym, 0) > 0 for sym in stock_symbols)
                    
                    if has_positions:
                        # 如果最早的记录已经有持仓，说明已经进行过交易
                        # 此时应该使用默认初始金额，因为无法准确推断初始CASH
                        initial_cash = 10000.0
                        print(f"ℹ️  {today_date} 早于position文件中的最早日期 ({earliest_date})，最早的记录已有持仓，使用默认初始金额 $10000")
                    else:
                        # 如果最早的记录没有持仓（所有股票为0），可以使用其CASH值作为初始金额
                        initial_cash = earliest_positions.get("CASH", 10000.0)
                        print(f"ℹ️  {today_date} 早于position文件中的最早日期 ({earliest_date})，从最早记录提取初始金额 ${initial_cash}")
                    
                    # 创建初始持仓：所有股票为0，CASH为初始金额
                    init_position = {symbol: 0 for symbol in stock_symbols}
                    init_position['CASH'] = initial_cash
                    
                    print(f"ℹ️  创建初始持仓 (所有股票为0，CASH=${initial_cash})")
                    return init_position
                
                # 如果最早的记录也没有持仓信息，创建默认初始持仓
                init_position = {symbol: 0 for symbol in all_nasdaq_100_symbols}
                init_position['CASH'] = 10000.0
                print(f"ℹ️  {today_date} 早于position文件中的最早日期 ({earliest_date})，创建默认初始持仓 (所有股票为0，CASH=$10000)")
                return init_position
            else:
                # today_date晚于或等于最早日期，使用最早的记录作为初始持仓
                earliest_positions = earliest_record.get("positions", {})
                if earliest_positions:
                    print(f"ℹ️  未找到 {yesterday_date} 的数据，使用最早的记录 ({earliest_date}) 作为初始持仓")
                    return earliest_positions
        except Exception as e:
            # 日期解析失败，使用初始记录或最早的记录
            if initial_record:
                initial_positions = initial_record.get("positions", {})
                if initial_positions:
                    print(f"ℹ️  未找到 {yesterday_date} 的数据，使用初始记录 (id=0) 的持仓")
                    return initial_positions
            earliest_positions = earliest_record.get("positions", {})
            if earliest_positions:
                print(f"ℹ️  未找到 {yesterday_date} 的数据，使用最早的记录 ({earliest_date}) 作为初始持仓")
                return earliest_positions
    
    return {}

def get_latest_position(today_date: str, modelname: str) -> Dict[str, float]:
    """
    获取最新持仓。从 ../data/agent_data/{modelname}/position/position.jsonl 中读取。
    优先选择当天 (today_date) 中 id 最大的记录；
    若当天无记录，则回退到上一个交易日，选择该日中 id 最大的记录。

    Args:
        today_date: 日期字符串，格式 YYYY-MM-DD，代表今天日期。
        modelname: 模型名称，用于构建文件路径。

    Returns:
        (positions, max_id):
          - positions: {symbol: weight} 的字典；若未找到任何记录，则为空字典。
          - max_id: 选中记录的最大 id；若未找到任何记录，则为 -1。
    """
    base_dir = Path(__file__).resolve().parents[1]
    position_file = base_dir / "data" / "agent_data" / modelname / "position" / "position.jsonl"

    if not position_file.exists():
        return {}, -1
    
    # 先尝试读取当天记录
    max_id_today = -1
    latest_positions_today: Dict[str, float] = {}
    
    with position_file.open("r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            try:
                doc = json.loads(line)
                if doc.get("date") == today_date:
                    current_id = doc.get("id", -1)
                    if current_id > max_id_today:
                        max_id_today = current_id
                        latest_positions_today = doc.get("positions", {})
            except Exception:
                continue
    
    if max_id_today >= 0:
        return latest_positions_today, max_id_today

    # 当天没有记录，则回退到上一个交易日
    prev_date = get_yesterday_date(today_date)
    max_id_prev = -1
    latest_positions_prev: Dict[str, float] = {}

    with position_file.open("r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            try:
                doc = json.loads(line)
                if doc.get("date") == prev_date:
                    current_id = doc.get("id", -1)
                    if current_id > max_id_prev:
                        max_id_prev = current_id
                        latest_positions_prev = doc.get("positions", {})
            except Exception:
                continue

    return latest_positions_prev, max_id_prev

def add_no_trade_record(today_date: str, modelname: str):
    """
    添加不交易记录。从 ../data/agent_data/{modelname}/position/position.jsonl 中前一日最后一条持仓，并更新在今日的position.jsonl文件中。
    Args:
        today_date: 日期字符串，格式 YYYY-MM-DD，代表今天日期。
        modelname: 模型名称，用于构建文件路径。

    Returns:
        None
    """
    save_item = {}
    current_position, current_action_id = get_latest_position(today_date, modelname)
    print(current_position, current_action_id)
    save_item["date"] = today_date
    save_item["id"] = current_action_id+1
    save_item["this_action"] = {"action":"no_trade","symbol":"","amount":0}
    
    save_item["positions"] = current_position
    base_dir = Path(__file__).resolve().parents[1]
    position_file = base_dir / "data" / "agent_data" / modelname / "position" / "position.jsonl"

    with position_file.open("a", encoding="utf-8") as f:
        f.write(json.dumps(save_item) + "\n")
    return 

if __name__ == "__main__":
    today_date = get_config_value("TODAY_DATE")
    signature = get_config_value("SIGNATURE")
    if signature is None:
        raise ValueError("SIGNATURE environment variable is not set")
    print(today_date, signature)
    yesterday_date = get_yesterday_date(today_date)
    # print(yesterday_date)
    today_buy_price = get_open_prices(today_date, all_nasdaq_100_symbols)
    # print(today_buy_price)
    yesterday_buy_prices, yesterday_sell_prices = get_yesterday_open_and_close_price(today_date, all_nasdaq_100_symbols)
    # print(yesterday_buy_prices)
    # print(yesterday_sell_prices)
    today_init_position = get_today_init_position(today_date, signature)
    # print(today_init_position)
    latest_position, latest_action_id = get_latest_position(today_date, signature)
    print(latest_position, latest_action_id)
    yesterday_profit = get_yesterday_profit(today_date, yesterday_buy_prices, yesterday_sell_prices, today_init_position)
    # print(yesterday_profit)
    add_no_trade_record(today_date, signature)
