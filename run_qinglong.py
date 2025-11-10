#!/usr/bin/env python3
"""
Novel Converter - TXT to EPUB Converter
青龙面板启动脚本 (批量处理 + JSON元数据 + Bark通知版)
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
    from main import create_epub
    from config import Config
except ImportError as e:
    logger.error(f"导入主模块失败: {e}")
    send("❌ 小说转换任务 - 启动失败", f"导入主模块失败: {e}")
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


def main_entry():
    """
    青龙脚本主入口 (批量处理)
    (修改) 此函数现在会返回一个执行摘要 (字典)
    """
    logger.info("="*30)
    logger.info("开始执行 [批量] 小说转换任务")

    input_dir = Config.get_input_dir()
    output_dir = Config.get_output_dir()
    cover_dir = Config.get_cover_dir()
    global_author = Config.get_global_author()
    metadata_path = Config.get_metadata_file_path()

    logger.info(f"输入目录 (TXT): {input_dir}")
    logger.info(f"输出目录 (EPUB): {output_dir}")

    metadata_lookup = load_metadata(metadata_path)
    txt_files = glob.glob(os.path.join(input_dir, '*.txt'))

    if not txt_files:
        logger.warning(f"在 {input_dir} 中未找到任何 .txt 文件。任务结束。")
        return {'total': 0, 'processed': 0, 'failed': 0, 'success_list': [], 'failure_list': []}

    logger.info(f"扫描到 {len(txt_files)} 个 .txt 文件，开始处理...")

    processed_count = 0
    failed_count = 0
    success_list = []
    failure_list = []

    for txt_file_path in txt_files:
        book_name = ""
        try:
            book_name = os.path.splitext(os.path.basename(txt_file_path))[0]
            logger.info(f"--- ( {processed_count + 1} / {len(txt_files)} ) ---")
            logger.info(f"正在处理: {book_name}.txt")

            title = book_name
            book_meta = metadata_lookup.get(book_name, {})
            author = book_meta.get('author', global_author)
            description = book_meta.get('description', None)

            logger.info(f"  > 作者: {author}")

            output_path = os.path.join(output_dir, f"{book_name}.epub")
            cover_path = find_matching_cover(cover_dir, book_name)

            create_epub(
                txt_file=txt_file_path,
                cover_image=cover_path,
                title=title,
                author=author,
                output_path=output_path,
                description=description
            )
            processed_count += 1
            success_list.append(book_name) # 记录成功书名

        except Exception as e:
            logger.error(f"处理 {txt_file_path} 时发生未捕获的异常！")
            logger.error(f"错误详情: {e}", exc_info=True)
            failed_count += 1
            failure_list.append(f"{book_name}: {str(e)}") # 记录失败详情

    logger.info("="*30)
    logger.info("批量小说转换任务执行完毕")
    logger.info(f"总数: {len(txt_files)}, 成功: {processed_count}, 失败: {failed_count}")
    logger.info("="*30)

    return {
        'total': len(txt_files),
        'processed': processed_count,
        'failed': failed_count,
        'success_list': success_list,
        'failure_list': failure_list
    }

# -----------------------------------------------------------------
# 5. 主执行逻辑 (通知部分已修改)
# -----------------------------------------------------------------
if __name__ == "__main__":
    notification_title = "小说转换" # 标题简洁点

    try:
        if not Config.validate_config():
            logger.error("配置验证失败，任务终止。")
            send(f"{notification_title} - 失败", "任务终止：配置验证失败，请检查青龙日志。")
            sys.exit(1)

        summary = main_entry()

        # --- (修改) 构建更详细的通知内容 ---
        content = "" # 从空内容开始

        # 1. 添加成功列表 (用户要求)
        if summary['processed'] > 0:
            content += "转换成功：\n"
            content += "\n".join(summary['success_list'])
        else:
            if summary['total'] > 0: # 意思是执行了，但全都失败了
                content += "本次任务未成功转换任何小说。\n"
            else: # 意思是没找到文件
                content += "未找到待转换的 .txt 文件。\n"

        # 2. 添加失败列表 (如果存在)
        if summary['failed'] > 0:
            if content: # 如果前面有成功内容，加个分隔
                content += "\n\n"
            content += "转换失败：\n"
            content += "\n".join(summary['failure_list'])

        # 3. 添加摘要 (放在最后)
        content += f"\n\n--- 摘要 ---\n"
        content += f"总数: {summary['total']}, 成功: {summary['processed']}, 失败: {summary['failed']}"

        # 4. 根据结果设置标题
        if summary['failed'] > 0 and summary['processed'] == 0 and summary['total'] > 0:
            notification_title += " - 全部失败"
        elif summary['failed'] > 0:
            notification_title += " - 部分成功"
        elif summary['processed'] > 0:
            notification_title += " - 全部成功"
        else: # (total == 0)
             notification_title += " - 未执行"

        # 发送通知
        send(notification_title, content)
        # --- 结束修改 ---

    except Exception as e:
        logger.error("脚本执行过程中发生未捕获的全局异常！")
        logger.error(f"错误详情: {e}", exc_info=True)

        error_message = f"任务发生致命错误，已中断：\n{e}\n\n{traceback.format_exc()}"
        if len(error_message) > 1000:
            error_message = error_message[:1000] + "..."

        send(f"❌ {notification_title} - 致命错误", error_message)
        sys.exit(1)