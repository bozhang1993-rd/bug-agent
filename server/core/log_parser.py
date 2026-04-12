from typing import List, Optional, Dict, Any
from dataclasses import dataclass
import re


@dataclass
class StackFrame:
    class_name: str
    method_name: str
    file_name: str
    line_number: int
    raw: str


@dataclass
class StackTraceInfo:
    exception_type: str
    exception_message: str
    frames: List[StackFrame]
    root_cause: Optional["StackTraceInfo"] = None

    def get_error_class(self) -> str:
        return self.exception_type

    def get_first_frame(self) -> Optional[StackFrame]:
        return self.frames[0] if self.frames else None

    def get_key_info(self) -> str:
        frame = self.get_first_frame()
        if frame:
            return f"{frame.class_name}.{frame.method_name} ({frame.file_name}:{frame.line_number})"
        return self.exception_type


class ErrorCategory:
    """错误分类枚举"""
    
    # 代码缺陷
    CODE_DEFECT = "CODE_DEFECT"           # 代码本身缺陷
    NULL_POINTER = "NULL_POINTER"         # 空指针
    ILLEGAL_ARGUMENT = "ILLEGAL_ARGUMENT"  # 参数错误
    ILLEGAL_STATE = "ILLEGAL_STATE"        # 状态错误
    INDEX_BOUNDS = "INDEX_BOUNDS"          # 数组越界
    
    # 上游问题
    UPSTREAM_PARAM = "UPSTREAM_PARAM"      # 上游参数错误
    UPSTREAM_DATA = "UPSTREAM_DATA"         # 上游数据错误
    
    # 数据问题
    DB_QUERY = "DB_QUERY"                  # 数据库查询问题
    DB_DATA = "DB_DATA"                     # 数据库数据问题
    
    # 下游问题
    DOWNSTREAM_CALL = "DOWNSTREAM_CALL"    # 调用下游失败
    DOWNSTREAM_RETURN = "DOWNSTREAM_RETURN" # 下游返回数据问题
    
    # 业务问题
    BUSINESS_LOGIC = "BUSINESS_LOGIC"      # 业务逻辑问题
    DATA_VALIDATION = "DATA_VALIDATION"     # 数据校验失败
    
    # 系统问题
    TIMEOUT = "TIMEOUT"                     # 超时
    RESOURCE = "RESOURCE"                    # 资源不足
    
    # 未知
    UNKNOWN = "UNKNOWN"


class LogParser:
    JAVA_EXCEPTION_PATTERN = re.compile(
        r"(?P<exception_type>[\w\.]+)(?::?\s*(?P<message>[^\n]+))?"
    )
    
    STACK_FRAME_PATTERN = re.compile(
        r"\s+at\s+(?P<class>[\w\.]+)\.(?P<method>[\w\$]+)\((?P<location>[^)]+)\)"
    )
    
    CAUSED_BY_PATTERN = re.compile(r"\s*Caused by:\s*(?P<exception_type>[\w\.]+)(?::?\s*(?P<message>[^\n]+))?")

    def __init__(self):
        self.error_category = ErrorCategory()

    def parse_stacktrace(self, content: str) -> Optional[StackTraceInfo]:
        if not content:
            return None

        lines = content.strip().split("\n")
        if not lines:
            return None

        main_exception = self._parse_exception_header(lines[0])
        if not main_exception:
            return None

        frames = []
        root_cause = None
        i = 1
        
        while i < len(lines):
            line = lines[i].strip()
            
            if not line:
                i += 1
                continue
            
            if line.startswith("at "):
                frame = self._parse_frame(line)
                if frame:
                    frames.append(frame)
            elif line.startswith("Caused by:"):
                root_cause = self._parse_caused_by(lines[i:])
                break
            elif line.startswith("..."):
                i += 1
                continue
            
            i += 1

        return StackTraceInfo(
            exception_type=main_exception["type"],
            exception_message=main_exception.get("message", ""),
            frames=frames,
            root_cause=root_cause
        )

    def _parse_exception_header(self, line: str) -> Optional[Dict[str, str]]:
        match = self.JAVA_EXCEPTION_PATTERN.match(line.strip())
        if match:
            return {
                "type": match.group("exception_type"),
                "message": match.group("message", "").strip()
            }
        return None

    def _parse_frame(self, line: str) -> Optional[StackFrame]:
        match = self.STACK_FRAME_PATTERN.match(line)
        if match:
            location = match.group("location")
            file_name = location
            line_number = 0
            
            if ":" in location:
                parts = location.rsplit(":", 1)
                try:
                    file_name = parts[0]
                    line_number = int(parts[1])
                except (ValueError, IndexError):
                    pass
            
            return StackFrame(
                class_name=match.group("class"),
                method_name=match.group("method"),
                file_name=file_name,
                line_number=line_number,
                raw=line.strip()
            )
        return None

    def _parse_caused_by(self, lines: List[str]) -> Optional[StackTraceInfo]:
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            if line.startswith("Caused by:"):
                match = self.CAUSED_BY_PATTERN.match(line)
                if match:
                    exception_type = match.group("exception_type")
                    message = match.group("message", "").strip()
                    
                    frames = []
                    j = i + 1
                    while j < len(lines):
                        frame_line = lines[j].strip()
                        if frame_line.startswith("at "):
                            frame = self._parse_frame(frame_line)
                            if frame:
                                frames.append(frame)
                            j += 1
                        elif frame_line.startswith("...") or frame_line.startswith("Caused by"):
                            break
                        else:
                            break
                    
                    return StackTraceInfo(
                        exception_type=exception_type,
                        exception_message=message,
                        frames=frames
                    )
            i += 1
        return None

    def extract_error_key(self, info: StackTraceInfo) -> str:
        parts = [info.exception_type]
        frame = info.get_first_frame()
        if frame:
            parts.append(f"{frame.class_name}.{frame.method_name}")
            parts.append(f"{frame.file_name}:{frame.line_number}")
        return " | ".join(parts)

    def classify_error(self, info: StackTraceInfo) -> str:
        exception_type = info.exception_type
        message = info.exception_message.lower()
        
        if "NullPointerException" in exception_type or "null" in message:
            return "NULL_POINTER"
        elif "IllegalArgumentException" in exception_type:
            return "ILLEGAL_ARGUMENT"
        elif "IllegalStateException" in exception_type:
            return "ILLEGAL_STATE"
        elif "ArrayIndexOutOfBoundsException" in exception_type or "IndexOutOfBoundsException" in exception_type:
            return "INDEX_BOUNDS"
        elif "NoSuchElementException" in exception_type:
            return "NO_SUCH_ELEMENT"
        elif "ClassCastException" in exception_type:
            return "CLASS_CAST"
        elif "ConcurrentModificationException" in exception_type:
            return "CONCURRENT_MODIFICATION"
        elif "SQLException" in exception_type or "Database" in exception_type or "sql" in message:
            return "DB_QUERY"
        elif "TimeoutException" in exception_type or "timeout" in message:
            return "TIMEOUT"
        elif "OutOfMemoryError" in exception_type:
            return "RESOURCE"
        elif "StackOverflowError" in exception_type:
            return "RESOURCE"
        else:
            return "OTHER"

    def classify_error_with_context(self, info: StackTraceInfo, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """根据错误信息和上下文进行分类"""
        exception_type = info.exception_type
        message = info.exception_message.lower()
        first_frame = info.get_first_frame()
        
        result = {
            "category": "UNKNOWN",
            "sub_category": "",
            "likely_cause": "",
            "analysis_focus": []
        }
        
        if first_frame:
            class_name = first_frame.class_name.lower()
            method_name = first_frame.method_name.lower()
            
            if any(kw in message for kw in ["null", "cannot", "is null"]):
                result["category"] = ErrorCategory.CODE_DEFECT
                result["sub_category"] = "NULL_POINTER"
                result["analysis_focus"] = ["检查变量来源", "添加空值校验", "查看调用方是否传参"]
                
            elif "illegal argument" in message or "invalid" in message:
                result["category"] = ErrorCategory.UPSTREAM_PARAM
                result["sub_category"] = "ILLEGAL_ARGUMENT"
                result["analysis_focus"] = ["检查传入参数", "校验上游调用", "查看参数来源"]
                
            elif "illegal state" in message or "state" in message:
                result["category"] = ErrorCategory.CODE_DEFECT
                result["sub_category"] = "ILLEGAL_STATE"
                result["analysis_focus"] = ["检查对象状态", "查看初始化逻辑"]
                
            elif "sql" in message or "database" in message or exception_type == "SQLException":
                result["category"] = ErrorCategory.DB_QUERY
                result["sub_category"] = "DATABASE_ERROR"
                result["analysis_focus"] = ["检查SQL语句", "查看查询条件", "检查数据是否存在"]
                
            elif "timeout" in message:
                result["category"] = ErrorCategory.DOWNSTREAM_CALL
                result["sub_category"] = "TIMEOUT"
                result["analysis_focus"] = ["检查下游服务", "查看超时原因", "检查网络"]
                
            elif "http" in message or "request" in message or "response" in message:
                result["category"] = ErrorCategory.DOWNSTREAM_CALL
                result["sub_category"] = "HTTP_ERROR"
                result["analysis_focus"] = ["检查下游返回", "查看HTTP状态码", "检查请求参数"]
                
            elif "not found" in message or "does not exist" in message:
                result["category"] = ErrorCategory.UPSTREAM_DATA
                result["sub_category"] = "DATA_NOT_FOUND"
                result["analysis_focus"] = ["检查数据是否存在", "查看查询条件", "检查数据状态"]
                
            elif "collection" in message or "list" in message or "map" in message:
                result["category"] = ErrorCategory.CODE_DEFECT
                result["sub_category"] = "COLLECTION_ERROR"
                result["analysis_focus"] = ["检查集合操作", "查看数据来源"]
                
            elif any(kw in method_name for kw in ["save", "insert", "update", "delete"]):
                result["category"] = ErrorCategory.DB_DATA
                result["sub_category"] = "DB_OPERATION"
                result["analysis_focus"] = ["检查数据库操作", "查看数据是否冲突", "检查事务"]
                
            elif any(kw in method_name for kw in ["get", "find", "query", "select", "load"]):
                result["category"] = ErrorCategory.DB_QUERY
                result["sub_category"] = "DB_FETCH"
                result["analysis_focus"] = ["检查查询结果", "查看SQL是否正确", "检查数据是否存在"]
                
            else:
                result["category"] = ErrorCategory.CODE_DEFECT
                result["analysis_focus"] = ["分析代码逻辑"]
        
        result["likely_cause"] = self._infer_likely_cause(info, result["category"])
        
        return result

    def _infer_likely_cause(self, info: StackTraceInfo, category: str) -> str:
        """推断可能的根本原因"""
        message = info.exception_message
        first_frame = info.get_first_frame()
        
        causes = []
        
        if category == ErrorCategory.CODE_DEFECT:
            causes.append("代码未对空值、边界情况进行处理")
            causes.append("调用方传入了不符合预期的参数")
            
        elif category == ErrorCategory.UPSTREAM_PARAM:
            causes.append("上游调用时参数为空或不符合要求")
            causes.append("参数校验逻辑缺失")
            
        elif category == ErrorCategory.UPSTREAM_DATA:
            causes.append("上游数据不存在或已被删除")
            causes.append("数据状态不符合预期")
            
        elif category == ErrorCategory.DB_QUERY:
            causes.append("SQL语句错误或查询条件有误")
            causes.append("数据库连接问题")
            causes.append("查询结果为空但未做空值处理")
            
        elif category == ErrorCategory.DB_DATA:
            causes.append("数据库数据不符合业务规则")
            causes.append("数据已被修改或删除")
            
        elif category == ErrorCategory.DOWNSTREAM_CALL:
            causes.append("下游服务返回错误")
            causes.append("下游返回数据不符合预期")
            causes.append("网络超时或服务不可用")
        
        return "; ".join(causes) if causes else "需要进一步分析"

    def parse_log_content(self, content: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        result = {
            "has_stacktrace": False,
            "error_info": None,
            "error_type": None,
            "error_key": None,
            "error_category": None
        }
        
        stacktrace_info = self.parse_stacktrace(content)
        if stacktrace_info:
            result["has_stacktrace"] = True
            result["error_info"] = {
                "exception_type": stacktrace_info.exception_type,
                "exception_message": stacktrace_info.exception_message,
                "frame_count": len(stacktrace_info.frames),
                "first_frame": stacktrace_info.get_key_info()
            }
            result["error_type"] = self.classify_error(stacktrace_info)
            result["error_key"] = self.extract_error_key(stacktrace_info)
            
            # 添加错误分类
            category_result = self.classify_error_with_context(stacktrace_info, context)
            result["error_category"] = category_result
        
        return result
