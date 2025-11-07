#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
@File: task_processor.py
@Description: 任务处理器，负责协调整个转换流程
"""

import logging
from typing import List, Dict, Any
from pathlib import Path

from .text_parser import TextParser
from .ebook_generator import EbookGenerator
from .utils import natural_sort_key, read_file_with_fallback, needs_update


class TaskProcessor:
    """任务处理器，负责协调整个转换流程"""

    def __init__(self, config):
        self.config = config
        self.text_parser = TextParser(config)
        self.ebook_generator = EbookGenerator(config)

    def scan_tasks(self) -> List[Dict[str, Any]]:
        """扫描源文件夹，发现处理任务 - 只处理文件夹"""
        tasks_to_process = []

        logging.info("正在扫描任务...")

        # 只扫描一级子文件夹
        for item in self.config.source_folder.iterdir():
            # 只处理文件夹
            if not item.is_dir():
                continue

            # 查找文件夹内的TXT文件
            txt_files = []
            for file_item in item.iterdir():
                if file_item.is_file() and file_item.suffix.lower() == '.txt':
                    txt_files.append(file_item.name)

            if txt_files:
                tasks_to_process.append({
                    'type': 'merge',
                    'source_dir': item,
                    'files': txt_files,
                    'folder_name': item.name  # 添加文件夹名
                })

        logging.info(f"扫描完成，共找到 {len(tasks_to_process)} 个处理任务")
        return tasks_to_process

    def process_merged_files(self, source_dir: Path, file_list: List[str],
                           dest_epub_path: Path, folder_name: str):
        """处理合并文件任务"""
        logging.info(f"开始合并文件夹: {source_dir}")

        # 读取并合并所有文件内容
        full_content_list = []
        sorted_files = sorted(file_list, key=natural_sort_key)

        logging.info(f"将按以下顺序合并 {len(sorted_files)} 个文件: {sorted_files}")
        for filename in sorted_files:
            file_path = source_dir / filename
            content = read_file_with_fallback(file_path)
            if content is not None:
                full_content_list.append(content)

        if not full_content_list:
            logging.error("没有成功读取任何文件内容，跳过此任务")
            return

        merged_content = "\n\n".join(full_content_list)

        try:
            # 解析章节并生成EPUB
            processed_chapters = self.text_parser.parse_chapters(merged_content, force_sort=True)
            epub_success = self.ebook_generator.create_epub(
                dest_epub_path, folder_name, processed_chapters, merged_content, source_dir
            )

            if epub_success:
                logging.info("EPUB生成成功")
            else:
                logging.error("EPUB生成失败")

        except Exception as e:
            logging.error(f"在合并处理过程中发生错误: {e}")

    def validate_directories(self):
        """验证目录是否存在"""
        if not self.config.source_folder.is_dir():
            raise FileNotFoundError(f"源文件夹不存在: {self.config.source_folder}")

        if not self.config.dest_folder.is_dir():
            logging.info(f"目标文件夹不存在，正在创建: {self.config.dest_folder}")
            self.config.dest_folder.mkdir(parents=True, exist_ok=True)

    def needs_update(self, source_paths: List[Path], dest_path: Path) -> bool:
        """检查是否需要更新（代理方法）"""
        return needs_update(source_paths, dest_path)