import os
import re
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from .log_parser import StackTraceInfo
from .code_locator import CodeLocator
from .llm.client import LLMClient


@dataclass
class FixSuggestion:
    root_cause: str
    fix_suggestion: str
    fix_code: str
    confidence: float
    file_path: Optional[str] = None
    line_number: Optional[int] = None


class Fixer:
    def __init__(self):
        self.code_locator = CodeLocator()
        self.llm_client = LLMClient()

    def generate_fix(self, error_info: Dict[str, Any], context: str, error_type: str) -> FixSuggestion:
        result = self.llm_client.analyze_error(error_info, context, error_type)
        
        return FixSuggestion(
            root_cause=result.get("root_cause", ""),
            fix_suggestion=result.get("fix_suggestion", ""),
            fix_code=result.get("fix_code", ""),
            confidence=result.get("confidence", 0.8)
        )

    def apply_fix(self, file_path: str, fix: FixSuggestion) -> bool:
        if not file_path or not os.path.exists(file_path):
            return False
        
        if not fix.fix_code:
            return False
        
        try:
            line_number = fix.line_number
            if not line_number:
                return False
            
            with open(file_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
            
            lines.insert(line_number - 1, fix.fix_code + "\n")
            
            with open(file_path, "w", encoding="utf-8") as f:
                f.writelines(lines)
            
            return True
        except Exception as e:
            print(f"应用修复失败: {str(e)}")
            return False

    def create_patch(self, file_path: str, fix: FixSuggestion) -> str:
        if not fix.fix_code:
            return ""
        
        line_number = fix.line_number or 0
        
        patch = f"""--- a/{file_path}
+++ b/{file_path} @@
@@ -{line_number},0 +{line_number},1 @@
+{fix.fix_code}
"""
        return patch

    def preview_fix(self, file_path: str, fix: FixSuggestion) -> Dict[str, Any]:
        if not os.path.exists(file_path):
            return {"error": "文件不存在"}
        
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
            
            line_number = fix.line_number or 1
            start = max(0, line_number - 6)
            end = min(len(lines), line_number + 3)
            
            preview_lines = []
            for i in range(start, end):
                marker = ">>>" if i == line_number - 1 else "   "
                preview_lines.append(f"{marker} {i+1:4d} | {lines[i].rstrip()}")
            
            if fix.fix_code:
                preview_lines.append(f"+++ {line_number:4d} | {fix.fix_code}")
            
            return {
                "preview": "\n".join(preview_lines),
                "file_path": file_path,
                "line_number": line_number
            }
        except Exception as e:
            return {"error": str(e)}

    def quick_fix(self, error_type: str, frame_info: dict) -> Optional[str]:
        class_name = frame_info.get("class_name", "")
        method_name = frame_info.get("method_name", "")
        
        if error_type == "NULL_POINTER":
            return self._null_pointer_fix(class_name, method_name)
        elif error_type == "ILLEGAL_ARGUMENT":
            return self._illegal_argument_fix(method_name)
        elif error_type == "INDEX_OUT_OF_BOUNDS":
            return self._index_bounds_fix()
        else:
            return None

    def _null_pointer_fix(self, class_name: str, method_name: str) -> str:
        return f"""if ({class_name.split('.')[-1].lower()} == null) {{
    throw new IllegalArgumentException("{class_name.split('.')[-1]} cannot be null");
}}"""

    def _illegal_argument_fix(self, method_name: str) -> str:
        return f"""if (/* condition */) {{
    throw new IllegalArgumentException("Invalid parameter for {method_name}");
}}"""

    def _index_bounds_fix(self) -> str:
        return "if (index < 0 || index >= collection.size()) {\n    throw new IndexOutOfBoundsException(...);\n}"


def get_fixer() -> Fixer:
    return Fixer()
