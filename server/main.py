from typing import Optional, List, Dict, Any
from pydantic import BaseModel
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from core.config import config
from core.log_fetcher import LogFetcher, LogEntry
from core.log_parser import LogParser, StackTraceInfo
from core.code_locator import CodeLocator
from core.fixer import Fixer, FixSuggestion
from llm.client import LLMClient


app = FastAPI(
    title="Bug Agent API",
    description="智能Bug分析助手API",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.get("server.cors_origins", ["*"]),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

log_fetcher = LogFetcher()
log_parser = LogParser()
code_locator = CodeLocator()
fixer = Fixer()
llm_client = LLMClient()


class AnalyzeRequest(BaseModel):
    error_content: str
    log_id: Optional[str] = None
    auto_fix: bool = False


class AnalyzeResponse(BaseModel):
    error_type: str
    error_message: str
    location: Optional[Dict[str, Any]]
    root_cause: str
    fix_suggestion: str
    fix_code: str
    confidence: float
    code_context: Optional[str] = None


class FixRequest(BaseModel):
    file_path: str
    line_number: int
    fix_code: str


class FixResponse(BaseModel):
    success: bool
    message: str
    patch: Optional[str] = None


@app.get("/")
async def root():
    return {"message": "Bug Agent API", "version": "1.0.0"}


@app.get("/health")
async def health():
    return {"status": "healthy"}


@app.get("/logs", response_model=List[LogEntry])
async def get_logs(limit: int = 100, level: Optional[str] = None):
    try:
        logs = await log_fetcher.fetch_recent_logs(limit=limit, level=level)
        return logs
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/logs/{log_id}", response_model=LogEntry)
async def get_log(log_id: str):
    log = await log_fetcher.fetch_log_by_id(log_id)
    if not log:
        raise HTTPException(status_code=404, detail="Log not found")
    return log


@app.post("/analyze", response_model=AnalyzeResponse)
async def analyze(request: AnalyzeRequest):
    error_content = request.error_content
    
    if request.log_id:
        log = await log_fetcher.fetch_log_by_id(request.log_id)
        if log and log.trace:
            error_content = log.trace
    
    parse_result = log_parser.parse_log_content(error_content)
    
    if not parse_result.get("has_stacktrace"):
        raise HTTPException(status_code=400, detail="No valid stacktrace found in content")
    
    error_info = parse_result["error_info"]
    error_type = parse_result["error_type"]
    key_info = parse_result["error_key"]
    
    file_path = None
    line_number = 0
    
    first_frame = error_info.get("first_frame", "")
    if first_frame:
        parts = first_frame.split(" | ")
        if len(parts) >= 3:
            location_part = parts[-1]
            if ":" in location_part:
                location_parts = location_part.rsplit(":", 1)
                class_method = location_parts[0]
                try:
                    line_number = int(location_parts[1])
                except ValueError:
                    line_number = 0
                
                if "." in class_method:
                    class_name = class_method.rsplit(".", 1)[0]
                    file_path = code_locator.locate_file(class_name)
    
    code_context = ""
    if file_path and line_number:
        code_context = code_locator.load_context(file_path, line_number)
    
    fix_suggestion = fixer.generate_fix(error_info, code_context, error_type)
    
    return AnalyzeResponse(
        error_type=error_type,
        error_message=error_info.get("exception_message", ""),
        location={
            "file": file_path,
            "line": line_number
        } if file_path else None,
        root_cause=fix_suggestion.root_cause,
        fix_suggestion=fix_suggestion.fix_suggestion,
        fix_code=fix_suggestion.fix_code,
        confidence=fix_suggestion.confidence,
        code_context=code_context if code_context else None
    )


@app.post("/fix", response_model=FixResponse)
async def apply_fix(request: FixRequest):
    if not request.file_path or not request.fix_code:
        raise HTTPException(status_code=400, detail="Invalid fix request")
    
    fix_suggestion = FixSuggestion(
        root_cause="",
        fix_suggestion="",
        fix_code=request.fix_code,
        confidence=1.0,
        line_number=request.line_number
    )
    
    success = fixer.apply_fix(request.file_path, fix_suggestion)
    
    if success:
        patch = fixer.create_patch(request.file_path, fix_suggestion)
        return FixResponse(
            success=True,
            message="修复已应用",
            patch=patch
        )
    else:
        return FixResponse(
            success=False,
            message="修复应用失败"
        )


@app.get("/locate/{class_name}")
async def locate_file(class_name: str):
    file_path = code_locator.locate_file(class_name)
    if not file_path:
        raise HTTPException(status_code=404, detail="File not found")
    return {"file_path": file_path}


@app.get("/context")
async def get_context(
    class_name: str, 
    line_number: int, 
    context_lines: int = 10
):
    file_path = code_locator.locate_file(class_name)
    if not file_path:
        raise HTTPException(status_code=404, detail="File not found")
    
    context = code_locator.load_context(file_path, line_number, context_lines)
    return {"context": context}


def main():
    uvicorn.run(
        "main:app",
        host=config.server_host,
        port=config.server_port,
        reload=True
    )


if __name__ == "__main__":
    main()
