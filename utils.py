#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
@File: utils.py
@Description: 工具函数模块
"""

import os
import re
import logging
import time
import urllib.parse
from typing import List, Any
from pathlib import Path
import requests


def setup_logging():
    """配置日志系统"""
    from .config import Config
    config = Config()

    # 确保日志目录存在
    try:
        config.log_dir.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        # 如果无法创建日志目录，回退到临时目录
        print(f"无法创建日志目录 {config.log_dir}: {e}")
        config.log_dir = Path('/tmp/txt_to_epub_logs')
        config.log_dir.mkdir(parents=True, exist_ok=True)

    log_level = os.getenv('LOG_LEVEL', 'INFO').upper()
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    date_format = '%Y-%m-%d %H:%M:%S'

    # 构建日志文件路径
    log_file = config.log_dir / 'txt_to_epub.log'

    # 配置日志
    logging.basicConfig(
        level=getattr(logging, log_level),
        format=log_format,
        datefmt=date_format,
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )

    logging.info(f"日志系统初始化完成，日志文件: {log_file}")


def natural_sort_key(s: str) -> List[Any]:
    """自然排序键函数"""
    return [int(text) if text.isdigit() else text.lower()
            for text in re.split(r'(\d+)', s)]


def safe_file_operation(func, *args, max_retries: int = 3, **kwargs):
    """安全的文件操作装饰器"""
    last_exception = None
    for attempt in range(max_retries):
        try:
            return func(*args, **kwargs)
        except (IOError, OSError) as e:
            last_exception = e
            if attempt < max_retries - 1:
                logging.warning(f"文件操作失败，第{attempt + 1}次重试: {e}")
                time.sleep(1)
            else:
                logging.error(f"文件操作最终失败: {e}")
                raise last_exception


def detect_encoding(file_path: Path) -> str:
    """简单检测文件编码"""
    encodings_to_try = ['utf-8', 'gbk', 'gb2312', 'big5', 'utf-16']

    for enc in encodings_to_try:
        try:
            with open(file_path, 'r', encoding=enc) as f:
                f.read(1024)  # 只读取前1KB进行测试
            return enc
        except (UnicodeDecodeError, UnicodeError):
            continue

    return 'utf-8'  # 默认回退


def read_file_with_fallback(file_path: Path, max_retries: int = 2) -> str | None:
    """增强的文件读取，支持重试和编码检测"""
    for attempt in range(max_retries + 1):
        encoding = detect_encoding(file_path)
        try:
            with open(file_path, 'r', encoding=encoding) as f:
                content = f.read()

            if attempt > 0:
                logging.info(f"第{attempt + 1}次尝试成功，编码: {encoding.upper()}")
            else:
                logging.debug(f"文件编码识别为: {encoding.upper()} ({file_path.name})")

            return content

        except Exception as e:
            if attempt == max_retries:
                logging.error(f"读取文件失败: {file_path}，最终错误: {e}")
            else:
                logging.warning(f"第{attempt + 1}次读取失败: {e}")
                time.sleep(1)

    return None


def send_bark_notification(title: str, body: str):
    """发送Bark通知"""
    bark_url = os.getenv('BARK_PUSH')
    if not bark_url:
        logging.warning("未在环境变量中找到 BARK_PUSH 配置，跳过通知")
        return

    try:
        encoded_title = urllib.parse.quote(title)
        encoded_body = urllib.parse.quote(body)
        url = f"{bark_url.rstrip('/')}/{encoded_title}/{encoded_body}"
        url += "?icon=https://raw.githubusercontent.com/yueshang/pic/main/miao/15.jpg"
        url += "&group=TXT转EPUB"
        url += "&sound=healthnotification"

        logging.info(f"📱 发送Bark通知: {title}")
        response = requests.get(url, timeout=10)

        if response.status_code == 200:
            logging.info("Bark 通知发送成功")
        else:
            logging.warning(f"Bark 通知发送失败: {response.status_code}")

    except Exception as e:
        logging.error(f"发送 Bark 通知时发生网络错误: {e}")


def needs_update(source_paths: List[Path], dest_path: Path) -> bool:
    """
    检查源文件是否需要更新目标文件
    如果目标文件不存在，或者任何一个源文件比目标文件新，则需要更新
    """
    if not dest_path.exists():
        logging.info(f"目标文件不存在，需要生成: {dest_path}")
        return True

    try:
        dest_mtime = dest_path.stat().st_mtime

        for source_path in source_paths:
            if not source_path.exists():
                logging.warning(f"源文件不存在: {source_path}")
                continue

            source_mtime = source_path.stat().st_mtime
            if source_mtime > dest_mtime:
                logging.info(f"源文件比目标文件新，需要更新: {source_path.name}")
                return True

        logging.info(f"所有源文件都比目标文件旧，跳过更新: {dest_path}")
        return False

    except Exception as e:
        logging.error(f"检查文件更新状态失败: {e}")
        return True  # 如果检查失败，默认需要更新