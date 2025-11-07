#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
@File: ebook_generator.py
@Description: EPUB电子书生成器
"""

import time
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path
from ebooklib import epub

from config import Config
from cover_generator import CoverGenerator
from utils import safe_file_operation, send_bark_notification


class EbookGenerator:
    """EPUB电子书生成器"""

    def __init__(self, config: Config):
        self.config = config
        self.cover_generator = CoverGenerator(config) if config.enable_covers else None

    def create_epub(self, dest_path: Path, book_title: str,
                    chapters: List[Dict[str, Any]], full_content: str, source_dir: Path) -> bool:
        """创建EPUB文件"""
        try:
            book = self._create_epub_structure(book_title)

            # 添加封面
            self._add_cover_to_epub(book, book_title, source_dir)

            spine_items = self._add_chapters_to_epub(book, chapters, full_content)
            self._finalize_epub(book, spine_items, dest_path)

            logging.info(f"成功生成EPUB: {dest_path}")
            self._send_success_notification(book_title)
            return True

        except Exception as e:
            logging.error(f"生成EPUB失败 {dest_path}: {e}")
            self._send_error_notification(book_title, str(e))
            return False

    def _create_epub_structure(self, book_title: str) -> epub.EpubBook:
        """创建EPUB基础结构"""
        book = epub.EpubBook()

        # 设置书籍元数据
        book.set_identifier(f"book_{int(time.time())}")
        book.set_title(book_title)
        book.set_language('zh')
        book.add_author(self.config.author)
        book.add_metadata('DC', 'publisher', self.config.publisher)

        # 添加CSS样式
        style_item = epub.EpubItem(
            uid="style",
            file_name="style/styles.css",
            media_type="text/css",
            content=self.config.css_style
        )
        book.add_item(style_item)

        return book

    def _add_cover_to_epub(self, book: epub.EpubBook, book_title: str, source_dir: Path):
        """添加封面到EPUB"""
        if not self.cover_generator or self.config.cover_method == 'none':
            return

        try:
            cover_data = self.cover_generator.generate_cover(book_title, source_dir)
            if cover_data:
                # 根据内容类型确定文件扩展名
                if cover_data.startswith(b'<svg'):
                    cover_file = 'cover.svg'
                    media_type = 'image/svg+xml'
                elif cover_data.startswith(b'\x89PNG'):
                    cover_file = 'cover.png'
                    media_type = 'image/png'
                else:
                    cover_file = 'cover.jpg'
                    media_type = 'image/jpeg'

                book.set_cover(cover_file, cover_data)
                logging.info(f"成功添加封面: {book_title}")
            else:
                logging.info(f"未找到本地封面: {book_title}")

        except Exception as e:
            logging.warning(f"添加封面失败 {book_title}: {e}")

    def _add_chapters_to_epub(self, book: epub.EpubBook, chapters: List[Dict],
                              full_content: str) -> List[epub.EpubHtml]:
        """添加章节到EPUB"""
        if not chapters:
            return [self._add_fallback_chapter(book, full_content)]

        spine_items = []
        for i, chap_data in enumerate(chapters, 1):
            chapter = self._create_chapter(chap_data, i)
            if chapter:
                book.add_item(chapter)
                spine_items.append(chapter)
                logging.debug(f"添加章节: {chap_data['title']}")

        return spine_items

    def _create_chapter(self, chap_data: Dict, index: int) -> Optional[epub.EpubHtml]:
        """创建单个章节"""
        try:
            chap_title = chap_data['title'][:100]  # 限制标题长度
            chap_content = self._clean_content(chap_data['content'])

            file_name = f'chapter_{index:04d}.xhtml'
            epub_chap = epub.EpubHtml(
                title=chap_title,
                file_name=file_name,
                lang='zh'
            )

            epub_chap.content = f'''
                <!DOCTYPE html>
                <html>
                <head>
                    <title>{chap_title}</title>
                    <link rel="stylesheet" type="text/css" href="../style/styles.css"/>
                </head>
                <body>
                    <div class="chapter">
                        <h1>{chap_title}</h1>
                        <div>{chap_content}</div>
                    </div>
                </body>
                </html>
                '''

            return epub_chap

        except Exception as e:
            logging.error(f"创建章节失败 {chap_data.get('title', '未知')}: {e}")
            return None

    def _add_fallback_chapter(self, book: epub.EpubBook, full_content: str) -> epub.EpubHtml:
        """创建回退章节（当没有识别到章节时）"""
        logging.warning("未识别到任何有效章节，创建单一章节")
        html_content = self._clean_content(full_content)

        chapter = epub.EpubHtml(
            title='正文',
            file_name='chapter_0001.xhtml',
            lang='zh'
        )
        chapter.content = f'''
            <!DOCTYPE html>
            <html>
            <head>
                <title>正文</title>
                <link rel="stylesheet" type="text/css" href="../style/styles.css"/>
            </head>
            <body>
                <div class="chapter">
                    <h1>正文</h1>
                    <div>{html_content}</div>
                </div>
            </body>
            </html>
            '''

        book.add_item(chapter)
        return chapter

    def _clean_content(self, content: str) -> str:
        """清理和格式化内容"""
        if not content:
            return "<p>内容为空</p>"

        # 分割段落并清理
        paragraphs = [p.strip() for p in content.split('\n') if p.strip()]
        formatted_paragraphs = []

        for para in paragraphs:
            # 跳过过短的空白行
            if len(para) < 2:
                continue

            # 智能段落合并
            if formatted_paragraphs and len(para) < 100:
                # 短文本可能接续上一段
                last_index = len(formatted_paragraphs) - 1
                formatted_paragraphs[last_index] = formatted_paragraphs[last_index].replace(
                    '</p>', f'{para}</p>'
                )
            else:
                formatted_paragraphs.append(f"<p>{para}</p>")

        return '\n'.join(formatted_paragraphs) if formatted_paragraphs else "<p>无有效内容</p>"

    def _finalize_epub(self, book: epub.EpubBook, spine_items: List[epub.EpubHtml],
                       dest_path: Path):
        """最终化EPUB文件"""
        # 设置目录
        book.toc = [epub.Link(item.file_name, item.title, f'chap_{i}')
                    for i, item in enumerate(spine_items, 1)]

        # 设置阅读顺序
        book.spine = ['nav'] + spine_items

        # 添加导航
        book.add_item(epub.EpubNcx())
        book.add_item(epub.EpubNav())

        # 写入文件
        safe_file_operation(epub.write_epub, str(dest_path), book, {})

    def _send_success_notification(self, book_title: str):
        """发送成功通知"""
        send_bark_notification(
            "EPUB转换完成 ✅",
            f"书籍《{book_title}》已成功生成"
        )

    def _send_error_notification(self, book_title: str, error_msg: str):
        """发送错误通知"""
        send_bark_notification(
            "EPUB转换失败 ❌",
            f"书籍《{book_title}》生成失败\n错误: {error_msg}"
        )