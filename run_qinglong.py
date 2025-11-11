#!/usr/bin/env python3
"""
Novel Converter - TXT to EPUB Converter
青龙面板启动脚本 (增量更新版)
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
# 4. 导入模块
# -----------------------------------------------------------------
try:
    from main import create_epub, create_epub_from_chapters
    from config import Config
    from chapter_parser import parse_chapters_from_content
except ImportError as e:
    logger.error(f"导入主模块失败: {e}")
    send("小说转换任务 - 启动失败", f"导入主模块失败: {e}")
    sys.exit(1)

# -----------------------------------------------------------------
# 5. (新增) 文件夹合并 与 MTime 检查逻辑
# -----------------------------------------------------------------
def get_source_mtime(task_path, task_type):
    """
    (新增)
    获取单个文件或文件夹中最新文件的修改时间
    """
    try:
        if task_type == 'single':
            return os.path.getmtime(task_path)

        elif task_type == 'folder':
            txt_files = glob.glob(os.path.join(task_path, '*.txt'))
            if not txt_files:
                return 0 # 文件夹为空

            latest_mtime = 0
            for f in txt_files:
                mtime = os.path.getmtime(f)
                if mtime > latest_mtime:
                    latest_mtime = mtime
            return latest_mtime

    except Exception as e:
        logger.warning(f"无法获取文件修改时间 {task_path}: {e}")
        return 0

def merge_chapters_from_folder(folder_path):
    """
    (保持)
    从文件夹中合并章节，并根据修改时间去重。
    """
    logger.info(f"开始合并文件夹: {folder_path}")

    txt_files = glob.glob(os.path.join(folder_path, '*.txt'))
    if not txt_files:
        logger.warning("文件夹为空，跳过。")
        return []

    files_with_mtime = []
    for f in txt_files:
        try:
            files_with_mtime.append((f, os.path.getmtime(f)))
        except OSError:
            logger.warning(f"无法获取文件修改时间: {f}，跳过此文件。")

    files_with_mtime.sort(key=lambda x: x[1])
    sorted_files = [f[0] for f in files_with_mtime]

    logger.info(f"将按以下顺序合并（旧->新）：{', '.join([os.path.basename(f) for f in sorted_files])}")

    all_chapters = {}
    final_chapter_order = []

    for txt_file in sorted_files:
        logger.debug(f"正在读取: {os.path.basename(txt_file)}")
        try:
            from chapter_parser import detect_file_encoding
            encoding = detect_file_encoding(txt_file)

            with open(txt_file, 'r', encoding=encoding, errors='ignore') as f:
                content = f.read()

            chapters_list = parse_chapters_from_content(content, Config)

            # (修正) 合并逻辑
            for chapter_string in chapters_list:
                lines = chapter_string.split('\n')
                title = lines[0] if lines else "未知章节"
                chapter_content = '\n'.join(lines[1:]) if len(lines) > 1 else ""

                if title not in all_chapters:
                    final_chapter_order.append(title)

                all_chapters[title] = chapter_content

        except Exception as e:
            logger.error(f"处理文件 {txt_file} 失败: {e}", exc_info=True)

    # 组装回 epub_builder 期望的格式 (字符串列表)
    merged_chapters_list = []
    for title in final_chapter_order:
        merged_chapters_list.append(f"{title}\n{all_chapters[title]}")

    logger.info(f"合并完成，共 {len(merged_chapters_list)} 个独立章节。")
    return merged_chapters_list


def find_matching_cover(cover_dir, book_name):
    """(保持) 匹配封面"""
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
    """(保持) 加载 metadata.json"""
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
    (修改)
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

    # 2. 扫描任务 (文件和文件夹)
    try:
        items = os.listdir(input_dir)
    except FileNotFoundError:
        logger.error(f"输入目录不存在: {input_dir}")
        return {'total': 0, 'processed': 0, 'failed': 0, 'skipped': 0, 'success_list': [], 'failure_list': [], 'skipped_list': []}

    tasks = []
    for item_name in items:
        item_path = os.path.join(input_dir, item_name)

        if item_name.endswith('.txt') and os.path.isfile(item_path):
            book_name = os.path.splitext(item_name)[0]
            tasks.append({'type': 'single', 'book_name': book_name, 'path': item_path})
        elif os.path.isdir(item_path):
            book_name = item_name
            tasks.append({'type': 'folder', 'book_name': book_name, 'path': item_path})

    if not tasks:
        logger.warning(f"在 {input_dir} 中未找到任何 .txt 文件或书籍文件夹。任务结束。")
        return {'total': 0, 'processed': 0, 'failed': 0, 'skipped': 0, 'success_list': [], 'failure_list': [], 'skipped_list': []}

    logger.info(f"扫描到 {len(tasks)} 个任务 (书籍)，开始处理...")

    processed_count = 0
    failed_count = 0
    skipped_count = 0 # (新增)
    success_list = []
    failure_list = []
    skipped_list = [] # (新增)

    # 3. 循环处理任务
    for task in tasks:
        book_name = ""
        try:
            book_name = task['book_name']
            task_type = task['type']
            task_path = task['path']

            output_path = os.path.join(output_dir, f"{book_name}.epub")

            # --- (新增) 检查文件更新时间 ---
            source_mtime = get_source_mtime(task_path, task_type)

            if source_mtime == 0:
                logger.warning(f"跳过 {book_name}: 源文件/文件夹为空或不可读。")
                skipped_count += 1
                skipped_list.append(f"{book_name} (源文件为空)")
                continue

            if os.path.exists(output_path):
                epub_mtime = os.path.getmtime(output_path)
                # 如果源文件 *不比* epub 新，则跳过
                if source_mtime <= epub_mtime:
                    logger.info(f"跳过 {book_name}: .epub 文件已是最新。")
                    skipped_count += 1
                    skipped_list.append(book_name)
                    continue
                else:
                    logger.info(f"{book_name} 源文件已更新，准备重新生成...")
            else:
                logger.info(f"{book_name}.epub 不存在，准备生成...")
            # --- 结束检查 ---

            logger.info(f"--- ( 任务 {processed_count + failed_count + skipped_count + 1} / {len(tasks)} ) ---")
            logger.info(f"正在处理: {book_name} (类型: {task_type})")

            # 4. 获取元数据
            book_meta = metadata_lookup.get(book_name, {})
            author = book_meta.get('author', global_author)
            description = book_meta.get('description', None)
            logger.info(f"  > 作者: {author}")

            cover_path = find_matching_cover(cover_dir, book_name)

            # 5. 根据任务类型调用不同函数
            if task_type == 'single':
                create_epub(
                    txt_file=task_path,
                    cover_image=cover_path,
                    title=book_name,
                    author=author,
                    output_path=output_path,
                    description=description
                )

            elif task_type == 'folder':
                merged_chapters = merge_chapters_from_folder(task_path)

                create_epub_from_chapters(
                    chapters_list=merged_chapters,
                    cover_image=cover_path,
                    title=book_name,
                    author=author,
                    output_path=output_path,
                    description=description
                )

            processed_count += 1
            success_list.append(book_name)

        except Exception as e:
            logger.error(f"处理 {book_name} 时发生未捕获的异常！")
            logger.error(f"错误详情: {e}", exc_info=True)
            failed_count += 1
            failure_list.append(f"{book_name}: {str(e)}")

    logger.info("="*30)
    logger.info("批量小说转换任务执行完毕")
    logger.info(f"总数: {len(tasks)}, 成功: {processed_count}, 失败: {failed_count}, 跳过: {skipped_count}")
    logger.info("="*30)

    return {
        'total': len(tasks),
        'processed': processed_count,
        'failed': failed_count,
        'skipped': skipped_count,
        'success_list': success_list,
        'failure_list': failure_list,
        'skipped_list': skipped_list
    }

# -----------------------------------------------------------------
# 7. (修改) 主执行逻辑 (通知部分)
# -----------------------------------------------------------------
if __name__ == "__main__":
    notification_title = "小说转换"

    try:
        if not Config.validate_config():
            logger.error("配置验证失败，任务终止。")
            send(f"{notification_title} - 失败", "任务终止：配置验证失败，请检查青龙日志。")
            sys.exit(1)

        summary = main_entry()

        # (修改) 构建通知内容
        content = ""

        # 1. 成功列表
        if summary['processed'] > 0:
            content += "转换成功：\n"
            content += "\n".join(summary['success_list'])

        # 2. 跳过列表 (新增)
        if summary['skipped'] > 0:
            if content: content += "\n\n"
            content += "跳过 (已是最新)：\n"
            # (优化：只显示部分跳过)
            if summary['skipped'] > 10:
                 content += f"{summary['skipped_list'][0]}, {summary['skipped_list'][1]}... (共 {summary['skipped']} 本)"
            else:
                 content += "\n".join(summary['skipped_list'])

        # 3. 失败列表
        if summary['failed'] > 0:
            if content: content += "\n\n"
            content += "转换失败：\n"
            content += "\n".join(summary['failure_list'])

        # 4. 处理 "什么都没发生" 的情况
        if summary['processed'] == 0 and summary['failed'] == 0:
            if summary['total'] == 0:
                 content = "未找到待转换的 .txt 文件或书籍文件夹。\n"
            elif summary['skipped'] > 0:
                 # 此时 content 已经包含了跳过列表
                 content += "\n\n(所有文件均已是最新)"
            else:
                 content = "任务执行，但未处理任何文件。\n" # 理论上不会发生

        # 5. 摘要
        content += f"\n\n--- 摘要 ---\n"
        content += f"总数: {summary['total']}, 成功: {summary['processed']}, 失败: {summary['failed']}, 跳过: {summary['skipped']}"

        # 6. 标题
        if summary['processed'] > 0:
             notification_title += " - 转换成功"
        elif summary['failed'] > 0:
             notification_title += " - 转换失败"
        elif summary['skipped'] > 0 and summary['processed'] == 0 and summary['failed'] == 0:
             notification_title += " - 全部跳过"
        elif summary['total'] == 0:
             notification_title += " - 未找到文件"
        else:
             notification_title += " - 执行完毕"

        send(notification_title, content)

    except Exception as e:
        logger.error("脚本执行过程中发生未捕获的全局异常！")
        logger.error(f"错误详情: {e}", exc_info=True)

        error_message = f"任务发生致命错误，已中断：\n{e}\n\n{traceback.format_exc()}"
        if len(error_message) > 1000:
            error_message = error_message[:1000] + "..."

        send(f"{notification_title} - 致命错误", error_message)
        sys.exit(1)