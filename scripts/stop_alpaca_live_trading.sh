#!/bin/bash
#
# Alpaca Live Trading Stop Script
# 停止 Alpaca 实时交易系统（含 Polymarket MCP 服务）
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
echo -e "${BLUE}🛑 停止 Alpaca 实时交易系统${NC}"
echo -e "${BLUE}============================================${NC}"

cd "$PROJECT_ROOT"

PID_FILE="pids/alpaca_live_trader.pid"

# 停止主进程
if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if ps -p "$PID" > /dev/null 2>&1; then
        echo -e "${YELLOW}正在停止主进程 (PID: $PID)...${NC}"
        kill "$PID" 2>/dev/null || true
        
        # 等待进程结束
        for i in {1..10}; do
            if ! ps -p "$PID" > /dev/null 2>&1; then
                break
            fi
            sleep 1
        done
        
        # 强制终止
        if ps -p "$PID" > /dev/null 2>&1; then
            echo -e "${YELLOW}强制终止进程...${NC}"
            kill -9 "$PID" 2>/dev/null || true
        fi
        
        echo -e "${GREEN}✅ 主进程已停止${NC}"
    else
        echo -e "${YELLOW}主进程已不存在${NC}"
    fi
    rm -f "$PID_FILE"
else
    echo -e "${YELLOW}⚠️ PID 文件不存在${NC}"
fi

# 停止所有 MCP 服务
echo -e "${BLUE}停止所有 MCP 服务...${NC}"

# 定义所有 MCP 服务端口
declare -A MCP_SERVICES=(
    ["Math"]="${MATH_HTTP_PORT:-8000}"
    ["Search"]="${SEARCH_HTTP_PORT:-8001}"
    ["LocalPrices"]="${GETPRICE_HTTP_PORT:-8003}"
    ["Alpaca"]="${ALPACA_HTTP_PORT:-8006}"
    ["Polymarket"]="${POLYMARKET_HTTP_PORT:-8007}"
)

STOPPED_COUNT=0

for SERVICE_NAME in "${!MCP_SERVICES[@]}"; do
    PORT="${MCP_SERVICES[$SERVICE_NAME]}"
    PID=$(lsof -t -i:$PORT 2>/dev/null || true)
    
    if [ -n "$PID" ]; then
        echo -e "${YELLOW}正在停止 $SERVICE_NAME MCP 服务 (PID: $PID, 端口: $PORT)...${NC}"
        kill "$PID" 2>/dev/null || true
        sleep 1
        
        # 检查是否需要强制终止
        if ps -p "$PID" > /dev/null 2>&1; then
            kill -9 "$PID" 2>/dev/null || true
        fi
        
        echo -e "${GREEN}✅ $SERVICE_NAME MCP 服务已停止${NC}"
        ((STOPPED_COUNT++))
    else
        echo -e "${YELLOW}⏭️ $SERVICE_NAME MCP 服务未运行 (端口: $PORT)${NC}"
    fi
done

if [ $STOPPED_COUNT -gt 0 ]; then
    echo -e "${GREEN}已停止 $STOPPED_COUNT 个 MCP 服务${NC}"
else
    echo -e "${YELLOW}没有需要停止的 MCP 服务${NC}"
fi

echo -e "${GREEN}============================================${NC}"
echo -e "${GREEN}✅ 所有服务已停止${NC}"
echo -e "${GREEN}============================================${NC}"
