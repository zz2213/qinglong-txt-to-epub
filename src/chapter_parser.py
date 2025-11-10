# src/chapter_parser.py (修改后的完整文件 - 修正版)

import re
import chardet
from config import Config
from QL_logger import logger # 导入青龙日志

def is_chapter_title(line):
    """
    检查是否为章节标题，支持多种格式
    按优先级返回匹配结果
    (修改) 增加了 (?!\S) 来确保关键字(章/节)后是空格或行尾
    """
    line = line.strip()

    # 规则1: 特殊字符标记 (最高优先级)
    if line.startswith('#') or line.startswith('##') or line.startswith('@'):
        # 这个规则不变，因为它只检查前缀
        return True, line.lstrip('#@').strip()

    # 规则2: 通用数字+章/节格式 (支持任意数字)
    patterns = [
        r'^第\s*\d+\s*章(?!\S)',                 # 第1章 (不能是 "第1章课")
        r'^第\s*\d+\s*节(?!\S)',                 # 第1节 (不能是 "第1节课")
        r'^Chapter\s*\d+(?!\S)',                # Chapter 1
        r'^Section\s*\d+(?!\S)',                # Section 1
        r'^第\s*[〇一二两三四五六七八九十百千万亿零壹贰叁肆伍陸柒捌玖拾佰仟]+\s*章(?!\S)',  # 第一章
        r'^第\s*[〇一二两三四五六七八九十百千万亿零壹贰叁肆伍陸柒捌玖拾佰仟]+\s*节(?!\S)',  # 第一节
    ]

    for pattern in patterns:
        match = re.match(pattern, line, re.IGNORECASE)
        if match:
            # (修改) 返回完整的行，以便保留（本卷完）这类信息
            return True, line

    # 规则3: 通用中文章节标识 (支持任意中文数字)
    chinese_patterns = [
        r'^第[〇一二两三四五六七八九十百千万亿零壹贰叁肆伍陸柒捌玖拾佰仟]+章(?!\S)',  # 第一章
        r'^第[〇一二两三四五六七八九十百千万亿零壹贰叁肆伍陸柒捌玖拾佰仟]+节(?!\S)',  # 第一节
        r'^第[〇一二两三四五六七八九十百千万亿零壹贰叁肆伍陸柒捌玖拾佰仟]+部(?!\S)',  # 第一部
    ]

    for pattern in chinese_patterns:
        match = re.match(pattern, line)
        if match:
            return True, line

    # 规则4: 英文章节标识 (支持罗马数字和阿拉伯数字)
    english_patterns = [
        r'^Chapter\s+[IVX]+(?!\S)',  # Chapter I
        r'^Section\s+[IVX]+(?!\S)',  # Section I
        r'^Chapter\s+\d+(?!\S)',     # Chapter 1 (与规则2重叠，但保持)
        r'^Section\s+\d+(?!\S)',     # Section 1 (与规则2重叠，但保持)
    ]

    for pattern in english_patterns:
        match = re.match(pattern, line, re.IGNORECASE)
        if match:
            return True, line

    # 规则5: 其他常见格式 (例如 1. 标题 或 一、 标题)
    other_patterns = [
        r'^\d+\s*[\.、](?!\S)',  # 1. (后面必须是空格或行尾，不能是 "1.2")
        r'^[〇一二两三四五六七八九十百千万亿零壹贰叁肆伍陸柒捌玖拾佰仟]+\s*[\.、](?!\S)',  # 一、 (后面必须是空格或行尾)
    ]

    for pattern in other_patterns:
        match = re.match(pattern, line)
        if match:
            return True, line

    return False, line

def detect_file_encoding(txt_file):
    """检测文件编码"""
    logger.info(f"开始检测文件编码: {txt_file}")
    try:
        with open(txt_file, 'rb') as f:
            raw_data = f.read(50000) # (优化) 只读取前 50k
            result = chardet.detect(raw_data)
            encoding = result['encoding']
            confidence = result['confidence']
            logger.info(f"检测到编码: {encoding} (置信度: {confidence})")

            if encoding == 'GB2312':
                logger.warning("编码检测为 GB2312，自动修正为 GBK。")
                encoding = 'GBK'

            return encoding

    except Exception as e:
        logger.error(f"无法检测文件编码: {e}", exc_info=True)
        return 'utf-8'  # 默认使用UTF-8

def add_chapter_marker_to_line(line, chapter_marker):
    """为行添加章节标记"""
    if not line.startswith(chapter_marker):
        return f"{chapter_marker}{line}"
    return line

def parse_chapters_from_file(txt_file):
    """从TXT文件中解析章节"""
    encoding = detect_file_encoding(txt_file)
    chapters = []
    chapter = []
    chapter_count = 0
    empty_line_count = 0  # 记录连续空行数

    # (注意) 移除了上一轮错误的 split_keywords 逻辑

    # 获取配置
    detection_method = Config.get_chapter_detection_method()
    enable_double_empty_line = Config.enable_double_empty_line_detection()
    enable_chapter_marker = Config.enable_chapter_marker()
    chapter_marker = Config.get_chapter_marker()

    logger.info(f"使用章节检测方法: {detection_method}")
    logger.info(f"启用双空行检测: {enable_double_empty_line}")
    logger.info(f"启用章节标记: {enable_chapter_marker}")
    if enable_chapter_marker:
        logger.info(f"章节标记字符: {chapter_marker}")

    try:
        with open(txt_file, 'r', encoding=encoding, errors='ignore') as f:
            for line in f:
                line = line.strip()

                if line:  # 非空行
                    empty_line_count = 0  # 重置空行计数

                    # (核心) 检查是否为章节标题
                    is_chapter, chapter_title_line = is_chapter_title(line)

                    if is_chapter:
                        # (修改) 我们使用返回的 chapter_title_line (即原始行)
                        final_title = chapter_title_line

                        if enable_chapter_marker:
                            final_title = add_chapter_marker_to_line(final_title, chapter_marker)

                        # 如果当前章节不为空，保存当前章节
                        if chapter:
                            chapters.append('\n'.join(chapter))
                            chapter_count += 1
                            first_line = chapter[0] if chapter else '未知章节'
                            logger.info(f"检测到章节 {chapter_count}: {first_line[:50]}...")

                        # 用最终的标题行开始新章节
                        chapter = [final_title]

                    else:
                        # 普通内容行，添加到当前章节
                        chapter.append(line)
                else:  # 空行
                    empty_line_count += 1

                    # 双空行分章规则
                    if enable_double_empty_line and empty_line_count == 2 and chapter:
                        chapters.append('\n'.join(chapter))
                        chapter_count += 1
                        first_line = chapter[0] if chapter else '未知章节'
                        logger.info(f"检测到章节 {chapter_count} (双空行分隔): {first_line[:50]}...")
                        chapter = []
                        empty_line_count = 0
                    elif chapter:
                        chapter.append('')  # 添加空行保持格式

            # 添加最后一章
            if chapter:
                chapters.append('\n'.join(chapter))
                chapter_count += 1
                first_line = chapter[0] if chapter else '未知章节'
                logger.info(f"检测到章节 {chapter_count}: {first_line[:50]}...")

    except Exception as e:
        logger.error(f"无法读取小说文件: {e}", exc_info=True)
        return []
    
    logger.info(f"总共解析到 {chapter_count} 个章节。")
    return chapters