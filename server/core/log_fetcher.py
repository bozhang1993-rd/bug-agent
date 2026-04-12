from typing import List, Optional, Dict, Any, Union
from datetime import datetime
from pathlib import Path
import re
import httpx
from pydantic import BaseModel
from .config import config


class LogEntry(BaseModel):
    log_id: str
    timestamp: str
    level: str
    message: str
    trace: Optional[str] = None
    source: Optional[str] = None


class LogSource:
    """日志来源类型"""
    API = "api"
    FILE = "file"
    TEXT = "text"


class LogFetcher:
    def __init__(self):
        self.base_url = config.log_api_base_url
        self.api_key = config.log_api_api_key
        self.timeout = config.log_api_timeout

    def _get_headers(self) -> Dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["X-API-Key"] = self.api_key
        return headers

    # ============ 远程 API 获取 ============
    
    async def fetch_recent_logs(self, limit: int = 100, level: Optional[str] = None) -> List[LogEntry]:
        params = {"limit": limit}
        if level:
            params["level"] = level
        
        endpoint = config.get("log.api.endpoints.log_list", "/api/v1/logs")
        url = f"{self.base_url}{endpoint}"
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.get(url, headers=self._get_headers(), params=params)
                response.raise_for_status()
                data = response.json()
                
                logs = []
                for item in data.get("data", []):
                    logs.append(LogEntry(
                        log_id=item.get("id", ""),
                        timestamp=item.get("timestamp", ""),
                        level=item.get("level", "INFO"),
                        message=item.get("message", ""),
                        trace=item.get("trace"),
                        source=item.get("source")
                    ))
                return logs
            except httpx.HTTPError as e:
                raise RuntimeError(f"获取日志失败: {str(e)}")

    async def fetch_log_by_id(self, log_id: str) -> Optional[LogEntry]:
        endpoint = config.get("log.api.endpoints.log_detail", "/api/v1/logs/{log_id}")
        url = f"{self.base_url}{endpoint}".format(log_id=log_id)
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.get(url, headers=self._get_headers())
                response.raise_for_status()
                data = response.json()
                
                item = data.get("data", {})
                return LogEntry(
                    log_id=item.get("id", ""),
                    timestamp=item.get("timestamp", ""),
                    level=item.get("level", "INFO"),
                    message=item.get("message", ""),
                    trace=item.get("trace"),
                    source=item.get("source")
                )
            except httpx.HTTPError:
                return None

    async def search_logs(
        self, 
        keyword: str, 
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100
    ) -> List[LogEntry]:
        endpoint = config.get("log.api.endpoints.search", "/api/v1/logs/search")
        url = f"{self.base_url}{endpoint}"
        
        params = {
            "keyword": keyword,
            "limit": limit
        }
        if start_time:
            params["start_time"] = start_time.isoformat()
        if end_time:
            params["end_time"] = end_time.isoformat()
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.get(url, headers=self._get_headers(), params=params)
                response.raise_for_status()
                data = response.json()
                
                logs = []
                for item in data.get("data", []):
                    logs.append(LogEntry(
                        log_id=item.get("id", ""),
                        timestamp=item.get("timestamp", ""),
                        level=item.get("level", "INFO"),
                        message=item.get("message", ""),
                        trace=item.get("trace"),
                        source=item.get("source")
                    ))
                return logs
            except httpx.HTTPError as e:
                raise RuntimeError(f"搜索日志失败: {str(e)}")

    # ============ 本地文件获取 ============

    def fetch_from_file(self, file_path: str, max_lines: int = 1000) -> List[LogEntry]:
        """
        从本地日志文件获取日志
        
        Args:
            file_path: 日志文件路径
            max_lines: 最大读取行数
            
        Returns:
            日志条目列表
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"日志文件不存在: {file_path}")
        
        logs = []
        log_id = 0
        
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
        
        for line in lines[-max_lines:]:
            line = line.strip()
            if not line:
                continue
            
            parsed = self._parse_log_line(line)
            log_id += 1
            
            logs.append(LogEntry(
                log_id=f"file_{log_id}",
                timestamp=parsed.get("timestamp", ""),
                level=parsed.get("level", "INFO"),
                message=parsed.get("message", line),
                trace=parsed.get("trace"),
                source=LogSource.FILE
            ))
        
        return logs

    def fetch_from_directory(self, dir_path: str, pattern: str = "*.log", max_files: int = 5) -> List[LogEntry]:
        """
        从目录获取日志文件
        
        Args:
            dir_path: 目录路径
            pattern: 文件匹配模式
            max_files: 最大读取文件数
            
        Returns:
            日志条目列表
        """
        path = Path(dir_path)
        if not path.exists() or not path.is_dir():
            raise NotADirectoryError(f"目录不存在: {dir_path}")
        
        logs = []
        
        log_files = sorted(path.glob(pattern), key=lambda p: p.stat().st_mtime, reverse=True)[:max_files]
        
        for log_file in log_files:
            try:
                file_logs = self.fetch_from_file(str(log_file), max_lines=200)
                logs.extend(file_logs)
            except Exception:
                continue
        
        return logs

    def _parse_log_line(self, line: str) -> Dict[str, str]:
        """解析单行日志"""
        result = {"timestamp": "", "level": "INFO", "message": "", "trace": None}
        
        # 常见日志格式匹配
        # 格式: 2026-04-12 10:30:15 ERROR message
        timestamp_pattern = re.compile(
            r"(\d{4}-\d{2}-\d{2}[\sT]\d{2}:\d{2}:\d{2}(?:\.\d+)?)"
        )
        level_pattern = re.compile(
            r"\b(DEBUG|INFO|WARN|WARNING|ERROR|FATAL|TRACE)\b",
            re.IGNORECASE
        )
        
        ts_match = timestamp_pattern.search(line)
        if ts_match:
            result["timestamp"] = ts_match.group(1)
        
        level_match = level_pattern.search(line)
        if level_match:
            result["level"] = level_match.group(1).upper()
        
        # 提取消息内容（移除时间戳和级别）
        message = line
        if ts_match:
            message = message.replace(ts_match.group(1), "").strip()
        if level_match:
            message = message.replace(level_match.group(1), "").strip()
        
        # 检测是否有堆栈信息
        if any(marker in line for marker in ["Exception", "Error", "at ", "Caused by:"]):
            result["trace"] = line
        
        result["message"] = message
        
        return result

    # ============ 文本输入获取 ============

    def parse_text_input(self, text: str) -> List[LogEntry]:
        """
        解析文本输入（用户粘贴的错误信息）
        
        Args:
            text: 用户输入的文本
            
        Returns:
            日志条目列表
        """
        logs = []
        
        # 按行分割
        lines = text.strip().split("\n")
        
        # 检测是否是堆栈信息
        is_stacktrace = any(
            line.strip().startswith("at ") or 
            line.strip().startswith("Caused by:") or
            "Exception" in line or 
            "Error" in line
            for line in lines[:20]
        )
        
        if is_stacktrace:
            # 解析为堆栈信息
            log_entry = self._parse_stacktrace_text(text)
            if log_entry:
                logs.append(log_entry)
        else:
            # 解析为普通日志行
            for i, line in enumerate(lines):
                line = line.strip()
                if not line:
                    continue
                
                parsed = self._parse_log_line(line)
                logs.append(LogEntry(
                    log_id=f"text_{i+1}",
                    timestamp=parsed.get("timestamp", ""),
                    level=parsed.get("level", "INFO"),
                    message=parsed.get("message", line),
                    trace=parsed.get("trace"),
                    source=LogSource.TEXT
                ))
        
        return logs

    def _parse_stacktrace_text(self, text: str) -> Optional[LogEntry]:
        """解析堆栈文本"""
        lines = text.strip().split("\n")
        
        if not lines:
            return None
        
        # 第一行通常是异常信息
        first_line = lines[0].strip()
        
        exception_type = "Unknown"
        exception_message = ""
        
        # 解析异常类型和消息
        if ":" in first_line:
            parts = first_line.split(":", 1)
            exception_type = parts[0].strip()
            exception_message = parts[1].strip() if len(parts) > 1 else ""
        else:
            exception_type = first_line
        
        # 提取关键堆栈帧
        stack_frames = []
        for line in lines[1:]:
            line = line.strip()
            if line.startswith("at "):
                stack_frames.append(line)
            elif line.startswith("..."):
                continue
            elif line.startswith("Caused by:"):
                break
        
        trace = "\n".join([first_line] + stack_frames) if stack_frames else first_line
        
        return LogEntry(
            log_id="stacktrace_1",
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            level="ERROR",
            message=exception_message or exception_type,
            trace=trace,
            source=LogSource.TEXT
        )

    # ============ 通用获取方法 ============

    def fetch(self, source: str = "api", **kwargs) -> List[LogEntry]:
        """
        统一获取日志接口
        
        Args:
            source: 来源类型 "api", "file", "text"
            **kwargs: 不同来源的参数
                - api: limit, level
                - file: file_path
                - text: text_content
                
        Returns:
            日志列表
        """
        if source == LogSource.API:
            import asyncio
            return asyncio.run(self.fetch_recent_logs(
                limit=kwargs.get("limit", 100),
                level=kwargs.get("level")
            ))
        elif source == LogSource.FILE:
            return self.fetch_from_file(
                kwargs.get("file_path", ""),
                max_lines=kwargs.get("max_lines", 1000)
            )
        elif source == LogSource.TEXT:
            return self.parse_text_input(kwargs.get("text_content", ""))
        else:
            raise ValueError(f"不支持的日志来源: {source}")
