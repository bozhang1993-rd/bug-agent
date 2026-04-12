import os
import re
from pathlib import Path
from typing import Optional, List, Tuple
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
                    brace_count = line.count("}")
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
