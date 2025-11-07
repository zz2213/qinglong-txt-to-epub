#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
@File: config.py
@Description: 配置管理类
"""

import os
import re
from pathlib import Path


class Config:
    """集中管理所有配置项"""

    def __init__(self):
        # 路径配置
        self.source_folder = Path(os.getenv('TXT_SOURCE_FOLDER') or '/ql/data/my_txts/')
        self.dest_folder = Path(os.getenv('EPUB_DEST_FOLDER') or '/ql/all/')
        self.log_dir = Path(os.getenv('LOG_DIR') or '/ql/logs/')

        # 书籍配置
        self.author = os.getenv('EPUB_AUTHOR') or 'Luna'
        self.publisher = os.getenv('EPUB_PUBLISHER') or 'Auto Generated'

        # 功能配置
        self.flatten_output = True
        self.enable_sorting = False
        self.enable_merge_mode = True

        # 封面配置 - 只保留本地封面功能
        self.enable_covers = True
        self.cover_method = 'local'  # 固定为本地封面

        # 性能配置
        self.chunk_size = 1024 * 1024  # 1MB
        self.max_retries = 3
        self.retry_delay = 1  # 秒

        # 格式配置
        self.default_encoding = 'utf-8'
        self.css_style = self._get_css_style()

        # 章节识别配置
        self.chinese_numerals = "0-9〇一二两三四五六七八九十百千万零壹贰叁肆伍陸柒捌玖拾佰仟"
        self.volume_regex = re.compile(fr'第\s*([{self.chinese_numerals}]+)\s*卷(?!\S)')
        self.chapter_regex = re.compile(fr'第\s*([{self.chinese_numerals}]+)\s*[章回节集](?!\S)')
        self.chapter_regex_line = re.compile(
            fr'^\s*'
            fr'(?:'
            fr'第\s*[{self.chinese_numerals}]+\s*[章回节集卷](?!\S)'
            fr'|'
            fr'[Cc][Hh][Aa][Pp][Tt][Ee][Rr]\s+\d+(?!\S)'
            fr'|'
            fr'卷末感言'
            fr'|'
            fr'^\s*\d+\s*[\.、]?\s*[^\.]'  # 数字开头
            fr')'
            fr'.*$'
            , re.MULTILINE
        )

    def _get_css_style(self):
        """获取CSS样式"""
        return '''
            body { 
                font-family: "SimSun", "宋体", "serif"; 
                line-height: 1.8; 
                margin: 2em; 
                font-size: 16px;
                color: #333;
            }
            h1 { 
                font-size: 1.8em; 
                text-align: center; 
                border-bottom: 2px solid #666; 
                padding-bottom: 0.5em; 
                margin-bottom: 1.5em;
                color: #222;
            }
            p { 
                text-indent: 2em; 
                margin-bottom: 1.2em; 
                text-align: justify;
            }
            .chapter { 
                page-break-before: always;
                margin-top: 2em;
            }
            '''