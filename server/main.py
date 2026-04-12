from typing import Optional, List, Dict, Any
from pydantic import BaseModel
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from core.config import config
from core.log_fetcher import LogFetcher, LogEntry, LogSource
from core.log_parser import LogParser, StackTraceInfo, ErrorCategory
from core.code_locator import CodeLocator
from core.fixer import Fixer, FixSuggestion
from core.document_searcher import DocumentSearcher
from core.workflow_analyzer import WorkflowAnalyzer, BusinessRuleExtractor
from core.interactive_analyzer import InteractiveAnalyzer
from llm.client import LLMClient


app = FastAPI(
    title="Bug Agent API",
    description="智能Bug分析助手API - 支持多种错误类型分析",
    version="1.2.0"
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
document_searcher = DocumentSearcher()
workflow_analyzer = WorkflowAnalyzer()
rule_extractor = BusinessRuleExtractor()
interactive_analyzer = InteractiveAnalyzer()


class AnalyzeRequest(BaseModel):
    error_content: str
    log_id: Optional[str] = None
    auto_fix: bool = False


class EnhancedAnalyzeRequest(BaseModel):
    file_path: str
    line_number: int
    error_type: Optional[str] = None
    error_message: Optional[str] = None


class AnalyzeResponse(BaseModel):
    error_type: str
    error_message: str
    location: Optional[Dict[str, Any]]
    error_category: Optional[Dict[str, Any]]
    root_cause: str
    fix_suggestion: str
    fix_code: str
    confidence: float
    code_context: Optional[str] = None


class EnhancedAnalyzeResponse(BaseModel):
    error_type: str
    error_message: str
    location: Dict[str, Any]
    error_category: Dict[str, Any]
    method_info: Optional[Dict[str, Any]]
    full_method: Optional[str]
    call_chain: Optional[Dict[str, Any]]
    related_classes: Optional[List[Dict[str, str]]]
    root_cause: str
    fix_suggestion: str
    fix_code: str
    confidence: float


class FileLogRequest(BaseModel):
    file_path: str
    max_lines: int = 1000


class TextLogRequest(BaseModel):
    text: str


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
    return {"message": "Bug Agent API", "version": "1.2.0"}


@app.get("/health")
async def health():
    return {"status": "healthy"}


# ============ 日志获取 API ============

@app.get("/logs", response_model=List[LogEntry])
async def get_logs(limit: int = 100, level: Optional[str] = None):
    """从远程 API 获取日志"""
    try:
        logs = await log_fetcher.fetch_recent_logs(limit=limit, level=level)
        return logs
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/logs/{log_id}", response_model=LogEntry)
async def get_log(log_id: str):
    """从远程 API 获取单条日志"""
    log = await log_fetcher.fetch_log_by_id(log_id)
    if not log:
        raise HTTPException(status_code=404, detail="Log not found")
    return log


@app.post("/logs/file", response_model=List[LogEntry])
async def get_logs_from_file(request: FileLogRequest):
    """从本地文件获取日志"""
    try:
        logs = log_fetcher.fetch_from_file(
            file_path=request.file_path,
            max_lines=request.max_lines
        )
        return logs
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/logs/text", response_model=List[LogEntry])
async def get_logs_from_text(request: TextLogRequest):
    """从文本输入获取日志"""
    try:
        logs = log_fetcher.parse_text_input(request.text)
        return logs
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/logs/directory", response_model=List[LogEntry])
async def get_logs_from_directory(
    dir_path: str,
    pattern: str = "*.log",
    max_files: int = 5
):
    """从目录获取日志"""
    try:
        logs = log_fetcher.fetch_from_directory(
            dir_path=dir_path,
            pattern=pattern,
            max_files=max_files
        )
        return logs
    except NotADirectoryError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============ 分析 API ============

@app.post("/analyze", response_model=AnalyzeResponse)
async def analyze(request: AnalyzeRequest):
    """基础分析：解析错误并定位代码"""
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
    error_category = parse_result.get("error_category", {})
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
        error_category=error_category,
        root_cause=fix_suggestion.root_cause,
        fix_suggestion=fix_suggestion.fix_suggestion,
        fix_code=fix_suggestion.fix_code,
        confidence=fix_suggestion.confidence,
        code_context=code_context if code_context else None
    )


@app.post("/analyze/enhanced", response_model=EnhancedAnalyzeResponse)
async def enhanced_analyze(request: EnhancedAnalyzeRequest):
    """增强分析：完整方法代码 + 调用链 + 错误分类"""
    file_path = request.file_path
    line_number = request.line_number
    
    if not file_path or not line_number:
        raise HTTPException(status_code=400, detail="file_path and line_number are required")
    
    if not code_locator.project_root.exists():
        raise HTTPException(status_code=400, detail="项目根目录不存在，请检查配置")
    
    error_info = {
        "exception_type": request.error_type or "Unknown",
        "exception_message": request.error_message or "",
        "first_frame": f"{file_path}:{line_number}"
    }
    
    stacktrace_info = log_parser.parse_stacktrace(request.error_message or "")
    if stacktrace_info:
        error_category = log_parser.classify_error_with_context(stacktrace_info)
    else:
        error_type = request.error_type or "OTHER"
        error_category = {
            "category": ErrorCategory.UNKNOWN,
            "sub_category": "",
            "likely_cause": "需要进一步分析",
            "analysis_focus": ["分析代码逻辑"]
        }
    
    error_type = request.error_type or log_parser.classify_error(stacktrace_info) if stacktrace_info else "OTHER"
    
    enhanced_context = code_locator.get_enhanced_context(file_path, line_number)
    
    method_info = enhanced_context.get("method")
    full_method = enhanced_context.get("full_method")
    call_chain = enhanced_context.get("call_chain")
    related_classes = enhanced_context.get("related_classes", [])
    
    if not full_method:
        raise HTTPException(status_code=400, detail="无法加载方法代码")
    
    fix_suggestion = fixer.generate_enhanced_fix(
        error_info=error_info,
        error_type=error_type,
        file_path=file_path,
        line_number=line_number,
        error_category=error_category
    )
    
    return EnhancedAnalyzeResponse(
        error_type=error_type,
        error_message=request.error_message or "",
        location={
            "file": file_path,
            "line": line_number
        },
        error_category=error_category,
        method_info=method_info,
        full_method=full_method,
        call_chain=call_chain,
        related_classes=related_classes,
        root_cause=fix_suggestion.root_cause,
        fix_suggestion=fix_suggestion.fix_suggestion,
        fix_code=fix_suggestion.fix_code,
        confidence=fix_suggestion.confidence
    )


@app.post("/analyze/file", response_model=AnalyzeResponse)
async def analyze_from_file(request: FileLogRequest):
    """从文件分析错误"""
    try:
        logs = log_fetcher.fetch_from_file(
            file_path=request.file_path,
            max_lines=request.max_lines
        )
        
        error_logs = [log for log in logs if log.trace and ("Exception" in log.trace or "Error" in log.trace)]
        
        if not error_logs:
            raise HTTPException(status_code=400, detail="文件中未找到错误信息")
        
        error_content = error_logs[0].trace
        
        return await analyze(AnalyzeRequest(error_content=error_content))
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/analyze/text", response_model=AnalyzeResponse)
async def analyze_from_text(request: TextLogRequest):
    """从文本分析错误"""
    try:
        logs = log_fetcher.parse_text_input(request.text)
        
        error_logs = [log for log in logs if log.trace and ("Exception" in log.trace or "Error" in log.trace)]
        
        if not error_logs:
            raise HTTPException(status_code=400, detail="文本中未找到错误信息")
        
        error_content = error_logs[0].trace
        
        return await analyze(AnalyzeRequest(error_content=error_content))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============ 定位 API ============

@app.get("/locate/{class_name}")
async def locate_file(class_name: str):
    """定位类文件"""
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
    """获取代码上下文"""
    file_path = code_locator.locate_file(class_name)
    if not file_path:
        raise HTTPException(status_code=404, detail="File not found")
    
    context = code_locator.load_context(file_path, line_number, context_lines)
    return {"context": context}


@app.get("/method")
async def get_method_info(
    file_path: str,
    line_number: int
):
    """获取完整方法信息"""
    method_info = code_locator.get_method_info(file_path, line_number)
    if not method_info:
        raise HTTPException(status_code=404, detail="无法定位方法")
    return method_info


@app.get("/callchain")
async def get_call_chain(
    file_path: str,
    line_number: int
):
    """获取方法调用链"""
    call_chain = code_locator.analyze_call_chain(file_path, line_number)
    if "error" in call_chain:
        raise HTTPException(status_code=404, detail=call_chain["error"])
    return call_chain


@app.get("/enhanced/context")
async def get_enhanced_context(
    file_path: str,
    line_number: int
):
    """获取增强的代码上下文"""
    if not code_locator.project_root.exists():
        raise HTTPException(status_code=400, detail="项目根目录不存在")
    
    context = code_locator.get_enhanced_context(file_path, line_number)
    return context


# ============ 修复 API ============

@app.post("/fix", response_model=FixResponse)
async def apply_fix(request: FixRequest):
    """应用修复代码"""
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


# ============ 错误分类 API ============

@app.get("/error/categories")
async def get_error_categories():
    """获取错误分类列表"""
    return {
        "categories": [
            {"code": ErrorCategory.CODE_DEFECT, "name": "代码缺陷", "desc": "代码本身的缺陷"},
            {"code": ErrorCategory.NULL_POINTER, "name": "空指针", "desc": "空指针异常"},
            {"code": ErrorCategory.ILLEGAL_ARGUMENT, "name": "参数错误", "desc": "上游参数不合法"},
            {"code": ErrorCategory.UPSTREAM_PARAM, "name": "上游参数问题", "desc": "调用方参数错误"},
            {"code": ErrorCategory.UPSTREAM_DATA, "name": "上游数据问题", "desc": "上游数据不存在或不符合预期"},
            {"code": ErrorCategory.DB_QUERY, "name": "数据库查询问题", "desc": "SQL错误或查询失败"},
            {"code": ErrorCategory.DB_DATA, "name": "数据库数据问题", "desc": "数据不符合业务规则"},
            {"code": ErrorCategory.DOWNSTREAM_CALL, "name": "下游调用失败", "desc": "调用下游服务失败"},
            {"code": ErrorCategory.DOWNSTREAM_RETURN, "name": "下游返回数据问题", "desc": "下游返回数据不符合预期"},
        ]
    }


def main():
    uvicorn.run(
        "main:app",
        host=config.server_host,
        port=config.server_port,
        reload=True
    )


# ============ 需求文档检索 API ============

@app.get("/docs/search")
async def search_documents(
    keyword: str,
    doc_type: Optional[str] = None,
    limit: int = 10
):
    """搜索需求文档"""
    try:
        results = document_searcher.search(keyword, doc_type, limit)
        return {"results": results, "total": len(results)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/docs")
async def list_documents(
    doc_type: Optional[str] = None,
    limit: int = 20
):
    """列出所有需求文档"""
    try:
        docs = document_searcher.list_documents(doc_type, limit)
        return {"documents": docs, "total": len(docs)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/docs/content")
async def get_document_content(file_path: str):
    """获取文档内容"""
    content = document_searcher.get_document_content(file_path)
    if content is None:
        raise HTTPException(status_code=404, detail="文档不存在")
    return {"content": content, "file_path": file_path}


# ============ 业务流程分析 API ============

class WorkflowAnalyzeRequest(BaseModel):
    workflow_description: str
    code: str
    language: str = "java"


class WorkflowCompareRequest(BaseModel):
    expected_workflow: str
    actual_code: str
    language: str = "java"


@app.post("/analyze/workflow", response_model=Dict[str, Any])
async def analyze_workflow(request: WorkflowAnalyzeRequest):
    """分析业务流程是否符合预期"""
    try:
        result = workflow_analyzer.analyze(
            workflow_description=request.workflow_description,
            code=request.code,
            language=request.language
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/analyze/workflow/compare", response_model=Dict[str, Any])
async def compare_workflow(request: WorkflowCompareRequest):
    """对比预期流程和实际代码"""
    try:
        result = workflow_analyzer.compare(
            expected_workflow=request.expected_workflow,
            actual_code=request.actual_code,
            language=request.language
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============ 业务规则分析 API ============

class ExtractRulesRequest(BaseModel):
    document_content: str


class MatchRuleRequest(BaseModel):
    code: str
    rules: List[str]


@app.post("/analyze/rules/extract", response_model=Dict[str, Any])
async def extract_rules(request: ExtractRulesRequest):
    """从文档中提取业务规则"""
    try:
        rules = rule_extractor.extract_rules(request.document_content)
        return {"rules": rules, "total": len(rules)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/analyze/rules/match", response_model=Dict[str, Any])
async def match_rules(request: MatchRuleRequest):
    """检查代码是否符合规则"""
    try:
        result = rule_extractor.match_rule(request.code, request.rules)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/rules/search")
async def search_rules(keyword: str, limit: int = 5):
    """搜索业务规则"""
    try:
        docs = document_searcher.search(keyword, limit=limit)
        
        all_rules = []
        for doc in docs:
            content = document_searcher.get_document_content(doc["file"])
            if content:
                rules = rule_extractor.extract_rules(content)
                for rule in rules:
                    if keyword.lower() in rule.lower():
                        all_rules.append({
                            "rule": rule,
                            "source": doc["file"]
                        })
        
        return {"rules": all_rules[:limit], "total": len(all_rules)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============ 交互式分析 API ============

@app.post("/analyze/interactive/start")
async def start_interactive_analysis():
    """开始交互式分析"""
    try:
        result = interactive_analyzer.start_session()
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/analyze/interactive/answer")
async def answer_interactive_question(
    session_id: str,
    answer: str
):
    """回答交互式问题"""
    try:
        result = interactive_analyzer.answer_question(session_id, answer)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/analyze/interactive/skip")
async def skip_interactive_question(session_id: str):
    """跳过当前问题"""
    try:
        result = interactive_analyzer.skip_question(session_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/analyze/interactive/status/{session_id}")
async def get_interactive_status(session_id: str):
    """获取交互式分析状态"""
    try:
        result = interactive_analyzer.get_session_status(session_id)
        if not result:
            raise HTTPException(status_code=404, detail="会话不存在")
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/analyze/interactive/sessions")
async def list_interactive_sessions():
    """列出所有交互式分析会话"""
    try:
        return {"sessions": interactive_analyzer.list_sessions()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/analyze/interactive/session/{session_id}")
async def delete_interactive_session(session_id: str):
    """删除交互式分析会话"""
    try:
        success = interactive_analyzer.delete_session(session_id)
        if success:
            return {"message": "会话已删除"}
        raise HTTPException(status_code=404, detail="会话不存在")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    main()
