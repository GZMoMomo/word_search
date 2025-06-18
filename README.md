# 文档解析API服务

这是一个基于Flask的文档解析API服务，可以从HTML文档和Word文档中提取目录章节和内容。

## 功能特性

- 支持从HTML文档和Word文档中提取目录结构
- 支持获取指定章节的内容
- 智能解析多种HTML结构和Word文档格式
- 支持层级目录导航
- 自动编码检测和内容清理
- 使用python-docx高效解析Word文档
- **新增功能**：当指定章节没有子章节时，自动返回该章节的正文内容

## 支持的文档格式

- **HTML文档**: 支持所有HTML格式的网页文档
- **Word文档**: 支持.docx和.doc格式的Word文档

## 安装依赖

```bash
pip install -r requirements.txt
```

## 运行服务

```bash
python app.py
# 或者
python run.py
```

服务将在 `http://localhost:5000` 启动

## API接口

### 1. 获取目录章节

**接口地址:** `GET /api/chapters`

**参数:**
- `url` (必选): 要解析的文档URL
- `chapter` (可选): 父级章节名称，如果不传则获取第一层级目录

**示例请求:**
```bash
# 获取HTML文档的第一层级目录
curl "http://localhost:5000/api/chapters?url=https://example.com/document.html"

# 获取Word文档的第一层级目录
curl "http://localhost:5000/api/chapters?url=https://example.com/document.docx"

# 获取指定章节的子目录
curl "http://localhost:5000/api/chapters?url=https://example.com/document.docx&chapter=第一章"

# 获取最子目录的内容（当指定章节没有子章节时）
curl "http://localhost:5000/api/chapters?url=https://example.com/document.docx&chapter=最子章节"
```

**响应格式:**

当获取到子章节时：
```json
{
  "success": true,
  "data": {
    "url": "https://example.com/document.docx",
    "document_type": "word",
    "parent_chapter": "第一章",
    "type": "chapters",
    "chapters": [
      {
        "title": "1.1 概述",
        "href": "#heading_0",
        "level": 2
      },
      {
        "title": "1.2 详细说明",
        "href": "#heading_1",
        "level": 2
      }
    ],
    "count": 2
  }
}
```

当指定章节没有子章节时（最子目录）：
```json
{
  "success": true,
  "data": {
    "url": "https://example.com/document.docx",
    "document_type": "word",
    "parent_chapter": "最子章节",
    "type": "content",
    "is_leaf": true,
    "content": "这是最子章节的正文内容...",
    "content_length": 1500
  }
}
```

### 2. 获取章节内容

**接口地址:** `GET /api/content`

**参数:**
- `url` (必选): 要解析的文档URL
- `chapter` (可选): 章节名称，如果不传则获取整个文档内容

**示例请求:**
```bash
# 获取整个文档内容
curl "http://localhost:5000/api/content?url=https://example.com/document.docx"

# 获取指定章节内容
curl "http://localhost:5000/api/content?url=https://example.com/document.docx&chapter=第一章"
```

**响应格式:**
```json
{
  "success": true,
  "data": {
    "url": "https://example.com/document.docx",
    "document_type": "word",
    "chapter": "第一章",
    "content": "这是第一章的内容...",
    "content_length": 1500
  }
}
```

### 3. 健康检查

**接口地址:** `GET /health`

**示例请求:**
```bash
curl "http://localhost:5000/health"
```

**响应格式:**
```json
{
  "status": "healthy",
  "message": "服务运行正常",
  "supported_formats": ["HTML", "Word (.docx, .doc)"]
}
```

## 新增功能：最子目录内容返回

### 功能说明

在 `/api/chapters` 接口中，当用户指定的章节没有子章节时，系统会自动判断该章节为最子目录，并返回该章节的正文内容，而不是返回空的章节列表。

### 实现逻辑

1. 当指定 `chapter` 参数时，系统首先尝试查找该章节的子章节
2. 如果没有找到子章节，系统会自动获取该章节的正文内容
3. 返回的数据结构包含 `type: "content"` 和 `is_leaf: true` 标识

### 使用场景

- **简化前端逻辑**：无需额外调用 `/api/content` 接口
- **提升用户体验**：自动识别最子目录，减少用户操作步骤
- **保持API一致性**：使用同一个接口处理章节和内容

### 示例

```bash
# 假设"1.2 详细说明"是最子章节，没有子章节
curl "http://localhost:5000/api/chapters?url=https://example.com/document.docx&chapter=1.2 详细说明"
```

响应：
```json
{
  "success": true,
  "data": {
    "url": "https://example.com/document.docx",
    "document_type": "word",
    "parent_chapter": "1.2 详细说明",
    "type": "content",
    "is_leaf": true,
    "content": "这是1.2章节的详细说明内容...",
    "content_length": 800
  }
}
```

## 错误处理

所有API接口都包含统一的错误处理机制：

```json
{
  "success": false,
  "error": "错误描述信息"
}
```

常见错误码：
- `400`: 参数错误（如缺少必选参数、URL格式错误）
- `404`: 接口不存在
- `500`: 服务器内部错误

## 技术实现

### 文档解析策略

#### HTML文档解析
1. **目录提取**: 使用多种CSS选择器来识别目录结构
   - 标题标签 (h1-h6)
   - 常见的目录类名 (.chapter, .section, .toc-item)
   - 导航链接 (nav a, .toc a)
   - 列表中的链接 (ul li a, ol li a)

2. **内容提取**: 智能识别文档的主要内容区域
   - 优先提取语义化标签 (main, article)
   - 支持常见的内容容器类名 (.content, .main-content)
   - 自动清理和格式化文本内容

#### Word文档解析
1. **目录提取**: 使用python-docx库解析Word文档
   - 基于段落样式识别标题（Heading 1, Heading 2等）
   - 自动识别章节层级关系
   - 支持父子章节导航

2. **内容提取**: 按章节提取Word文档内容
   - 基于标题样式定位章节
   - 提取章节间的正文内容
   - 保持文档结构完整性

### 性能优化

- 内容长度限制（最大10000字符）
- 章节数量限制（最大20个）
- 请求超时设置（10秒）
- 自动编码检测
- 文档类型自动识别

## 使用示例

### Python客户端示例

```python
import requests

# 获取HTML文档目录
response = requests.get('http://localhost:5000/api/chapters', params={
    'url': 'https://example.com/document.html'
})
chapters = response.json()

# 获取Word文档目录
response = requests.get('http://localhost:5000/api/chapters', params={
    'url': 'https://example.com/document.docx'
})
chapters = response.json()

# 获取最子目录内容
response = requests.get('http://localhost:5000/api/chapters', params={
    'url': 'https://example.com/document.docx',
    'chapter': '最子章节'
})
result = response.json()

# 检查返回类型
if result['data']['type'] == 'content':
    print("这是最子目录，内容：", result['data']['content'])
else:
    print("这是目录，子章节：", result['data']['chapters'])
```

## 测试

运行测试脚本：
```bash
python test_api.py
```

测试脚本会验证以下功能：
- 健康检查接口
- 获取第一层级章节
- 获取指定章节的子章节
- 获取最子目录的内容
- 获取指定章节内容 