import os
import re
from pathlib import Path
from typing import Optional, List, Tuple, Dict, Any
from .config import config


class CodeLocator:
    def __init__(self):
        self.project_root = Path(config.project_root)
        self.package_base = config.java_package_base
        self.source_dirs = config.get("project.source_dirs", ["src/main/java"])

    def locate_file(self, class_name: str) -> Optional[str]:
        class_name = class_name.replace("$", ".")
        
        for source_dir in self.source_dirs:
            source_path = self.project_root / source_dir
            
            if not source_path.exists():
                continue
            
            package_path = self._class_to_package_path(class_name)
            full_path = source_path / package_path
            
            if full_path.exists():
                return str(full_path)
            
            java_file = source_path / f"{class_name.replace('.', '/')}.java"
            if java_file.exists():
                return str(java_file)
        
        return self._search_in_project(class_name)

    def _class_to_package_path(self, class_name: str) -> str:
        parts = class_name.split(".")
        
        if parts[0] == self.package_base.split(".")[0]:
            return "/".join(parts) + ".java"
        
        return "/".join(parts) + ".java"

    def _search_in_project(self, class_name: str) -> Optional[str]:
        class_name_clean = class_name.split("$")[0]
        
        for root, dirs, files in os.walk(self.project_root):
            dirs[:] = [d for d in dirs if d not in config.get("project.exclude_dirs", [])]
            
            for file in files:
                if file.endswith(".java"):
                    if file.startswith(class_name_clean.split(".")[-1] + ".java"):
                        full_path = os.path.join(root, file)
                        if self._check_class_match(full_path, class_name_clean):
                            return full_path
        
        return None

    def _check_class_match(self, file_path: str, class_name: str) -> bool:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
                
                class_simple_name = class_name.split(".")[-1]
                if f"class {class_simple_name}" in content or f"interface {class_simple_name}" in content:
                    return True
        except Exception:
            pass
        return False

    # ============ 基础方法 ============

    def load_context(self, file_path: str, error_line: int, context_lines: int = 10) -> str:
        if not os.path.exists(file_path):
            return f"文件不存在: {file_path}"
        
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
            
            start = max(0, error_line - context_lines - 1)
            end = min(len(lines), error_line + context_lines)
            
            context = []
            for i in range(start, end):
                line_num = i + 1
                marker = ">>>" if line_num == error_line else "   "
                context.append(f"{marker} {line_num:4d} | {lines[i].rstrip()}")
            
            return "\n".join(context)
        except Exception as e:
            return f"读取文件失败: {str(e)}"

    # ============ 完整方法分析 ============

    def get_method_info(self, file_path: str, line_number: int) -> Optional[Dict[str, Any]]:
        """获取方法完整信息"""
        if not os.path.exists(file_path):
            return None
        
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
            
            return self._find_method_boundaries(lines, line_number)
        except Exception:
            return None

    def _find_method_boundaries(self, lines: List[str], target_line: int) -> Optional[Dict[str, Any]]:
        """查找方法的开始和结束行"""
        method_pattern = re.compile(
            r"(public|private|protected)?\s*"
            r"(static\s+)?"
            r"(@\w+\s+)*"
            r"(\w+[\<\w+\>]?)\s+"
            r"(\w+)\s*\(([^)]*)\)"
        )
        
        class_pattern = re.compile(
            r"(public|private|protected)?\s*"
            r"(class|interface|enum)\s+(\w+)"
        )
        
        current_class = None
        methods = []
        
        for i, line in enumerate(lines):
            line_num = i + 1
            
            class_match = class_pattern.search(line)
            if class_match:
                current_class = class_match.group(3)
            
            if "{" in line:
                method_match = method_pattern.search(line)
                if method_match:
                    method_name = method_match.group(5)
                    params = method_match.group(6)
                    is_static = "static" in method_match.group(2) or ""
                    modifier = method_match.group(1) or "package-private"
                    
                    methods.append({
                        "start": line_num,
                        "name": method_name,
                        "params": params,
                        "modifier": modifier,
                        "is_static": bool(is_static),
                        "class": current_class
                    })
        
        method_info = None
        for method in reversed(methods):
            if method["start"] <= target_line:
                method_info = method
                method_end = self._find_method_end(lines, method["start"])
                method_info["end"] = method_end
                method_info["full_content"] = self._get_method_content(lines, method["start"], method_end)
                break
        
        return method_info

    def _find_method_end(self, lines: List[str], start_line: int) -> int:
        """查找方法结束行"""
        brace_count = 0
        start_idx = start_line - 1
        
        for i in range(start_idx, len(lines)):
            brace_count += lines[i].count("{") - lines[i].count("}")
            if brace_count == 0 and i > start_idx:
                return i + 1
        
        return len(lines)

    def _get_method_content(self, lines: List[str], start: int, end: int) -> str:
        """获取方法完整内容"""
        content = []
        for i in range(start - 1, min(end, len(lines))):
            line_num = i + 1
            content.append(f"{line_num:4d} | {lines[i].rstrip()}")
        return "\n".join(content)

    def load_full_method(self, file_path: str, line_number: int) -> str:
        """加载完整方法体"""
        method_info = self.get_method_info(file_path, line_number)
        if method_info and method_info.get("full_content"):
            return method_info["full_content"]
        return self.load_context(file_path, line_number, 20)

    # ============ 调用链分析 ============

    def analyze_call_chain(self, file_path: str, line_number: int) -> Dict[str, Any]:
        """分析方法的调用链"""
        if not os.path.exists(file_path):
            return {"error": "文件不存在"}
        
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
            
            method_info = self.get_method_info(file_path, line_number)
            if not method_info:
                return {"error": "无法定位方法"}
            
            calls = self._extract_method_calls(lines, method_info["start"], method_info["end"])
            called_by = self._find_methods_calling(lines, method_info["name"])
            
            return {
                "method": method_info["name"],
                "class": method_info.get("class"),
                "calls": calls,
                "called_by": called_by
            }
        except Exception as e:
            return {"error": str(e)}

    def _extract_method_calls(self, lines: List[str], start: int, end: int) -> List[Dict[str, str]]:
        """提取方法内的调用"""
        calls = []
        
        call_pattern = re.compile(
            r"(\w+[\.\w+]*)\.(\w+)\s*\("
        )
        
        for i in range(start - 1, min(end, len(lines))):
            line = lines[i]
            matches = call_pattern.findall(line)
            for obj, method in matches:
                if not method.startswith("assert"):
                    calls.append({
                        "object": obj,
                        "method": method,
                        "line": i + 1
                    })
        
        return calls

    def _find_methods_calling(self, lines: List[str], target_method: str) -> List[Dict[str, Any]]:
        """查找调用该方法的其他方法"""
        callers = []
        
        call_pattern = re.compile(
            rf"\.{target_method}\s*\("
        )
        
        method_pattern = re.compile(
            r"(public|private|protected)?\s*(static\s+)?(\w+[\<\w+\>]?)\s+(\w+)\s*\(([^)]*)\)"
        )
        
        current_method = None
        current_class = None
        
        for i, line in enumerate(lines):
            method_match = method_pattern.search(line)
            if method_match:
                current_method = method_match.group(4)
                current_class = None
            
            class_match = re.search(r"class\s+(\w+)", line)
            if class_match:
                current_class = class_match.group(1)
            
            if call_pattern.search(line) and current_method:
                callers.append({
                    "method": current_method,
                    "class": current_class,
                    "line": i + 1
                })
        
        return callers

    # ============ 相关类加载 ============

    def get_related_classes(self, file_path: str) -> List[Dict[str, str]]:
        """获取相关的类（通过 Import）"""
        if not os.path.exists(file_path):
            return []
        
        related = []
        
        import_pattern = re.compile(r"import\s+([\w\.]+);")
        static_import_pattern = re.compile(r"import\s+static\s+([\w\.]+);")
        
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                for line in f:
                    match = import_pattern.match(line.strip())
                    if match:
                        class_name = match.group(1)
                        file_path = self.locate_file(class_name)
                        if file_path:
                            related.append({
                                "import": class_name,
                                "file": file_path
                            })
                    
                    match = static_import_pattern.match(line.strip())
                    if match:
                        related.append({
                            "import": match.group(1),
                            "static": True
                        })
        except Exception:
            pass
        
        return related

    def load_related_classes(self, file_path: str, limit: int = 3) -> str:
        """加载相关类的代码"""
        related = self.get_related_classes(file_path)
        
        content = []
        for rel in related[:limit]:
            if "file" in rel and rel["file"]:
                try:
                    with open(rel["file"], "r", encoding="utf-8") as f:
                        lines = f.readlines()[:50]
                    
                    content.append(f"\n=== {rel['import']} ===")
                    content.append("".join(lines))
                except Exception:
                    pass
        
        return "\n".join(content)

    # ============ 获取完整类 ============

    def load_full_class(self, file_path: str) -> str:
        """加载完整类的代码"""
        if not os.path.exists(file_path):
            return "文件不存在"
        
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
            
            content = []
            for i, line in enumerate(lines):
                content.append(f"{i+1:4d} | {line.rstrip()}")
            
            return "\n".join(content)
        except Exception as e:
            return f"读取失败: {str(e)}"

    # ============ 增强代码分析 ============

    def get_enhanced_context(self, file_path: str, line_number: int) -> Dict[str, Any]:
        """获取增强的代码上下文"""
        result = {
            "file": file_path,
            "line": line_number,
            "method": None,
            "full_method": None,
            "call_chain": None,
            "related_classes": None,
            "full_class": None
        }
        
        if not os.path.exists(file_path):
            return result
        
        method_info = self.get_method_info(file_path, line_number)
        if method_info:
            result["method"] = {
                "name": method_info["name"],
                "class": method_info.get("class"),
                "modifier": method_info.get("modifier"),
                "params": method_info.get("params"),
                "start": method_info["start"],
                "end": method_info["end"]
            }
            result["full_method"] = method_info.get("full_content")
        
        call_chain = self.analyze_call_chain(file_path, line_number)
        result["call_chain"] = call_chain
        
        related = self.get_related_classes(file_path)
        result["related_classes"] = related[:5]
        
        result["full_class"] = self.load_full_class(file_path)
        
        return result

    # ============ 原有方法保持兼容 ============

    def get_method_context(self, file_path: str, line_number: int) -> Optional[dict]:
        if not os.path.exists(file_path):
            return None
        
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
            
            method_info = {
                "method_name": None,
                "class_name": None,
                "method_start": None,
                "method_end": None
            }
            
            class_pattern = re.compile(r"(public|private|protected)?\s+(class|interface|enum)\s+(\w+)")
            method_pattern = re.compile(r"(public|private|protected|\s)+(static\s+)?(\w+[\<\w+\>]?)\s+\(([^)]*)\)")

            current_class = None
            method_start = None
            
            for i, line in enumerate(lines):
                class_match = class_pattern.search(line)
                if class_match:
                    current_class = class_match.group(3)
                    method_info["class_name"] = current_class

                if method_start is None:
                    method_match = method_pattern.search(line)
                    if method_match and (line.strip().startswith("public") or line.strip().startswith("private")):
                        method_info["method_name"] = method_match.group(3)
                        method_start = i + 1
                        method_info["method_start"] = method_start
                
                if method_start and line.strip().startswith("}"):
                    method_info["method_end"] = i + 1
                    if line_number <= method_info["method_end"]:
                        break
            
            return method_info
        except Exception:
            return None

    def find_related_files(self, class_name: str) -> List[str]:
        related = []
        class_name_clean = class_name.split("$")[0]
        
        base_dir = self.project_root / "src" / "main" / "java"
        if not base_dir.exists():
            return related
        
        package_dir = "/".join(class_name_clean.split(".")[:-1])
        package_path = base_dir / package_dir
        
        if package_path.exists():
            for file in package_path.iterdir():
                if file.is_file() and file.suffix == ".java":
                    related.append(str(file))
        
        return related

    def get_imports(self, file_path: str) -> List[str]:
        if not os.path.exists(file_path):
            return []
        
        imports = []
        import_pattern = re.compile(r"import\s+([\w\.]+);")
        
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                for line in f:
                    match = import_pattern.match(line.strip())
                    if match:
                        imports.append(match.group(1))
        except Exception:
            pass
        
        return imports

    def resolve_file_path(self, frame: dict) -> Optional[Tuple[str, int]]:
        class_name = frame.get("class_name", "")
        line_number = frame.get("file_name", "")
        
        if ":" in str(line_number):
            parts = str(line_number).rsplit(":", 1)
            try:
                line_number = int(parts[1])
            except ValueError:
                line_number = 0
        
        file_path = self.locate_file(class_name)
        
        if file_path:
            return (file_path, line_number)
        
        return None
