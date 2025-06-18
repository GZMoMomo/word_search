from flask import Flask, request, jsonify
import requests
from bs4 import BeautifulSoup
import re
from urllib.parse import urljoin, urlparse
import logging
from docx import Document
import io
import os

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

class DocumentParser:
    """文档解析器类，支持HTML和Word文档"""
    
    def __init__(self, url):
        self.url = url
        self.soup = None
        self.doc = None
        self.document_type = self._detect_document_type()
        self._fetch_document()
    
    def _detect_document_type(self):
        """检测文档类型"""
        url_lower = self.url.lower()
        
        # 首先检查URL扩展名
        if url_lower.endswith(('.docx', '.doc')):
            return 'word'
        
        # 如果URL没有扩展名，通过HTTP请求检查Content-Type
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            # 只发送HEAD请求来获取响应头，不下载完整内容
            response = requests.head(self.url, headers=headers, timeout=5, allow_redirects=True)
            
            if response.status_code == 200:
                content_type = response.headers.get('Content-Type', '').lower()
                
                # 检查是否为Word文档的MIME类型
                if any(word_type in content_type for word_type in [
                    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',  # .docx
                    'application/msword',  # .doc
                    'application/vnd.ms-word',  # .doc
                ]):
                    return 'word'
                
                # 检查是否为HTML文档
                if any(html_type in content_type for html_type in [
                    'text/html',
                    'application/xhtml+xml'
                ]):
                    return 'html'
                
                # 如果Content-Type是application/octet-stream或其他通用类型，需要进一步检测
                if 'application/octet-stream' in content_type or not content_type:
                    # 下载一小部分内容来判断文件类型
                    return self._detect_by_content()
                
                # 如果Content-Type不明确，尝试通过文件扩展名或URL特征判断
                if 'word' in url_lower or 'doc' in url_lower:
                    return 'word'
                elif 'html' in url_lower or 'htm' in url_lower:
                    return 'html'
                
                # 默认返回HTML（保持向后兼容）
                logger.info(f"无法确定文档类型，Content-Type: {content_type}，默认返回HTML")
                return 'html'
            else:
                logger.warning(f"无法获取响应头，状态码: {response.status_code}，默认返回HTML")
                return 'html'
                
        except Exception as e:
            logger.warning(f"检测文档类型时出错: {e}，默认返回HTML")
            return 'html'
    
    def _detect_by_content(self):
        """通过文件内容特征判断文档类型"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            # 只下载前1024字节来判断文件类型
            response = requests.get(self.url, headers=headers, timeout=10, stream=True)
            response.raise_for_status()
            
            # 读取前1024字节
            content = b''
            for chunk in response.iter_content(chunk_size=1024):
                content += chunk
                if len(content) >= 1024:
                    break
            
            # 检查Word文档的文件头特征
            # .docx文件是ZIP格式，以PK开头
            # .doc文件以特定的字节序列开头
            if content.startswith(b'PK') or content.startswith(b'\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1'):
                logger.info("通过文件内容特征检测到Word文档")
                return 'word'
            
            # 检查HTML文档特征
            content_str = content.decode('utf-8', errors='ignore').lower()
            if '<html' in content_str or '<!doctype' in content_str or '<head' in content_str:
                logger.info("通过文件内容特征检测到HTML文档")
                return 'html'
            
            # 如果无法通过内容判断，尝试解析为Word文档
            # 如果解析失败，则认为是HTML
            try:
                Document(io.BytesIO(content))
                logger.info("通过尝试解析检测到Word文档")
                return 'word'
            except Exception:
                logger.info("无法解析为Word文档，默认为HTML")
                return 'html'
                
        except Exception as e:
            logger.warning(f"通过内容检测文档类型时出错: {e}，默认返回HTML")
            return 'html'
    
    def _fetch_document(self):
        """获取文档内容"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            response = requests.get(self.url, headers=headers, timeout=10)
            response.raise_for_status()
            
            if self.document_type == 'word':
                # 处理Word文档
                self.doc = Document(io.BytesIO(response.content))
                logger.info(f"成功获取Word文档: {self.url}")
            else:
                # 处理HTML文档
                response.encoding = response.apparent_encoding
                self.soup = BeautifulSoup(response.text, 'html.parser')
                logger.info(f"成功获取HTML文档: {self.url}")
                
        except Exception as e:
            logger.error(f"获取文档失败: {e}")
            raise
    
    def get_chapters(self, parent_chapter=None, return_content=False):
        """
        获取目录章节
        
        Args:
            parent_chapter (str, optional): 父级章节名称，如果为None则获取第一层级
            return_content (bool): 如果没有子章节，是否返回章节内容
            
        Returns:
            list: 章节列表，或者包含内容的字典
        """
        if self.document_type == 'word':
            return self._get_word_chapters(parent_chapter, return_content)
        else:
            return self._get_html_chapters(parent_chapter, return_content)
    
    def _get_word_chapters(self, parent_chapter=None, return_content=False):
        """从Word文档中获取章节"""
        if not self.doc:
            return []
        
        chapters = []
        current_level = 0
        parent_found = parent_chapter is None
        
        for paragraph in self.doc.paragraphs:
            # 检查段落样式来判断是否为标题
            if paragraph.style.name.startswith('Heading'):
                try:
                    level = int(paragraph.style.name.replace('Heading ', ''))
                except ValueError:
                    level = 1
                
                title = paragraph.text.strip()
                if not title:
                    continue
                
                # 如果指定了父章节，需要找到该章节的子章节
                if parent_chapter:
                    if parent_chapter in title:
                        parent_found = True
                        current_level = level
                        continue
                    elif parent_found:
                        # 如果已经找到父章节，检查当前章节是否是子章节
                        if level > current_level:
                            chapters.append({
                                'title': title,
                                'href': f"#heading_{len(chapters)}",
                                'level': level
                            })
                        elif level <= current_level:
                            # 遇到同级或更高级的标题，停止搜索子章节
                            break
                else:
                    # 获取第一层级章节（通常是Heading 1）
                    if level == 1:
                        chapters.append({
                            'title': title,
                            'href': f"#heading_{len(chapters)}",
                            'level': level
                        })
        
        # 如果没有找到子章节且要求返回内容，则返回父章节的内容
        if parent_chapter and not chapters and return_content:
            content = self.get_content(parent_chapter)
            if content and content != "未找到指定章节的内容":
                return {
                    'type': 'content',
                    'chapter': parent_chapter,
                    'content': content,
                    'is_leaf': True
                }
        
        if return_content:
            for chapter in chapters:
                chapter['content'] = self.get_content(chapter['title'])
        
        return chapters[:20]  # 限制返回数量
    
    def _get_html_chapters(self, parent_chapter=None, return_content=False):
        """从HTML文档中获取章节"""
        if not self.soup:
            return []
        
        chapters = []
        
        # 常见的目录选择器
        selectors = [
            'h1, h2, h3, h4, h5, h6',  # 标题标签
            '.chapter, .section, .toc-item',  # 常见的目录类
            'nav a, .toc a',  # 导航链接
            'ul li a, ol li a',  # 列表中的链接
        ]
        
        for selector in selectors:
            elements = self.soup.select(selector)
            if elements:
                for element in elements:
                    chapter_text = element.get_text(strip=True)
                    if chapter_text and len(chapter_text) > 1:
                        # 检查是否是子章节
                        if parent_chapter:
                            # 这里可以根据实际文档结构调整判断逻辑
                            # 简单示例：检查父章节是否在当前章节的父级元素中
                            parent = element.parent
                            while parent and parent != self.soup:
                                if parent_chapter in parent.get_text():
                                    chapters.append({
                                        'title': chapter_text,
                                        'href': element.get('href', ''),
                                        'level': self._get_heading_level(element.name) if element.name else 1
                                    })
                                    break
                                parent = parent.parent
                        else:
                            # 获取第一层级章节
                            if self._is_top_level_chapter(element):
                                chapters.append({
                                    'title': chapter_text,
                                    'href': element.get('href', ''),
                                    'level': self._get_heading_level(element.name) if element.name else 1
                                })
                
                if chapters:
                    break
        
        # 去重并返回
        unique_chapters = []
        seen_titles = set()
        for chapter in chapters:
            if chapter['title'] not in seen_titles:
                unique_chapters.append(chapter)
                seen_titles.add(chapter['title'])
        
        # 如果没有找到子章节且要求返回内容，则返回父章节的内容
        if parent_chapter and not unique_chapters and return_content:
            content = self.get_content(parent_chapter)
            if content and content != "未找到指定章节的内容":
                return {
                    'type': 'content',
                    'chapter': parent_chapter,
                    'content': content,
                    'is_leaf': True
                }
        
        if return_content:
            for chapter in unique_chapters:
                chapter['content'] = self.get_content(chapter['title'])
        
        return unique_chapters[:20]  # 限制返回数量
    
    def get_content(self, chapter_name=None):
        """
        获取章节内容
        
        Args:
            chapter_name (str, optional): 章节名称，如果为None则获取整个文档内容
            
        Returns:
            str: 章节内容
        """
        if self.document_type == 'word':
            return self._get_word_content(chapter_name)
        else:
            return self._get_html_content(chapter_name)
    
    def _get_word_content(self, chapter_name=None):
        """从Word文档中获取内容"""
        if not self.doc:
            return ""
        
        content_parts = []
        in_target_chapter = chapter_name is None
        
        for paragraph in self.doc.paragraphs:
            text = paragraph.text.strip()
            if not text:
                continue
            
            # 检查是否是标题
            if paragraph.style.name.startswith('Heading'):
                if chapter_name and chapter_name in text:
                    # 找到目标章节
                    in_target_chapter = True
                    continue
                elif in_target_chapter and paragraph.style.name.startswith('Heading'):
                    # 遇到下一个标题，停止收集内容
                    break
            elif in_target_chapter:
                # 收集章节内容
                content_parts.append(text)
        
        return self._clean_content('\n'.join(content_parts))
    
    def _get_html_content(self, chapter_name=None):
        """从HTML文档中获取内容"""
        if not self.soup:
            return ""
        
        if not chapter_name:
            # 返回整个文档的主要内容
            content_selectors = [
                'main',
                'article',
                '.content',
                '.main-content',
                'body'
            ]
            
            for selector in content_selectors:
                content_element = self.soup.select_one(selector)
                if content_element:
                    return self._clean_content(content_element.get_text())
            
            return self._clean_content(self.soup.get_text())
        
        # 查找指定章节的内容
        # 首先尝试通过标题查找
        headings = self.soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
        
        for heading in headings:
            if chapter_name in heading.get_text():
                # 找到章节标题，获取其后的内容
                content = []
                current = heading.next_sibling
                
                while current:
                    if current.name and current.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                        # 遇到下一个标题，停止
                        break
                    if hasattr(current, 'get_text'):
                        text = current.get_text(strip=True)
                        if text:
                            content.append(text)
                    current = current.next_sibling
                
                return self._clean_content('\n'.join(content))
        
        # 如果通过标题没找到，尝试通过链接查找
        links = self.soup.find_all('a')
        for link in links:
            if chapter_name in link.get_text():
                href = link.get('href')
                if href:
                    # 获取链接指向的内容
                    try:
                        full_url = urljoin(self.url, href)
                        response = requests.get(full_url, timeout=10)
                        response.raise_for_status()
                        response.encoding = response.apparent_encoding
                        chapter_soup = BeautifulSoup(response.text, 'html.parser')
                        
                        # 提取主要内容
                        content_selectors = ['main', 'article', '.content', '.main-content']
                        for selector in content_selectors:
                            content_element = chapter_soup.select_one(selector)
                            if content_element:
                                return self._clean_content(content_element.get_text())
                        
                        return self._clean_content(chapter_soup.get_text())
                    except Exception as e:
                        logger.error(f"获取章节内容失败: {e}")
                        continue
        
        return "未找到指定章节的内容"
    
    def _is_top_level_chapter(self, element):
        """判断是否为顶级章节"""
        # 检查父级元素，如果父级是body或main等，则认为是顶级章节
        parent = element.parent
        while parent and parent != self.soup:
            if parent.name in ['body', 'main', 'article', 'div']:
                return True
            parent = parent.parent
        return False
    
    def _get_heading_level(self, tag_name):
        """获取标题级别"""
        if tag_name and tag_name.startswith('h'):
            try:
                return int(tag_name[1])
            except ValueError:
                pass
        return 1
    
    def _clean_content(self, content):
        """清理内容文本"""
        if not content:
            return ""
        
        # 移除多余的空白字符
        content = re.sub(r'\s+', ' ', content)
        content = re.sub(r'\n\s*\n', '\n\n', content)
        
        # 限制内容长度
        if len(content) > 10000:
            content = content[:10000] + "..."
        
        return content.strip()

@app.route('/api/chapters', methods=['GET'])
def get_chapters():
    """
    获取目录章节API
    
    参数:
    - url (必选): 文件URL
    - chapter (可选): 父级章节名称
    
    返回:
    - JSON格式的章节列表，如果指定章节没有子章节则返回该章节的内容
    """
    try:
        # 获取参数
        file_url = request.args.get('url')
        parent_chapter = request.args.get('chapter')
        
        # 验证必选参数
        if not file_url:
            return jsonify({
                'success': False,
                'error': '缺少必选参数: url'
            }), 400
        
        # 验证URL格式
        try:
            parsed_url = urlparse(file_url)
            if not parsed_url.scheme or not parsed_url.netloc:
                return jsonify({
                    'success': False,
                    'error': '无效的URL格式'
                }), 400
        except Exception:
            return jsonify({
                'success': False,
                'error': '无效的URL格式'
            }), 400
        
        # 解析文档
        parser = DocumentParser(file_url)
        
        # 如果指定了章节，尝试获取子章节，如果没有子章节则返回内容
        if parent_chapter:
            chapters = parser.get_chapters(parent_chapter, return_content=True)
            
            # 检查是否返回的是内容而不是章节列表
            if isinstance(chapters, dict) and chapters.get('type') == 'content':
                return jsonify({
                    'success': True,
                    'data': {
                        'url': file_url,
                        'document_type': parser.document_type,
                        'parent_chapter': parent_chapter,
                        'type': 'content',
                        'is_leaf': True,
                        'content': chapters['content'],
                        'content_length': len(chapters['content'])
                    }
                })
            else:
                return jsonify({
                    'success': True,
                    'data': {
                        'url': file_url,
                        'document_type': parser.document_type,
                        'parent_chapter': parent_chapter,
                        'type': 'chapters',
                        'chapters': chapters,
                        'count': len(chapters)
                    }
                })
        else:
            # 获取第一层级章节
            chapters = parser.get_chapters()
            return jsonify({
                'success': True,
                'data': {
                    'url': file_url,
                    'document_type': parser.document_type,
                    'parent_chapter': parent_chapter,
                    'type': 'chapters',
                    'chapters': chapters,
                    'count': len(chapters)
                }
            })
        
    except Exception as e:
        logger.error(f"获取章节失败: {e}")
        return jsonify({
            'success': False,
            'error': f'获取章节失败: {str(e)}'
        }), 500

@app.route('/api/content', methods=['GET'])
def get_content():
    """
    获取章节内容API
    
    参数:
    - url (必选): 文件URL
    - chapter (可选): 章节名称
    
    返回:
    - JSON格式的章节内容
    """
    try:
        # 获取参数
        file_url = request.args.get('url')
        chapter_name = request.args.get('chapter')
        
        # 验证必选参数
        if not file_url:
            return jsonify({
                'success': False,
                'error': '缺少必选参数: url'
            }), 400
        
        # 验证URL格式
        try:
            parsed_url = urlparse(file_url)
            if not parsed_url.scheme or not parsed_url.netloc:
                return jsonify({
                    'success': False,
                    'error': '无效的URL格式'
                }), 400
        except Exception:
            return jsonify({
                'success': False,
                'error': '无效的URL格式'
            }), 400
        
        # 解析文档
        parser = DocumentParser(file_url)
        content = parser.get_content(chapter_name)
        
        return jsonify({
            'success': True,
            'data': {
                'url': file_url,
                'document_type': parser.document_type,
                'chapter': chapter_name,
                'content': content,
                'content_length': len(content)
            }
        })
        
    except Exception as e:
        logger.error(f"获取内容失败: {e}")
        return jsonify({
            'success': False,
            'error': f'获取内容失败: {str(e)}'
        }), 500

@app.route('/health', methods=['GET'])
def health_check():
    """健康检查接口"""
    return jsonify({
        'status': 'healthy',
        'message': '服务运行正常',
        'supported_formats': ['HTML', 'Word (.docx, .doc)']
    })

@app.errorhandler(404)
def not_found(error):
    return jsonify({
        'success': False,
        'error': '接口不存在'
    }), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({
        'success': False,
        'error': '服务器内部错误'
    }), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000) 