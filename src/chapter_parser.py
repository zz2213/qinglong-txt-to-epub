# src/chapter_parser.py (修改后的完整文件)

import re
import chardet
from config import Config
from QL_logger import logger # (新增)

def is_chapter_title(line):
    """
    检查是否为章节标题，支持多种格式
    按优先级返回匹配结果
    """
    line = line.strip()
    
    # 规则1: 特殊字符标记 (最高优先级)
    if line.startswith('#') or line.startswith('##') or line.startswith('@'):
        return True, line.lstrip('#@').strip()
    
    # 规则2: 通用数字+章/节格式 (支持任意数字)
    patterns = [
        r'^第\s*\d+\s*章',  # 第1章, 第 1 章, 第1000章
        r'^第\s*\d+\s*节',  # 第1节, 第 1 节, 第1000节
        r'^Chapter\s*\d+',  # Chapter 1, Chapter 1000
        r'^Section\s*\d+',  # Section 1, Section 1000
        r'^第\s*[〇一二两三四五六七八九十百千万亿零壹贰叁肆伍陸柒捌玖拾佰仟]+\s*章',  # 第一章, 第一百章, 第一千章
        r'^第\s*[〇一二两三四五六七八九十百千万亿零壹贰叁肆伍陸柒捌玖拾佰仟]+\s*节',  # 第一节, 第一百节
    ]
    
    for pattern in patterns:
        if re.match(pattern, line, re.IGNORECASE):
            return True, line
    
    # 规则3: 通用中文章节标识 (支持任意中文数字)
    chinese_patterns = [
        r'^第[〇一二两三四五六七八九十百千万亿零壹贰叁肆伍陸柒捌玖拾佰仟]+章',  # 第一章, 第一百章, 第一千章
        r'^第[〇一二两三四五六七八九十百千万亿零壹贰叁肆伍陸柒捌玖拾佰仟]+节',  # 第一节, 第一百节
        r'^第[〇一二两三四五六七八九十百千万亿零壹贰叁肆伍陸柒捌玖拾佰仟]+部',  # 第一节, 第一百节
    ]
    
    for pattern in chinese_patterns:
        if re.match(pattern, line):
            return True, line
    
    # 规则4: 英文章节标识 (支持罗马数字和阿拉伯数字)
    english_patterns = [
        r'^Chapter\s+[IVX]+',  # Chapter I, Chapter II, Chapter X
        r'^Section\s+[IVX]+',  # Section I, Section II
        r'^Chapter\s+\d+',     # Chapter 1, Chapter 1000
        r'^Section\s+\d+',     # Section 1, Section 1000
    ]
    
    for pattern in english_patterns:
        if re.match(pattern, line, re.IGNORECASE):
            return True, line
    
    # 规则5: 其他常见格式
    other_patterns = [
        r'^\d+\s*[\.、]\s*',  # 1. 标题, 1、标题, 1000. 标题
        r'^[〇一二两三四五六七八九十百千万亿零壹贰叁肆伍陸柒捌玖拾佰仟]+\s*[\.、]\s*',  # 一、标题, 一百、标题
    ]
    
    for pattern in other_patterns:
        if re.match(pattern, line):
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
            
            # (新增) 修正 chardet 的常见错误
            if encoding == 'GB2312':
                logger.warning("编码检测为 GB2312，自动修正为 GBK。")
                encoding = 'GBK'
            
            return encoding
            
    except Exception as e:
        # (修改)
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
    
    # 获取配置
    detection_method = Config.get_chapter_detection_method()
    enable_double_empty_line = Config.enable_double_empty_line_detection()
    enable_chapter_marker = Config.enable_chapter_marker()
    chapter_marker = Config.get_chapter_marker()
    
    # (修改)
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
                    
                    # 检查是否为章节标题
                    is_chapter, chapter_title = is_chapter_title(line)
                    
                    if is_chapter:
                        # 如果启用章节标记功能，为章节标题添加特殊字符
                        if enable_chapter_marker:
                            line = add_chapter_marker_to_line(line, chapter_marker)
                        
                        # 如果当前章节不为空，保存当前章节
                        if chapter:
                            chapters.append('\n'.join(chapter))
                            chapter_count += 1
                            first_line = chapter[0] if chapter else '未知章节'
                            # (修改)
                            logger.info(f"检测到章节 {chapter_count}: {first_line[:50]}...")
                        # 开始新章节
                        chapter = [line]
                    else:
                        # 普通内容行，添加到当前章节
                        chapter.append(line)
                else:  # 空行
                    empty_line_count += 1
                    
                    # 双空行分章规则：连续两个空行表示章节分隔
                    if enable_double_empty_line and empty_line_count == 2 and chapter:
                        # 保存当前章节
                        chapters.append('\n'.join(chapter))
                        chapter_count += 1
                        first_line = chapter[0] if chapter else '未知章节'
                        # (修改)
                        logger.info(f"检测到章节 {chapter_count} (双空行分隔): {first_line[:50]}...")
                        # 开始新章节
                        chapter = []
                        empty_line_count = 0
                    elif chapter:
                        # 单个空行，保持段落分隔
                        chapter.append('')  # 添加空行保持格式
            
            # 添加最后一章
            if chapter:
                chapters.append('\n'.join(chapter))
                chapter_count += 1
                first_line = chapter[0] if chapter else '未知章节'
                # (修改)
                logger.info(f"检测到章节 {chapter_count}: {first_line[:50]}...")
                
    except Exception as e:
        # (修改)
        logger.error(f"无法读取小说文件: {e}", exc_info=True)
        return []
    
    logger.info(f"总共解析到 {chapter_count} 个章节。")
    return chapters