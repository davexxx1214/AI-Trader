import requests
import os
from dotenv import load_dotenv
load_dotenv()
import json
from pathlib import Path
from datetime import datetime, timedelta

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

def get_config_date_range():
    """读取配置文件中的日期范围"""
    try:
        # 尝试读取配置文件
        config_path = Path(__file__).parent.parent / "configs" / "default_config.json"
        if config_path.exists():
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                date_range = config.get("date_range", {})
                init_date = date_range.get("init_date")
                end_date = date_range.get("end_date")
                if init_date and end_date:
                    return init_date, end_date
    except Exception as e:
        print(f"⚠️  读取配置文件失败: {e}")
    
    # 如果没有配置文件或读取失败，检查环境变量
    init_date = os.getenv("INIT_DATE")
    end_date = os.getenv("END_DATE")
    if init_date and end_date:
        return init_date, end_date
    
    return None, None

def get_daily_price(SYMBOL: str):
    FUNCTION = "TIME_SERIES_DAILY"
    
    # 读取配置中的日期范围，决定使用 compact 还是 full
    init_date, end_date = get_config_date_range()
    OUTPUTSIZE = 'compact'  # 默认使用 compact
    
    if init_date:
        try:
            init_date_obj = datetime.strptime(init_date, "%Y-%m-%d")
            # 如果起始日期早于100个交易日之前，使用full模式
            # 100个交易日大约等于140个自然日（考虑周末）
            days_ago = (datetime.now() - init_date_obj).days
            if days_ago > 140:
                OUTPUTSIZE = 'full'
                print(f"ℹ️  检测到起始日期 {init_date}，使用 full 模式获取完整历史数据")
        except Exception as e:
            print(f"⚠️  解析日期失败: {e}，使用默认 compact 模式")
    
    APIKEY = os.getenv("ALPHAADVANTAGE_API_KEY")
    url = f'https://www.alphavantage.co/query?function={FUNCTION}&symbol={SYMBOL}&outputsize={OUTPUTSIZE}&apikey={APIKEY}'
    r = requests.get(url)
    data = r.json()
    print(data)
    if data.get('Note') is not None or data.get('Information') is not None:
        print(f"Error")
        return
    with open(f'./daily_prices_{SYMBOL}.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    if SYMBOL == "QQQ":
        with open(f'./Adaily_prices_{SYMBOL}.json', 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)



if __name__ == "__main__":
    for symbol in all_nasdaq_100_symbols:
        get_daily_price(symbol)

    get_daily_price("QQQ")