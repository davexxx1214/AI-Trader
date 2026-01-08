#!/bin/bash
#
# Alpaca Live Trading Startup Script
# 启动 Alpaca 实时交易系统
#
# 使用方法:
#   bash scripts/start_alpaca_live_trading.sh [config_path]
#
# 示例:
#   bash scripts/start_alpaca_live_trading.sh
#   bash scripts/start_alpaca_live_trading.sh configs/my_alpaca_config.json
#

set -e

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}============================================${NC}"
echo -e "${BLUE}🚀 AI-Trader Alpaca 实时交易系统${NC}"
echo -e "${BLUE}============================================${NC}"

# 进入项目根目录
cd "$PROJECT_ROOT"

# 检查 Python 环境
if ! command -v python3 &> /dev/null; then
    if ! command -v python &> /dev/null; then
        echo -e "${RED}❌ Python 未安装${NC}"
        exit 1
    fi
    PYTHON_CMD="python"
else
    PYTHON_CMD="python3"
fi

echo -e "${GREEN}✅ 使用 Python: $($PYTHON_CMD --version)${NC}"

# 检查 .env 文件
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}⚠️ .env 文件不存在，请复制 .env.example 并配置 Alpaca API 密钥${NC}"
    echo -e "${YELLOW}   cp .env.example .env${NC}"
    exit 1
fi

# 检查 Alpaca API 密钥
source .env 2>/dev/null || true

if [ -z "$ALPACA_GEMINI_API_KEY" ] && [ -z "$ALPACA_DEEPSEEK_API_KEY" ]; then
    echo -e "${YELLOW}⚠️ 未配置任何 Alpaca API 密钥${NC}"
    echo -e "${YELLOW}   请在 .env 中配置 ALPACA_GEMINI_API_KEY 或 ALPACA_DEEPSEEK_API_KEY${NC}"
fi

# 检查依赖
echo -e "${BLUE}📦 检查依赖...${NC}"
$PYTHON_CMD -c "import alpaca.trading.client" 2>/dev/null || {
    echo -e "${YELLOW}⚠️ alpaca-py 未安装，正在安装...${NC}"
    pip install alpaca-py
}

# 创建日志目录
mkdir -p logs
mkdir -p pids

# 配置文件路径
CONFIG_PATH="${1:-configs/alpaca_live_trading_config.json}"

if [ ! -f "$CONFIG_PATH" ]; then
    echo -e "${RED}❌ 配置文件不存在: $CONFIG_PATH${NC}"
    exit 1
fi

echo -e "${GREEN}✅ 使用配置文件: $CONFIG_PATH${NC}"

# 检查是否已经在运行
PID_FILE="pids/alpaca_live_trader.pid"
if [ -f "$PID_FILE" ]; then
    OLD_PID=$(cat "$PID_FILE")
    if ps -p "$OLD_PID" > /dev/null 2>&1; then
        echo -e "${YELLOW}⚠️ Alpaca 实时交易系统已在运行 (PID: $OLD_PID)${NC}"
        echo -e "${YELLOW}   如需重启，请先运行: bash scripts/stop_alpaca_live_trading.sh${NC}"
        exit 1
    fi
fi

# 启动实时交易系统
echo -e "${BLUE}🚀 启动 Alpaca 实时交易系统...${NC}"

nohup $PYTHON_CMD scripts/start_alpaca_live_trading.py "$CONFIG_PATH" \
    > logs/alpaca_live_trader.log 2>&1 &

PID=$!
echo $PID > "$PID_FILE"

# 等待启动
sleep 3

# 检查是否启动成功
if ps -p $PID > /dev/null 2>&1; then
    echo -e "${GREEN}============================================${NC}"
    echo -e "${GREEN}✅ Alpaca 实时交易系统已启动${NC}"
    echo -e "${GREEN}============================================${NC}"
    echo -e "   PID: $PID"
    echo -e "   日志: logs/alpaca_live_trader.log"
    echo -e "   配置: $CONFIG_PATH"
    echo -e ""
    echo -e "📖 查看日志:"
    echo -e "   tail -f logs/alpaca_live_trader.log"
    echo -e ""
    echo -e "🛑 停止服务:"
    echo -e "   bash scripts/stop_alpaca_live_trading.sh"
else
    echo -e "${RED}❌ 启动失败，请检查日志: logs/alpaca_live_trader.log${NC}"
    cat logs/alpaca_live_trader.log
    exit 1
fi
