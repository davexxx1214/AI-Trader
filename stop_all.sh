#!/bin/bash
# AI-Trader 停止脚本
# 停止所有运行中的服务

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 项目根目录
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PID_DIR="$PROJECT_ROOT/pids"
MAIN_PID_FILE="$PID_DIR/main.pid"
MCP_PID_FILE="$PID_DIR/mcp.pid"

echo "============================================================"
echo -e "${BLUE}🛑 AI-Trader 停止脚本${NC}"
echo "============================================================"

# 停止main.py
if [ -f "$MAIN_PID_FILE" ]; then
    pid=$(cat "$MAIN_PID_FILE")
    if ps -p $pid > /dev/null 2>&1; then
        echo -e "${YELLOW}🛑 正在停止 main.py (PID: $pid)...${NC}"
        kill -9 $pid 2>/dev/null || true
        rm -f "$MAIN_PID_FILE"
        echo -e "${GREEN}✅ main.py 已停止${NC}"
    else
        echo -e "${YELLOW}⚠️  main.py 进程不存在 (PID: $pid)${NC}"
        rm -f "$MAIN_PID_FILE"
    fi
else
    echo -e "${YELLOW}⚠️  main.py PID文件不存在，尝试查找进程...${NC}"
    # 尝试通过进程名查找并kill
    pkill -9 -f "python.*main.py" 2>/dev/null && echo -e "${GREEN}✅ 已通过进程名停止 main.py${NC}" || echo -e "${YELLOW}ℹ️  未找到运行中的 main.py 进程${NC}"
fi

# 停止MCP服务
if [ -f "$MCP_PID_FILE" ]; then
    pid=$(cat "$MCP_PID_FILE")
    if ps -p $pid > /dev/null 2>&1; then
        echo -e "${YELLOW}🛑 正在停止 MCP服务 (PID: $pid)...${NC}"
        kill -9 $pid 2>/dev/null || true
        rm -f "$MCP_PID_FILE"
        echo -e "${GREEN}✅ MCP服务已停止${NC}"
    else
        echo -e "${YELLOW}⚠️  MCP服务进程不存在 (PID: $pid)${NC}"
        rm -f "$MCP_PID_FILE"
    fi
else
    echo -e "${YELLOW}⚠️  MCP服务 PID文件不存在，尝试查找进程...${NC}"
    # 尝试通过进程名查找并kill
    pkill -9 -f "python.*start_mcp_services.py" 2>/dev/null && echo -e "${GREEN}✅ 已通过进程名停止 MCP服务${NC}" || echo -e "${YELLOW}ℹ️  未找到运行中的 MCP服务进程${NC}"
fi

echo ""
echo "============================================================"
echo -e "${GREEN}✅ 停止完成！${NC}"
echo "============================================================"

# 显示仍在运行的Python进程（可选）
echo ""
echo -e "${BLUE}📊 检查是否还有相关进程运行:${NC}"
remaining=$(ps aux | grep -E "python.*(main\.py|start_mcp_services)" | grep -v grep || true)
if [ -z "$remaining" ]; then
    echo -e "${GREEN}✅ 没有发现相关进程${NC}"
else
    echo -e "${YELLOW}⚠️  发现以下进程:${NC}"
    echo "$remaining"
fi

