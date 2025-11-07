# src/main.py (修改后的完整文件)

from config import Config
from chapter_parser import parse_chapters_from_file
from epub_builder import create_epub_book, save_epub_file
from QL_logger import logger

def create_epub(txt_file, cover_image, title, author, output_path, description=None):
    """
    创建EPUB文件的主函数
    (修改：添加 description)
    """
    logger.info(f"开始处理: {txt_file}")

    # 解析章节
    chapters = parse_chapters_from_file(txt_file)
    if not chapters:
        logger.warning(f"文件 {txt_file} 没有检测到任何章节，跳过创建EPUB文件")
        return

    # 创建EPUB书籍
    # (修改：传入 description)
    book = create_epub_book(chapters, title, author, cover_image, description=description)

    # 保存文件
    save_epub_file(book, output_path)

if __name__ == "__main__":
    # 修正：确保在直接运行此文件时，根目录在路径中
    import sys, os
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

    from QL_logger import logger

    logger.warning("此文件 (src/main.py) 不应再被直接运行。")
    logger.warning("请运行项目根目录下的 run_qinglong.py。")