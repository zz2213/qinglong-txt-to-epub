import logging
import sys

def setup_logger():
    """
    配置一个输出到 stdout 的标准 logger
    """
    # 获取根 logger
    logger = logging.getLogger()

    # 防止重复添加 handler
    if not logger.hasHandlers():
        logger.setLevel(logging.INFO)

        # 创建一个流 handler，输出到 sys.stdout
        stream_handler = logging.StreamHandler(sys.stdout)
        stream_handler.setLevel(logging.INFO)

        # 定义日志格式
        formatter = logging.Formatter(
            '[%(asctime)s] [%(levelname)s] - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        stream_handler.setFormatter(formatter)

        # 添加 handler
        logger.addHandler(stream_handler)

    return logger

# 实例化 logger，以便其他模块导入
logger = setup_logger()