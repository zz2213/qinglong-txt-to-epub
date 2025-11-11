# src/chapter_parser.py (修改后的完整文件)
# (已支持 CHAPTER_DETECTION_METHOD)

import re
import chardet
from config import Config
from QL_logger import logger # 导入青龙日志

def is_chapter_title(line):
    """
    检查是否为章节标题，支持多种格式
    (此函数保持原样，包含我们所有的强化规则)
    """
    line = line.strip()

    # --- 中文数字字符集 ---
    chinese_num_chars = r'〇一二两三四五六七八九十百千万亿零壹贰叁肆伍陸柒捌玖拾佰仟'

    # 规则1: 特殊字符标记 (最高优先级)
    if line.startswith('#') or line.startswith('##') or line.startswith('@'):
        return True, line.lstrip('#@').strip()

    # 规则2: 通用数字+章/节格式 (支持任意数字)
    patterns = [
        r'^第\s*\d+\s*章(?!\S)',                 # 第1章
        r'^第\s*\d+\s*节(?!\S)',                 # 第1节
        r'^Chapter\s*\d+(?!\S)',                # Chapter 1
        r'^Section\s*\d+(?!\S)',                # Section 1
        r'^第\s*[' + chinese_num_chars + r']+\s*章(?!\S)',
        r'^第\s*[' + chinese_num_chars + r']+\s*节(?!\S)',
    ]

    for pattern in patterns:
        match = re.match(pattern, line, re.IGNORECASE)
        if match:
            return True, line

    # 规则3: 通用中文章节标识 (支持任意中文数字)
    chinese_patterns = [
        r'^第[' + chinese_num_chars + r']+章(?!\S)',
        r'^第[' + chinese_num_chars + r']+节(?!\S)',
        r'^第[' + chinese_num_chars + r']+部(?!\S)',
    ]

    for pattern in chinese_patterns:
        match = re.match(pattern, line)
        if match:
            return True, line

    # 规则4: 英文章节标识 (支持罗马数字和阿拉伯数字)
    english_patterns = [
        r'^Chapter\s+[IVX]+(?!\S)',  # Chapter I
        r'^Section\s+[IVX]+(?!\S)',  # Section I
        r'^Chapter\s+\d+(?!\S)',     # Chapter 1
        r'^Section\s+\d+(?!\S)',     # Section 1
    ]

    for pattern in english_patterns:
        match = re.match(pattern, line, re.IGNORECASE)
        if match:
            return True, line

    # 规则5: 其他常见格式
    other_patterns = [
        r'^\d+\s*[\.、](?!\S)',
        r'^[' + chinese_num_chars + r']+\s*[\.、](?!\S)',
    ]

    for pattern in other_patterns:
        match = re.match(pattern, line)
        if match:
            return True, line

    return False, line

def detect_file_encoding(txt_file):
    """检测文件编码 (此函数保持原样)"""
    logger.info(f"开始检测文件编码: {txt_file}")
    try:
        with open(txt_file, 'rb') as f:
            raw_data = f.read(50000)
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
        return 'utf-8'

def add_chapter_marker_to_line(line, chapter_marker):
    """为行添加章节标记 (此函数保持原样)"""
    if not line.startswith(chapter_marker):
        return f"{chapter_marker}{line}"
    return line

# --- (修改) 核心解析逻辑 (已支持 DETECTION_METHOD) ---
def parse_chapters_from_content(content_string, config):
    """
    (修改) 从字符串内容中解析章节
    config: 传入 Config 类的引用
    """
    chapters = []
    chapter = []
    chapter_count = 0
    empty_line_count = 0

    # --- (修改) 获取所有相关配置 ---
    detection_method = config.get_chapter_detection_method()
    enable_double_empty_line = config.enable_double_empty_line_detection()
    enable_chapter_marker = config.enable_chapter_marker()
    chapter_marker = config.get_chapter_marker()

    logger.info(f"使用章节检测方法: {detection_method}")
    logger.info(f"启用双空行检测: {enable_double_empty_line}")
    logger.info(f"启用章节标记: {enable_chapter_marker}")

    try:
        lines = content_string.splitlines()
        for line in lines:
            line = line.strip()

            if line:  # 非空行
                empty_line_count = 0

                # --- (修改) 章节标题匹配逻辑 ---
                is_chapter = False
                if detection_method in ['auto', 'pattern_only']:
                    # 只有 auto 和 pattern_only 模式才执行标题匹配
                    is_chapter, chapter_title_line = is_chapter_title(line)
                else:
                    # (detection_method == 'double_empty_line_only')
                    # 强制所有行都为内容，不执行标题匹配
                    chapter_title_line = line
                # --- 结束修改 ---

                if is_chapter:
                    final_title = chapter_title_line
                    if enable_chapter_marker:
                        final_title = add_chapter_marker_to_line(final_title, chapter_marker)

                    if chapter:
                        chapters.append('\n'.join(chapter))
                        chapter_count += 1

                    chapter = [final_title] # 开始新章节

                else:
                    # 普通内容行
                    chapter.append(line)
            else:  # 空行
                empty_line_count += 1

                # --- (修改) 空行分割逻辑 ---
                if detection_method == 'pattern_only':
                    # 'pattern_only' 模式下，空行仅用于格式化，绝不用于分割
                    if chapter:
                        chapter.append('')  # 保持段落
                    continue # 跳过下面的分割逻辑

                # (适用于 'auto' 和 'double_empty_line_only' 模式)
                if enable_double_empty_line and empty_line_count == 2 and chapter:
                    chapters.append('\n'.join(chapter))
                    chapter_count += 1
                    chapter = []
                    empty_line_count = 0
                elif chapter:
                    chapter.append('')  # 保持段落
                # --- 结束修改 ---

        # 添加最后一章
        if chapter:
            chapters.append('\n'.join(chapter))
            chapter_count += 1

    except Exception as e:
        logger.error(f"解析内容时发生错误: {e}", exc_info=True)
        return []

    return chapters

# --- (修改) 重构 parse_chapters_from_file ---
def parse_chapters_from_file(txt_file):
    """
    (修改) 从TXT文件中解析章节。
    此函数现在只负责读取文件，然后调用 parse_chapters_from_content
    """
    encoding = detect_file_encoding(txt_file)
    try:
        with open(txt_file, 'r', encoding=encoding, errors='ignore') as f:
            content = f.read()

        # (修改) 传入 Config 类本身
        chapters = parse_chapters_from_content(content, Config)

        logger.info(f"文件 {txt_file} 共解析到 {len(chapters)} 个章节。")
        return chapters

    except Exception as e:
        logger.error(f"无法读取小说文件: {txt_file} - {e}", exc_info=True)
        return []