import os
import re
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from .log_parser import StackTraceInfo, ErrorCategory
from .code_locator import CodeLocator
from .llm.client import LLMClient
from .llm.prompt import (
    build_analysis_prompt, 
    build_enhanced_analysis_prompt,
    build_upstream_analysis_prompt,
    build_downstream_analysis_prompt,
    build_db_analysis_prompt
)


@dataclass
class FixSuggestion:
    root_cause: str
    fix_suggestion: str
    fix_code: str
    confidence: float
    file_path: Optional[str] = None
    line_number: Optional[int] = None
    error_category: Optional[str] = None
    analysis_focus: Optional[List[str]] = None


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
            confidence=result.get("confidence", 0.8),
            error_category=error_type,
            analysis_focus=[]
        )

    def generate_enhanced_fix(
        self, 
        error_info: Dict[str, Any], 
        error_type: str,
        file_path: str,
        line_number: int,
        error_category: Optional[Dict[str, Any]] = None
    ) -> FixSuggestion:
        """增强版修复：使用完整的代码分析 + 错误分类"""
        
        enhanced_context = self.code_locator.get_enhanced_context(file_path, line_number)
        
        method_info = enhanced_context.get("method")
        full_method = enhanced_context.get("full_method", "")
        call_chain = enhanced_context.get("call_chain")
        related_classes = enhanced_context.get("related_classes", [])
        
        if not full_method:
            return self.generate_fix(error_info, "无法加载方法代码", error_type)
        
        # 根据错误分类选择不同的 prompt
        category = error_category.get("category", "UNKNOWN") if error_category else "UNKNOWN"
        
        prompt = self._build_category_prompt(
            category=category,
            error_info=error_info,
            error_category=error_category,
            method_info=method_info,
            full_method=full_method,
            call_chain=call_chain,
            related_classes=related_classes,
            error_type=error_type
        )
        
        messages = [
            {"role": "system", "content": self._get_system_prompt(category)},
            {"role": "user", "content": prompt}
        ]
        
        result = self.llm_client.chat(messages)
        
        return self._parse_enhanced_result(result, file_path, line_number, category)

    def _get_system_prompt(self, category: str) -> str:
        """根据错误分类返回不同的系统提示"""
        prompts = {
            ErrorCategory.CODE_DEFECT: "你是一个资深的Java开发工程师，擅长分析代码Bug并给出精确的修复方案。重点关注代码本身的缺陷。",
            ErrorCategory.UPSTREAM_PARAM: "你是一个资深的Java开发工程师，擅长分析上游参数问题。请重点分析调用方传入的参数是否正确。",
            ErrorCategory.UPSTREAM_DATA: "你是一个资深的Java开发工程师，擅长分析数据问题。请重点分析数据来源和状态是否正确。",
            ErrorCategory.DB_QUERY: "你是一个资深的Java开发工程师，擅长分析数据库问题。请重点分析SQL语句和查询结果。",
            ErrorCategory.DB_DATA: "你是一个资深的Java开发工程师，擅长分析数据库数据问题。请重点分析数据是否符合业务规则。",
            ErrorCategory.DOWNSTREAM_CALL: "你是一个资深的Java开发工程师，擅长分析下游服务调用问题。请重点分析下游返回的错误。",
            ErrorCategory.DOWNSTREAM_RETURN: "你是一个资深的Java开发工程师，擅长分析下游返回数据问题。请重点分析下游返回的数据是否符合预期。",
        }
        return prompts.get(category, "你是一个资深的Java开发工程师，擅长分析代码Bug并给出精确的修复方案。")

    def _build_category_prompt(
        self,
        category: str,
        error_info: Dict[str, Any],
        error_category: Optional[Dict[str, Any]],
        method_info: Dict[str, Any],
        full_method: str,
        call_chain: Dict[str, Any],
        related_classes: list,
        error_type: str
    ) -> str:
        """根据错误分类构建不同的 prompt"""
        
        if category in [ErrorCategory.UPSTREAM_PARAM, ErrorCategory.UPSTREAM_DATA]:
            return build_upstream_analysis_prompt(error_info, method_info, call_chain)
        elif category in [ErrorCategory.DOWNSTREAM_CALL, ErrorCategory.DOWNSTREAM_RETURN]:
            return build_downstream_analysis_prompt(error_info, method_info, call_chain)
        elif category in [ErrorCategory.DB_QUERY, ErrorCategory.DB_DATA]:
            return build_db_analysis_prompt(error_info, method_info, call_chain)
        else:
            return build_enhanced_analysis_prompt(
                error_info=error_info,
                error_category=error_category or {},
                method_info=method_info,
                full_method=full_method,
                call_chain=call_chain,
                related_classes=related_classes,
                error_type=error_type
            )

    def _parse_enhanced_result(self, result: str, file_path: str, line_number: int, category: str = "") -> FixSuggestion:
        """解析增强版分析结果"""
        analysis = {
            "root_cause": "",
            "fix_suggestion": "",
            "fix_code": "",
            "confidence": 0.9,
            "file_path": file_path,
            "line_number": line_number,
            "error_category": category,
            "analysis_focus": []
        }
        
        lines = result.split("\n")
        current_section = None
        
        code_block = []
        in_code_block = False
        
        for line in lines:
            line = line.strip()
            
            if any(kw in line for kw in ["问题定位", "问题分析", "问题分析"]):
                current_section = "root_cause"
                continue
            elif "根因分析" in line or "原因分析" in line:
                current_section = "root_cause"
                continue
            elif "修复建议" in line and "代码" not in line:
                current_section = "fix_suggestion"
                continue
            elif "修复代码" in line or "代码" in line:
                current_section = "fix_code"
                in_code_block = True
                continue
            elif "影响分析" in line:
                in_code_block = False
                current_section = "fix_suggestion"
                continue
            elif "防御建议" in line or "建议" in line:
                in_code_block = False
                continue
            
            if in_code_block:
                if line.startswith("```"):
                    in_code_block = False
                    continue
                if line:
                    code_block.append(line)
            elif current_section and line:
                if current_section == "root_cause":
                    analysis["root_cause"] += line + "\n"
                elif current_section == "fix_suggestion":
                    analysis["fix_suggestion"] += line + "\n"
        
        if code_block:
            analysis["fix_code"] = "\n".join(code_block)
        
        analysis["root_cause"] = analysis["root_cause"].strip()
        analysis["fix_suggestion"] = analysis["fix_suggestion"].strip()
        analysis["fix_code"] = analysis["fix_code"].strip()
        
        return FixSuggestion(
            root_cause=analysis["root_cause"],
            fix_suggestion=analysis["fix_suggestion"],
            fix_code=analysis["fix_code"],
            confidence=analysis["confidence"],
            file_path=analysis["file_path"],
            line_number=analysis["line_number"],
            error_category=analysis["error_category"],
            analysis_focus=analysis["analysis_focus"]
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
