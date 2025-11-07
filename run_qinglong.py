#!/usr/bin/env python3
"""
Novel Converter - TXT to EPUB Converter
青龙面板启动脚本 (批量处理 + JSON元数据版)
"""

import sys
import os
import traceback
import glob
import json # (新增)

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
# 3. 导入模块
# -----------------------------------------------------------------
try:
    from main import create_epub
    from config import Config
except ImportError as e:
    logger.error(f"导入主模块失败: {e}")
    logger.error("请确保 src 目录中的文件已按要求修改。")
    sys.exit(1)

def find_matching_cover(cover_dir, book_name):
    """在封面目录中查找匹配的封面"""
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
    """
    (新增) 加载 metadata.json 文件
    """
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
    except json.JSONDecodeError:
        logger.error(f"解析元数据文件失败: {metadata_path}。请检查JSON格式。", exc_info=True)
        return {}
    except Exception as e:
        logger.error(f"读取元数据文件时发生未知错误: {e}", exc_info=True)
        return {}


def main_entry():
    """
    青龙脚本主入口 (批量处理)
    """
    logger.info("="*30)
    logger.info("开始执行 [批量] 小说转换任务")
    logger.info("="*30)

    # 1. 获取配置
    input_dir = Config.get_input_dir()
    output_dir = Config.get_output_dir()
    cover_dir = Config.get_cover_dir()
    global_author = Config.get_global_author()
    metadata_path = Config.get_metadata_file_path()

    logger.info(f"输入目录 (TXT): {input_dir}")
    logger.info(f"输出目录 (EPUB): {output_dir}")
    logger.info(f"封面目录 (Image): {cover_dir or '未配置'}")
    logger.info(f"全局作者: {global_author or '未配置'}")
    logger.info(f"元数据文件: {metadata_path or '未配置'}")

    # (新增) 加载元数据
    metadata_lookup = load_metadata(metadata_path)

    # 2. 扫描 TXT 文件
    txt_files = glob.glob(os.path.join(input_dir, '*.txt'))

    if not txt_files:
        logger.warning(f"在 {input_dir} 中未找到任何 .txt 文件。任务结束。")
        return

    logger.info(f"扫描到 {len(txt_files)} 个 .txt 文件，开始处理...")

    processed_count = 0
    failed_count = 0

    # 3. 循环处理
    for txt_file_path in txt_files:
        try:
            book_name = os.path.splitext(os.path.basename(txt_file_path))[0]
            logger.info(f"--- ( {processed_count + 1} / {len(txt_files)} ) ---")
            logger.info(f"正在处理: {book_name}.txt")

            # 4. (修改) 定义元数据 (从 metadata.json 或全局配置中获取)
            title = book_name
            book_meta = metadata_lookup.get(book_name, {})

            author = book_meta.get('author', global_author) # 优先用JSON的作者，否则用全局作者
            description = book_meta.get('description', None) # 优先用JSON的简介

            logger.info(f"  > 作者: {author}")
            logger.info(f"  > 简介: {'有' if description else '无'}")

            output_path = os.path.join(output_dir, f"{book_name}.epub")

            # 5. 查找匹配的封面
            cover_path = find_matching_cover(cover_dir, book_name)

            # 6. (修改) 调用 create_epub (传入 description)
            create_epub(
                txt_file=txt_file_path,
                cover_image=cover_path,
                title=title,
                author=author,
                output_path=output_path,
                description=description
            )
            processed_count += 1

        except Exception as e:
            logger.error(f"处理 {txt_file_path} 时发生未捕获的异常！")
            logger.error(f"错误详情: {e}", exc_info=True)
            failed_count += 1

    logger.info("="*30)
    logger.info("批量小说转换任务执行完毕")
    logger.info(f"总数: {len(txt_files)}, 成功: {processed_count}, 失败: {failed_count}")
    logger.info("="*30)

if __name__ == "__main__":
    if Config.validate_config():
        main_entry()
    else:
        logger.error("配置验证失败，任务终止。")
        logger.error("请检查青龙面板环境变量设置。")
        sys.exit(1)