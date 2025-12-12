#!/bin/bash

# ============================================
# AI-Trader 实时交易停止脚本
# Live Trading Stop Script
# ============================================

# 获取项目根目录
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"

cd "$PROJECT_ROOT"

# PID 文件
MCP_PID_FILE="pids/mcp_live.pid"
TRADER_PID_FILE="pids/live_trader.pid"

echo "============================================"
echo "🛑 AI-Trader 实时交易系统停止脚本"
echo "============================================"

# 停止实时交易调度器
if [ -f "$TRADER_PID_FILE" ]; then
    TRADER_PID=$(cat "$TRADER_PID_FILE")
    if kill -0 $TRADER_PID 2>/dev/null; then
        echo "🔄 正在停止实时交易调度器 (PID: $TRADER_PID)..."
        kill $TRADER_PID 2>/dev/null
        sleep 2
        
        # 如果还在运行，强制停止
        if kill -0 $TRADER_PID 2>/dev/null; then
            echo "   ⚠️  正在强制停止..."
            kill -9 $TRADER_PID 2>/dev/null
        fi
        
        echo "   ✅ 实时交易调度器已停止"
    else
        echo "   ℹ️  实时交易调度器未在运行"
    fi
    rm -f "$TRADER_PID_FILE"
else
    echo "   ℹ️  未找到实时交易调度器 PID 文件"
fi

# 停止 MCP 服务
if [ -f "$MCP_PID_FILE" ]; then
    MCP_PID=$(cat "$MCP_PID_FILE")
    if kill -0 $MCP_PID 2>/dev/null; then
        echo "🔄 正在停止 MCP 服务 (PID: $MCP_PID)..."
        kill $MCP_PID 2>/dev/null
        sleep 2
        
        # 如果还在运行，强制停止
        if kill -0 $MCP_PID 2>/dev/null; then
            echo "   ⚠️  正在强制停止..."
            kill -9 $MCP_PID 2>/dev/null
        fi
        
        echo "   ✅ MCP 服务已停止"
    else
        echo "   ℹ️  MCP 服务未在运行"
    fi
    rm -f "$MCP_PID_FILE"
else
    echo "   ℹ️  未找到 MCP 服务 PID 文件"
fi

# 清理可能残留的 Python 进程（可选）
echo ""
echo "🔍 检查残留进程..."

# 查找并显示相关进程
RELATED_PROCS=$(pgrep -f "start_live_trading.py|start_mcp_services.py" 2>/dev/null)
if [ -n "$RELATED_PROCS" ]; then
    echo "   ⚠️  发现相关残留进程:"
    ps -p $RELATED_PROCS -o pid,cmd 2>/dev/null
    echo ""
    read -p "   是否强制停止这些进程? [y/N] " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo $RELATED_PROCS | xargs kill -9 2>/dev/null
        echo "   ✅ 残留进程已清理"
    fi
else
    echo "   ✅ 无残留进程"
fi

echo ""
echo "============================================"
echo "✅ AI-Trader 实时交易系统已停止"
echo "============================================"

