#!/bin/bash

# ============================================
# AI-Trader 状态查看脚本
# Status check script
# ============================================

# 获取项目根目录
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"

cd "$PROJECT_ROOT"

# PID 文件
MCP_PID_FILE="logs/mcp.pid"
TRADER_PID_FILE="logs/trader.pid"

echo "============================================"
echo "📊 AI-Trader 运行状态"
echo "============================================"

# ============================================
# MCP 服务状态
# ============================================
echo ""
echo "📡 MCP 服务:"

if [ -f "$MCP_PID_FILE" ]; then
    MCP_PID=$(cat "$MCP_PID_FILE")
    if kill -0 $MCP_PID 2>/dev/null; then
        echo "   ✅ 运行中 (PID: $MCP_PID)"
    else
        echo "   ❌ 已停止 (PID 文件存在但进程不存在)"
    fi
else
    echo "   ❌ 未运行"
fi

# 检查 MCP 端口
echo ""
echo "   端口状态:"
for port in 8000 8001 8002 8003 8005; do
    if command -v nc &> /dev/null; then
        if nc -z localhost $port 2>/dev/null; then
            echo "      ✅ 端口 $port: 已开启"
        else
            echo "      ❌ 端口 $port: 未开启"
        fi
    elif command -v ss &> /dev/null; then
        if ss -tuln | grep -q ":$port "; then
            echo "      ✅ 端口 $port: 已开启"
        else
            echo "      ❌ 端口 $port: 未开启"
        fi
    fi
done

# ============================================
# 交易代理状态
# ============================================
echo ""
echo "🤖 交易代理:"

if [ -f "$TRADER_PID_FILE" ]; then
    TRADER_PID=$(cat "$TRADER_PID_FILE")
    if kill -0 $TRADER_PID 2>/dev/null; then
        echo "   ✅ 运行中 (PID: $TRADER_PID)"
    else
        echo "   ❌ 已停止 (PID 文件存在但进程不存在)"
    fi
else
    echo "   ❌ 未运行"
fi

# ============================================
# 相关进程
# ============================================
echo ""
echo "📋 相关进程:"
PROCESSES=$(ps aux | grep -E "tool_math|tool_alphavantage|tool_trade|tool_get_price|tool_crypto|main.py|start_mcp" | grep -v grep)

if [ -n "$PROCESSES" ]; then
    echo "$PROCESSES" | awk '{printf "   PID: %-8s CMD: %s\n", $2, $11" "$12" "$13}'
else
    echo "   无相关进程在运行"
fi

# ============================================
# 日志文件
# ============================================
echo ""
echo "📁 日志文件:"
echo "   - MCP 日志:    $PROJECT_ROOT/logs/mcp_service.log"
echo "   - 交易日志:    $PROJECT_ROOT/logs/trader.log"

echo ""
echo "📖 查看日志命令:"
echo "   tail -f logs/mcp_service.log   # 查看 MCP 日志"
echo "   tail -f logs/trader.log        # 查看交易日志"
echo "   tail -f logs/*.log             # 查看所有日志"
echo ""

