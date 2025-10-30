#!/bin/bash

# 同步数据到 docs 目录的脚本

echo "🔄 开始同步数据到 docs/data 目录..."

# 创建目标目录
mkdir -p docs/data

# 复制 agent_data 目录
if [ -d "data/agent_data" ]; then
    echo "📁 复制 agent_data 目录..."
    rm -rf docs/data/agent_data
    cp -r data/agent_data docs/data/
    echo "✅ agent_data 目录已同步"
else
    echo "⚠️  data/agent_data 目录不存在"
fi

# 复制股票价格数据文件
echo "📊 复制股票价格数据..."
count=0
for file in data/daily_prices_*.json; do
    if [ -f "$file" ]; then
        cp "$file" docs/data/
        count=$((count + 1))
    fi
done

if [ -f "data/Adaily_prices_QQQ.json" ]; then
    cp data/Adaily_prices_QQQ.json docs/data/
    echo "✅ QQQ 基准数据已同步"
fi

if [ $count -gt 0 ]; then
    echo "✅ 已同步 $count 个股票价格数据文件"
fi

echo "🎉 数据同步完成！"
echo "🌐 现在可以启动 Web 服务器查看可视化界面："
echo "   cd docs"
echo "   python3 -m http.server 8000"

