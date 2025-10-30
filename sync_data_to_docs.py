#!/usr/bin/env python3
"""
将交易数据同步到 docs/data 目录，用于可视化界面展示
"""

import os
import shutil
from pathlib import Path

def sync_data_to_docs():
    """将 data 目录下的数据同步到 docs/data 目录"""
    
    # 定义源目录和目标目录
    source_data_dir = Path("data")
    target_data_dir = Path("docs/data")
    
    # 创建目标目录
    target_data_dir.mkdir(parents=True, exist_ok=True)
    
    print("🔄 开始同步数据到 docs/data 目录...")
    
    # 1. 同步 agent_data 目录
    source_agent_data = source_data_dir / "agent_data"
    target_agent_data = target_data_dir / "agent_data"
    
    if source_agent_data.exists():
        if target_agent_data.exists():
            shutil.rmtree(target_agent_data)
        shutil.copytree(source_agent_data, target_agent_data)
        print(f"✅ 已同步 agent_data 目录")
    else:
        print(f"⚠️  源目录不存在: {source_agent_data}")
    
    # 2. 同步股票价格数据文件
    price_files = list(source_data_dir.glob("daily_prices_*.json"))
    qqq_file = source_data_dir / "Adaily_prices_QQQ.json"
    
    copied_count = 0
    for price_file in price_files:
        target_file = target_data_dir / price_file.name
        shutil.copy2(price_file, target_file)
        copied_count += 1
    
    if qqq_file.exists():
        target_qqq = target_data_dir / qqq_file.name
        shutil.copy2(qqq_file, target_qqq)
        print(f"✅ 已同步 QQQ 基准数据")
    
    if copied_count > 0:
        print(f"✅ 已同步 {copied_count} 个股票价格数据文件")
    
    print(f"🎉 数据同步完成！")
    print(f"📁 数据位置: {target_data_dir.absolute()}")
    print(f"🌐 现在可以启动 Web 服务器查看可视化界面：")
    print(f"   cd docs")
    print(f"   python -m http.server 8000")

if __name__ == "__main__":
    sync_data_to_docs()

