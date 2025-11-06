#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
flzt.top 自动签到脚本 for 青龙面板
处理压缩响应和编码问题
"""

import requests
import json
import os
import time
import sys
import logging
import urllib.parse
import brotli
import gzip
import zlib

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


class FLZTClient:
  def __init__(self):
    self.base_url = "https://flzt.top"
    self.session = requests.Session()

    # 设置完整的请求头，模拟浏览器
    self.session.headers.update({
      'authority': 'flzt.top',
      'accept': 'application/json, text/plain, */*',
      'accept-encoding': 'gzip, deflate, br, zstd',
      'accept-language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
      'content-type': 'application/json;charset=UTF-8',
      'origin': 'https://flzt.top',
      'priority': 'u=1, i',
      'referer': 'https://flzt.top/user/login?redirect=%2Fuser%2Findex',
      'sec-ch-ua': '"Chromium";v="142", "Microsoft Edge";v="142", "Not_A Brand";v="99"',
      'sec-ch-ua-mobile': '?0',
      'sec-ch-ua-platform': '"Windows"',
      'sec-fetch-dest': 'empty',
      'sec-fetch-mode': 'cors',
      'sec-fetch-site': 'same-origin',
      'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36 Edg/142.0.0.0'
    })

    self.access_token = None

  def decode_response(self, response):
    """解码响应内容，处理各种压缩格式"""
    content_encoding = response.headers.get('content-encoding', '').lower()
    content = response.content

    logging.info(f"📡 响应编码: {content_encoding}")
    logging.info(f"📡 响应长度: {len(content)} 字节")

    try:
      if 'br' in content_encoding and content:
        # Brotli 压缩
        content = brotli.decompress(content)
        logging.info("✅ 已解压 Brotli 压缩响应")
      elif 'gzip' in content_encoding and content:
        # Gzip 压缩
        content = gzip.decompress(content)
        logging.info("✅ 已解压 Gzip 压缩响应")
      elif 'deflate' in content_encoding and content:
        # Deflate 压缩
        content = zlib.decompress(content)
        logging.info("✅ 已解压 Deflate 压缩响应")

      # 尝试多种编码解码
      encodings = ['utf-8', 'gbk', 'gb2312', 'latin-1']
      for encoding in encodings:
        try:
          text = content.decode(encoding)
          logging.info(f"✅ 使用 {encoding} 编码成功解码")
          return text
        except UnicodeDecodeError:
          continue

      # 如果所有编码都失败，返回原始内容
      logging.warning("⚠️ 无法解码响应内容，返回原始字节")
      return content

    except Exception as e:
      logging.error(f"❌ 解压/解码响应时出错: {str(e)}")
      return content

  def login(self, email, password):
    """登录获取Access Token"""
    url = f"{self.base_url}/api/token"
    login_data = {
      "email": email,
      "passwd": password
    }

    try:
      logging.info("🔑 正在登录获取Access Token...")

      # 确保使用正确的JSON编码
      json_data = json.dumps(login_data, ensure_ascii=False)

      # 发送登录请求
      response = self.session.post(url, data=json_data, timeout=15)

      logging.info(f"📡 登录响应状态码: {response.status_code}")
      logging.info(f"📡 响应头: {dict(response.headers)}")

      # 解码响应内容
      response_text = self.decode_response(response)

      # 记录响应内容（截断以避免日志过长）
      response_preview = str(response_text)[:500] if response_text else "空响应"
      logging.info(f"📄 登录响应预览: {response_preview}")

      if response.status_code == 200:
        # 尝试解析JSON
        try:
          if isinstance(response_text, bytes):
            # 如果是字节，尝试直接解析
            result = json.loads(response_text)
          else:
            result = json.loads(response_text)

          if result.get('ret') == 1:
            # 从多个可能的位置提取token
            token = (result.get('token') or
                     result.get('result', {}).get('token') or
                     result.get('data', {}).get('token'))

            if token:
              self.access_token = token
              logging.info(f"✅ 登录成功，用户: {result.get('username', 'N/A')}")
              logging.info(f"🔑 获取到Token: {token[:10]}...{token[-10:]}")
              return {
                'success': True,
                'token': token,
                'user_info': result
              }
            else:
              return {
                'success': False,
                'message': '登录响应中未找到token'
              }
          else:
            return {
              'success': False,
              'message': f'登录失败: {result.get("msg", "未知错误")}'
            }
        except json.JSONDecodeError as e:
          logging.error(f"❌ JSON解析失败: {str(e)}")
          # 尝试从原始响应中查找token
          if 'token' in str(response_text):
            logging.info("ℹ️ 响应中包含token关键字，但无法解析JSON")

          return {
            'success': False,
            'message': f'登录响应解析失败: {str(e)}',
            'raw_response': response_text
          }
      else:
        return {
          'success': False,
          'message': f'登录请求失败，HTTP状态码: {response.status_code}'
        }

    except requests.exceptions.RequestException as e:
      return {
        'success': False,
        'message': f'登录网络请求异常: {str(e)}'
      }

  def check_in(self):
    """执行签到操作"""
    if not self.access_token:
      return {
        'success': False,
        'message': '未获取到Access Token，请先登录'
      }

    url = f"{self.base_url}/api/user/checkin"

    # 为签到请求设置特定的请求头
    checkin_headers = {
      'Access-token': self.access_token,
      'referer': 'https://flzt.top/user/index',
      'content-type': 'application/json;charset=UTF-8'
    }

    try:
      logging.info("🔄 发送签到请求...")
      response = self.session.post(url, headers=checkin_headers, timeout=10)

      # 输出原始响应用于调试
      logging.info(f"📡 签到响应状态码: {response.status_code}")
      response_text = self.decode_response(response)
      logging.info(f"📄 签到响应预览: {str(response_text)[:500]}")

      if response.status_code == 200:
        try:
          if isinstance(response_text, bytes):
            result = json.loads(response_text)
          else:
            result = json.loads(response_text)
          return self.handle_checkin_result(result)
        except json.JSONDecodeError as e:
          return {
            'success': False,
            'message': f'签到响应解析失败: {str(e)}',
            'raw_response': response_text
          }
      else:
        return {
          'success': False,
          'message': f'签到请求失败，HTTP状态码: {response.status_code}',
          'response': response_text
        }

    except requests.exceptions.RequestException as e:
      return {
        'success': False,
        'message': f'签到网络请求异常: {str(e)}'
      }

  def handle_checkin_result(self, result):
    """处理签到结果"""
    if isinstance(result, dict):
      ret_code = result.get('ret')
      result_msg = result.get('result', '')

      if ret_code == 1:
        # 签到成功
        return {
          'success': True,
          'message': f'签到成功！{result_msg}',
          'ret': ret_code,
          'result': result_msg,
          'data': result
        }
      elif ret_code == 0:
        # 今日已签到
        return {
          'success': True,
          'message': f'签到状态：{result_msg}',
          'ret': ret_code,
          'result': result_msg,
          'data': result
        }
      else:
        # 其他状态码
        return {
          'success': False,
          'message': f'未知返回状态: {ret_code}, 信息: {result_msg}',
          'ret': ret_code,
          'result': result_msg,
          'data': result
        }
    else:
      return {
        'success': False,
        'message': '响应格式异常',
        'data': result
      }


def send_bark_notification(title, body):
  """发送Bark通知"""
  bark_url = os.getenv('BARK_PUSH')
  if not bark_url:
    logging.warning("未在环境变量中找到 BARK_PUSH 配置，跳过通知。")
    return False

  try:
    # 使用您提供的相同格式构建URL
    url = f"{bark_url.rstrip('/')}/{urllib.parse.quote(title)}/{urllib.parse.quote(body)}"
    url += "?icon=https://raw.githubusercontent.com/yueshang/pic/main/miao/15.jpg"
    url += "&group=flzt签到"
    url += "&sound=healthnotification"

    logging.info(f"📱 发送Bark通知: {title}")
    response = requests.get(url, timeout=10)

    if response.status_code == 200:
      logging.info("Bark 通知发送成功。")
      return True
    else:
      logging.warning(f"Bark 通知发送失败: {response.status_code}")
      return False
  except Exception as e:
    logging.error(f"发送 Bark 通知时发生网络错误: {e}")
    return False


def main():
  # 从环境变量获取登录凭据
  email = os.getenv('FLZT_EMAIL')
  password = os.getenv('FLZT_PASSWORD')

  # 检查必要的环境变量
  if not email or not password:
    logging.error("❌ 错误：未找到登录凭据")
    logging.error("请在青龙面板的环境变量中设置 FLZT_EMAIL 和 FLZT_PASSWORD")
    sys.exit(1)

  logging.info("=" * 60)
  logging.info("🚀 flzt.top 自动签到脚本")
  logging.info("=" * 60)
  logging.info(f"📧 邮箱: {email}")
  logging.info(f"🕒 执行时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")

  # 检查Bark配置
  if os.getenv('BARK_PUSH'):
    logging.info("📱 Bark通知: 已启用")
  else:
    logging.info("📱 Bark通知: 未配置(BARK_PUSH)")

  # 创建客户端并登录
  client = FLZTClient()

  # 执行登录
  login_result = client.login(email, password)
  if not login_result['success']:
    logging.error(f"❌ 登录失败: {login_result['message']}")

    # 如果有原始响应，记录更多信息
    if 'raw_response' in login_result:
      logging.info(f"📄 原始响应内容: {login_result['raw_response']}")

    # 发送失败通知
    title = "flzt登录失败❌"
    body = f"登录失败: {login_result['message']}"
    send_bark_notification(title, body)

    sys.exit(1)

  # 执行签到
  logging.info("🎯 开始签到...")
  checkin_result = client.check_in()

  # 输出结果
  logging.info("=" * 60)
  if checkin_result['success']:
    if checkin_result.get('ret') == 1:
      logging.info("🎉 ✅ 签到成功!")
      status_emoji = "🎉"
      status_text = "签到成功"
    else:
      logging.info("ℹ️ ✅ 签到完成")
      status_emoji = "ℹ️"
      status_text = "签到完成"
    logging.info(f"📢 {checkin_result['message']}")
  else:
    logging.info("❌ 签到失败!")
    status_emoji = "❌"
    status_text = "签到失败"
    logging.info(f"💬 错误信息: {checkin_result['message']}")

  # 输出详细信息
  if 'ret' in checkin_result:
    status_map = {0: "今日已签到", 1: "签到成功"}
    status_msg = status_map.get(checkin_result['ret'], "未知状态")
    logging.info(f"🔢 返回代码: {checkin_result['ret']} ({status_msg})")

  logging.info("=" * 60)

  # 发送Bark通知
  title = f"flzt签到{status_emoji}"
  body = checkin_result['message']

  # 添加详细信息
  if 'ret' in checkin_result:
    body += f"\n状态码: {checkin_result['ret']}"

  body += f"\n时间: {time.strftime('%H:%M:%S')}"

  send_bark_notification(title, body)

  # 发送通知（适用于青龙面板的通知机制）
  if checkin_result['success']:
    logging.info(f"✅ 签到任务执行成功: {checkin_result['message']}")
  else:
    logging.info(f"❌ 签到任务执行失败: {checkin_result['message']}")

  # 青龙面板需要退出码
  sys.exit(0 if checkin_result['success'] else 1)


if __name__ == "__main__":
  main()