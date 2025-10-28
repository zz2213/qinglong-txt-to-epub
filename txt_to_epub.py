#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
@File: txt_to_epub.py
@Author: luna
@Date: 2025-10-14
@Version: 16.1 (Notification Hotfix)
@Description: 青龙脚本 txt转epub
"""

import os
import re
import logging
import requests
from ebooklib import epub
import cn2an

# --- 用户配置区 ---
# 脚本现在会优先从青龙面板的 配置文件(config.sh) 中读取路径。
# 如果配置文件中未设置，则会使用 "or" 后面的默认值。
# 您可以在青龙「配置文件」中添加以下内容进行自定义：
# export TXT_SOURCE_FOLDER="/your/path/to/txts/"
# export EPUB_DEST_FOLDER="/your/path/to/epubs/"
SOURCE_FOLDER = os.getenv('TXT_SOURCE_FOLDER') or '/ql/data/my_txts/'
DESTINATION_FOLDER = os.getenv('EPUB_DEST_FOLDER') or '/ql/all/'

AUTHOR = 'Luna'
FLATTEN_OUTPUT = True
ENABLE_SORTING = False
ENABLE_MERGE_MODE = True

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


# ... 后续所有代码 (TextParser, EbookGenerator, main 函数等) 与 v16.0 完全相同，保持不变 ...
def natural_sort_key(s): return [int(text) if text.isdigit() else text.lower() for text in re.split(r'(\d+)', s)]


def find_common_book_name(file_list, source_dir):
  if not file_list: return os.path.basename(source_dir)
  common_prefix = os.path.commonprefix(file_list);
  cleaned_name = common_prefix.strip(' _-').strip()
  if len(cleaned_name) < 2: folder_name = os.path.basename(source_dir); logging.warning(
    f"共同文件名前缀 '{cleaned_name}' 过短或为空，将使用文件夹名称 '{folder_name}' 作为书名。"); return folder_name
  logging.info(f"从文件名中提取共同书名: '{cleaned_name}'");
  return cleaned_name


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
    except Exception as e:
      logging.error(f"写入Epub文件失败: {dest_path}，错误: {e}")


def send_bark_notification(title, body):
  if not os.getenv('BARK_PUSH'): logging.warning("未在环境变量中找到 BARK_PUSH 配置，跳过通知。"); return
  try:
    bark_url = os.getenv('BARK_PUSH')
    url = f"{bark_url.rstrip('/')}/{title}/{body}?icon=https://raw.githubusercontent.com/yueshang/pic/main/miao/15.jpg";
    response = requests.get(url, timeout=10)
    if response.status_code == 200:
      logging.info("Bark 通知发送成功。")
    else:
      logging.warning(f"Bark 通知发送失败: {response.status_code}")
  except Exception as e:
    logging.error(f"发送 Bark 通知时发生网络错误: {e}")


def process_single_file(source_path, dest_path, parser, generator):
  logging.info(f"开始处理单文件: {source_path}");
  content = read_file_with_fallback(source_path)
  if content is None: return
  book_title = os.path.splitext(os.path.basename(source_path))[0];
  processed_chapters = parser.parse_chapters(content, force_sort=False);
  generator.create_epub(dest_path, book_title, processed_chapters, content)


def process_merged_files(source_dir, file_list, dest_path, parser, generator):
  logging.info(f"开始合并处理文件夹: {source_dir}");
  full_content = []
  sorted_files = sorted(file_list, key=natural_sort_key);
  logging.info(f"将按以下顺序合并 {len(sorted_files)} 个文件: {sorted_files}")
  for filename in sorted_files:
    file_path = os.path.join(source_dir, filename);
    content = read_file_with_fallback(file_path)
    if content is None: continue
    full_content.append(content)
  merged_content = "\n".join(full_content);
  book_title = os.path.splitext(os.path.basename(dest_path))[0]
  processed_chapters = parser.parse_chapters(merged_content, force_sort=True);
  generator.create_epub(dest_path, book_title, processed_chapters, merged_content)


def main():
  logging.info("================== 开始执行TXT转EPUB任务 (v16.1) ==================");
  logging.info(f"源文件夹路径 (SOURCE_FOLDER): {SOURCE_FOLDER}")
  logging.info(f"目标文件夹路径 (DESTINATION_FOLDER): {DESTINATION_FOLDER}")
  if not os.path.isdir(SOURCE_FOLDER): logging.error(f"源文件夹不存在: {SOURCE_FOLDER}"); return
  if not os.path.isdir(DESTINATION_FOLDER):
    logging.info(f"目标文件夹不存在，正在创建: {DESTINATION_FOLDER}");
    os.makedirs(DESTINATION_FOLDER, exist_ok=True)
  text_parser, ebook_generator = TextParser(), EbookGenerator(author=AUTHOR);
  tasks = {}
  if ENABLE_MERGE_MODE:
    logging.info("合并模式已开启。正在扫描任务...")
    for dirpath, dirnames, filenames in os.walk(SOURCE_FOLDER):
      txt_files = [f for f in filenames if f.lower().endswith('.txt')];
      if not txt_files: continue
      is_root_dir = dirpath.rstrip('/') == SOURCE_FOLDER.rstrip('/')
      if not is_root_dir:
        tasks[dirpath] = ('merge', txt_files)
      else:
        for f in txt_files: tasks[os.path.join(dirpath, f)] = ('single', [])
  else:
    logging.info("合并模式已关闭。正在扫描所有独立文件...")
    for dirpath, _, filenames in os.walk(SOURCE_FOLDER):
      for filename in [f for f in filenames if f.lower().endswith('.txt')]: tasks[os.path.join(dirpath, filename)] = (
        'single', [])
  if not tasks: logging.warning(f"在源文件夹 {SOURCE_FOLDER} 及其子文件夹中没有找到任何 .txt 文件或合并任务。"); return
  logging.info(f"扫描完成，共找到 {len(tasks)} 个处理任务。")
  for source_path, (task_type, file_list) in tasks.items():
    try:
      if task_type == 'merge':
        book_name = find_common_book_name(file_list, source_path)
      else:
        book_name = os.path.splitext(os.path.basename(source_path))[0]
      dest_filename = f"{book_name}.epub";
      dest_file_path = os.path.join(DESTINATION_FOLDER, dest_filename)

      if os.path.exists(dest_file_path):
        dest_mtime = os.path.getmtime(dest_file_path)
        source_mtime = 0
        if task_type == 'merge':
          latest_mtime = os.path.getmtime(source_path)
          for f in file_list:
            file_path = os.path.join(source_path, f)
            if os.path.exists(file_path):
              latest_mtime = max(latest_mtime, os.path.getmtime(file_path))
          source_mtime = latest_mtime
        else:
          source_mtime = os.path.getmtime(source_path)

        if source_mtime <= dest_mtime:
          logging.info(f"任务 '{source_path}' 对应的EPUB已存在且未更新，跳过。")
          continue
        else:
          logging.info(f"任务 '{source_path}' 对应的EPUB需要更新。")

      if task_type == 'merge':
        process_merged_files(source_path, file_list, dest_file_path, text_parser, ebook_generator)
      else:
        process_single_file(source_path, dest_file_path, text_parser, ebook_generator)
    except Exception as e:
      logging.error(f"处理任务 '{source_path}' 时发生未知严重错误，已跳过。错误详情: {e}")
    finally:
      logging.info("-" * 40)
  logging.info("================== 任务执行完毕 ==================")


if __name__ == '__main__':
  main()