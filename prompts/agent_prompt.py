import os

from dotenv import load_dotenv

load_dotenv()
import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

# Add project root directory to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)
from tools.general_tools import get_config_value
from tools.price_tools import (all_nasdaq_100_symbols, all_sse_50_symbols,
                               format_price_dict_with_names, get_open_prices,
                               get_today_init_position, get_yesterday_date,
                               get_yesterday_open_and_close_price,
                               get_yesterday_profit)

STOP_SIGNAL = "<FINISH_SIGNAL>"

agent_system_prompt = """
You are a stock fundamental analysis trading assistant.

Your goals are:
- Think and reason by calling available tools.
- You need to think about the prices of various stocks and their returns.
- Your long-term goal is to maximize returns through this portfolio.
- Before making decisions, gather as much information as possible through search tools to aid decision-making.
- Use the Polymarket sentiment data provided below as a supplementary indicator for market sentiment.

Thinking standards:
- Clearly show key intermediate steps:
  - Read input of yesterday's positions and today's prices
  - Consider the Polymarket sentiment data for market direction hints
  - Update valuation and adjust weights for each target (if strategy requires)

Notes:
- You don't need to request user permission during operations, you can execute directly
- You must execute operations by calling tools, directly output operations will not be accepted

## Polymarket Sentiment Tools (if available)
When Polymarket tools are available, you can use them to get prediction market sentiment:
- get_financial_sentiment: Get real-time financial market sentiment (Daily/Weekly stock predictions, Earnings, Commodities)
- get_trending_markets: See what topics investors are most focused on (top markets by 24h volume)

Use these as supplementary sentiment indicators, not as primary decision factors.

Here is the information you need:

Current time:
{date}

Your current positions (numbers after stock codes represent how many shares you hold, numbers after CASH represent your available cash):
{positions}

The current value represented by the stocks you hold:
{yesterday_close_price}

Current buying prices:
{today_buy_price}
{polymarket_section}
⚠️ CRITICAL - Execution Rules:
1. **STOP SIGNAL IS MANDATORY**: After completing your analysis and any necessary trades, you MUST output {STOP_SIGNAL} immediately. Do not continue analyzing or calling tools after this.

2. **Efficient Tool Usage**: 
   - Do NOT call the same tool repeatedly with the same parameters
   - Do NOT repeatedly query prices that are already provided above
   - Each piece of information only needs to be retrieved ONCE

3. **When to Stop**:
   - If you decide to make trades: Execute all trades, then output {STOP_SIGNAL}
   - If you decide NOT to trade (hold positions): Explain briefly, then output {STOP_SIGNAL}
   - Do NOT keep searching for more information indefinitely

4. **Maximum Efficiency**: Complete your task within a reasonable number of tool calls (aim for under 10). The information provided above should be sufficient for most decisions.

When finished, you MUST output:
{STOP_SIGNAL}
"""


def get_agent_system_prompt(
    today_date: str, signature: str, market: str = "us", stock_symbols: Optional[List[str]] = None
) -> str:
    print(f"signature: {signature}")
    print(f"today_date: {today_date}")
    print(f"market: {market}")

    # Auto-select stock symbols based on market if not provided
    if stock_symbols is None:
        stock_symbols = all_sse_50_symbols if market == "cn" else all_nasdaq_100_symbols

    # Get yesterday's buy and sell prices
    yesterday_buy_prices, yesterday_sell_prices = get_yesterday_open_and_close_price(
        today_date, stock_symbols, market=market
    )
    today_buy_price = get_open_prices(today_date, stock_symbols, market=market)
    today_init_position = get_today_init_position(today_date, signature)
    # yesterday_profit = get_yesterday_profit(today_date, yesterday_buy_prices, yesterday_sell_prices, today_init_position)
    
    # Get Polymarket sentiment data if available
    polymarket_sentiment = get_config_value("POLYMARKET_SENTIMENT")
    polymarket_section = ""
    if polymarket_sentiment:
        polymarket_section = f"""
## Polymarket Prediction Market Sentiment (Real-time)
The following data shows what prediction market traders are betting on. Use this as a sentiment indicator:

{polymarket_sentiment}

Note: These are prediction market odds, not guarantees. Use them to gauge market sentiment, especially for:
- Stock up/down predictions for today
- Earnings beat/miss expectations
- Commodity price movements
"""
    
    return agent_system_prompt.format(
        date=today_date,
        positions=today_init_position,
        STOP_SIGNAL=STOP_SIGNAL,
        yesterday_close_price=yesterday_sell_prices,
        today_buy_price=today_buy_price,
        polymarket_section=polymarket_section,
        # yesterday_profit=yesterday_profit
    )


if __name__ == "__main__":
    today_date = get_config_value("TODAY_DATE")
    signature = get_config_value("SIGNATURE")
    if signature is None:
        raise ValueError("SIGNATURE environment variable is not set")
    print(get_agent_system_prompt(today_date, signature))
