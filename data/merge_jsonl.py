import json
import os
import glob


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

# 读取配置文件中的日期范围
current_dir = os.path.dirname(__file__)
config_path = os.path.join(current_dir, '..', 'configs', 'default_config.json')

with open(config_path, 'r', encoding='utf-8') as f:
    config = json.load(f)

init_date = config.get('date_range', {}).get('init_date', '1900-01-01')
end_date = config.get('date_range', {}).get('end_date', '2099-12-31')

print(f"📅 日期范围: {init_date} ~ {end_date}")

def is_date_in_range(date_str: str, init_date: str, end_date: str) -> bool:
    """检查日期是否在指定范围内"""
    try:
        return init_date <= date_str <= end_date
    except:
        return False

# 合并所有以 daily_price 开头的 json，逐文件一行写入 merged.jsonl
pattern = os.path.join(current_dir, 'daily_price*.json')
files = sorted(glob.glob(pattern))

output_file = os.path.join(current_dir, 'merged.jsonl')

processed_count = 0
skipped_count = 0

with open(output_file, 'w', encoding='utf-8') as fout:
    for fp in files:
        basename = os.path.basename(fp)
        # 仅当文件名包含任一纳指100成分符号时才写入
        if not any(symbol in basename for symbol in all_nasdaq_100_symbols):
            skipped_count += 1
            continue
        with open(fp, 'r', encoding='utf-8') as f:
            data = json.load(f)
        # 统一重命名："1. open" -> "1. buy price"；"4. close" -> "4. sell price"
        # 对于最新的一天，只保留并写入 "1. buy price"
        try:
            # 查找所有以 "Time Series" 开头的键
            series = None
            for key, value in data.items():
                if key.startswith("Time Series"):
                    series = value
                    break
            if isinstance(series, dict) and series:
                # 1. 过滤日期范围外的数据
                dates_to_remove = [d for d in series.keys() if not is_date_in_range(d, init_date, end_date)]
                for d in dates_to_remove:
                    del series[d]
                
                # 如果过滤后没有数据，跳过该文件
                if not series:
                    continue
                
                # 2. 对所有日期做键名重命名
                for d, bar in list(series.items()):
                    if not isinstance(bar, dict):
                        continue
                    if "1. open" in bar:
                        bar["1. buy price"] = bar.pop("1. open")
                    if "4. close" in bar:
                        bar["4. sell price"] = bar.pop("4. close")
                
                # 3. 处理最新日期，仅保留买入价
                latest_date = max(series.keys())
                latest_bar = series.get(latest_date, {})
                if isinstance(latest_bar, dict):
                    buy_val = latest_bar.get("1. buy price")
                    series[latest_date] = {"1. buy price": buy_val} if buy_val is not None else {}
                
                # 4. 更新 Meta Data 描述和日期范围
                meta = data.get("Meta Data", {})
                if isinstance(meta, dict):
                    meta["1. Information"] = "Daily Prices (buy price, high, low, sell price) and Volumes"
                    meta["3. Last Refreshed"] = latest_date
        except Exception as e:
            # 若结构异常则原样写入
            print(f"⚠️  处理 {basename} 时出错: {e}")

        fout.write(json.dumps(data, ensure_ascii=False) + "\n")
        processed_count += 1

print(f"✅ 合并完成！")
print(f"   - 处理文件数: {processed_count}")
print(f"   - 跳过文件数: {skipped_count}")
print(f"   - 输出文件: {output_file}")
