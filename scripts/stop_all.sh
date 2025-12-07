#!/bin/bash

# ============================================
# AI-Trader 一键停止脚本
# One-click stop script
# ============================================

# 获取项目根目录
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"

cd "$PROJECT_ROOT"

# PID 文件
MCP_PID_FILE="logs/mcp.pid"
TRADER_PID_FILE="logs/trader.pid"

echo "============================================"
echo "🛑 AI-Trader 一键停止脚本"
echo "============================================"

STOPPED_COUNT=0

# ============================================
# 停止交易代理
# ============================================
echo ""
echo "🤖 停止交易代理..."

if [ -f "$TRADER_PID_FILE" ]; then
    TRADER_PID=$(cat "$TRADER_PID_FILE")
    if kill -0 $TRADER_PID 2>/dev/null; then
        kill $TRADER_PID 2>/dev/null
        sleep 2
        # 如果还没停止，强制杀死
        if kill -0 $TRADER_PID 2>/dev/null; then
            kill -9 $TRADER_PID 2>/dev/null
        fi
        echo "   ✅ 交易代理已停止 (PID: $TRADER_PID)"
        STOPPED_COUNT=$((STOPPED_COUNT + 1))
    else
        echo "   ℹ️  交易代理未在运行"
    fi
    rm -f "$TRADER_PID_FILE"
else
    echo "   ℹ️  未找到交易代理 PID 文件"
fi

# ============================================
# 停止 MCP 服务
# ============================================
echo ""
echo "📡 停止 MCP 服务..."

if [ -f "$MCP_PID_FILE" ]; then
    MCP_PID=$(cat "$MCP_PID_FILE")
    if kill -0 $MCP_PID 2>/dev/null; then
        kill $MCP_PID 2>/dev/null
        sleep 2
        # 如果还没停止，强制杀死
        if kill -0 $MCP_PID 2>/dev/null; then
            kill -9 $MCP_PID 2>/dev/null
        fi
        echo "   ✅ MCP 服务已停止 (PID: $MCP_PID)"
        STOPPED_COUNT=$((STOPPED_COUNT + 1))
    else
        echo "   ℹ️  MCP 服务未在运行"
    fi
    rm -f "$MCP_PID_FILE"
else
    echo "   ℹ️  未找到 MCP PID 文件"
fi

# ============================================
# 清理残留的 Python 进程 (MCP 子进程)
# ============================================
echo ""
echo "🧹 清理残留进程..."

# 查找并杀死 MCP 相关的 Python 进程
MCP_PROCESSES=$(ps aux | grep -E "tool_math|tool_alphavantage|tool_trade|tool_get_price|tool_crypto" | grep -v grep | awk '{print $2}')

if [ -n "$MCP_PROCESSES" ]; then
    echo "$MCP_PROCESSES" | xargs kill 2>/dev/null
    sleep 1
    echo "   ✅ 已清理 MCP 子进程"
else
    echo "   ℹ️  无残留 MCP 子进程"
fi

# 查找 main.py 进程
MAIN_PROCESSES=$(ps aux | grep "python main.py" | grep -v grep | awk '{print $2}')

if [ -n "$MAIN_PROCESSES" ]; then
    echo "$MAIN_PROCESSES" | xargs kill 2>/dev/null
    sleep 1
    echo "   ✅ 已清理 main.py 进程"
else
    echo "   ℹ️  无残留 main.py 进程"
fi

# ============================================
# 完成
# ============================================
echo ""
echo "============================================"
echo "✅ AI-Trader 已停止"
echo "============================================"
echo ""

# 显示当前状态
echo "📋 当前状态检查:"
RUNNING_PROCESSES=$(ps aux | grep -E "tool_math|tool_alphavantage|tool_trade|tool_get_price|tool_crypto|main.py" | grep -v grep | wc -l)

if [ "$RUNNING_PROCESSES" -eq 0 ]; then
    echo "   ✅ 所有 AI-Trader 相关进程已停止"
else
    echo "   ⚠️  仍有 $RUNNING_PROCESSES 个相关进程在运行:"
    ps aux | grep -E "tool_math|tool_alphavantage|tool_trade|tool_get_price|tool_crypto|main.py" | grep -v grep
fi
echo ""

