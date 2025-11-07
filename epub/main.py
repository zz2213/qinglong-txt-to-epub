#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
@File: main.py
@Author: Gemini & User
@Date: 2025-10-14
@Version: 17.7 (Local Cover Only)
@Description:
    TXT转EPUB主程序入口
"""

import sys
import os

# 添加当前目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from task_processor import TaskProcessor
from config import Config
from utils import setup_logging, send_bark_notification


def main():
    """主函数"""
    setup_logging()

    try:
        print("🚀 TXT转EPUB任务开始 (本地封面版 v17.7)")

        # 初始化配置和处理器
        config = Config()
        processor = TaskProcessor(config)

        # 验证目录
        processor.validate_directories()
        print(f"源文件夹: {config.source_folder}, 目标文件夹: {config.dest_folder}")
        print(f"封面生成方式: {config.cover_method}")

        # 扫描和处理任务
        tasks = processor.scan_tasks()
        if not tasks:
            print("📭 未找到待处理任务")
            return

        # 处理每个任务
        success_count = 0
        for task in tasks:
            try:
                # 所有任务都是合并任务
                success = _process_merge_task(processor, task, config)

                if success:
                    success_count += 1

            except Exception as e:
                print(f"处理任务失败: {task}，错误: {e}")
            finally:
                print("-" * 50)

        # 总结报告
        print(f"✅ 任务处理完成: {success_count}/{len(tasks)} 成功")
        send_bark_notification(
            "TXT转EPUB任务完成",
            f"处理了 {len(tasks)} 个任务，成功 {success_count} 个"
        )

    except Exception as e:
        print(f"❌ 任务执行失败: {e}")
        send_bark_notification("TXT转EPUB失败", f"错误: {str(e)}")
        raise


def _process_merge_task(processor: TaskProcessor, task: dict, config: Config) -> bool:
    """处理合并任务"""
    source_dir = task['source_dir']
    folder_name = task['folder_name']

    # 使用文件夹名作为EPUB文件名
    dest_epub_path = config.dest_folder / f"{folder_name}.epub"

    # 获取所有源文件的完整路径
    source_paths = [source_dir / filename for filename in task['files']]

    # 检查是否需要更新
    if not processor.needs_update(source_paths, dest_epub_path):
        print(f"合并任务 '{source_dir}' 对应的EPUB已是最新，跳过")
        return False

    processor.process_merged_files(source_dir, task['files'], dest_epub_path, folder_name)
    return True


if __name__ == '__main__':
    main()