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


class LogParser:
    JAVA_EXCEPTION_PATTERN = re.compile(
        r"(?P<exception_type>[\w\.]+)(?::?\s*(?P<message>[^\n]+))?"
    )
    
    STACK_FRAME_PATTERN = re.compile(
        r"\s+at\s+(?P<class>[\w\.]+)\.(?P<method>[\w\$]+)\((?P<location>[^)]+)\)"
    )
    
    CAUSED_BY_PATTERN = re.compile(r"\s*Caused by:\s*(?P<exception_type>[\w\.]+)(?::?\s*(?P<message>[^\n]+))?")

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
        
        if "NullPointerException" in exception_type or "NullPointer" in exception_type:
            return "NULL_POINTER"
        elif "IllegalArgumentException" in exception_type:
            return "ILLEGAL_ARGUMENT"
        elif "IllegalStateException" in exception_type:
            return "ILLEGAL_STATE"
        elif "ArrayIndexOutOfBoundsException" in exception_type:
            return "INDEX_OUT_OF_BOUNDS"
        elif "NoSuchElementException" in exception_type:
            return "NO_SUCH_ELEMENT"
        elif "ClassCastException" in exception_type:
            return "CLASS_CAST"
        elif "ConcurrentModificationException" in exception_type:
            return "CONCURRENT_MODIFICATION"
        elif "SQLException" in exception_type or "Database" in exception_type:
            return "DATABASE"
        elif "TimeoutException" in exception_type:
            return "TIMEOUT"
        elif "OutOfMemoryError" in exception_type:
            return "OUT_OF_MEMORY"
        elif "StackOverflowError" in exception_type:
            return "STACK_OVERFLOW"
        else:
            return "OTHER"

    def parse_log_content(self, content: str) -> Dict[str, Any]:
        result = {
            "has_stacktrace": False,
            "error_info": None,
            "error_type": None,
            "error_key": None
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
        
        return result
