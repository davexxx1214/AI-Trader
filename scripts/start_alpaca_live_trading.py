#!/usr/bin/env python3
"""
Alpaca Live Trading Scheduler - Alpaca 实时交易调度器

功能：
1. 在美股交易时间内，每小时执行一次交易决策
2. 使用 Alpaca Paper Trading API 执行真实下单
3. 支持多账户（每个 AI 模型一个 Alpaca 账户）
4. 自动拉取实时数据并更新 merged.jsonl

使用方法：
    python scripts/start_alpaca_live_trading.py [config_path]
    
    默认配置文件: configs/alpaca_live_trading_config.json
"""

import asyncio
import json
import os
import re
import signal
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

# 将项目根目录加入 Python 路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from dotenv import load_dotenv
load_dotenv()

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from tools.trading_calendar import (
    get_eastern_now,
    is_trading_day,
    is_market_hours,
    get_current_trading_hour,
    get_next_trading_time,
    format_eastern_time,
    seconds_until_next_hour,
    US_EASTERN,
)
from tools.general_tools import write_config_value, get_config_value

# 全局变量
scheduler: Optional[AsyncIOScheduler] = None
current_config: Optional[dict] = None
is_running = True
alpaca_mcp_process: Optional[subprocess.Popen] = None
mcp_processes: dict = {}  # 存储所有 MCP 服务进程


def resolve_env_variables(config: dict) -> dict:
    """
    解析配置中的环境变量占位符 ${VAR_NAME}
    
    Args:
        config: 原始配置字典
        
    Returns:
        解析后的配置字典
    """
    def resolve_value(value):
        if isinstance(value, str):
            # 匹配 ${VAR_NAME} 格式
            pattern = r'\$\{([^}]+)\}'
            matches = re.findall(pattern, value)
            for var_name in matches:
                env_value = os.getenv(var_name, "")
                value = value.replace(f"${{{var_name}}}", env_value)
            return value
        elif isinstance(value, dict):
            return {k: resolve_value(v) for k, v in value.items()}
        elif isinstance(value, list):
            return [resolve_value(item) for item in value]
        return value
    
    return resolve_value(config)


def load_config(config_path: Optional[str] = None) -> dict:
    """
    加载配置文件并解析环境变量
    
    Args:
        config_path: 配置文件路径，默认为 configs/alpaca_live_trading_config.json
        
    Returns:
        配置字典
    """
    if config_path is None:
        config_path = os.path.join(project_root, "configs", "alpaca_live_trading_config.json")
    
    config_path = Path(config_path)
    if not config_path.exists():
        print(f"❌ 配置文件不存在: {config_path}")
        sys.exit(1)
    
    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)
    
    # 解析环境变量
    config = resolve_env_variables(config)
    
    print(f"✅ 加载配置文件: {config_path}")
    return config


def is_port_available(port: int) -> bool:
    """检查端口是否可用"""
    import socket
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        result = sock.connect_ex(("localhost", port))
        sock.close()
        return result != 0  # 连接失败表示端口可用
    except:
        return False


def check_service_health(port: int) -> bool:
    """检查服务是否健康（端口是否响应）"""
    import socket
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        result = sock.connect_ex(("localhost", port))
        sock.close()
        return result == 0
    except:
        return False


def start_mcp_service(service_name: str, script_name: str, port: int, log_name: str) -> tuple:
    """
    启动单个 MCP 服务
    
    Args:
        service_name: 服务显示名称
        script_name: 脚本文件名
        port: 端口号
        log_name: 日志文件名
        
    Returns:
        tuple: (进程对象, 日志文件句柄) 或 (None, None)
    """
    script_path = os.path.join(project_root, "agent_tools", script_name)
    
    if not os.path.exists(script_path):
        print(f"  ❌ {service_name} 脚本不存在: {script_path}")
        return None, None
    
    # 检查端口是否已被占用（可能服务已在运行）
    if check_service_health(port):
        print(f"  ✅ {service_name} 服务已在运行 (端口: {port})")
        return None, None  # 返回 None 但不是错误，服务已在运行
    
    log_dir = Path(project_root) / "logs"
    log_dir.mkdir(exist_ok=True)
    log_file = log_dir / log_name
    
    # 打开日志文件（保持打开状态，不使用 with）
    log_handle = open(log_file, "w")
    
    process = subprocess.Popen(
        [sys.executable, script_path],
        stdout=log_handle,
        stderr=subprocess.STDOUT,
        cwd=project_root
    )
    
    return process, log_handle


def start_all_mcp_services() -> dict:
    """
    启动所有必需的 MCP 服务
    
    Returns:
        dict: 服务名称到进程的映射
    """
    global mcp_processes
    
    # 定义需要启动的服务
    services = [
        {
            "name": "Math",
            "script": "tool_math.py",
            "port": int(os.getenv("MATH_HTTP_PORT", "8000")),
            "log": "math_mcp.log",
            "key": "math"
        },
        {
            "name": "Search",
            "script": "tool_alphavantage_news.py",
            "port": int(os.getenv("SEARCH_HTTP_PORT", "8001")),
            "log": "search_mcp.log",
            "key": "search"
        },
        {
            "name": "LocalPrices",
            "script": "tool_get_price_local.py",
            "port": int(os.getenv("GETPRICE_HTTP_PORT", "8003")),
            "log": "price_mcp.log",
            "key": "price"
        },
        {
            "name": "Alpaca",
            "script": "tool_alpaca_trade.py",
            "port": int(os.getenv("ALPACA_HTTP_PORT", "8006")),
            "log": "alpaca_mcp.log",
            "key": "alpaca"
        },
    ]
    
    print("🚀 启动 MCP 服务...")
    
    for svc in services:
        print(f"  🔄 启动 {svc['name']} MCP 服务 (端口: {svc['port']})...")
        process, log_handle = start_mcp_service(svc["name"], svc["script"], svc["port"], svc["log"])
        if process:
            mcp_processes[svc["key"]] = {
                "process": process,
                "name": svc["name"],
                "port": svc["port"],
                "log_handle": log_handle
            }
    
    # 等待服务启动（带重试检查）
    print("  ⏳ 等待服务启动...")
    max_wait = 30  # 最多等待 30 秒
    check_interval = 2  # 每 2 秒检查一次
    
    for wait_time in range(0, max_wait, check_interval):
        time.sleep(check_interval)
        
        # 检查所有服务是否都已启动
        all_ready = True
        for svc in services:
            if not check_service_health(svc["port"]):
                all_ready = False
                break
        
        if all_ready:
            print(f"  ✅ 所有服务已在 {wait_time + check_interval} 秒内启动")
            break
        
        if wait_time + check_interval >= max_wait:
            print(f"  ⚠️ 等待超时 ({max_wait}秒)")
    
    # 检查服务状态
    print("  🔍 检查服务状态...")
    all_healthy = True
    for svc in services:
        if check_service_health(svc["port"]):
            print(f"  ✅ {svc['name']} 服务运行正常 (端口: {svc['port']})")
        else:
            # 检查进程是否还在运行
            key = svc["key"]
            if key in mcp_processes:
                proc = mcp_processes[key].get("process")
                if proc and proc.poll() is not None:
                    print(f"  ❌ {svc['name']} 进程已退出 (端口: {svc['port']})，请检查日志: logs/{svc['log']}")
                else:
                    print(f"  ❌ {svc['name']} 服务未响应 (端口: {svc['port']})")
            else:
                print(f"  ❌ {svc['name']} 服务启动失败 (端口: {svc['port']})")
            all_healthy = False
    
    if not all_healthy:
        print("  ⚠️ 部分 MCP 服务启动失败，请检查 logs/ 目录下的日志文件")
    
    return mcp_processes


def stop_all_mcp_services():
    """停止本脚本启动的 MCP 服务"""
    global mcp_processes
    
    if not mcp_processes:
        return
    
    print("🛑 停止本脚本启动的 MCP 服务...")
    
    for key, svc in mcp_processes.items():
        process = svc.get("process")
        name = svc.get("name", key)
        port = svc.get("port", "?")
        log_handle = svc.get("log_handle")
        
        if process and process.poll() is None:
            try:
                process.terminate()
                process.wait(timeout=5)
                print(f"  ✅ {name} 服务已停止 (端口: {port})")
            except subprocess.TimeoutExpired:
                process.kill()
                print(f"  🔨 {name} 服务已强制停止 (端口: {port})")
            except Exception as e:
                print(f"  ❌ 停止 {name} 服务时出错: {e}")
        
        # 关闭日志文件句柄
        if log_handle:
            try:
                log_handle.close()
            except:
                pass
    
    mcp_processes.clear()
    print("💡 如需停止所有 MCP 服务，请运行: ./scripts/stop_alpaca_live_trading.sh")


def start_alpaca_mcp_service() -> Optional[subprocess.Popen]:
    """
    启动 Alpaca MCP 服务（兼容旧代码）
    
    Returns:
        服务进程对象
    """
    alpaca_script = os.path.join(project_root, "agent_tools", "tool_alpaca_trade.py")
    
    if not os.path.exists(alpaca_script):
        print(f"❌ Alpaca MCP 脚本不存在: {alpaca_script}")
        return None
    
    port = int(os.getenv("ALPACA_HTTP_PORT", "8006"))
    print(f"🚀 启动 Alpaca MCP 服务 (端口: {port})...")
    
    log_dir = Path(project_root) / "logs"
    log_dir.mkdir(exist_ok=True)
    log_file = log_dir / "alpaca_mcp.log"
    
    with open(log_file, "w") as f:
        process = subprocess.Popen(
            [sys.executable, alpaca_script],
            stdout=f,
            stderr=subprocess.STDOUT,
            cwd=project_root
        )
    
    # 等待服务启动
    time.sleep(3)
    
    if process.poll() is None:
        print(f"✅ Alpaca MCP 服务已启动 (PID: {process.pid})")
        return process
    else:
        print(f"❌ Alpaca MCP 服务启动失败，请检查日志: {log_file}")
        return None


def stop_alpaca_mcp_service(process: Optional[subprocess.Popen]):
    """停止 Alpaca MCP 服务"""
    if process and process.poll() is None:
        print("🛑 停止 Alpaca MCP 服务...")
        process.terminate()
        try:
            process.wait(timeout=5)
            print("✅ Alpaca MCP 服务已停止")
        except subprocess.TimeoutExpired:
            process.kill()
            print("🔨 Alpaca MCP 服务已强制停止")


def validate_alpaca_credentials(model_config: dict) -> bool:
    """
    验证 Alpaca API 凭证
    
    Args:
        model_config: 模型配置
        
    Returns:
        凭证是否有效
    """
    api_key = model_config.get("alpaca_api_key", "")
    secret_key = model_config.get("alpaca_secret_key", "")
    
    if not api_key or not secret_key:
        return False
    
    # 检查是否是占位符
    if api_key.startswith("your_") or secret_key.startswith("your_"):
        return False
    
    # 尝试连接 Alpaca API
    try:
        from alpaca.trading.client import TradingClient
        client = TradingClient(api_key, secret_key, paper=True)
        account = client.get_account()
        print(f"  ✅ Alpaca 账户验证成功: ${float(account.portfolio_value):,.2f}")
        return True
    except Exception as e:
        print(f"  ❌ Alpaca 账户验证失败: {e}")
        return False


def fetch_alpaca_account_snapshot(api_key: str, secret_key: str) -> Optional[dict]:
    """
    获取 Alpaca 账户实时信息（余额与持仓）

    Returns:
        dict 包含 account 与 positions，失败返回 None
    """
    try:
        from alpaca.trading.client import TradingClient
        client = TradingClient(api_key, secret_key, paper=True)
        account = client.get_account()
        positions = client.get_all_positions()
        return {"account": account, "positions": positions}
    except Exception as e:
        print(f"  ❌ 获取 Alpaca 账户信息失败: {e}")
        return None


def print_alpaca_account_snapshot(snapshot: dict, model_name: Optional[str] = None) -> float:
    """
    打印 Alpaca 账户余额与持仓，返回现金余额
    """
    if model_name:
        print(f"📌 账户快照 ({model_name})")
    account = snapshot["account"]
    positions = snapshot["positions"]
    cash = float(getattr(account, "cash", 0.0))
    portfolio_value = float(getattr(account, "portfolio_value", cash))
    print(f"💰 账户余额: ${cash:,.2f} | 账户总值: ${portfolio_value:,.2f}")
    if positions:
        print(f"📦 当前持仓数量: {len(positions)}")
        for pos in positions:
            symbol = getattr(pos, "symbol", "UNKNOWN")
            qty = getattr(pos, "qty", "0")
            market_value = getattr(pos, "market_value", "0")
            unrealized_pl = getattr(pos, "unrealized_pl", "0")
            print(f"  - {symbol}: {qty} 股, 市值 ${market_value}, 浮盈亏 ${unrealized_pl}")
    else:
        print("📦 当前无持仓")
    return cash


async def fetch_live_data() -> bool:
    """
    获取实时数据
    
    Returns:
        是否成功
    """
    print(f"📡 开始获取实时数据 - {format_eastern_time()}")
    
    try:
        # 导入并执行数据获取
        sys.path.insert(0, os.path.join(project_root, "data"))
        from get_live_price import fetch_and_merge
        
        success = fetch_and_merge()
        
        if success:
            print("✅ 实时数据获取完成")
        else:
            print("⚠️ 部分数据获取失败")
        
        return success
        
    except Exception as e:
        print(f"❌ 实时数据获取异常: {e}")
        return False


def get_alpaca_mcp_config() -> dict:
    """
    获取 Alpaca 交易专用的 MCP 配置
    将 trade 服务指向 Alpaca MCP 端口
    """
    return {
        "math": {
            "transport": "streamable_http",
            "url": f"http://localhost:{os.getenv('MATH_HTTP_PORT', '8000')}/mcp",
        },
        "stock_local": {
            "transport": "streamable_http",
            "url": f"http://localhost:{os.getenv('GETPRICE_HTTP_PORT', '8003')}/mcp",
        },
        "search": {
            "transport": "streamable_http",
            "url": f"http://localhost:{os.getenv('SEARCH_HTTP_PORT', '8001')}/mcp",
        },
        # 关键：使用 Alpaca 交易服务而不是默认的模拟交易服务
        "trade": {
            "transport": "streamable_http",
            "url": f"http://localhost:{os.getenv('ALPACA_HTTP_PORT', '8006')}/mcp",
        },
    }


async def run_trading_decision(config: dict) -> bool:
    """
    执行交易决策
    
    Args:
        config: 配置字典
        
    Returns:
        是否成功
    """
    from agent.base_agent.live_agent_hour import LiveAgent_Hour
    
    # 获取启用的模型
    enabled_models = [m for m in config["models"] if m.get("enabled", True)]
    
    if not enabled_models:
        print("⚠️ 没有启用的模型")
        return False
    
    agent_config = config.get("agent_config", {})
    log_config = config.get("log_config", {})
    log_path = log_config.get("log_path", "./data/agent_data_alpaca")
    
    success = True
    
    for model_config in enabled_models:
        model_name = model_config.get("name", "unknown")
        basemodel = model_config.get("basemodel")
        signature = model_config.get("signature")
        openai_base_url = model_config.get("openai_base_url")
        openai_api_key = model_config.get("openai_api_key")
        
        # Alpaca credentials
        alpaca_api_key = model_config.get("alpaca_api_key", "")
        alpaca_secret_key = model_config.get("alpaca_secret_key", "")
        
        if not basemodel or not signature:
            print(f"⚠️ 模型 {model_name} 配置不完整，跳过")
            continue
        
        # 验证 Alpaca 凭证
        if not alpaca_api_key or not alpaca_secret_key:
            print(f"⚠️ 模型 {model_name} 缺少 Alpaca API 凭证，跳过")
            continue
        
        print(f"\n{'='*50}")
        print(f"🤖 使用模型: {model_name} ({signature})")
        print(f"🦙 使用 Alpaca Paper Trading API")
        print(f"{'='*50}")
        
        # 设置运行时配置（包括 Alpaca 凭证）
        write_config_value("SIGNATURE", signature)
        write_config_value("IF_TRADE", False)
        write_config_value("MARKET", "us")
        write_config_value("LOG_PATH", log_path)
        write_config_value("ALPACA_API_KEY", alpaca_api_key)
        write_config_value("ALPACA_SECRET_KEY", alpaca_secret_key)

        # 拉取账户实时余额和持仓，用于初始化资金
        snapshot = fetch_alpaca_account_snapshot(alpaca_api_key, alpaca_secret_key)
        if snapshot:
            cash = print_alpaca_account_snapshot(snapshot, model_name=model_name)
            initial_cash = cash
            write_config_value("INITIAL_CASH", cash)
        else:
            initial_cash = agent_config.get("initial_cash", 10000.0)
            print(f"⚠️ 使用配置初始资金: ${float(initial_cash):,.2f}")
            write_config_value("INITIAL_CASH", initial_cash)
        
        try:
            # 创建 Agent 实例，使用 Alpaca MCP 配置
            agent = LiveAgent_Hour(
                signature=signature,
                basemodel=basemodel,
                log_path=log_path,
                max_steps=agent_config.get("max_steps", 30),
                max_retries=agent_config.get("max_retries", 3),
                base_delay=agent_config.get("base_delay", 1.0),
                recursion_limit=agent_config.get("recursion_limit", 300),
                initial_cash=initial_cash,
                init_date=get_eastern_now().strftime("%Y-%m-%d %H:00:00"),
                openai_base_url=openai_base_url,
                openai_api_key=openai_api_key,
                mcp_config=get_alpaca_mcp_config(),  # 使用 Alpaca MCP 配置
            )
            
            # 初始化
            await agent.initialize()
            
            # 执行实时交易
            result = await agent.run_live()
            
            if not result:
                print(f"📊 模型 {model_name} 当前无交易")
            
        except Exception as e:
            print(f"❌ 模型 {model_name} 交易执行失败: {e}")
            import traceback
            traceback.print_exc()
            success = False
    
    return success


async def trading_job():
    """
    交易任务 - 每小时执行一次
    """
    global current_config
    
    now = get_eastern_now()
    print("\n" + "=" * 60)
    print(f"⏰ Alpaca 交易任务触发 - {format_eastern_time(now)}")
    print("=" * 60)
    
    # 检查是否在交易时间
    if not is_trading_day(now):
        print(f"📅 今天不是交易日，跳过")
        return
    
    if not is_market_hours(now):
        print(f"⏰ 当前不在交易时间，跳过")
        return
    
    current_hour = get_current_trading_hour(now)
    if current_hour is None:
        print(f"⏰ 当前小时不是有效交易小时，跳过")
        return
    
    print(f"📊 当前交易时间点: {current_hour}")
    
    # 1. 获取实时数据
    live_config = current_config.get("live_config", {})
    if live_config.get("auto_fetch_data", True):
        await fetch_live_data()
    
    # 2. 执行交易决策
    await run_trading_decision(current_config)
    
    # 3. 显示下次执行时间
    next_time, next_str = get_next_trading_time(now)
    print(f"\n⏭️ 下次交易时间: {next_str}")
    print("=" * 60 + "\n")


def signal_handler(signum, frame):
    """信号处理函数"""
    global is_running, scheduler, alpaca_mcp_process
    print("\n🛑 收到停止信号，正在关闭...")
    is_running = False
    if scheduler:
        scheduler.shutdown(wait=False)
    stop_all_mcp_services()  # 停止所有 MCP 服务


async def main(config_path: Optional[str] = None):
    """
    主函数
    
    Args:
        config_path: 配置文件路径
    """
    global scheduler, current_config, is_running, alpaca_mcp_process
    
    print("=" * 60)
    print("🚀 AI-Trader Alpaca 实时交易系统")
    print("=" * 60)
    
    # 注册信号处理
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # 加载配置
    current_config = load_config(config_path)
    
    # 启动所有必需的 MCP 服务（包括 math, search, price, alpaca）
    start_all_mcp_services()
    
    # 检查 Alpaca MCP 服务是否运行
    alpaca_port = int(os.getenv("ALPACA_HTTP_PORT", "8006"))
    if not check_service_health(alpaca_port):
        print("❌ Alpaca MCP 服务未能启动，退出")
        stop_all_mcp_services()
        sys.exit(1)
    
    # 验证 Alpaca 凭证
    print("\n🔑 验证 Alpaca API 凭证...")
    enabled_models = [m for m in current_config.get("models", []) if m.get("enabled", True)]
    valid_models = []
    model_cash = {}
    
    for model in enabled_models:
        model_name = model.get("name", "unknown")
        print(f"\n检查模型: {model_name}")
        if validate_alpaca_credentials(model):
            valid_models.append(model_name)
            # 启动时拉取账户余额与持仓（即便非交易时间）
            snapshot = fetch_alpaca_account_snapshot(
                model.get("alpaca_api_key", ""),
                model.get("alpaca_secret_key", "")
            )
            if snapshot:
                cash = print_alpaca_account_snapshot(snapshot, model_name=model_name)
                model_cash[model_name] = cash
        else:
            print(f"  ⚠️ 跳过模型 {model_name} (凭证无效)")
    
    if not valid_models:
        print("\n❌ 没有可用的 Alpaca 账户，请检查 .env 配置")
        stop_alpaca_mcp_service(alpaca_mcp_process)
        sys.exit(1)
    
    # 显示配置信息
    live_config = current_config.get("live_config", {})
    
    print(f"\n📈 市场: 美股 (US) - Alpaca Paper Trading")
    print(f"⏰ 交易时间: {live_config.get('market_open', '09:30')} - {live_config.get('market_close', '16:00')} ET")
    print(f"📊 交易小时: {live_config.get('trading_hours', [10, 11, 12, 13, 14, 15, 16])}")
    print(f"🤖 有效模型: {valid_models}")
    if model_cash:
        for name, cash in model_cash.items():
            print(f"💰 初始资金({name}): ${float(cash):,.2f}")
    else:
        print(f"💰 初始资金: ${current_config.get('agent_config', {}).get('initial_cash', 10000.0):,.2f}")
    print()
    
    # 创建调度器
    scheduler = AsyncIOScheduler(timezone=US_EASTERN)
    
    # 添加每小时整点执行的任务
    trading_hours = live_config.get("trading_hours", [10, 11, 12, 13, 14, 15, 16])
    
    # 使用 cron 触发器，在指定小时的第 5 分钟执行
    scheduler.add_job(
        trading_job,
        CronTrigger(
            hour=",".join(map(str, trading_hours)),
            minute=5,
            timezone=US_EASTERN,
        ),
        id="alpaca_trading_job",
        name="Alpaca 实时交易任务",
        replace_existing=True,
    )
    
    # 启动调度器
    scheduler.start()
    
    now = get_eastern_now()
    print(f"✅ 调度器已启动 - 当前美东时间: {format_eastern_time(now)}")
    
    # 检查当前状态
    if is_trading_day(now):
        if is_market_hours(now):
            print(f"📈 当前在交易时间内")
            current_hour = get_current_trading_hour(now)
            if current_hour:
                print(f"🚀 立即执行首次交易任务...")
                await trading_job()
        else:
            next_time, next_str = get_next_trading_time(now)
            print(f"⏰ 当前不在交易时间，下次交易: {next_str}")
    else:
        next_time, next_str = get_next_trading_time(now)
        print(f"📅 今天不是交易日，下次交易: {next_str}")
    
    print("\n💡 按 Ctrl+C 停止服务")
    print("=" * 60 + "\n")
    
    # 保持运行
    try:
        while is_running:
            await asyncio.sleep(1)
    except (KeyboardInterrupt, SystemExit):
        pass
    finally:
        stop_all_mcp_services()  # 停止所有 MCP 服务
        print("\n🛑 Alpaca 实时交易系统已停止")


if __name__ == "__main__":
    # 支持命令行指定配置文件
    config_path = sys.argv[1] if len(sys.argv) > 1 else None
    
    try:
        asyncio.run(main(config_path))
    except KeyboardInterrupt:
        print("\n🛑 用户中断")
    except Exception as e:
        print(f"❌ 程序异常: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
