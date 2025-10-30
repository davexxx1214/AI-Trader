#!/usr/bin/env python3
"""
将交易数据同步到 docs/data 目录，用于可视化界面展示
"""

import os
import shutil
from pathlib import Path

def is_same_file(path1, path2):
    """检查两个路径是否指向同一个文件（处理符号链接）"""
    try:
        return os.path.samefile(path1, path2)
    except (OSError, FileNotFoundError):
        return False

def sync_data_to_docs():
    """将 data 目录下的数据同步到 docs/data 目录"""
    
    # 使用绝对路径避免路径混淆
    project_root = Path(__file__).parent.absolute()
    source_data_dir = project_root / "data"
    target_data_dir = project_root / "docs" / "data"
    
    print("🔄 开始同步数据到 docs/data 目录...")
    print(f"📁 源目录: {source_data_dir}")
    print(f"📁 目标目录: {target_data_dir}")
    
    # 检查源目录是否存在
    if not source_data_dir.exists():
        print(f"❌ 源目录不存在: {source_data_dir}")
        print("💡 提示: 请先运行 main.py 生成交易数据")
        return False
    
    # ⚠️ 关键修复：检查 docs/data 是否是符号链接
    if target_data_dir.exists():
        try:
            if is_same_file(source_data_dir, target_data_dir):
                print("⚠️  警告: docs/data 是指向 data 的符号链接！")
                print("📝 将解除符号链接并创建独立的数据副本...")
                # 解除符号链接（不会删除源数据）
                if target_data_dir.is_symlink():
                    target_data_dir.unlink()
                else:
                    # 如果是同一个目录（硬链接），需要先移除
                    # 但这次我们确保不删除源数据
                    print("⚠️  docs/data 与 data 是同一个目录，将创建独立的副本")
                    # 先重命名，然后创建新目录
                    backup_name = target_data_dir.with_suffix('.backup')
                    if backup_name.exists():
                        shutil.rmtree(backup_name)
                    shutil.move(str(target_data_dir), str(backup_name))
            elif target_data_dir.is_symlink():
                print("⚠️  docs/data 是符号链接，将解除链接")
                target_data_dir.unlink()
        except Exception as e:
            print(f"⚠️  检查目录时出错: {e}")
            # 如果是符号链接，直接解除
            if target_data_dir.is_symlink():
                try:
                    target_data_dir.unlink()
                except Exception:
                    pass
    
    # 创建目标目录（确保不是符号链接）
    if not target_data_dir.exists():
        target_data_dir.mkdir(parents=True, exist_ok=True)
    
    # 1. 同步 agent_data 目录
    source_agent_data = source_data_dir / "agent_data"
    target_agent_data = target_data_dir / "agent_data"
    
    if source_agent_data.exists() and source_agent_data.is_dir():
        try:
            # ⚠️ 关键修复：检查目标是否指向源数据（符号链接）
            if target_agent_data.exists():
                if is_same_file(source_agent_data, target_agent_data):
                    print(f"⚠️  警告: target_agent_data 指向源数据，将解除链接")
                    if target_agent_data.is_symlink():
                        target_agent_data.unlink()
                    else:
                        # 不能直接删除，先重命名
                        backup = target_agent_data.parent / (target_agent_data.name + '.backup')
                        if backup.exists():
                            shutil.rmtree(backup)
                        shutil.move(str(target_agent_data), str(backup))
                else:
                    # 正常情况，删除目标目录
                    if target_agent_data.is_symlink():
                        target_agent_data.unlink()
                    elif target_agent_data.is_dir():
                        shutil.rmtree(target_agent_data)
            
            # 复制数据
            shutil.copytree(source_agent_data, target_agent_data)
            print(f"✅ 已同步 agent_data 目录")
        except Exception as e:
            print(f"❌ 同步 agent_data 失败: {e}")
            import traceback
            traceback.print_exc()
            return False
    else:
        print(f"⚠️  源目录不存在或不是目录: {source_agent_data}")
        print("💡 提示: 如果还没有运行过交易，这是正常的")
    
    # 2. 同步股票价格数据文件
    price_files = list(source_data_dir.glob("daily_prices_*.json"))
    qqq_file = source_data_dir / "Adaily_prices_QQQ.json"
    
    copied_count = 0
    skipped_count = 0
    
    for price_file in price_files:
        if not price_file.is_file():
            continue
            
        target_file = target_data_dir / price_file.name
        
        # ⚠️ 关键修复：检查是否是同一个文件（符号链接）
        if target_file.exists():
            try:
                if is_same_file(price_file, target_file):
                    skipped_count += 1
                    continue
            except Exception:
                pass
        
        try:
            # 如果目标存在且是符号链接，先解除
            if target_file.exists():
                if target_file.is_symlink():
                    target_file.unlink()
                elif target_file.is_file():
                    target_file.unlink()
            
            if not target_file.exists():
                shutil.copy2(price_file, target_file)
                copied_count += 1
        except shutil.SameFileError:
            skipped_count += 1
        except Exception as e:
            print(f"⚠️  复制文件失败 {price_file.name}: {e}")
    
    if qqq_file.exists() and qqq_file.is_file():
        target_qqq = target_data_dir / qqq_file.name
        if target_qqq.exists():
            try:
                if is_same_file(qqq_file, target_qqq):
                    print(f"ℹ️  QQQ 数据已存在（符号链接），跳过")
                else:
                    if target_qqq.is_symlink():
                        target_qqq.unlink()
                    elif target_qqq.is_file():
                        target_qqq.unlink()
                    shutil.copy2(qqq_file, target_qqq)
                    print(f"✅ 已同步 QQQ 基准数据")
            except shutil.SameFileError:
                print(f"ℹ️  QQQ 数据已存在，跳过")
            except Exception as e:
                print(f"⚠️  复制 QQQ 数据失败: {e}")
        else:
            shutil.copy2(qqq_file, target_qqq)
            print(f"✅ 已同步 QQQ 基准数据")
    
    if copied_count > 0:
        print(f"✅ 已同步 {copied_count} 个股票价格数据文件")
    if skipped_count > 0:
        print(f"ℹ️  跳过 {skipped_count} 个已存在的文件（符号链接）")
    
    print(f"🎉 数据同步完成！")
    print(f"📁 数据位置: {target_data_dir}")
    print(f"🌐 现在可以启动 Web 服务器查看可视化界面：")
    print(f"   cd docs")
    print(f"   python -m http.server 8000")
    
    return True

if __name__ == "__main__":
    sync_data_to_docs()

