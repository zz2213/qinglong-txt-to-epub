#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
@File: text_parser.py
@Description: 文本解析器，负责章节识别和解析
"""

import re
import logging
import cn2an
from typing import List, Dict, Any, Tuple


class TextParser:
    """文本解析器，负责章节识别和解析"""

    def __init__(self, config):
        self.config = config
        self.chapter_patterns = [
            config.volume_regex,
            config.chapter_regex,
            re.compile(r'^\s*(\d+)\s*[\.、]'),  # 数字开头
            re.compile(r'^\s*[（\(][^）\)]+[）\)]'),  # 括号内容
        ]

    def parse_chapters(self, content: str, force_sort: bool = False) -> List[Dict[str, Any]]:
        """解析内容为章节列表"""
        if not content or not content.strip():
            logging.warning("内容为空，无法解析章节")
            return [{'title': '正文', 'content': content or '', 'sort_key': (0, 1)}]

        chapter_markers = self._find_all_chapter_markers(content)
        if not chapter_markers:
            return self._handle_no_chapters(content)

        return self._build_chapter_list(content, chapter_markers, force_sort)

    def _find_all_chapter_markers(self, content: str) -> List[re.Match]:
        """查找所有章节标记"""
        markers = []
        # 使用主正则表达式
        markers.extend(list(self.config.chapter_regex_line.finditer(content)))

        # 按位置排序
        markers.sort(key=lambda x: x.start())

        # 去重相近的标记
        return self._deduplicate_markers(markers)

    def _deduplicate_markers(self, markers: List[re.Match]) -> List[re.Match]:
        """去重相近的章节标记"""
        if not markers:
            return []

        unique_markers = [markers[0]]
        for current in markers[1:]:
            last = unique_markers[-1]
            # 如果位置相近(50字符内)，认为是同一个标记
            if current.start() - last.end() > 50:
                unique_markers.append(current)

        return unique_markers

    def _handle_no_chapters(self, content: str) -> List[Dict[str, Any]]:
        """处理没有章节标记的内容"""
        logging.info("未找到章节标记，将整个内容作为单一章节")
        return [{'title': '正文', 'content': content.strip(), 'sort_key': (0, 1)}]

    def _build_chapter_list(self, content: str, markers: List[re.Match],
                            force_sort: bool) -> List[Dict[str, Any]]:
        """构建章节列表"""
        chapters = []
        current_volume = 0

        # 处理前言部分
        prologue_content = content[:markers[0].start()].strip()
        if prologue_content:
            chapters.append({'title': '前言', 'content': prologue_content, 'sort_key': (0, 0)})

        # 处理各个章节
        for i, match in enumerate(markers):
            title = match.group(0).strip()
            content_start = match.end()
            content_end = markers[i + 1].start() if i + 1 < len(markers) else len(content)
            chapter_content = content[content_start:content_end].strip()

            if not chapter_content:
                logging.debug(f"跳过空章节: {title}")
                continue

            # 解析卷号和章节号
            vol_num, chap_num = self._parse_chapter_numbers(title, current_volume)
            if vol_num > 0:
                current_volume = vol_num

            chapters.append({
                'title': title,
                'content': chapter_content,
                'sort_key': (vol_num, chap_num)
            })

        # 去重和排序
        return self._finalize_chapters(chapters, force_sort)

    def _parse_chapter_numbers(self, title: str, current_volume: int) -> Tuple[int, float]:
        """解析章节的卷号和章节号"""
        vol_num, chap_num = current_volume, float('inf')

        # 检查卷号
        volume_match = self.config.volume_regex.search(title)
        if volume_match:
            try:
                vol_num = cn2an.cn2an(volume_match.group(1), "smart")
                chap_num = 0  # 卷标题的章节号为0
            except Exception as e:
                logging.warning(f"无法转换卷号 '{title}': {e}")

        # 检查章节号
        chapter_match = self.config.chapter_regex.search(title)
        if chapter_match:
            try:
                chap_num = cn2an.cn2an(chapter_match.group(1), "smart")
            except Exception as e:
                logging.warning(f"无法转换章节号 '{title}': {e}")

        return vol_num, chap_num

    def _finalize_chapters(self, chapters: List[Dict], force_sort: bool) -> List[Dict]:
        """最终处理章节列表（去重和排序）"""
        # 去重
        unique_chapters_map = {}
        for chapter in chapters:
            title = chapter['title']
            if title not in unique_chapters_map and chapter['content'].strip():
                unique_chapters_map[title] = chapter

        deduplicated_chapters = list(unique_chapters_map.values())
        logging.info(f"章节去重: {len(chapters)} -> {len(deduplicated_chapters)}")

        # 排序
        if self.config.enable_sorting or force_sort:
            logging.info("正在进行分层排序...")
            sorted_chapters = sorted(deduplicated_chapters, key=lambda x: x['sort_key'])
            logging.info("章节排序完成")
            return sorted_chapters
        else:
            logging.info("排序已关闭")
            return deduplicated_chapters