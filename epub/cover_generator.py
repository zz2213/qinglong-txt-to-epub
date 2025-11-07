#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
@File: cover_generator.py
@Description: 封面生成器 - 仅支持本地封面
"""

import logging
from typing import Optional
from pathlib import Path


class CoverGenerator:
    """封面生成器 - 仅支持本地封面"""

    def __init__(self, config):
        self.config = config

    def generate_cover(self, book_title: str, source_dir: Path) -> Optional[bytes]:
        """生成封面图片 - 仅使用本地封面"""
        if self.config.cover_method == 'none':
            return None

        try:
            logging.info(f"尝试获取本地封面: {book_title}")
            cover_data = self._generate_local_cover(book_title, source_dir)
            if cover_data:
                logging.info(f"本地封面获取成功: {book_title}")
                return cover_data
            else:
                logging.info(f"未找到本地封面: {book_title}")
                return None
        except Exception as e:
            logging.warning(f"本地封面获取失败: {e}")
            return None

    def _generate_local_cover(self, book_title: str, source_dir: Path) -> Optional[bytes]:
        """从本地获取封面图片"""
        try:
            # 支持的图片格式
            image_extensions = ['.jpg', '.jpeg', '.png', '.webp', '.bmp', '.gif']

            # 尝试查找与文件夹同名的图片文件
            for ext in image_extensions:
                cover_path = source_dir / f"{book_title}{ext}"
                if cover_path.exists():
                    logging.info(f"找到本地封面: {cover_path}")
                    with open(cover_path, 'rb') as f:
                        return f.read()

            # 尝试查找常见的封面文件名
            common_names = ['cover', '封面', 'folder', 'book']
            for name in common_names:
                for ext in image_extensions:
                    cover_path = source_dir / f"{name}{ext}"
                    if cover_path.exists():
                        logging.info(f"找到本地封面: {cover_path}")
                        with open(cover_path, 'rb') as f:
                            return f.read()

            logging.info(f"未找到本地封面: {book_title}")
            return None

        except Exception as e:
            logging.warning(f"读取本地封面失败: {e}")
            return None