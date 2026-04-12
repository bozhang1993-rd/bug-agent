from typing import Dict, Any, List, Optional
from .session_manager import SessionManager, QuestionGenerator, AnalysisSession
from .code_locator import CodeLocator
from .document_searcher import DocumentSearcher
from .workflow_analyzer import WorkflowAnalyzer
from .log_parser import LogParser
from .llm.client import LLMClient
import re


class InteractiveAnalyzer:
    """交互式分析器"""
    
    def __init__(self):
        self.session_manager = SessionManager()
        self.code_locator = CodeLocator()
        self.document_searcher = DocumentSearcher()
        self.workflow_analyzer = WorkflowAnalyzer()
        self.log_parser = LogParser()
        self.llm_client = LLMClient()
    
    def start_session(self) -> Dict[str, Any]:
        """开始新的交互式分析会话"""
        session_id = self.session_manager.create_session()
        question = self.get_next_question(session_id)
        
        return {
            "session_id": session_id,
            "status": "started",
            "question": question,
            "progress": "1/6"
        }
    
    def answer_question(self, session_id: str, answer: str) -> Dict[str, Any]:
        """回答问题并获取下一个问题或分析结果"""
        session = self.session_manager.get_session(session_id)
        if not session:
            return {"error": "会话不存在，请重新开始"}
        
        # 获取当前问题
        current_question = self.session_manager.get_next_question(session)
        if not current_question:
            # 已回答完所有问题，开始分析
            return self._start_analysis(session_id)
        
        # 保存回答
        key = current_question["key"]
        self.session_manager.update_session(session_id, **{key: answer})
        self.session_manager.add_question(session_id, current_question["question"], answer)
        
        # 获取下一个问题
        next_question = self.session_manager.get_next_question(session)
        
        if next_question:
            return {
                "session_id": session_id,
                "status": "collecting",
                "question": next_question,
                "progress": self._calculate_progress(session),
                "collected": self._get_collected_info(session)
            }
        else:
            # 开始分析
            return self._start_analysis(session_id)
    
    def get_next_question(self, session_id: str) -> Optional[Dict[str, Any]]:
        """获取下一个问题"""
        session = self.session_manager.get_session(session_id)
        if not session:
            return None
        return QuestionGenerator.get_next_question(session)
    
    def skip_question(self, session_id: str) -> Dict[str, Any]:
        """跳过当前问题"""
        session = self.session_manager.get_session(session_id)
        if not session:
            return {"error": "会话不存在"}
        
        current_question = self.session_manager.get_next_question(session)
        if current_question:
            key = current_question["key"]
            default_value = ""
            if key == "related_files":
                default_value = []
            self.session_manager.update_session(session_id, **{key: default_value})
        
        return self.answer_question(session_id, "")
    
    def _start_analysis(self, session_id: str) -> Dict[str, Any]:
        """开始分析"""
        session = self.session_manager.get_session(session_id)
        if not session:
            return {"error": "会话不存在"}
        
        self.session_manager.update_session(session_id, status="analyzing")
        
        analysis_result = self._analyze(session)
        
        self.session_manager.set_result(session_id, analysis_result)
        
        return {
            "session_id": session_id,
            "status": "completed",
            "result": analysis_result,
            "progress": "100%"
        }
    
    def _analyze(self, session: AnalysisSession) -> Dict[str, Any]:
        """执行分析"""
        result = {
            "bug_description": session.bug_description,
            "expected_result": session.expected_result,
            "actual_result": session.actual_result,
            "root_cause": "",
            "fix_suggestion": "",
            "fix_code": "",
            "related_files": [],
            "business_rules": []
        }
        
        # 1. 尝试定位相关代码
        if session.related_files:
            result["related_files"] = session.related_files
        
        # 2. 搜索相关文档
        if session.bug_description:
            search_keyword = self._extract_keyword(session.bug_description)
            docs = self.document_searcher.search(search_keyword, limit=3)
            if docs:
                result["business_rules"] = [
                    {
                        "file": doc["file"],
                        "matches": doc.get("matches", [])
                    }
                    for doc in docs
                ]
        
        # 3. 代码分析
        if session.related_code:
            analysis = self.workflow_analyzer.analyze(
                workflow_description=session.expected_result,
                code=session.related_code
            )
            result.update(analysis)
        elif session.related_files:
            # 尝试读取代码文件
            code_content = self._load_related_code(session.related_files)
            if code_content:
                analysis = self.workflow_analyzer.compare(
                    expected_workflow=session.expected_result,
                    actual_code=code_content
                )
                result.update(analysis)
        
        # 4. 如果没有代码，生成建议
        if not result.get("root_cause"):
            result["root_cause"] = self._generate_initial_analysis(session)
        
        return result
    
    def _extract_keyword(self, description: str) -> str:
        """从描述中提取关键词"""
        keywords = []
        
        # 提取业务相关词汇
        business_words = ["还款", "放款", "利息", "罚息", "提前", "分期", "逾期", "冲销", "计算"]
        
        for word in business_words:
            if word in description:
                keywords.append(word)
        
        return keywords[0] if keywords else description[:10]
    
    def _load_related_code(self, file_paths: List[str]) -> str:
        """加载相关代码"""
        code_parts = []
        
        for file_path in file_paths:
            if isinstance(file_path, str):
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        code_parts.append(f.read()[:2000])
                except Exception:
                    pass
        
        return "\n\n".join(code_parts)
    
    def _generate_initial_analysis(self, session: AnalysisSession) -> str:
        """生成初步分析（没有代码时）"""
        prompt = f"""请帮我分析一个业务问题：

## Bug 描述
{session.bug_description}

## 期望结果
{session.expected_result}

## 实际结果
{session.actual_result}

请给出可能的原因分析和排查建议。

请按以下格式回复：

### 可能原因
1. ...
2. ...

### 排查建议
1. ...
2. ...

### 需要的更多信息
（如果需要更多信息来定位问题）

"""
        
        messages = [
            {"role": "system", "content": "你是一个资深的开发工程师，擅长分析和排查业务问题。"},
            {"role": "user", "content": prompt}
        ]
        
        return self.llm_client.chat(messages)
    
    def _calculate_progress(self, session: AnalysisSession) -> str:
        """计算进度"""
        total = 6  # 总问题数
        current = 0
        
        if session.bug_description:
            current += 1
        if session.expected_result:
            current += 1
        if session.actual_result:
            current += 1
        if session.related_code or session.related_files:
            current += 1
        if session.error_logs:
            current += 1
        
        return f"{current}/{total}"
    
    def _get_collected_info(self, session: AnalysisSession) -> Dict[str, str]:
        """获取已收集的信息"""
        return {
            "bug_description": session.bug_description[:50] + "..." if len(session.bug_description) > 50 else session.bug_description,
            "expected_result": session.expected_result[:50] + "..." if len(session.expected_result) > 50 else session.expected_result,
            "actual_result": session.actual_result[:50] + "..." if len(session.actual_result) > 50 else session.actual_result
        }
    
    def get_session_status(self, session_id: str) -> Optional[Dict[str, Any]]:
        """获取会话状态"""
        session = self.session_manager.get_session(session_id)
        if not session:
            return None
        
        return {
            "session_id": session.session_id,
            "status": session.status,
            "progress": self._calculate_progress(session),
            "questions": session.questions,
            "result": session.analysis_result
        }
    
    def list_sessions(self) -> List[Dict[str, Any]]:
        """列出所有会话"""
        return self.session_manager.list_sessions()
    
    def delete_session(self, session_id: str) -> bool:
        """删除会话"""
        return self.session_manager.delete_session(session_id)


def get_interactive_analyzer() -> InteractiveAnalyzer:
    return InteractiveAnalyzer()
