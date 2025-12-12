#!/bin/bash

# ============================================
# AI-Trader 实时交易启动脚本
# Live Trading Startup Script
# ============================================
# 用法:
#   bash scripts/start_live_trading.sh              # 使用默认配置
#   bash scripts/start_live_trading.sh config.json  # 使用自定义配置
# ============================================

# 获取项目根目录
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"

cd "$PROJECT_ROOT"

# 解析参数
CONFIG_FILE="${1:-configs/live_trading_config.json}"

# 创建目录
mkdir -p logs
mkdir -p pids

# PID 文件
MCP_PID_FILE="pids/mcp_live.pid"
TRADER_PID_FILE="pids/live_trader.pid"

# 日志文件
MCP_LOG="logs/mcp_live.log"
TRADER_LOG="logs/live_trader.log"

echo "============================================"
echo "🚀 AI-Trader 实时交易系统"
echo "   📄 配置: $CONFIG_FILE"
echo "============================================"

# 检查配置文件是否存在
if [ ! -f "$CONFIG_FILE" ]; then
    echo "❌ 配置文件不存在: $CONFIG_FILE"
    exit 1
fi

# 检查是否已有进程在运行
if [ -f "$MCP_PID_FILE" ] && kill -0 $(cat "$MCP_PID_FILE") 2>/dev/null; then
    echo "⚠️  MCP 服务已在运行 (PID: $(cat $MCP_PID_FILE))"
    echo "   如需重启，请先运行: bash scripts/stop_live_trading.sh"
    exit 1
fi

if [ -f "$TRADER_PID_FILE" ] && kill -0 $(cat "$TRADER_PID_FILE") 2>/dev/null; then
    echo "⚠️  实时交易服务已在运行 (PID: $(cat $TRADER_PID_FILE))"
    echo "   如需重启，请先运行: bash scripts/stop_live_trading.sh"
    exit 1
fi

# ============================================
# 步骤1: 启动 MCP 服务
# ============================================
echo ""
echo "📡 步骤1: 启动 MCP 服务..."
echo "   日志文件: $MCP_LOG"

cd agent_tools
nohup python start_mcp_services.py > "$PROJECT_ROOT/$MCP_LOG" 2>&1 &
MCP_PID=$!
echo $MCP_PID > "$PROJECT_ROOT/$MCP_PID_FILE"
cd "$PROJECT_ROOT"

echo "   ✅ MCP 服务已启动 (PID: $MCP_PID)"

# 等待 MCP 服务启动完成
echo "   ⏳ 等待 MCP 服务启动..."
sleep 15

# 检查 MCP 是否成功启动
if ! kill -0 $MCP_PID 2>/dev/null; then
    echo "   ❌ MCP 服务启动失败，请检查日志: $MCP_LOG"
    cat "$MCP_LOG"
    exit 1
fi

# 检查端口是否可用
if command -v nc &> /dev/null; then
    if nc -z localhost 8000 2>/dev/null; then
        echo "   ✅ MCP 服务运行正常 (端口 8000 已开启)"
    else
        echo "   ⚠️  端口 8000 未响应，MCP 可能仍在启动中..."
    fi
fi

# ============================================
# 步骤2: 启动实时交易调度器
# ============================================
echo ""
echo "🤖 步骤2: 启动实时交易调度器..."
echo "   配置文件: $CONFIG_FILE"
echo "   日志文件: $TRADER_LOG"

nohup python scripts/start_live_trading.py "$CONFIG_FILE" > "$TRADER_LOG" 2>&1 &
TRADER_PID=$!
echo $TRADER_PID > "$TRADER_PID_FILE"

echo "   ✅ 实时交易调度器已启动 (PID: $TRADER_PID)"

# ============================================
# 启动完成
# ============================================
echo ""
echo "============================================"
echo "✅ AI-Trader 实时交易系统启动完成!"
echo "============================================"
echo ""
echo "📈 模式: 实时模拟交易"
echo "📄 配置: $CONFIG_FILE"
echo ""
echo "📋 进程信息:"
echo "   - MCP 服务:      PID $MCP_PID"
echo "   - 实时交易调度:   PID $TRADER_PID"
echo ""
echo "📁 日志文件:"
echo "   - MCP 日志:      $PROJECT_ROOT/$MCP_LOG"
echo "   - 交易日志:      $PROJECT_ROOT/$TRADER_LOG"
echo ""
echo "📖 查看日志命令:"
echo "   tail -f $PROJECT_ROOT/$MCP_LOG       # 查看 MCP 日志"
echo "   tail -f $PROJECT_ROOT/$TRADER_LOG    # 查看交易日志"
echo ""
echo "🛑 停止服务:"
echo "   bash scripts/stop_live_trading.sh"
echo ""
echo "🌐 查看交易结果:"
echo "   打开 data/portfolio.html 或访问 http://localhost:8080"
echo ""

