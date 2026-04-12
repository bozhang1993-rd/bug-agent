from typing import List, Optional, Dict, Any
from datetime import datetime
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
