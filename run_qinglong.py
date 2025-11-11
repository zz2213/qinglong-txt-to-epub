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
# 4. 导入模块
# -----------------------------------------------------------------
try:
    # 导入两个 create 函数
    from main import create_epub, create_epub_from_chapters
    from config import Config
    # 导入我们重构的解析器
    from chapter_parser import parse_chapters_from_content
except ImportError as e:
    logger.error(f"导入主模块失败: {e}")
    send("小说转换任务 - 启动失败", f"导入主模块失败: {e}")
    sys.exit(1)

# -----------------------------------------------------------------
# 5. 文件夹合并逻辑
# -----------------------------------------------------------------
def merge_chapters_from_folder(folder_path):
    """
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

    # 3. 按修改时间排序（从旧到新）
    files_with_mtime.sort(key=lambda x: x[1])
    sorted_files = [f[0] for f in files_with_mtime]

    logger.info(f"将按以下顺序合并（旧->新）：{', '.join([os.path.basename(f) for f in sorted_files])}")

    # 4. 合并章节逻辑
    all_chapters = {}
    final_chapter_order = []

    for txt_file in sorted_files:
        logger.debug(f"正在读取: {os.path.basename(txt_file)}")
        try:
            # 导入 detect_file_encoding (它在 chapter_parser.py 中)
            from chapter_parser import detect_file_encoding
            encoding = detect_file_encoding(txt_file)

            with open(txt_file, 'r', encoding=encoding, errors='ignore') as f:
                content = f.read()

            # 调用 parse_chapters_from_content
            # 传入 Config 类，以便函数内部可以获取配置
            chapters_list = parse_chapters_from_content(content, Config)

            for chapter in chapters_list:
                # 假设 chapter 是 (标题, 内容)
                # (修正) chapter_parser 返回的是一个字符串列表，
                # 我们需要重新在 epub_builder 中拆分
                # 让我们回到 (标题, 内容) 的假设，
                # 假设 chapter_parser 已被正确修改

                # --- 假设 chapter_parser.py 返回的是 字符串列表 ---
                # (我们需要在 epub_builder.py 中处理这个)
                # --- 假设结束 ---

                # --- 让我们假设 chapter_parser.py 返回 (标题, 内容) ---
                # (检查 chapter_parser.py ...
                #  是的, parse_chapters_from_content 返回一个字符串列表
                #  `chapters.append('\n'.join(chapter))`
                #  这与 src/main.py (create_epub_from_chapters) 的预期不符
                #  src/main.py 预期一个 "chapters_list"
                #  而 epub_builder.py 预期 (标题, 内容)
                #
                #  我们必须在 merge_chapters_from_folder 中
                #  *自己* 拆分标题和内容
                # )

                # --- (修正) 真正的合并逻辑 ---
                for chapter_string in chapters_list:
                    lines = chapter_string.split('\n')
                    title = lines[0] if lines else "未知章节"
                    chapter_content = '\n'.join(lines[1:]) if len(lines) > 1 else ""

                    if title not in all_chapters:
                        final_chapter_order.append(title)

                    all_chapters[title] = chapter_content
                # --- 修正结束 ---

        except Exception as e:
            logger.error(f"处理文件 {txt_file} 失败: {e}", exc_info=True)

    # 5. 重新组装成 (标题, 内容) 列表，保持原始顺序
    merged_chapters_list = []
    for title in final_chapter_order:
        # (修正) create_epub_from_chapters 预期一个字符串列表
        # (检查 src/main.py...
        #  `book = create_epub_book(chapters_list, ...)`
        # (检查 src/epub_builder.py...
        #  `for i, chapter_text in enumerate(chapters):`
        #  `lines = chapter_text.split('\n')`
        #  `chapter_title = lines[0]...`
        #
        #  啊, (标题, 内容) 列表是 *错误* 的
        #  `epub_builder` 预期的是 *字符串列表* (每项是 '标题\n内容')
        #  所以我的 `chapter_parser` 返回值是正确的
        #  `create_epub_from_chapters` 也是正确的
        #
        #  *但是*，我的去重逻辑是错的
        #  我必须在 *合并时* 就使用 (标题, 内容) 键值对
        #  然后在 *返回时* 再把它们合并回字符串列表
        #  )

        # (二次修正) `all_chapters` 是 {标题: 内容}
        # `final_chapter_order` 是 [标题1, 标题2...]

        # 组装回 `epub_builder` 期望的格式 (字符串列表)
        merged_chapters_list.append(f"{title}\n{all_chapters[title]}")

    logger.info(f"合并完成，共 {len(merged_chapters_list)} 个独立章节。")
    return merged_chapters_list


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
    """加载 metadata.json 文件"""
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
# 6. (重写) main_entry (修正版)
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

    # 2. 扫描任务 (文件和文件夹)
    try:
        items = os.listdir(input_dir)
    except FileNotFoundError:
        logger.error(f"输入目录不存在: {input_dir}")
        return {'total': 0, 'processed': 0, 'failed': 0, 'success_list': [], 'failure_list': []}

    tasks = []
    for item_name in items:
        item_path = os.path.join(input_dir, item_name)

        # --- (修正) 这是你出错的地方 ---
        # 确保 if 和 elif 处于同一缩进级别
        # 确保 if 块内部有缩进

        if item_name.endswith('.txt') and os.path.isfile(item_path):
            # (正确) if 块内部必须缩进
            # 任务类型 1: 单个 txt 文件
            book_name = os.path.splitext(item_name)[0]
            tasks.append({'type': 'single', 'book_name': book_name, 'path': item_path})

        elif os.path.isdir(item_path):
            # (正确) elif 块内部必须缩进
            # 任务类型 2: 文件夹 (一本书)
            book_name = item_name
            tasks.append({'type': 'folder', 'book_name': book_name, 'path': item_path})
        # --- 修正结束 ---

    if not tasks:
        logger.warning(f"在 {input_dir} 中未找到任何 .txt 文件或书籍文件夹。任务结束。")
        return {'total': 0, 'processed': 0, 'failed': 0, 'success_list': [], 'failure_list': []}

    logger.info(f"扫描到 {len(tasks)} 个任务 (书籍)，开始处理...")

    processed_count = 0
    failed_count = 0
    success_list = []
    failure_list = []

    # 3. 循环处理任务
    for task in tasks:
        book_name = ""
        try:
            book_name = task['book_name']
            task_type = task['type']
            task_path = task['path']

            logger.info(f"--- ( {processed_count + 1} / {len(tasks)} ) ---")
            logger.info(f"正在处理: {book_name} (类型: {task_type})")

            # 4. 获取元数据
            book_meta = metadata_lookup.get(book_name, {})
            author = book_meta.get('author', global_author)
            description = book_meta.get('description', None)
            logger.info(f"  > 作者: {author}")

            output_path = os.path.join(output_dir, f"{book_name}.epub")
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
    logger.info(f"总数: {len(tasks)}, 成功: {processed_count}, 失败: {failed_count}")
    logger.info("="*30)

    return {
        'total': len(tasks),
        'processed': processed_count,
        'failed': failed_count,
        'success_list': success_list,
        'failure_list': failure_list
    }

# -----------------------------------------------------------------
# 7. 主执行逻辑 (通知部分)
# -----------------------------------------------------------------
if __name__ == "__main__":
    notification_title = "小说转换"

    try:
        if not Config.validate_config():
            logger.error("配置验证失败，任务终止。")
            send(f"{notification_title} - 失败", "任务终止：配置验证失败，请检查青龙日志。")
            sys.exit(1)

        summary = main_entry()

        content = ""
        if summary['processed'] > 0:
            content += "转换成功：\n"
            content += "\n".join(summary['success_list'])
        else:
            if summary['total'] > 0:
                content += "本次任务未成功转换任何小说。\n"
            else:
                content += "未找到待转换的 .txt 文件或书籍文件夹。\n"

        if summary['failed'] > 0:
            if content:
                content += "\n\n"
            content += "转换失败：\n"
            content += "\n".join(summary['failure_list'])

        content += f"\n\n--- 摘要 ---\n"
        content += f"总数: {summary['total']}, 成功: {summary['processed']}, 失败: {summary['failed']}"

        if summary['failed'] > 0 and summary['processed'] == 0 and summary['total'] > 0:
            notification_title += " - 全部失败"
        elif summary['failed'] > 0:
            notification_title += " - 部分成功"
        elif summary['processed'] > 0:
            notification_title += " - 全部成功"
        else:
             notification_title += " - 未执行"

        send(notification_title, content)

    except Exception as e:
        logger.error("脚本执行过程中发生未捕获的全局异常！")
        logger.error(f"错误详情: {e}", exc_info=True)

        error_message = f"任务发生致命错误，已中断：\n{e}\n\n{traceback.format_exc()}"
        if len(error_message) > 1000:
            error_message = error_message[:1000] + "..."

        send(f"{notification_title} - 致命错误", error_message)
        sys.exit(1)