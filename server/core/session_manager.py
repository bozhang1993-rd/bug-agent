from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
import uuid


@dataclass
class AnalysisSession:
    """分析会话"""
    session_id: str
    created_at: datetime = field(default_factory=datetime.now)
    status: str = "pending"  # pending, collecting, analyzing, completed, failed
    
    # 收集的信息
    bug_description: str = ""
    expected_result: str = ""
    actual_result: str = ""
    related_code: str = ""
    related_files: List[str] = field(default_factory=list)
    error_logs: str = ""
    
    # 问答记录
    questions: List[Dict[str, str]] = field(default_factory=list)
    
    # 分析结果
    analysis_result: Optional[Dict[str, Any]] = None
    

class SessionManager:
    """会话管理器"""
    
    def __init__(self):
        self.sessions: Dict[str, AnalysisSession] = {}
    
    def create_session(self) -> str:
        """创建新会话"""
        session_id = str(uuid.uuid4())[:8]
        self.sessions[session_id] = AnalysisSession(session_id=session_id)
        return session_id
    
    def get_session(self, session_id: str) -> Optional[AnalysisSession]:
        """获取会话"""
        return self.sessions.get(session_id)
    
    def update_session(self, session_id: str, **kwargs) -> bool:
        """更新会话信息"""
        session = self.sessions.get(session_id)
        if not session:
            return False
        
        for key, value in kwargs.items():
            if hasattr(session, key):
                setattr(session, key, value)
        
        return True
    
    def add_question(self, session_id: str, question: str, answer: str) -> bool:
        """添加问答记录"""
        session = self.sessions.get(session_id)
        if not session:
            return False
        
        session.questions.append({
            "question": question,
            "answer": answer,
            "timestamp": datetime.now().isoformat()
        })
        return True
    
    def set_result(self, session_id: str, result: Dict[str, Any]) -> bool:
        """设置分析结果"""
        session = self.sessions.get(session_id)
        if not session:
            return False
        
        session.analysis_result = result
        session.status = "completed"
        return True
    
    def delete_session(self, session_id: str) -> bool:
        """删除会话"""
        if session_id in self.sessions:
            del self.sessions[session_id]
            return True
        return False
    
    def list_sessions(self) -> List[Dict[str, Any]]:
        """列出所有会话"""
        return [
            {
                "session_id": s.session_id,
                "created_at": s.created_at.isoformat(),
                "status": s.status,
                "bug_description": s.bug_description[:100]
            }
            for s in self.sessions.values()
        ]


class QuestionGenerator:
    """问题生成器 - 根据不同阶段生成问题"""
    
    # 第一阶段：基础信息
    BASIC_QUESTIONS = [
        {
            "key": "bug_description",
            "question": "请描述一下这个 bug 的具体情况？",
            "placeholder": "例如：用户提前还款时，最后一期的金额计算错误"
        },
        {
            "key": "expected_result",
            "question": "你期望的结果是什么？",
            "placeholder": "例如：最后一期应该只还剩余本金1000元"
        },
        {
            "key": "actual_result",
            "question": "实际的结果是什么？",
            "placeholder": "例如：最后一期显示了2000元，多算了利息"
        }
    ]
    
    # 第二阶段：代码相关
    CODE_QUESTIONS = [
        {
            "key": "related_code",
            "question": "请提供相关的代码片段（选填）",
            "placeholder": "粘贴相关的代码，或者直接回车跳过"
        },
        {
            "key": "related_files",
            "question": "这是哪个功能的代码？请告诉我在项目中的路径",
            "placeholder": "例如：loan-application 模块的 RepaymentService.java"
        }
    ]
    
    # 第三阶段：日志/数据
    LOG_QUESTIONS = [
        {
            "key": "error_logs",
            "question": "有没有相关的错误日志？可以粘贴过来",
            "placeholder": "粘贴错误日志，如果没有可以直接回车"
        },
        {
            "key": "test_data",
            "question": "能否提供测试数据？例如：合同号、金额、期限等",
            "placeholder": "例如：合同号 CTR20260321001，金额 10000，期限 3 期"
        }
    ]
    
    @classmethod
    def get_next_question(cls, session: AnalysisSession) -> Optional[Dict[str, Any]]:
        """根据会话状态获取下一个问题"""
        
        # 阶段1：基础信息
        if not session.bug_description:
            return cls.BASIC_QUESTIONS[0]
        if not session.expected_result:
            return cls.BASIC_QUESTIONS[1]
        if not session.actual_result:
            return cls.BASIC_QUESTIONS[2]
        
        # 阶段2：代码相关
        if not session.related_files:
            return cls.CODE_QUESTIONS[0]
        
        # 阶段3：日志
        if not session.error_logs:
            return cls.LOG_QUESTIONS[0]
        
        # 所有问题已收集完成
        return None
    
    @classmethod
    def get_questions_for_stage(cls, stage: str) -> List[Dict[str, Any]]:
        """获取指定阶段的问题列表"""
        if stage == "basic":
            return cls.BASIC_QUESTIONS
        elif stage == "code":
            return cls.CODE_QUESTIONS
        elif stage == "log":
            return cls.LOG_QUESTIONS
        return []
