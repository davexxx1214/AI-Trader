#!/bin/bash

# ============================================
# AI-Trader 一键启动脚本 (A股版)
# One-click startup script for A-shares trading
# ============================================

# 获取项目根目录
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"

cd "$PROJECT_ROOT"

# 创建日志目录
mkdir -p logs

# PID 文件
MCP_PID_FILE="logs/mcp.pid"
TRADER_PID_FILE="logs/trader.pid"

# 日志文件
MCP_LOG="logs/mcp_service.log"
TRADER_LOG="logs/trader.log"

echo "============================================"
echo "🚀 AI-Trader 一键启动脚本"
echo "============================================"

# 检查是否已有进程在运行
if [ -f "$MCP_PID_FILE" ] && kill -0 $(cat "$MCP_PID_FILE") 2>/dev/null; then
    echo "⚠️  MCP 服务已在运行 (PID: $(cat $MCP_PID_FILE))"
    echo "   如需重启，请先运行: bash scripts/stop_all.sh"
    exit 1
fi

if [ -f "$TRADER_PID_FILE" ] && kill -0 $(cat "$TRADER_PID_FILE") 2>/dev/null; then
    echo "⚠️  交易代理已在运行 (PID: $(cat $TRADER_PID_FILE))"
    echo "   如需重启，请先运行: bash scripts/stop_all.sh"
    exit 1
fi

# ============================================
# 步骤1: 启动 MCP 服务
# ============================================
echo ""
echo "📡 步骤1: 启动 MCP 服务..."
echo "   日志文件: $MCP_LOG"

nohup bash scripts/main_a_stock_step2.sh > "$MCP_LOG" 2>&1 &
MCP_PID=$!
echo $MCP_PID > "$MCP_PID_FILE"

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
# 步骤2: 启动交易代理
# ============================================
echo ""
echo "🤖 步骤2: 启动交易代理..."
echo "   日志文件: $TRADER_LOG"

nohup bash scripts/main_a_stock_step3.sh > "$TRADER_LOG" 2>&1 &
TRADER_PID=$!
echo $TRADER_PID > "$TRADER_PID_FILE"

echo "   ✅ 交易代理已启动 (PID: $TRADER_PID)"

# ============================================
# 启动完成
# ============================================
echo ""
echo "============================================"
echo "✅ AI-Trader 启动完成!"
echo "============================================"
echo ""
echo "📋 进程信息:"
echo "   - MCP 服务:  PID $MCP_PID"
echo "   - 交易代理:  PID $TRADER_PID"
echo ""
echo "📁 日志文件:"
echo "   - MCP 日志:    $PROJECT_ROOT/$MCP_LOG"
echo "   - 交易日志:    $PROJECT_ROOT/$TRADER_LOG"
echo ""
echo "📖 查看日志命令:"
echo "   tail -f $PROJECT_ROOT/$MCP_LOG      # 查看 MCP 日志"
echo "   tail -f $PROJECT_ROOT/$TRADER_LOG   # 查看交易日志"
echo ""
echo "🛑 停止服务:"
echo "   bash scripts/stop_all.sh"
echo ""

