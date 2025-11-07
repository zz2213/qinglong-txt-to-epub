# src/config.py (修改后的完整文件)

import os
from QL_logger import logger # 导入日志

class Config:
    """配置类，管理所有配置参数"""

    @staticmethod
    def get_input_dir():
        """获取 TXT 文件输入目录"""
        return os.getenv('INPUT_DIR')

    @staticmethod
    def get_output_dir():
        """获取 EPUB 文件输出目录"""
        return os.getenv('OUTPUT_DIR')

    @staticmethod
    def get_cover_dir():
        """获取封面图片目录 (可选)"""
        return os.getenv('COVER_DIR')

    @staticmethod
    def get_author():
        """获取全局作者信息 (可选)"""
        return os.getenv('AUTHOR', 'Unknown Author')

    @staticmethod
    def get_chapter_detection_method():
        """获取章节检测方法"""
        method = os.getenv('CHAPTER_DETECTION_METHOD', 'auto')
        return method.lower()

    @staticmethod
    def enable_double_empty_line_detection():
        """是否启用双空行分章检测"""
        return os.getenv('ENABLE_DOUBLE_EMPTY_LINE', 'true').lower() == 'true'

    @staticmethod
    def enable_chapter_marker():
        """是否启用章节标记功能（在双空行分章时添加特殊字符）"""
        return os.getenv('ENABLE_CHAPTER_MARKER', 'false').lower() == 'true'

    @staticmethod
    def get_chapter_marker():
        """获取章节标记字符"""
        return os.getenv('CHAPTER_MARKER', '#')

    @staticmethod
    def validate_config():
        """验证配置是否完整"""
        required_dirs = ['INPUT_DIR', 'OUTPUT_DIR']
        missing_fields = []

        for field in required_dirs:
            if not os.getenv(field):
                missing_fields.append(field)

        if missing_fields:
            logger.error(f"缺少必要的环境变量: {', '.join(missing_fields)}")
            return False

        # 验证路径是否存在
        input_dir = os.getenv('INPUT_DIR')
        output_dir = os.getenv('OUTPUT_DIR')

        if not os.path.isdir(input_dir):
            logger.error(f"配置的输入目录(INPUT_DIR)不存在或不是一个文件夹: {input_dir}")
            return False

        if not os.path.isdir(output_dir):
            logger.warning(f"配置的输出目录(OUTPUT_DIR)不存在: {output_dir}")
            try:
                os.makedirs(output_dir, exist_ok=True)
                logger.info(f"已自动创建输出目录: {output_dir}")
            except Exception as e:
                logger.error(f"自动创建输出目录失败: {e}", exc_info=True)
                return False

        # 验证封面目录 (如果配置了)
        cover_dir = os.getenv('COVER_DIR')
        if cover_dir and not os.path.isdir(cover_dir):
            logger.warning(f"配置的封面目录(COVER_DIR)不存在: {cover_dir}。将无法匹配封面。")

        logger.info("配置验证通过。")
        return True