#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试文档类型检测逻辑
"""

import requests
import io
from docx import Document

def test_document_detection(url):
    """测试文档类型检测"""
    print(f"测试URL: {url}")
    print("-" * 50)
    
    # 测试HEAD请求获取Content-Type
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        print("1. 发送HEAD请求获取响应头...")
        response = requests.head(url, headers=headers, timeout=5, allow_redirects=True)
        print(f"   状态码: {response.status_code}")
        print(f"   Content-Type: {response.headers.get('Content-Type', '未设置')}")
        
        if response.status_code == 200:
            content_type = response.headers.get('Content-Type', '').lower()
            
            # 检查是否为Word文档的MIME类型
            word_types = [
                'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                'application/msword',
                'application/vnd.ms-word'
            ]
            
            if any(word_type in content_type for word_type in word_types):
                print("   ✓ 通过Content-Type检测到Word文档")
                return 'word'
            
            # 检查是否为HTML文档
            html_types = ['text/html', 'application/xhtml+xml']
            if any(html_type in content_type for html_type in html_types):
                print("   ✓ 通过Content-Type检测到HTML文档")
                return 'html'
            
            # 如果Content-Type不明确，通过内容检测
            if 'application/octet-stream' in content_type or not content_type:
                print("2. Content-Type不明确，通过文件内容特征检测...")
                return detect_by_content(url, headers)
        
        return 'unknown'
        
    except Exception as e:
        print(f"   ✗ HEAD请求失败: {e}")
        return 'unknown'

def detect_by_content(url, headers):
    """通过文件内容特征判断文档类型"""
    try:
        print("   下载前1024字节进行检测...")
        response = requests.get(url, headers=headers, timeout=10, stream=True)
        response.raise_for_status()
        
        # 读取前1024字节
        content = b''
        for chunk in response.iter_content(chunk_size=1024):
            content += chunk
            if len(content) >= 1024:
                break
        
        print(f"   已下载 {len(content)} 字节")
        
        # 检查Word文档的文件头特征
        if content.startswith(b'PK'):
            print("   ✓ 检测到.docx文件（ZIP格式，以PK开头）")
            return 'word'
        
        if content.startswith(b'\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1'):
            print("   ✓ 检测到.doc文件（特定字节序列开头）")
            return 'word'
        
        # 检查HTML文档特征
        content_str = content.decode('utf-8', errors='ignore').lower()
        if '<html' in content_str or '<!doctype' in content_str or '<head' in content_str:
            print("   ✓ 检测到HTML文档特征")
            return 'html'
        
        # 尝试解析为Word文档
        try:
            Document(io.BytesIO(content))
            print("   ✓ 通过python-docx解析成功，确认为Word文档")
            return 'word'
        except Exception as parse_error:
            print(f"   ✗ python-docx解析失败: {parse_error}")
            print("   ✓ 默认为HTML文档")
            return 'html'
            
    except Exception as e:
        print(f"   ✗ 内容检测失败: {e}")
        return 'unknown'

def main():
    """主测试函数"""
    # 测试您提到的URL
    test_url = "https://uat.agentspro.cn/api/fs/s/6852bf3497dbe47b8a5d3025"
    
    print("开始测试文档类型检测...")
    print("=" * 60)
    
    result = test_document_detection(test_url)
    
    print("=" * 60)
    print(f"最终检测结果: {result}")
    
    if result == 'word':
        print("✓ 正确识别为Word文档")
    elif result == 'html':
        print("✗ 错误识别为HTML文档")
    else:
        print("? 无法确定文档类型")

if __name__ == "__main__":
    main() 