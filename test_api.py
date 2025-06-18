#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试API功能的脚本
"""

import requests
import json

def test_chapters_api():
    """测试章节API"""
    base_url = "http://localhost:5000"
    
    # 测试用例1：获取第一层级章节
    print("=== 测试1：获取第一层级章节 ===")
    response = requests.get(f"{base_url}/api/chapters", params={
        'url': 'https://example.com/test.html'
    })
    print(f"状态码: {response.status_code}")
    print(f"响应: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
    print()
    
    # 测试用例2：获取指定章节的子章节
    print("=== 测试2：获取指定章节的子章节 ===")
    response = requests.get(f"{base_url}/api/chapters", params={
        'url': 'https://example.com/test.html',
        'chapter': '第一章'
    })
    print(f"状态码: {response.status_code}")
    print(f"响应: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
    print()
    
    # 测试用例3：获取最子目录的内容
    print("=== 测试3：获取最子目录的内容 ===")
    response = requests.get(f"{base_url}/api/chapters", params={
        'url': 'https://example.com/test.html',
        'chapter': '最子章节'
    })
    print(f"状态码: {response.status_code}")
    print(f"响应: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
    print()

def test_content_api():
    """测试内容API"""
    base_url = "http://localhost:5000"
    
    print("=== 测试内容API ===")
    response = requests.get(f"{base_url}/api/content", params={
        'url': 'https://example.com/test.html',
        'chapter': '第一章'
    })
    print(f"状态码: {response.status_code}")
    print(f"响应: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
    print()

def test_health_api():
    """测试健康检查API"""
    base_url = "http://localhost:5000"
    
    print("=== 测试健康检查API ===")
    response = requests.get(f"{base_url}/health")
    print(f"状态码: {response.status_code}")
    print(f"响应: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
    print()

if __name__ == "__main__":
    try:
        test_health_api()
        test_chapters_api()
        test_content_api()
    except requests.exceptions.ConnectionError:
        print("错误：无法连接到服务器，请确保服务器正在运行在 http://localhost:5000")
    except Exception as e:
        print(f"测试过程中出现错误: {e}") 