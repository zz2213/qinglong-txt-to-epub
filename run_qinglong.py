#!/usr/bin/env python3
"""
Novel Converter - TXT to EPUB Converter
青龙面板启动脚本 (支持文件夹合并版)
"""

import sys
import os
import traceback
import glob
import json

# -----------------------------------------------------------------
# 1. 设置 Python 路径
# -----------------------------------------------------------------
project_root = os.path.dirname(os.path.abspath(__file__))
src_path = os.path.join(project_root, 'src')

if src_path not in sys.path:
    sys.path.insert(0, src_path)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# -----------------------------------------------------------------
# 2. 初始化日志
# -----------------------------------------------------------------
try:
    from QL_logger import logger
except ImportError:
    print("[CRITICAL] QL_logger.py 丢失或导入失败。请确保它在项目根目录。", flush=True)
    sys.exit(1)

# -----------------------------------------------------------------
# 3. 导入青龙通知
# -----------------------------------------------------------------
try:
    from notify import send
    logger.info("成功导入青龙 [notify] 通知模块。")
except ImportError:
    logger.warning("notify.py 导入失败，将无法发送青龙通知。")
    def send(title, content):
        logger.warning(f"无法发送通知 (notify.py 缺失): {title}")
        pass

# -----------------------------------------------------------------
# 4. 导入模块 (修改)
# -----------------------------------------------------------------
try:
    # (修改) 导入两个 create 函数
    from main import create_epub, create_epub_from_chapters
    from config import Config
    # (新增) 导入我们重构的解析器
    from chapter_parser import parse_chapters_from_content
except ImportError as e:
    logger.error(f"导入主模块失败: {e}")
    send("小说转换任务 - 启动失败", f"导入主模块失败: {e}")
    sys.exit(1)

# -----------------------------------------------------------------
# 5. (新增) 文件夹合并逻辑
# -----------------------------------------------------------------
def merge_chapters_from_folder(folder_path):
    """
    (新增)
    从文件夹中合并章节，并根据修改时间去重。
    """
    logger.info(f"开始合并文件夹: {folder_path}")

    # 1. 查找所有 txt 文件
    txt_files = glob.glob(os.path.join(folder_path, '*.txt'))
    if not txt_files:
        logger.warning("文件夹为空，跳过。")
        return []

    # 2. 获取文件及其修改时间
    files_with_mtime = []
    for f in txt_files:
        try:
            files_with_mtime.append((f, os.path.getmtime(f)))
        except OSError:
            logger.warning(f"无法获取文件修改时间: {f}，跳过此文件。")

    # 3. (核心) 按修改时间排序（从旧到新）
    files_with_mtime.sort(key=lambda x: x[1])
    sorted_files = [f[0] for f in files_with_mtime]

    logger.info(f"将按以下顺序合并（旧->新）：{', '.join([os.path.basename(f) for f in sorted_files])}")

    # 4. (核心) 合并章节逻辑
    # all_chapters 存储 {章节标题: 章节内容}
    # final_chapter_order 存储章节的原始顺序
    all_chapters = {}
    final_chapter_order = []

    for txt_file in sorted_files:
        logger.debug(f"正在读取: {os.path.basename(txt_file)}")
        try:
            # (新增) 我们需要 detect_encoding，但它不在 parser 中
            # 让我们简单地在 parser 中重新导入 detect_file_encoding
            from chapter_parser import detect_file_encoding
            encoding = detect_file_encoding(txt_file)

            with open(txt_file, 'r', encoding=encoding, errors='ignore') as f:
                content = f.read()

            # (调用) 使用新的 parse_chapters_from_content
            # 传入 Config 类，以便函数内部可以获取配置
            chapters_list = parse_chapters_from_content(content, Config)

            for chapter in chapters_list:
                # 假设 chapter 是 (标题, 内容)
                title, chapter_content = chapter[0], chapter[1]

                # (核心) 你的去重逻辑
                if title not in all_chapters:
                    # 这是一个新章节，记录它的顺序
                    final_chapter_order.append(title)

                # 无论如何都覆盖，这样最新的文件总能"获胜"
                all_chapters[title] = chapter_content

        except Exception as e:
            logger.error(f"处理文件 {txt_file} 失败: {e}", exc_info=True)

    # 5. 重新组装成 (标题, 内容) 列表，保持原始顺序
    merged_chapters_list = []
    for title in final_chapter_order:
        merged_chapters_list.append((title, all_chapters[title]))

    logger.info(f"合并完成，共 {len(merged_chapters_list)} 个独立章节。")
    return merged_chapters_list


def find_matching_cover(cover_dir, book_name):
    """在封面目录中查找匹配的封面 (保持原样)"""
    if not cover_dir:
        return None
    for ext in ['.jpg', '.png', '.jpeg']:
        cover_path = os.path.join(cover_dir, f"{book_name}{ext}")
        if os.path.exists(cover_path):
            logger.info(f"找到匹配封面: {cover_path}")
            return cover_path
    logger.info(f"未找到 {book_name} 的匹配封面。")
    return None

def load_metadata(metadata_path):
    """加载 metadata.json 文件 (保持原样)"""
    if not metadata_path:
        logger.info("未配置 METADATA_FILE_PATH，跳过加载自定义元数据。")
        return {}
    if not os.path.exists(metadata_path):
        logger.warning(f"元数据文件不存在: {metadata_path}，跳过加载。")
        return {}
    try:
        with open(metadata_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            logger.info(f"成功从 {metadata_path} 加载 {len(data)} 条元数据记录。")
            return data
    except Exception as e:
        logger.error(f"读取元数据文件失败: {e}", exc_info=True)
        return {}


# -----------------------------------------------------------------
# 6. (修改) 重写 main_entry
# -----------------------------------------------------------------
def main_entry():
    """
    (重写)
    青龙脚本主入口 (批量处理)
    """
    logger.info("="*30)
    logger.info("开始执行 [批量] 小说转换任务")

    # 1. 获取配置
    input_dir = Config.get_input_dir()
    output_dir = Config.get_output_dir()
    cover_dir = Config.get_cover_dir()
    global_author = Config.get_global_author()
    metadata_path = Config.get_metadata_file_path()

    logger.info(f"输入目录 (TXT): {input_dir}")
    logger.info(f"输出目录 (EPUB): {output_dir}")

    metadata_lookup = load_metadata(metadata_path)

    # 2. (修改) 扫描任务 (文件和文件夹)
    try:
        items = os.listdir(input_dir)
    except FileNotFoundError:
        logger.error(f"输入目录不存在: {input_dir}")
        return {'total': 0, 'processed': 0, 'failed': 0, 'success_list': [], 'failure_list': []}

    tasks = []
    for item_name in items:
        item_path = os.path.join(input_dir, item_name)
        if item_name.endswith('.txt') and os.path.isfile(item_path):