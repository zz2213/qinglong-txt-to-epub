#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
@File: txt_to_epub_optimized.py
@Author: Gemini & User
@Date: 2025-10-14
@Version: 17.0 (Optimized Version)
@Description:
    一个优化版的TXT文本文件转换为EPUB电子书的自动化脚本。
    包含更好的错误处理、内存管理、格式优化和配置管理。
"""

import os
import re
import logging
import shutil
import time
import requests
from ebooklib import epub
import cn2an
from typing import List, Dict, Any, Optional, Tuple


# ============================ 配置类 ============================
class Config:
  """集中管理所有配置项"""

  def __init__(self):
    # 路径配置
    self.source_folder = os.getenv('TXT_SOURCE_FOLDER') or '/ql/data/my_txts/'
    self.dest_folder = os.getenv('EPUB_DEST_FOLDER') or '/ql/all/'

    # 书籍配置
    self.author = os.getenv('EPUB_AUTHOR') or 'Luna'
    self.publisher = os.getenv('EPUB_PUBLISHER') or 'Auto Generated'

    # 功能配置
    self.flatten_output = True
    self.enable_sorting = False
    self.enable_merge_mode = True
    self.delete_source_on_merge = True
    self.backup_before_delete = False

    # 性能配置
    self.chunk_size = 1024 * 1024  # 1MB
    self.max_retries = 3
    self.retry_delay = 1  # 秒

    # 格式配置
    self.default_encoding = 'utf-8'
    self.css_style = '''
        body { 
            font-family: "SimSun", "宋体", "serif"; 
            line-height: 1.8; 
            margin: 2em; 
            font-size: 16px;
            color: #333;
        }
        h1 { 
            font-size: 1.8em; 
            text-align: center; 
            border-bottom: 2px solid #666; 
            padding-bottom: 0.5em; 
            margin-bottom: 1.5em;
            color: #222;
        }
        p { 
            text-indent: 2em; 
            margin-bottom: 1.2em; 
            text-align: justify;
        }
        .chapter { 
            page-break-before: always;
            margin-top: 2em;
        }
        '''

    # 章节识别配置
    self.chinese_numerals = "0-9〇一二两三四五六七八九十百千万零壹贰叁肆伍陸柒捌玖拾佰仟"
    self.volume_regex = re.compile(fr'第\s*([{self.chinese_numerals}]+)\s*卷(?!\S)')
    self.chapter_regex = re.compile(fr'第\s*([{self.chinese_numerals}]+)\s*[章回节集](?!\S)')
    self.chapter_regex_line = re.compile(
        fr'^\s*'
        fr'(?:'
        fr'第\s*[{self.chinese_numerals}]+\s*[章回节集卷](?!\S)'
        fr'|'
        fr'[Cc][Hh][Aa][Pp][Tt][Ee][Rr]\s+\d+(?!\S)'
        fr'|'
        fr'卷末感言'
        fr'|'
        fr'^\s*\d+\s*[\.、]?\s*[^\.]'  # 数字开头
        fr')'
        fr'.*$'
        , re.MULTILINE
    )


# ============================ 工具函数 ============================
def setup_logging():
  """配置日志系统"""
  log_level = os.getenv('LOG_LEVEL', 'INFO').upper()
  log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
  date_format = '%Y-%m-%d %H:%M:%S'

  logging.basicConfig(
      level=getattr(logging, log_level),
      format=log_format,
      datefmt=date_format,
      handlers=[
        logging.FileHandler('/ql/logs/txt_to_epub.log', encoding='utf-8'),
        logging.StreamHandler()
      ]
  )


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


def detect_encoding(file_path: str) -> str:
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


def read_file_with_fallback(file_path: str, max_retries: int = 2) -> Optional[str]:
  """增强的文件读取，支持重试和编码检测"""
  for attempt in range(max_retries + 1):
    encoding = detect_encoding(file_path)
    try:
      with open(file_path, 'r', encoding=encoding) as f:
        content = f.read()

      if attempt > 0:
        logging.info(f"第{attempt + 1}次尝试成功，编码: {encoding.upper()}")
      else:
        logging.debug(f"文件编码识别为: {encoding.upper()} ({os.path.basename(file_path)})")

      return content

    except Exception as e:
      if attempt == max_retries:
        logging.error(f"读取文件失败: {file_path}，最终错误: {e}")
      else:
        logging.warning(f"第{attempt + 1}次读取失败: {e}")
        time.sleep(1)

  return None


def find_common_book_name(file_list: List[str], source_dir: str) -> str:
  """从文件名列表中提取共同的书名"""
  if not file_list:
    return os.path.basename(source_dir)

  common_prefix = os.path.commonprefix(file_list)
  cleaned_name = common_prefix.strip(' _-').strip()

  if len(cleaned_name) < 2:
    folder_name = os.path.basename(source_dir)
    logging.warning(f"共同文件名前缀 '{cleaned_name}' 过短或为空，使用文件夹名称 '{folder_name}' 作为书名")
    return folder_name

  logging.info(f"从文件名中提取共同书名: '{cleaned_name}'")
  return cleaned_name


def send_bark_notification(title: str, body: str):
  """发送Bark通知"""
  bark_url = os.getenv('BARK_PUSH')
  if not bark_url:
    logging.warning("未在环境变量中找到 BARK_PUSH 配置，跳过通知")
    return

  try:
    encoded_title = requests.utils.quote(title)
    encoded_body = requests.utils.quote(body)
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


def backup_source_files(file_list: List[str], source_dir: str):
  """备份源文件"""
  config = Config()
  if not config.backup_before_delete:
    return

  backup_dir = os.path.join(source_dir, 'backup')
  os.makedirs(backup_dir, exist_ok=True)
  timestamp = time.strftime("%Y%m%d_%H%M%S")

  for filename in file_list:
    source_path = os.path.join(source_dir, filename)
    backup_path = os.path.join(backup_dir, f"{timestamp}_{filename}")
    safe_file_operation(shutil.copy2, source_path, backup_path)

  logging.info(f"已备份 {len(file_list)} 个文件到 {backup_dir}")


# ============================ 核心类 ============================
class TextParser:
  """文本解析器，负责章节识别和解析"""

  def __init__(self, config: Config):
    self.config = config
    self.chapter_patterns = [
      config.volume_regex,
      config.chapter_regex,
      re.compile(r'^\s*(\d+)\s*[\.、]'),  # 数字开头
      re.compile(r'^\s*[（\(][^）\)]+[）\)]'),  # 括号内容
    ]

  def parse_chapters(self, content: str, force_sort: bool = False) -> List[Dict[str, Any]]:
    """解析内容为章节列表"""
    if not content or not content.strip():
      logging.warning("内容为空，无法解析章节")
      return [{'title': '正文', 'content': content or '', 'sort_key': (0, 1)}]

    chapter_markers = self._find_all_chapter_markers(content)
    if not chapter_markers:
      return self._handle_no_chapters(content)

    return self._build_chapter_list(content, chapter_markers, force_sort)

  def _find_all_chapter_markers(self, content: str) -> List[re.Match]:
    """查找所有章节标记"""
    markers = []
    # 使用主正则表达式
    markers.extend(list(self.config.chapter_regex_line.finditer(content)))

    # 按位置排序
    markers.sort(key=lambda x: x.start())

    # 去重相近的标记
    return self._deduplicate_markers(markers)

  def _deduplicate_markers(self, markers: List[re.Match]) -> List[re.Match]:
    """去重相近的章节标记"""
    if not markers:
      return []

    unique_markers = [markers[0]]
    for current in markers[1:]:
      last = unique_markers[-1]
      # 如果位置相近(50字符内)，认为是同一个标记
      if current.start() - last.end() > 50:
        unique_markers.append(current)

    return unique_markers

  def _handle_no_chapters(self, content: str) -> List[Dict[str, Any]]:
    """处理没有章节标记的内容"""
    logging.info("未找到章节标记，将整个内容作为单一章节")
    return [{'title': '正文', 'content': content.strip(), 'sort_key': (0, 1)}]

  def _build_chapter_list(self, content: str, markers: List[re.Match],
      force_sort: bool) -> List[Dict[str, Any]]:
    """构建章节列表"""
    chapters = []
    current_volume = 0

    # 处理前言部分
    prologue_content = content[:markers[0].start()].strip()
    if prologue_content:
      chapters.append({'title': '前言', 'content': prologue_content, 'sort_key': (0, 0)})

    # 处理各个章节
    for i, match in enumerate(markers):
      title = match.group(0).strip()
      content_start = match.end()
      content_end = markers[i + 1].start() if i + 1 < len(markers) else len(content)
      chapter_content = content[content_start:content_end].strip()

      if not chapter_content:
        logging.debug(f"跳过空章节: {title}")
        continue

      # 解析卷号和章节号
      vol_num, chap_num = self._parse_chapter_numbers(title, current_volume)
      if vol_num > 0:
        current_volume = vol_num

      chapters.append({
        'title': title,
        'content': chapter_content,
        'sort_key': (vol_num, chap_num)
      })

    # 去重和排序
    return self._finalize_chapters(chapters, force_sort)

  def _parse_chapter_numbers(self, title: str, current_volume: int) -> Tuple[int, float]:
    """解析章节的卷号和章节号"""
    vol_num, chap_num = current_volume, float('inf')

    # 检查卷号
    volume_match = self.config.volume_regex.search(title)
    if volume_match:
      try:
        vol_num = cn2an.cn2an(volume_match.group(1), "smart")
        chap_num = 0  # 卷标题的章节号为0
      except Exception as e:
        logging.warning(f"无法转换卷号 '{title}': {e}")

    # 检查章节号
    chapter_match = self.config.chapter_regex.search(title)
    if chapter_match:
      try:
        chap_num = cn2an.cn2an(chapter_match.group(1), "smart")
      except Exception as e:
        logging.warning(f"无法转换章节号 '{title}': {e}")

    return vol_num, chap_num

  def _finalize_chapters(self, chapters: List[Dict], force_sort: bool) -> List[Dict]:
    """最终处理章节列表（去重和排序）"""
    # 去重
    unique_chapters_map = {}
    for chapter in chapters:
      title = chapter['title']
      if title not in unique_chapters_map and chapter['content'].strip():
        unique_chapters_map[title] = chapter

    deduplicated_chapters = list(unique_chapters_map.values())
    logging.info(f"章节去重: {len(chapters)} -> {len(deduplicated_chapters)}")

    # 排序
    if self.config.enable_sorting or force_sort:
      logging.info("正在进行分层排序...")
      sorted_chapters = sorted(deduplicated_chapters, key=lambda x: x['sort_key'])
      logging.info("章节排序完成")
      return sorted_chapters
    else:
      logging.info("排序已关闭")
      return deduplicated_chapters


class EbookGenerator:
  """EPUB电子书生成器"""

  def __init__(self, config: Config):
    self.config = config

  def create_epub(self, dest_path: str, book_title: str,
      chapters: List[Dict[str, Any]], full_content: str) -> bool:
    """创建EPUB文件"""
    try:
      book = self._create_epub_structure(book_title)
      spine_items = self._add_chapters_to_epub(book, chapters, full_content)
      self._finalize_epub(book, spine_items, dest_path)

      logging.info(f"成功生成EPUB: {dest_path}")
      self._send_success_notification(book_title)
      return True

    except Exception as e:
      logging.error(f"生成EPUB失败 {dest_path}: {e}")
      self._send_error_notification(book_title, str(e))
      return False

  def _create_epub_structure(self, book_title: str) -> epub.EpubBook:
    """创建EPUB基础结构"""
    book = epub.EpubBook()

    # 设置书籍元数据
    book.set_identifier(f"book_{int(time.time())}")
    book.set_title(book_title)
    book.set_language('zh')
    book.add_author(self.config.author)
    book.add_metadata('DC', 'publisher', self.config.publisher)

    # 添加CSS样式
    style_item = epub.EpubItem(
        uid="style",
        file_name="style/styles.css",
        media_type="text/css",
        content=self.config.css_style
    )
    book.add_item(style_item)

    return book

  def _add_chapters_to_epub(self, book: epub.EpubBook, chapters: List[Dict],
      full_content: str) -> List[epub.EpubHtml]:
    """添加章节到EPUB"""
    if not chapters:
      return [self._add_fallback_chapter(book, full_content)]

    spine_items = []
    for i, chap_data in enumerate(chapters, 1):
      chapter = self._create_chapter(chap_data, i)
      if chapter:
        book.add_item(chapter)
        spine_items.append(chapter)
        logging.debug(f"添加章节: {chap_data['title']}")

    return spine_items

  def _create_chapter(self, chap_data: Dict, index: int) -> Optional[epub.EpubHtml]:
    """创建单个章节"""
    try:
      chap_title = chap_data['title'][:100]  # 限制标题长度
      chap_content = self._clean_content(chap_data['content'])

      file_name = f'chapter_{index:04d}.xhtml'
      epub_chap = epub.EpubHtml(
          title=chap_title,
          file_name=file_name,
          lang='zh'
      )

      epub_chap.content = f'''
            <!DOCTYPE html>
            <html>
            <head>
                <title>{chap_title}</title>
                <link rel="stylesheet" type="text/css" href="../style/styles.css"/>
            </head>
            <body>
                <div class="chapter">
                    <h1>{chap_title}</h1>
                    <div>{chap_content}</div>
                </div>
            </body>
            </html>
            '''

      return epub_chap

    except Exception as e:
      logging.error(f"创建章节失败 {chap_data.get('title', '未知')}: {e}")
      return None

  def _add_fallback_chapter(self, book: epub.EpubBook, full_content: str) -> epub.EpubHtml:
    """创建回退章节（当没有识别到章节时）"""
    logging.warning("未识别到任何有效章节，创建单一章节")
    html_content = self._clean_content(full_content)

    chapter = epub.EpubHtml(
        title='正文',
        file_name='chapter_0001.xhtml',
        lang='zh'
    )
    chapter.content = f'''
        <!DOCTYPE html>
        <html>
        <head>
            <title>正文</title>
            <link rel="stylesheet" type="text/css" href="../style/styles.css"/>
        </head>
        <body>
            <div class="chapter">
                <h1>正文</h1>
                <div>{html_content}</div>
            </div>
        </body>
        </html>
        '''

    book.add_item(chapter)
    return chapter

  def _clean_content(self, content: str) -> str:
    """清理和格式化内容"""
    if not content:
      return "<p>内容为空</p>"

    # 分割段落并清理
    paragraphs = [p.strip() for p in content.split('\n') if p.strip()]
    formatted_paragraphs = []

    for para in paragraphs:
      # 跳过过短的空白行
      if len(para) < 2:
        continue

      # 智能段落合并
      if formatted_paragraphs and len(para) < 100:
        # 短文本可能接续上一段
        last_index = len(formatted_paragraphs) - 1
        formatted_paragraphs[last_index] = formatted_paragraphs[last_index].replace(
            '</p>', f'{para}</p>'
        )
      else:
        formatted_paragraphs.append(f"<p>{para}</p>")

    return '\n'.join(formatted_paragraphs) if formatted_paragraphs else "<p>无有效内容</p>"

  def _finalize_epub(self, book: epub.EpubBook, spine_items: List[epub.EpubHtml],
      dest_path: str):
    """最终化EPUB文件"""
    # 设置目录
    book.toc = [epub.Link(item.file_name, item.title, f'chap_{i}')
                for i, item in enumerate(spine_items, 1)]

    # 设置阅读顺序
    book.spine = ['nav'] + spine_items

    # 添加导航
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())

    # 写入文件
    safe_file_operation(epub.write_epub, dest_path, book, {})

  def _send_success_notification(self, book_title: str):
    """发送成功通知"""
    send_bark_notification(
        "EPUB转换完成 ✅",
        f"书籍《{book_title}》已成功生成"
    )

  def _send_error_notification(self, book_title: str, error_msg: str):
    """发送错误通知"""
    send_bark_notification(
        "EPUB转换失败 ❌",
        f"书籍《{book_title}》生成失败\n错误: {error_msg}"
    )


# ============================ 任务处理器 ============================
class TaskProcessor:
  """任务处理器，负责协调整个转换流程"""

  def __init__(self, config: Config):
    self.config = config
    self.text_parser = TextParser(config)
    self.ebook_generator = EbookGenerator(config)

  def scan_tasks(self) -> List[Dict[str, Any]]:
    """扫描源文件夹，发现处理任务"""
    tasks_to_process = []

    logging.info("正在扫描任务...")
    for dirpath, _, filenames in os.walk(self.config.source_folder):
      txt_files = [f for f in filenames if f.lower().endswith('.txt')]
      if not txt_files:
        continue

      is_root_dir = dirpath.rstrip('/') == self.config.source_folder.rstrip('/')

      # 判断任务类型
      if self.config.enable_merge_mode and len(txt_files) > 1 and not is_root_dir:
        tasks_to_process.append({
          'type': 'merge',
          'source_dir': dirpath,
          'files': txt_files
        })
      else:
        for f in txt_files:
          tasks_to_process.append({
            'type': 'single',
            'source_path': os.path.join(dirpath, f)
          })

    logging.info(f"扫描完成，共找到 {len(tasks_to_process)} 个处理任务")
    return tasks_to_process

  def process_single_file(self, source_path: str, dest_epub_path: str):
    """处理单个文件任务"""
    logging.info(f"开始处理单文件任务: {source_path}")

    content = read_file_with_fallback(source_path)
    if content is None:
      return

    book_title = os.path.splitext(os.path.basename(source_path))[0]
    processed_chapters = self.text_parser.parse_chapters(content, force_sort=False)

    self.ebook_generator.create_epub(dest_epub_path, book_title, processed_chapters, content)

  def process_merged_files(self, source_dir: str, file_list: List[str],
      master_txt_path: str, dest_epub_path: str):
    """处理合并文件任务"""
    logging.info(f"开始就地整合文件夹: {source_dir}")

    # 读取并合并所有文件内容
    full_content_list = []
    sorted_files = sorted(file_list, key=natural_sort_key)

    logging.info(f"将按以下顺序合并 {len(sorted_files)} 个文件: {sorted_files}")
    for filename in sorted_files:
      file_path = os.path.join(source_dir, filename)
      content = read_file_with_fallback(file_path)
      if content is not None:
        full_content_list.append(content)

    if not full_content_list:
      logging.error("没有成功读取任何文件内容，跳过此任务")
      return

    merged_content = "\n\n".join(full_content_list)
    book_title = os.path.splitext(os.path.basename(dest_epub_path))[0]

    try:
      # 创建主版本TXT文件
      logging.info(f"正在创建主版本 TXT 文件: {master_txt_path}")
      safe_file_operation(
          lambda: self._write_master_txt(master_txt_path, merged_content)
      )

      # 解析章节并生成EPUB
      processed_chapters = self.text_parser.parse_chapters(merged_content, force_sort=True)
      epub_success = self.ebook_generator.create_epub(
          dest_epub_path, book_title, processed_chapters, merged_content
      )

      # 处理源文件
      if os.path.exists(master_txt_path) and epub_success:
        self._handle_source_files_after_merge(source_dir, file_list)
      else:
        logging.error("主版本 TXT 或 EPUB 文件创建失败，已中止操作，未删除源文件")

    except Exception as e:
      logging.error(f"在整合处理过程中发生严重错误，已中止操作: {e}")

  def _write_master_txt(self, file_path: str, content: str):
    """写入主版本TXT文件"""
    with open(file_path, 'w', encoding='utf-8') as f:
      f.write(content)

  def _handle_source_files_after_merge(self, source_dir: str, file_list: List[str]):
    """合并成功后处理源文件"""
    if self.config.delete_source_on_merge:
      if self.config.backup_before_delete:
        backup_source_files(file_list, source_dir)

      logging.info(f"整合成功，正在删除原始 {len(file_list)} 个源文件...")
      for filename in file_list:
        file_path = os.path.join(source_dir, filename)
        safe_file_operation(os.remove, file_path)

      logging.info("原始源文件已删除")
    else:
      logging.info("整合成功，根据配置保留原始源文件")

  def validate_directories(self):
    """验证目录是否存在"""
    if not os.path.isdir(self.config.source_folder):
      raise FileNotFoundError(f"源文件夹不存在: {self.config.source_folder}")

    if not os.path.isdir(self.config.dest_folder):
      logging.info(f"目标文件夹不存在，正在创建: {self.config.dest_folder}")
      safe_file_operation(os.makedirs, self.config.dest_folder, exist_ok=True)


# ============================ 主函数 ============================
def main():
  """主函数"""
  setup_logging()

  try:
    logging.info("🚀 TXT转EPUB任务开始 (优化版 v17.0)")

    # 初始化配置和处理器
    config = Config()
    processor = TaskProcessor(config)

    # 验证目录
    processor.validate_directories()
    logging.info(f"源文件夹: {config.source_folder}, 目标文件夹: {config.dest_folder}")

    # 扫描和处理任务
    tasks = processor.scan_tasks()
    if not tasks:
      logging.info("📭 未找到待处理任务")
      return

    # 处理每个任务
    success_count = 0
    for task in tasks:
      try:
        if task['type'] == 'merge':
          success = _process_merge_task(processor, task, config)
        else:
          success = _process_single_task(processor, task, config)

        if success:
          success_count += 1

      except Exception as e:
        logging.error(f"处理任务失败: {task}，错误: {e}")
      finally:
        logging.info("-" * 50)

    # 总结报告
    logging.info(f"✅ 任务处理完成: {success_count}/{len(tasks)} 成功")
    send_bark_notification(
        "TXT转EPUB任务完成",
        f"处理了 {len(tasks)} 个任务，成功 {success_count} 个"
    )

  except Exception as e:
    logging.error(f"❌ 任务执行失败: {e}")
    send_bark_notification("TXT转EPUB失败", f"错误: {str(e)}")
    raise


def _process_merge_task(processor: TaskProcessor, task: Dict, config: Config) -> bool:
  """处理合并任务"""
  source_dir = task['source_dir']
  book_name = os.path.basename(source_dir)
  dest_epub_path = os.path.join(config.dest_folder, f"{book_name}.epub")
  master_txt_path = os.path.join(source_dir, f"{book_name}.txt")

  # 检查是否已存在
  if os.path.exists(dest_epub_path) or os.path.exists(master_txt_path):
    logging.info(f"合并任务 '{source_dir}' 对应的文件已存在，跳过")
    return False

  processor.process_merged_files(
      source_dir, task['files'], master_txt_path, dest_epub_path
  )
  return True


def _process_single_task(processor: TaskProcessor, task: Dict, config: Config) -> bool:
  """处理单个文件任务"""
  source_path = task['source_path']
  book_name = os.path.splitext(os.path.basename(source_path))[0]
  dest_epub_path = os.path.join(config.dest_folder, f"{book_name}.epub")

  # 检查是否需要更新
  if os.path.exists(dest_epub_path):
    source_mtime = os.path.getmtime(source_path)
    dest_mtime = os.path.getmtime(dest_epub_path)
    if source_mtime <= dest_mtime:
      logging.info(f"文件 '{source_path}' 对应的EPUB已存在且未更新，跳过")
      return False

  processor.process_single_file(source_path, dest_epub_path)
  return True


if __name__ == '__main__':
  main()