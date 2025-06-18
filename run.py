#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Flask应用启动脚本
"""

import os
import sys
from app import app

def main():
    """主启动函数"""
    print("=" * 50)
    print("文档解析API服务")
    print("=" * 50)
    print("服务正在启动...")
    print("访问地址: http://localhost:5000")
    print("API文档: http://localhost:5000/health")
    print("按 Ctrl+C 停止服务")
    print("=" * 50)
    
    try:
        # 设置环境变量
        os.environ['FLASK_ENV'] = 'development'
        
        # 启动Flask应用
        app.run(
            debug=True,
            host='0.0.0.0',
            port=5000,
            use_reloader=True
        )
    except KeyboardInterrupt:
        print("\n服务已停止")
    except Exception as e:
        print(f"启动失败: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 