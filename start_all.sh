#!/bin/bash
# AI-Trader 一键启动脚本 (Linux/Mac)
# 使用nohup后台启动，并实时显示日志

set -e  # 遇到错误时退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 项目根目录
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MCP_DIR="$PROJECT_ROOT/agent_tools"
MAIN_SCRIPT="$PROJECT_ROOT/main.py"
LOG_DIR="$PROJECT_ROOT/logs"
PID_DIR="$PROJECT_ROOT/pids"

# 创建必要的目录
mkdir -p "$LOG_DIR"
mkdir -p "$PID_DIR"

# MCP服务端口配置
MATH_PORT=${MATH_HTTP_PORT:-8000}
SEARCH_PORT=${SEARCH_HTTP_PORT:-8001}
TRADE_PORT=${TRADE_HTTP_PORT:-8002}
PRICE_PORT=${GETPRICE_HTTP_PORT:-8003}

# 日志文件
MCP_LOG="$LOG_DIR/mcp_services.log"
MAIN_LOG="$LOG_DIR/main_$(date +%Y%m%d_%H%M%S).log"
MAIN_PID_FILE="$PID_DIR/main.pid"
MCP_PID_FILE="$PID_DIR/mcp.pid"

echo "============================================================"
echo -e "${BLUE}🚀 AI-Trader 一键启动脚本 (Linux/Mac)${NC}"
echo "============================================================"

# 检查端口是否被占用
check_port() {
    local port=$1
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
        return 0  # 端口被占用
    else
        return 1  # 端口未被占用
    fi
}

# 检查进程是否在运行
check_process() {
    local pid_file=$1
    if [ -f "$pid_file" ]; then
        local pid=$(cat "$pid_file")
        if ps -p $pid > /dev/null 2>&1; then
            return 0  # 进程在运行
        else
            rm -f "$pid_file"
            return 1  # 进程未运行
        fi
    else
        return 1  # PID文件不存在
    fi
}

# 检查MCP服务状态
check_mcp_services() {
    echo ""
    echo -e "${BLUE}📊 检查MCP服务状态...${NC}"
    
    local running_count=0
    local total_count=4
    
    if check_port $MATH_PORT; then
        echo -e "${GREEN}✅ Math服务正在运行 (端口: $MATH_PORT)${NC}"
        ((running_count++))
    else
        echo -e "${RED}❌ Math服务未运行 (端口: $MATH_PORT)${NC}"
    fi
    
    if check_port $SEARCH_PORT; then
        echo -e "${GREEN}✅ Search服务正在运行 (端口: $SEARCH_PORT)${NC}"
        ((running_count++))
    else
        echo -e "${RED}❌ Search服务未运行 (端口: $SEARCH_PORT)${NC}"
    fi
    
    if check_port $TRADE_PORT; then
        echo -e "${GREEN}✅ Trade服务正在运行 (端口: $TRADE_PORT)${NC}"
        ((running_count++))
    else
        echo -e "${RED}❌ Trade服务未运行 (端口: $TRADE_PORT)${NC}"
    fi
    
    if check_port $PRICE_PORT; then
        echo -e "${GREEN}✅ Price服务正在运行 (端口: $PRICE_PORT)${NC}"
        ((running_count++))
    else
        echo -e "${RED}❌ Price服务未运行 (端口: $PRICE_PORT)${NC}"
    fi
    
    if [ $running_count -eq $total_count ]; then
        return 0  # 所有服务都在运行
    else
        return 1  # 有服务未运行
    fi
}

# 启动MCP服务
start_mcp_services() {
    echo ""
    echo -e "${YELLOW}🚀 正在启动MCP服务...${NC}"
    
    # 检查是否已经在运行
    if check_process "$MCP_PID_FILE"; then
        echo -e "${GREEN}✅ MCP服务已在运行 (PID: $(cat $MCP_PID_FILE))${NC}"
        return 0
    fi
    
    cd "$MCP_DIR"
    
    # 使用nohup后台启动MCP服务
    nohup python3 start_mcp_services.py > "$MCP_LOG" 2>&1 &
    local mcp_pid=$!
    echo $mcp_pid > "$MCP_PID_FILE"
    
    cd "$PROJECT_ROOT"
    
    echo -e "${GREEN}✅ MCP服务已启动 (PID: $mcp_pid)${NC}"
    echo -e "${BLUE}📝 日志文件: $MCP_LOG${NC}"
    
    # 等待服务启动
    echo -e "${YELLOW}⏳ 等待MCP服务启动...${NC}"
    sleep 5
    
    # 检查服务状态
    if check_mcp_services; then
        echo -e "${GREEN}✅ MCP服务启动成功！${NC}"
        return 0
    else
        echo -e "${YELLOW}⚠️  MCP服务可能未完全启动，请检查日志${NC}"
        return 1
    fi
}

# 检查main.py状态
check_main() {
    echo ""
    echo -e "${BLUE}📊 检查main.py状态...${NC}"
    
    if check_process "$MAIN_PID_FILE"; then
        local pid=$(cat "$MAIN_PID_FILE")
        echo -e "${GREEN}✅ main.py 正在运行 (PID: $pid)${NC}"
        return 0
    else
        echo -e "${RED}❌ main.py 未运行${NC}"
        return 1
    fi
}

# 启动main.py
start_main() {
    echo ""
    echo -e "${YELLOW}🚀 正在启动main.py...${NC}"
    
    # 检查是否已经在运行
    if check_process "$MAIN_PID_FILE"; then
        echo -e "${GREEN}✅ main.py 已在运行 (PID: $(cat $MAIN_PID_FILE))${NC}"
        return 0
    fi
    
    # 构建命令
    local cmd="python3 $MAIN_SCRIPT"
    if [ $# -gt 0 ]; then
        cmd="$cmd $@"
    fi
    
    # 使用nohup后台启动main.py
    cd "$PROJECT_ROOT"
    nohup $cmd > "$MAIN_LOG" 2>&1 &
    local main_pid=$!
    echo $main_pid > "$MAIN_PID_FILE"
    
    echo -e "${GREEN}✅ main.py 已启动 (PID: $main_pid)${NC}"
    echo -e "${BLUE}📝 日志文件: $MAIN_LOG${NC}"
    
    # 等待一下让日志生成
    sleep 2
    
    # 显示日志的最后30行
    if [ -f "$MAIN_LOG" ]; then
        echo ""
        echo -e "${BLUE}📋 显示日志文件最后30行:${NC}"
        echo "============================================================"
        tail -n 30 "$MAIN_LOG"
        echo "============================================================"
        echo ""
        echo -e "${GREEN}💡 提示: 使用以下命令查看实时日志:${NC}"
        echo -e "   ${YELLOW}tail -f $MAIN_LOG${NC}"
    fi
    
    return 0
}

# 主函数
main() {
    # 检查MCP服务
    if ! check_mcp_services; then
        start_mcp_services
    else
        echo -e "${GREEN}✅ MCP服务已在运行${NC}"
    fi
    
    # 等待一下确保MCP服务完全启动
    sleep 2
    
    # 检查main.py
    if ! check_main; then
        start_main "$@"
    else
        echo -e "${GREEN}✅ main.py 已在运行${NC}"
        # 显示最新的日志
        local latest_log=$(ls -t "$LOG_DIR"/main_*.log 2>/dev/null | head -n 1)
        if [ -n "$latest_log" ] && [ -f "$latest_log" ]; then
            echo ""
            echo -e "${BLUE}📋 显示最新日志文件最后30行:${NC}"
            echo "============================================================"
            tail -n 30 "$latest_log"
            echo "============================================================"
            echo ""
            echo -e "${GREEN}💡 提示: 使用以下命令查看实时日志:${NC}"
            echo -e "   ${YELLOW}tail -f $latest_log${NC}"
        fi
    fi
    
    echo ""
    echo "============================================================"
    echo -e "${GREEN}✅ 启动完成！${NC}"
    echo "============================================================"
    echo ""
    echo -e "${BLUE}📁 日志目录: $LOG_DIR${NC}"
    echo -e "${BLUE}📁 PID文件目录: $PID_DIR${NC}"
    echo -e "${GREEN}💡 提示: 所有服务已在后台运行${NC}"
    echo -e "${GREEN}💡 提示: 关闭Terminal后进程会继续运行${NC}"
    echo ""
}

# 运行主函数
main "$@"

