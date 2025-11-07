# src/epub_builder.py (修改后的完整文件)

from ebooklib import epub
import os
from QL_logger import logger

def setup_book_metadata(book, title, author):
    """设置EPUB书籍的元数据"""
    book.set_title(title)
    book.set_language('zh')
    book.add_author(author)
    logger.info(f"设置书籍元数据: 标题={title}, 作者={author}")

def add_cover_image(book, cover_image):
    """添加封面图片"""
    if not cover_image:
        logger.info("未提供封面图片路径，跳过添加封面。")
        return

    if not os.path.exists(cover_image):
        logger.warning(f"封面图片路径不存在: {cover_image}，跳过添加封面。")
        return

    try:
        with open(cover_image, 'rb') as cover:
            book.set_cover("cover.jpg", cover.read())
            logger.info(f"成功添加封面: {cover_image}")
    except Exception as e:
        logger.error(f"无法读取或添加封面图片: {e}", exc_info=True)

def create_chapter_items(book, chapters):
    """创建章节项目并添加到书籍中"""
    logger.info("开始创建 EPUB 章节内容...")
    toc = []

    for i, chapter_text in enumerate(chapters):
        # 提取章节标题和内容
        lines = chapter_text.split('\n')
        chapter_title = lines[0] if lines else f'第{i + 1}章'

        # 获取章节内容（排除标题行）
        chapter_content_lines = lines[1:] if len(lines) > 1 else ['']

        # 优化HTML格式：保留段落
        paragraphs = []
        for line in chapter_content_lines:
            if line: # 非空行
                paragraphs.append(f"<p>{line}</p>")
            else: # 空行
                paragraphs.append("<p>&nbsp;</p>") # 保留空行

        formatted_content = "\n".join(paragraphs)

        chapter_item = epub.EpubHtml(title=chapter_title, file_name=f'chapter_{i + 1}.xhtml', lang='zh')
        chapter_item.set_content(f'<h1>{chapter_title}</h1>{formatted_content}')

        book.add_item(chapter_item)
        book.spine.append(chapter_item)
        toc.append(epub.Link(f'chapter_{i + 1}.xhtml', chapter_title, f'chap_{i + 1}'))

    book.toc = tuple(toc)
    logger.info(f"已创建 {len(chapters)} 个章节。")


def save_epub_file(book, output_path):
    """
    保存EPUB文件
    (修改)
    """
    # output_filename = f"{title}.epub" # (移除)
    output_filename = output_path # (新增)

    try:
        epub.write_epub(output_filename, book, {})
        logger.info(f"EPUB文件已成功保存: {os.path.abspath(output_filename)}")
        return True
    except Exception as e:
        logger.error(f"无法保存EPUB文件: {e}", exc_info=True)
        return False

def create_epub_book(chapters, title, author, cover_image=None):
    """创建EPUB书籍对象"""
    logger.info("创建 EPUB 书籍对象...")
    # 创建EPUB对象
    book = epub.EpubBook()

    # 设置元数据
    setup_book_metadata(book, title, author)

    # 添加封面
    add_cover_image(book, cover_image)

    # 创建章节项目
    create_chapter_items(book, chapters)

    # 添加导航
    book.add_item(epub.EpubNav())
    book.add_item(epub.EpubNcx())
    
    return book