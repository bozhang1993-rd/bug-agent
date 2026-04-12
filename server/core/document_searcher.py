from typing import List, Optional, Dict, Any
from pathlib import Path
import re
import os
from .config import config


class DocumentType:
    """文档类型"""
    REQUIREMENT = "requirement"      # 需求文档
    DESIGN = "design"                # 设计文档
    TEST_CASE = "test_case"          # 测试用例
    API = "api"                      # API 文档
    OTHER = "other"                  # 其他


class Document:
    def __init__(self, doc_type: str, title: str, content: str, file_path: str):
        self.doc_type = doc_type
        self.title = title
        self.content = content
        self.file_path = file_path


class DocumentSearcher:
    """需求文档检索器"""
    
    def __init__(self):
        self.project_root = Path(config.project_root)
        self.document_dirs = config.get("project.document_dirs", ["docs", "doc", "."])
        self.file_extensions = [".md", ".txt", ".doc", ".docx"]
    
    def search(self, keyword: str, doc_type: Optional[str] = None, limit: int = 10) -> List[Dict[str, Any]]:
        """搜索文档"""
        results = []
        
        for doc_dir in self.document_dirs:
            dir_path = self.project_root / doc_dir
            if not dir_path.exists():
                continue
            
            for root, dirs, files in os.walk(dir_path):
                dirs[:] = [d for d in dirs if not d.startswith(".")]
                
                for file in files:
                    if not any(file.endswith(ext) for ext in self.file_extensions):
                        continue
                    
                    file_path = os.path.join(root, file)
                    
                    # 根据文档类型过滤
                    if doc_type and not self._match_doc_type(file, doc_type):
                        continue
                    
                    # 搜索关键词
                    matches = self._search_in_file(file_path, keyword)
                    if matches:
                        results.append({
                            "file": file_path,
                            "title": self._extract_title(file_path),
                            "matches": matches[:3],
                            "doc_type": self._detect_doc_type(file)
                        })
        
        return results[:limit]
    
    def _search_in_file(self, file_path: str, keyword: str) -> List[str]:
        """在文件中搜索关键词"""
        matches = []
        
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
            
            keyword_lower = keyword.lower()
            content_lower = content.lower()
            
            if keyword_lower in content_lower:
                lines = content.split("\n")
                for i, line in enumerate(lines):
                    if keyword_lower in line.lower():
                        context_start = max(0, i - 1)
                        context_end = min(len(lines), i + 2)
                        context = "\n".join(lines[context_start:context_end])
                        matches.append(context.strip())
        
        except Exception:
            pass
        
        return matches
    
    def _extract_title(self, file_path: str) -> str:
        """提取文档标题"""
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                first_lines = [f.readline() for _ in range(10)]
            
            for line in first_lines:
                line = line.strip()
                if line.startswith("# "):
                    return line[2:].strip()
                elif line and not line.startswith("<!--"):
                    return line[:50]
        
        except Exception:
            pass
        
        return Path(file_path).stem
    
    def _detect_doc_type(self, file_path: str) -> str:
        """检测文档类型"""
        file_name = Path(file_path).name.lower()
        
        if "需求" in file_name or "requirement" in file_name:
            return DocumentType.REQUIREMENT
        elif "设计" in file_name or "design" in file_name or "architecture" in file_name:
            return DocumentType.DESIGN
        elif "测试" in file_name or "test" in file_name:
            return DocumentType.TEST_CASE
        elif "api" in file_name or "接口" in file_name:
            return DocumentType.API
        else:
            return DocumentType.OTHER
    
    def _match_doc_type(self, file_path: str, doc_type: str) -> bool:
        """匹配文档类型"""
        detected = self._detect_doc_type(file_path)
        
        type_mapping = {
            "需求": DocumentType.REQUIREMENT,
            "设计": DocumentType.DESIGN,
            "测试": DocumentType.TEST_CASE,
            "api": DocumentType.API
        }
        
        target_type = type_mapping.get(doc_type, doc_type)
        return detected == target_type
    
    def get_document_content(self, file_path: str) -> Optional[str]:
        """获取文档内容"""
        if not os.path.exists(file_path):
            return None
        
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                return f.read()
        except Exception:
            return None
    
    def list_documents(self, doc_type: Optional[str] = None, limit: int = 20) -> List[Dict[str, Any]]:
        """列出所有文档"""
        documents = []
        
        for doc_dir in self.document_dirs:
            dir_path = self.project_root / doc_dir
            if not dir_path.exists():
                continue
            
            for root, dirs, files in os.walk(dir_path):
                dirs[:] = [d for d in dirs if not d.startswith(".")]
                
                for file in files:
                    if not any(file.endswith(ext) for ext in self.file_extensions):
                        continue
                    
                    file_path = os.path.join(root, file)
                    
                    if doc_type and not self._match_doc_type(file_path, doc_type):
                        continue
                    
                    documents.append({
                        "file": file_path,
                        "title": self._extract_title(file_path),
                        "doc_type": self._detect_doc_type(file_path)
                    })
        
        return documents[:limit]
