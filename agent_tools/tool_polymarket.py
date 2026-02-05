#!/usr/bin/env python3
"""
Polymarket MCP Tool - 预测市场情绪指标

提供以下工具:
- get_financial_sentiment: 金融情绪指标（按分类获取 TOP 3 热门市场）
- get_trending_markets: 全站热门趋势市场
"""

import json
import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import requests
from dotenv import load_dotenv
from fastmcp import FastMCP

load_dotenv()

logger = logging.getLogger(__name__)

# Polymarket API 配置
BASE_URL = "https://gamma-api.polymarket.com"
DEFAULT_TIMEOUT = 30


class PolymarketClient:
    """Polymarket API 客户端"""
    
    def __init__(self):
        self.base_url = BASE_URL
        self.timeout = DEFAULT_TIMEOUT
    
    def fetch(self, endpoint: str, params: dict = None) -> dict:
        """从 Gamma API 获取数据"""
        url = f"{self.base_url}{endpoint}"
        try:
            resp = requests.get(url, params=params, timeout=self.timeout)
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as e:
            logger.error(f"Polymarket API 请求失败: {e}")
            raise
    
    def get_trending(self, limit: int = 10) -> list:
        """获取热门市场"""
        params = {
            "order": "volume24hr",
            "ascending": "false",
            "closed": "false",
            "limit": limit
        }
        return self.fetch("/events", params)


def format_price(price) -> str:
    """格式化价格为百分比"""
    if price is None:
        return "N/A"
    try:
        pct = float(price) * 100
        return f"{pct:.1f}%"
    except:
        return str(price)


def format_volume(volume) -> str:
    """格式化交易量"""
    if volume is None:
        return "N/A"
    try:
        v = float(volume)
        if v >= 1_000_000:
            return f"${v/1_000_000:.1f}M"
        elif v >= 1_000:
            return f"${v/1_000:.1f}K"
        else:
            return f"${v:.0f}"
    except:
        return str(volume)


def extract_market_info(market: dict) -> dict:
    """提取市场信息"""
    question = market.get("question") or market.get("title", "Unknown")
    
    # 获取价格
    yes_price = None
    no_price = None
    prices = market.get("outcomePrices", [])
    
    if prices:
        if isinstance(prices, str):
            try:
                prices = json.loads(prices)
            except:
                pass
        if isinstance(prices, list) and len(prices) >= 1:
            yes_price = float(prices[0]) if prices[0] else None
            if len(prices) >= 2:
                no_price = float(prices[1]) if prices[1] else None
    
    # 获取交易量
    volume = market.get("volume") or market.get("volumeNum")
    
    # 获取结束日期
    end_date = market.get("endDate") or market.get("end_date_iso")
    formatted_end_date = None
    if end_date:
        try:
            dt = datetime.fromisoformat(end_date.replace("Z", "+00:00"))
            formatted_end_date = dt.strftime("%b %d, %Y")
        except:
            formatted_end_date = end_date
    
    return {
        "question": question,
        "yes_price": yes_price,
        "no_price": no_price,
        "yes_probability": format_price(yes_price),
        "no_probability": format_price(no_price),
        "volume": format_volume(volume),
        "volume_raw": volume,
        "end_date": formatted_end_date,
        "slug": market.get("slug") or market.get("market_slug")
    }


def extract_event_info(event: dict) -> dict:
    """提取事件信息"""
    title = event.get("title", "Unknown Event")
    volume = event.get("volume")
    markets = event.get("markets", [])
    
    market_infos = []
    for m in markets[:5]:
        market_infos.append(extract_market_info(m))
    
    return {
        "title": title,
        "total_volume": format_volume(volume),
        "volume_raw": volume,
        "market_count": len(markets),
        "markets": market_infos,
        "slug": event.get("slug")
    }


# ============================================
# 核心函数（供直接调用和测试）
# ============================================

def get_financial_sentiment_impl() -> str:
    """
    获取金融市场实时情绪指标。
    
    按以下分类查询热门市场：
    - Finance Daily: 每日金融市场（TOP 5）
    - Finance Weekly: 每周金融市场（TOP 5）
    - Stocks: 股票相关市场（TOP 20）
    - Earnings: 财报预测市场（TOP 20）
    - Commodities: 大宗商品市场（TOP 5）
    
    Returns:
        包含各分类热门市场的结构化信息
    """
    try:
        client = PolymarketClient()
        
        # 定义要查询的分类 (tag_slug, 显示名称, limit)
        categories = [
            ("daily", "Finance Daily (每日)", 5),
            ("weekly", "Finance Weekly (每周)", 5),
            ("stocks", "Stocks (股票)", 20),
            ("earnings", "Earnings (财报)", 20),
            ("commodities", "Commodities (大宗商品)", 5),
        ]
        
        output_lines = [
            "📊 **Polymarket 金融市场实时情绪指标**",
            f"数据时间: {datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')}",
            ""
        ]
        
        for tag_slug, category_name, limit in categories:
            try:
                # 使用 tag_slug 过滤获取市场
                events = client.fetch("/events", {
                    "limit": limit,
                    "closed": "false",
                    "tag_slug": tag_slug,
                    "order": "volume24hr",
                    "ascending": "false"
                })
                
                if not events:
                    continue
                
                output_lines.append(f"## {category_name}")
                
                for i, event in enumerate(events[:limit], 1):
                    title = event.get("title", "Unknown")
                    vol24 = event.get("volume24hr", 0)
                    
                    # 获取第一个市场的价格
                    markets = event.get("markets", [])
                    if markets:
                        m = markets[0]
                        prices = m.get("outcomePrices", [])
                        if isinstance(prices, str):
                            try:
                                prices = json.loads(prices)
                            except:
                                prices = []
                        
                        yes_pct = float(prices[0]) * 100 if prices else 0
                        output_lines.append(f"{i}. **{title}** | Yes: {yes_pct:.1f}% | 24h: ${vol24:,.0f}")
                    else:
                        output_lines.append(f"{i}. **{title}** | 24h: ${vol24:,.0f}")
                
                output_lines.append("")
                
            except Exception as e:
                logger.warning(f"获取分类 '{tag_slug}' 失败: {e}")
        
        return "\n".join(output_lines)
    
    except Exception as e:
        logger.error(f"获取金融情绪失败: {e}")
        return f"❌ 获取金融情绪失败: {str(e)}"


def get_trending_markets_impl(limit: int = 10) -> str:
    """
    获取 Polymarket 上当前最热门的预测市场。
    
    按24小时交易量排序，返回最活跃的市场。
    
    Args:
        limit: 返回市场数量，默认10个，最大20个
    
    Returns:
        热门市场列表，包含问题、概率和交易量
    """
    try:
        client = PolymarketClient()
        
        limit = min(max(1, limit), 20)
        events = client.get_trending(limit=limit)
        
        output_lines = [
            "🔥 **Polymarket 热门市场**",
            f"数据时间: {datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')}",
            f"显示前 {len(events)} 个最活跃市场（按24h交易量排序）",
            ""
        ]
        
        for i, event in enumerate(events, 1):
            event_info = extract_event_info(event)
            output_lines.append(f"### {i}. {event_info['title']}")
            output_lines.append(f"总交易量: {event_info['total_volume']} | 市场数: {event_info['market_count']}")
            
            for m in event_info["markets"][:3]:
                output_lines.append(f"  • {m['question']}")
                output_lines.append(f"    Yes: {m['yes_probability']} | 交易量: {m['volume']} | 截止: {m['end_date'] or 'N/A'}")
            
            output_lines.append("")
        
        return "\n".join(output_lines)
    
    except Exception as e:
        logger.error(f"获取热门市场失败: {e}")
        return f"❌ 获取热门市场失败: {str(e)}"


# ============================================
# MCP 工具包装（调用核心函数）
# ============================================

mcp = FastMCP("Polymarket")


@mcp.tool()
def get_financial_sentiment() -> str:
    """
    获取金融市场实时情绪指标。
    
    按以下分类查询热门市场（按24h交易量排序）：
    - Finance Daily: 每日金融市场（TOP 5）
    - Finance Weekly: 每周金融市场（TOP 5）
    - Stocks: 股票相关市场（TOP 20）
    - Earnings: 财报预测市场（TOP 20）
    - Commodities: 大宗商品市场（TOP 5）
    
    Returns:
        包含各分类热门市场的结构化信息，含概率和交易量
    """
    return get_financial_sentiment_impl()


@mcp.tool()
def get_trending_markets(limit: int = 10) -> str:
    """
    获取 Polymarket 上当前最热门的预测市场。
    
    按24小时交易量排序，返回最活跃的市场。
    这些市场反映了当前投资者最关注的话题。
    
    Args:
        limit: 返回市场数量，默认10个，最大20个
    
    Returns:
        热门市场列表，包含问题、概率和交易量
    """
    return get_trending_markets_impl(limit)


if __name__ == "__main__":
    # 运行 MCP 服务
    print("🚀 启动 Polymarket MCP 服务...")
    port = int(os.getenv("POLYMARKET_HTTP_PORT", "8007"))
    mcp.run(transport="streamable-http", port=port)
