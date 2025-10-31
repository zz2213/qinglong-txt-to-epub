#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
@File: txt_to_epub.py
@Author: luna
@Date: 2025-10-14
@Version: 16.5 (In-place Consolidation)
@Description:
    一个将TXT文本文件转换为EPUB电子书的自动化脚本。
    此版本引入“就地整合”模式：在合并文件时，会在原始子文件夹内生成一个
    永久的“主版本”TXT文件，然后再进行EPUB转换，并可选择删除原始的零散TXT文件。
"""

import os
import re
import logging
import shutil
from ebooklib import epub
import cn2an

# --- 用户配置区 ---
SOURCE_FOLDER = os.getenv('TXT_SOURCE_FOLDER') or '/ql/data/my_txts/'
DESTINATION_FOLDER = os.getenv('EPUB_DEST_FOLDER') or '/ql/all/'
AUTHOR = 'Luna'
FLATTEN_OUTPUT = True
ENABLE_SORTING = False
ENABLE_MERGE_MODE = True
# --- !! 安全警告 !! ---
# 是否在成功合并并生成 主版本TXT 和 EPUB 后，删除原始的零散 .txt 文件。
DELETE_SOURCE_ON_MERGE = True

# --- 核心正则表达式配置 ---
CHINESE_NUMERALS = "0-9〇一二两三四五六七八九十百千万零壹贰叁肆伍陸柒捌玖拾佰仟"
VOLUME_REGEX = re.compile(fr'第\s*([{CHINESE_NUMERALS}]+)\s*卷(?!\S)')
CHAPTER_REGEX = re.compile(fr'第\s*([{CHINESE_NUMERALS}]+)\s*[章回节集](?!\S)')
CHAPTER_REGEX_LINE = re.compile(
    fr'^\s*'
    fr'(?:'
    fr'第\s*[{CHINESE_NUMERALS}]+\s*[章回节集卷](?!\S)'
    fr'|'
    fr'[Cc][Hh][Aa][Pp][Tt][Ee][Rr]\s+\d+(?!\S)'
    fr'|'
    fr'卷末感言'
    fr')'
    fr'.*$'
    , re.MULTILINE
)
# --- 用户配置区结束 ---

# --- 配置日志系统 ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')


# ... TextParser, EbookGenerator 和其他辅助函数保持不变 ...
def natural_sort_key(s): return [int(text) if text.isdigit() else text.lower() for text in re.split(r'(\d+)', s)]


def read_file_with_fallback(file_path):
  encodings_to_try = ['utf-8', 'utf-16', 'gbk']
  for enc in encodings_to_try:
    try:
      with open(file_path, 'r', encoding=enc) as f:
        content = f.read()
      logging.info(f"文件编码识别为: {enc.upper()} ({os.path.basename(file_path)})");
      return content
    except (UnicodeDecodeError, UnicodeError):
      logging.debug(f"尝试 {enc.upper()} 编码失败...")
  logging.error(f"读取文件失败: {file_path}，尝试 {encodings_to_try} 编码后均失败。");
  return None


class TextParser:
  def parse_chapters(self, content, force_sort=False):
    chapters, matches = [], list(CHAPTER_REGEX_LINE.finditer(content))
    if not matches:
      if content.strip(): chapters.append({'title': '正文', 'content': content.strip(), 'sort_key': (0, 1)});
      return chapters
    prologue_content = content[:matches[0].start()].strip()
    if prologue_content: chapters.append({'title': '前言', 'content': prologue_content, 'sort_key': (0, 0)})
    current_volume = 0
    for i, match in enumerate(matches):
      title = match.group(0).strip()
      content_start = match.end()
      content_end = matches[i + 1].start() if i + 1 < len(matches) else len(content)
      final_content = content[content_start:content_end].strip()
      volume_match = VOLUME_REGEX.search(title);
      chapter_match = CHAPTER_REGEX.search(title)
      vol_num, chap_num = current_volume, float('inf')
      if volume_match:
        try:
          current_volume = cn2an.cn2an(volume_match.group(1), "smart"); vol_num = current_volume; chap_num = 0
        except Exception:
          logging.warning(f"无法转换卷号: {title}")
      if chapter_match:
        try:
          chap_num = cn2an.cn2an(chapter_match.group(1), "smart")
        except Exception:
          logging.warning(f"无法转换章节号: {title}")
      chapters.append({'title': title, 'content': final_content, 'sort_key': (vol_num, chap_num)})
    logging.info(f"原始识别到 {len(chapters)} 个章节，开始去重...")
    unique_chapters_map = {};
    for chapter in chapters:
      title = chapter['title']
      if title not in unique_chapters_map and chapter['content'].strip(): unique_chapters_map[title] = chapter
    deduplicated_chapters = list(unique_chapters_map.values())
    logging.info(f"去重后剩余 {len(deduplicated_chapters)} 个有效章节。")
    if ENABLE_SORTING or force_sort:
      logging.info("正在进行分层排序...");
      sorted_chapters = sorted(deduplicated_chapters, key=lambda x: x['sort_key']);
      logging.info("章节排序完成。");
      return sorted_chapters
    else:
      logging.info("排序已关闭。");
      return deduplicated_chapters


class EbookGenerator:
  def __init__(self, author="Unknown Author"):
    self.author = author

  def create_epub(self, dest_path, book_title, chapters, full_content):
    book = epub.EpubBook();
    book.set_identifier(book_title);
    book.set_title(book_title);
    book.set_language('zh');
    book.add_author(self.author)
    if not chapters:
      logging.warning("未识别到任何有效章节...");
      html_content = full_content.replace('\n', '<br />');
      chapter = epub.EpubHtml(title=book_title, file_name='chap_1.xhtml', lang='zh');
      chapter.content = f'<h1>{book_title}</h1><p>{html_content}</p>';
      book.add_item(chapter);
      book.toc = [epub.Link('chap_1.xhtml', book_title, 'intro')];
      book.spine = ['nav', chapter]
    else:
      logging.info(f"按顺序开始处理 {len(chapters)} 个章节...");
      epub_chapters = []
      for i, chap_data in enumerate(chapters):
        chap_title, chap_content = chap_data['title'], chap_data['content'];
        logging.info(f"    - (顺序 {i + 1}) 章节标题: {chap_title}");
        preview = chap_content[:40].replace('\n', ' ').replace('\r', ' ');
        logging.info(f"      章节内容预览: {preview}...");
        file_name = f'chap_{i + 1}.xhtml';
        epub_chap = epub.EpubHtml(title=chap_title, file_name=file_name, lang='zh');
        html_content = chap_content.replace('\n', '<br />');
        epub_chap.content = f'<h1>{chap_title}</h1><p>{html_content}</p>';
        book.add_item(epub_chap);
        epub_chapters.append(epub_chap)
      book.toc = [epub.Link(c.file_name, c.title, f'chap_{i + 1}') for i, c in enumerate(epub_chapters)];
      book.spine = ['nav'] + epub_chapters
    book.add_item(epub.EpubNcx());
    book.add_item(epub.EpubNav())
    try:
      epub.write_epub(dest_path, book, {});
      logging.info(f"成功转换: {dest_path}")
      send_bark_notification("EPUB转换完成", f"书籍《{book_title}》已成功生成。")
      return True
    except Exception as e:
      logging.error(f"写入Epub文件失败: {dest_path}，错误: {e}")
      return False


def send_bark_notification(title, body):
  bark_url = os.getenv('BARK_PUSH')
  if not bark_url: logging.warning("未在环境变量中找到 BARK_PUSH 配置，跳过通知。"); return
  try:
    url = f"{bark_url.rstrip('/')}/{title}/{body}?icon=https://raw.githubusercontent.com/yueshang/pic/main/miao/15.jpg";
    response = requests.get(url, timeout=10)
    if response.status_code == 200:
      logging.info("Bark 通知发送成功。")
    else:
      logging.warning(f"Bark 通知发送失败: {response.status_code}")
  except Exception as e:
    logging.error(f"发送 Bark 通知时发生网络错误: {e}")


# --- 核心修改：process_single_file现在也处理已整合的文件夹 ---
def process_single_file(source_path, dest_epub_path, parser, generator):
  logging.info(f"开始处理单文件任务: {source_path}")
  content = read_file_with_fallback(source_path)
  if content is None: return
  book_title = os.path.splitext(os.path.basename(source_path))[0]
  # 单文件默认不强制排序，遵循全局开关
  processed_chapters = parser.parse_chapters(content, force_sort=False)
  generator.create_epub(dest_epub_path, book_title, processed_chapters, content)


def process_merged_files(source_dir, file_list, dest_epub_path, parser, generator):
  logging.info(f"开始就地整合文件夹: {source_dir}")

  # 确定主版本 TXT 的路径（在源子文件夹内）
  book_title = os.path.basename(source_dir)
  master_txt_path = os.path.join(source_dir, f"{book_title}.txt")

  full_content_list = []
  sorted_files = sorted(file_list, key=natural_sort_key)
  logging.info(f"将按以下顺序合并 {len(sorted_files)} 个文件: {sorted_files}")
  for filename in sorted_files:
    file_path = os.path.join(source_dir, filename)
    content = read_file_with_fallback(file_path)
    if content is not None:
      full_content_list.append(content)

  merged_content = "\n\n".join(full_content_list)

  try:
    # 1. 创建主版本 TXT 文件
    logging.info(f"正在创建主版本 TXT 文件: {master_txt_path}")
    with open(master_txt_path, 'w', encoding='utf-8') as f:
      f.write(merged_content)

    # 2. 基于新创建的主版本 TXT 内容生成 EPUB
    # 合并文件强制开启排序
    processed_chapters = parser.parse_chapters(merged_content, force_sort=True)
    epub_success = generator.create_epub(dest_epub_path, book_title, processed_chapters, merged_content)

    # 3. 只有在两个文件都成功创建后，才执行删除操作
    if os.path.exists(master_txt_path) and epub_success:
      if DELETE_SOURCE_ON_MERGE:
        logging.info(f"整合成功，正在删除原始 {len(file_list)} 个源文件...")
        for f_to_delete in file_list:
          os.remove(os.path.join(source_dir, f_to_delete))
        logging.info("原始源文件已删除。")
      else:
        logging.info("整合成功，根据配置保留原始源文件。")
    else:
      logging.error("主版本 TXT 或 EPUB 文件创建失败，已中止操作，未删除源文件。")

  except Exception as e:
    logging.error(f"在整合处理过程中发生严重错误，已中止操作，未删除源文件。错误: {e}")


def main():
  logging.info("================== 开始执行TXT转EPUB任务 (v16.5) ==================");
  logging.info(f"源文件夹: {SOURCE_FOLDER}, 目标文件夹: {DESTINATION_FOLDER}")
  if not os.path.isdir(SOURCE_FOLDER): logging.error(f"源文件夹不存在: {SOURCE_FOLDER}"); return
  if not os.path.isdir(DESTINATION_FOLDER):
    logging.info(f"目标文件夹不存在，正在创建...");
    os.makedirs(DESTINATION_FOLDER, exist_ok=True)

  text_parser, ebook_generator = TextParser(), EbookGenerator(author=AUTHOR)
  tasks_to_process = []

  logging.info("正在扫描任务...")
  for dirpath, _, filenames in os.walk(SOURCE_FOLDER):
    txt_files = [f for f in filenames if f.lower().endswith('.txt')]
    if not txt_files: continue

    # 核心逻辑：判断当前目录是单文件任务还是合并任务
    if ENABLE_MERGE_MODE and len(txt_files) > 1 and dirpath != SOURCE_FOLDER:
      tasks_to_process.append({'type': 'merge', 'source_dir': dirpath, 'files': txt_files})
    else:
      for f in txt_files:
        tasks_to_process.append({'type': 'single', 'source_path': os.path.join(dirpath, f)})

  if not tasks_to_process: logging.warning(f"在 {SOURCE_FOLDER} 中未找到任何任务。"); return
  logging.info(f"扫描完成，共找到 {len(tasks_to_process)} 个处理任务。")

  for task in tasks_to_process:
    try:
      if task['type'] == 'merge':
        source_dir = task['source_dir']
        book_name = os.path.basename(source_dir)
        dest_epub_path = os.path.join(DESTINATION_FOLDER, f"{book_name}.epub")

        if os.path.exists(dest_epub_path):
          logging.info(f"合并任务 '{source_dir}' 对应的EPUB已存在，跳过（就地整合模式下不重复处理源）。")
          continue

        process_merged_files(source_dir, task['files'], dest_epub_path, text_parser, ebook_generator)

      elif task['type'] == 'single':
        source_path = task['source_path']
        book_name = os.path.splitext(os.path.basename(source_path))[0]
        dest_epub_path = os.path.join(DESTINATION_FOLDER, f"{book_name}.epub")

        if os.path.exists(dest_epub_path):
          source_mtime = os.path.getmtime(source_path)
          dest_mtime = os.path.getmtime(dest_epub_path)
          if source_mtime <= dest_mtime:
            logging.info(f"文件 '{source_path}' 对应的EPUB已存在且未更新，跳过。")
            continue

        process_single_file(source_path, dest_epub_path, text_parser, ebook_generator)

    except Exception as e:
      logging.error(f"处理任务时发生未知严重错误，已跳过。任务详情: {task}，错误: {e}")
    finally:
      logging.info("-" * 40)

  logging.info("================== 任务执行完毕 ==================")


if __name__ == '__main__':
  main()