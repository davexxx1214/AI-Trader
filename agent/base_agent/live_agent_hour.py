"""
LiveAgent_Hour class - 实时交易 Agent

继承 BaseAgent_Hour，专门用于实时模拟交易场景。
主要区别：
1. get_trading_dates() 只返回当前时间点
2. run_single_hour() 执行单次交易决策
3. 支持实时数据更新后立即执行
"""

import os
import sys
from datetime import datetime
from typing import List, Optional

from dotenv import load_dotenv

# 将项目根目录加入 Python 路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from agent.base_agent.base_agent_hour import BaseAgent_Hour
from tools.general_tools import write_config_value
from tools.trading_calendar import (
    get_eastern_now,
    get_current_trading_hour,
    is_market_hours,
    is_trading_day,
    format_eastern_time,
)

load_dotenv()


class LiveAgent_Hour(BaseAgent_Hour):
    """
    实时交易 Agent，用于每小时执行一次交易决策
    
    与回测版本的主要区别：
    1. 不依赖历史数据范围，只处理当前时间点
    2. 支持实时调用，每次只执行一个交易决策
    3. 集成交易日历判断
    """
    
    def __init__(self, *args, **kwargs):
        """初始化 LiveAgent_Hour"""
        super().__init__(*args, **kwargs)
        self.is_live_trading = True
    
    def get_trading_dates(self, init_date: str, end_date: str) -> List[str]:
        """
        获取交易时间点 - 实时版本只返回当前时间点
        
        Args:
            init_date: 开始日期（实时交易中忽略）
            end_date: 结束日期（实时交易中忽略）
            
        Returns:
            包含当前交易时间点的列表，如果不在交易时间则返回空列表
        """
        now = get_eastern_now()
        
        # 检查是否是交易日
        if not is_trading_day(now):
            print(f"📅 今天不是交易日 ({format_eastern_time(now)})")
            return []
        
        # 检查是否在交易时间
        if not is_market_hours(now):
            print(f"⏰ 当前不在交易时间 ({format_eastern_time(now)})")
            return []
        
        # 获取当前交易小时
        current_hour = get_current_trading_hour(now)
        if current_hour is None:
            print(f"⏰ 当前小时不是有效交易小时 ({format_eastern_time(now)})")
            return []
        
        # 检查是否已经处理过这个时间点
        if os.path.exists(self.position_file):
            import json
            with open(self.position_file, "r") as f:
                for line in f:
                    doc = json.loads(line)
                    if doc.get("date") == current_hour:
                        print(f"⏭️ 时间点 {current_hour} 已处理过，跳过")
                        return []
        
        print(f"✅ 当前交易时间点: {current_hour}")
        return [current_hour]
    
    async def run_single_hour(self, trading_hour: Optional[str] = None) -> bool:
        """
        执行单次交易决策
        
        Args:
            trading_hour: 交易时间点，格式 'YYYY-MM-DD HH:00:00'
                         如果为 None，自动获取当前交易时间
        
        Returns:
            是否成功执行
        """
        # 如果没有指定时间，获取当前交易时间
        if trading_hour is None:
            trading_hour = get_current_trading_hour()
            if trading_hour is None:
                print("❌ 当前不在有效交易时间")
                return False
        
        print(f"🚀 开始实时交易决策: {trading_hour}")
        
        # 设置配置
        write_config_value("TODAY_DATE", trading_hour)
        write_config_value("SIGNATURE", self.signature)
        
        try:
            await self.run_with_retry(trading_hour)
            print(f"✅ 实时交易决策完成: {trading_hour}")
            return True
        except Exception as e:
            print(f"❌ 实时交易决策失败: {e}")
            return False
    
    async def run_live(self) -> bool:
        """
        实时交易主入口
        检查当前是否应该交易，如果是则执行交易决策
        
        Returns:
            是否执行了交易
        """
        now = get_eastern_now()
        print(f"📡 实时交易检查 - {format_eastern_time(now)}")
        
        # 获取当前可交易的时间点
        trading_dates = self.get_trading_dates("", "")
        
        if not trading_dates:
            print("📊 当前无需交易")
            return False
        
        # 执行交易
        trading_hour = trading_dates[0]
        return await self.run_single_hour(trading_hour)
    
    async def run_date_range(self, init_date: str, end_date: str) -> None:
        """
        实时交易版本的日期范围处理
        对于实时交易，忽略日期范围参数，只处理当前时间点
        
        Args:
            init_date: 开始日期（被忽略）
            end_date: 结束日期（被忽略）
        """
        print(f"📡 实时交易模式 - 忽略日期范围，只处理当前时间点")
        await self.run_live()
    
    def __str__(self) -> str:
        return f"LiveAgent_Hour(signature='{self.signature}', basemodel='{self.basemodel}', stocks={len(self.stock_symbols)}, live=True)"
    
    def __repr__(self) -> str:
        return self.__str__()

