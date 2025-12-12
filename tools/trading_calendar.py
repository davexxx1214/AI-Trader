"""
Trading Calendar Module - 美股交易日历判断工具

提供以下功能：
1. 判断当前是否是美股交易日（排除周末和美国节假日）
2. 判断当前是否在交易时间内（美东时间 9:30-16:00）
3. 返回下一个有效交易时间点
4. 获取当前美东时间的整点交易时刻
"""

import os
from datetime import datetime, timedelta, time
from typing import Optional, Tuple
from zoneinfo import ZoneInfo

# 美东时区
US_EASTERN = ZoneInfo("America/New_York")

# 美股交易时间（美东时间）
MARKET_OPEN = time(9, 30)
MARKET_CLOSE = time(16, 0)

# 2024-2025 美国股市休市日（需要定期更新）
# 来源: NYSE 和 NASDAQ 休市日历
US_MARKET_HOLIDAYS = {
    # 2024 年
    "2024-01-01",  # New Year's Day
    "2024-01-15",  # Martin Luther King Jr. Day
    "2024-02-19",  # Presidents Day
    "2024-03-29",  # Good Friday
    "2024-05-27",  # Memorial Day
    "2024-06-19",  # Juneteenth
    "2024-07-04",  # Independence Day
    "2024-09-02",  # Labor Day
    "2024-11-28",  # Thanksgiving Day
    "2024-12-25",  # Christmas Day
    # 2025 年
    "2025-01-01",  # New Year's Day
    "2025-01-20",  # Martin Luther King Jr. Day
    "2025-02-17",  # Presidents Day
    "2025-04-18",  # Good Friday
    "2025-05-26",  # Memorial Day
    "2025-06-19",  # Juneteenth
    "2025-07-04",  # Independence Day
    "2025-09-01",  # Labor Day
    "2025-11-27",  # Thanksgiving Day
    "2025-12-25",  # Christmas Day
    # 2026 年（提前添加部分已知节假日）
    "2026-01-01",  # New Year's Day
    "2026-01-19",  # Martin Luther King Jr. Day
    "2026-02-16",  # Presidents Day
    "2026-04-03",  # Good Friday
    "2026-05-25",  # Memorial Day
    "2026-06-19",  # Juneteenth
    "2026-07-03",  # Independence Day (observed)
    "2026-09-07",  # Labor Day
    "2026-11-26",  # Thanksgiving Day
    "2026-12-25",  # Christmas Day
}


def get_eastern_now() -> datetime:
    """获取当前美东时间"""
    return datetime.now(US_EASTERN)


def is_weekend(dt: datetime) -> bool:
    """判断是否是周末"""
    return dt.weekday() >= 5  # Saturday = 5, Sunday = 6


def is_us_holiday(dt: datetime) -> bool:
    """判断是否是美国股市休市日"""
    date_str = dt.strftime("%Y-%m-%d")
    return date_str in US_MARKET_HOLIDAYS


def is_trading_day(dt: Optional[datetime] = None) -> bool:
    """
    判断指定日期是否是美股交易日
    
    Args:
        dt: 要检查的日期时间（美东时间），默认为当前时间
        
    Returns:
        bool: 是否是交易日
    """
    if dt is None:
        dt = get_eastern_now()
    
    # 周末不交易
    if is_weekend(dt):
        return False
    
    # 节假日不交易
    if is_us_holiday(dt):
        return False
    
    return True


def is_market_hours(dt: Optional[datetime] = None) -> bool:
    """
    判断当前是否在交易时间内（美东时间 9:30-16:00）
    
    Args:
        dt: 要检查的日期时间（美东时间），默认为当前时间
        
    Returns:
        bool: 是否在交易时间内
    """
    if dt is None:
        dt = get_eastern_now()
    
    # 首先检查是否是交易日
    if not is_trading_day(dt):
        return False
    
    # 检查时间是否在交易时间范围内
    current_time = dt.time()
    return MARKET_OPEN <= current_time <= MARKET_CLOSE


def is_trading_hour(dt: Optional[datetime] = None) -> bool:
    """
    判断指定时间是否是有效的交易小时整点
    有效的交易小时：10:00, 11:00, 12:00, 13:00, 14:00, 15:00, 16:00
    
    Args:
        dt: 要检查的日期时间（美东时间），默认为当前时间
        
    Returns:
        bool: 是否是有效的交易小时
    """
    if dt is None:
        dt = get_eastern_now()
    
    # 首先检查是否是交易日
    if not is_trading_day(dt):
        return False
    
    # 有效的交易小时（整点）
    valid_hours = [10, 11, 12, 13, 14, 15, 16]
    return dt.hour in valid_hours


def get_current_trading_hour(dt: Optional[datetime] = None) -> Optional[str]:
    """
    获取当前的交易小时时间戳
    如果当前在交易时间内，返回当前整点的时间戳
    
    Args:
        dt: 要检查的日期时间（美东时间），默认为当前时间
        
    Returns:
        str: 交易时间戳，格式 'YYYY-MM-DD HH:00:00'，如果不在交易时间则返回 None
    """
    if dt is None:
        dt = get_eastern_now()
    
    if not is_market_hours(dt):
        return None
    
    # 返回当前小时的整点时间
    # 注意：如果是 9:30-9:59，应该等到 10:00 才有数据
    if dt.hour == 9:
        return None
    
    return dt.strftime("%Y-%m-%d") + f" {dt.hour:02d}:00:00"


def get_next_trading_time(dt: Optional[datetime] = None) -> Tuple[datetime, str]:
    """
    获取下一个交易时间点
    
    Args:
        dt: 起始时间（美东时间），默认为当前时间
        
    Returns:
        Tuple[datetime, str]: (下一个交易时间点, 时间戳字符串)
    """
    if dt is None:
        dt = get_eastern_now()
    
    # 如果当前在交易时间内，返回下一个整点
    if is_market_hours(dt):
        if dt.hour < 16:
            next_hour = dt.replace(hour=dt.hour + 1, minute=0, second=0, microsecond=0)
            if dt.hour == 9:
                next_hour = dt.replace(hour=10, minute=0, second=0, microsecond=0)
            return next_hour, next_hour.strftime("%Y-%m-%d %H:00:00")
    
    # 如果不在交易时间，找到下一个交易日的开盘时间
    check_date = dt.date()
    
    # 如果今天的交易时间已经过了，从明天开始找
    if dt.time() >= MARKET_CLOSE or not is_trading_day(dt):
        check_date = check_date + timedelta(days=1)
    
    # 找到下一个交易日
    max_days = 10  # 最多找10天（防止无限循环）
    for _ in range(max_days):
        check_dt = datetime.combine(check_date, MARKET_OPEN, tzinfo=US_EASTERN)
        if is_trading_day(check_dt):
            # 返回第一个有效交易小时（10:00）
            next_trading = check_dt.replace(hour=10, minute=0, second=0, microsecond=0)
            return next_trading, next_trading.strftime("%Y-%m-%d %H:00:00")
        check_date = check_date + timedelta(days=1)
    
    # 如果找不到，返回一周后的时间
    fallback = dt + timedelta(days=7)
    return fallback, fallback.strftime("%Y-%m-%d %H:00:00")


def get_trading_hours_today(dt: Optional[datetime] = None) -> list[str]:
    """
    获取今天所有的交易小时时间戳
    
    Args:
        dt: 日期（美东时间），默认为当前时间
        
    Returns:
        list[str]: 今天的交易小时时间戳列表
    """
    if dt is None:
        dt = get_eastern_now()
    
    if not is_trading_day(dt):
        return []
    
    date_str = dt.strftime("%Y-%m-%d")
    # 有效的交易小时：10:00, 11:00, 12:00, 13:00, 14:00, 15:00, 16:00
    return [f"{date_str} {h:02d}:00:00" for h in [10, 11, 12, 13, 14, 15, 16]]


def seconds_until_next_hour() -> int:
    """
    计算距离下一个整点还有多少秒
    
    Returns:
        int: 距离下一个整点的秒数
    """
    now = get_eastern_now()
    next_hour = (now + timedelta(hours=1)).replace(minute=0, second=0, microsecond=0)
    return int((next_hour - now).total_seconds())


def format_eastern_time(dt: Optional[datetime] = None) -> str:
    """
    格式化美东时间为字符串
    
    Args:
        dt: 日期时间，默认为当前时间
        
    Returns:
        str: 格式化的时间字符串
    """
    if dt is None:
        dt = get_eastern_now()
    return dt.strftime("%Y-%m-%d %H:%M:%S ET")


if __name__ == "__main__":
    # 测试代码
    now = get_eastern_now()
    print(f"当前美东时间: {format_eastern_time(now)}")
    print(f"是否是交易日: {is_trading_day(now)}")
    print(f"是否在交易时间: {is_market_hours(now)}")
    print(f"当前交易小时: {get_current_trading_hour(now)}")
    print(f"下一个交易时间: {get_next_trading_time(now)}")
    print(f"今天的交易小时: {get_trading_hours_today(now)}")
    print(f"距离下一整点: {seconds_until_next_hour()} 秒")

