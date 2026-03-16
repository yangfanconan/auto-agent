"""
对话管理系统 - 支持多轮对话和上下文

参考 Qwen Code 的对话设计，实现：
- 对话状态管理
- 上下文压缩
- 意图识别
- 会话持久化
"""

import json
import uuid
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from pathlib import Path

from utils import get_logger


class MessageRole(Enum):
    """消息角色"""
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


class ConversationState(Enum):
    """对话状态"""
    IDLE = "idle"              # 空闲
    THINKING = "thinking"      # 思考中
    EXECUTING = "executing"    # 执行中
    WAITING = "waiting"        # 等待用户输入
    ERROR = "error"            # 错误状态


@dataclass
class Message:
    """对话消息"""
    role: MessageRole
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "role": self.role.value,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "Message":
        return cls(
            role=MessageRole(data["role"]),
            content=data["content"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            metadata=data.get("metadata", {}),
            id=data.get("id", str(uuid.uuid4())[:8])
        )


@dataclass
class ConversationContext:
    """对话上下文"""
    session_id: str
    messages: List[Message] = field(default_factory=list)
    state: ConversationState = ConversationState.IDLE
    variables: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    def add_message(self, role: MessageRole, content: str, metadata: Optional[Dict] = None):
        """添加消息"""
        message = Message(role=role, content=content, metadata=metadata or {})
        self.messages.append(message)
        self.updated_at = datetime.now()
        return message

    def get_recent(self, n: int = 5) -> List[Message]:
        """获取最近 n 条消息"""
        return self.messages[-n:] if self.messages else []

    def get_history(self, max_tokens: int = 4000) -> str:
        """获取格式化的历史记录（带长度限制）"""
        history = []
        total_length = 0

        for msg in reversed(self.messages):
            formatted = f"{msg.role.value}: {msg.content}\n"
            total_length += len(formatted)
            if total_length > max_tokens:
                break
            history.insert(0, formatted)

        return "".join(history)

    def clear(self):
        """清空对话"""
        self.messages.clear()
        self.variables.clear()
        self.state = ConversationState.IDLE
        self.updated_at = datetime.now()

    def to_dict(self) -> Dict:
        return {
            "session_id": self.session_id,
            "messages": [m.to_dict() for m in self.messages],
            "state": self.state.value,
            "variables": self.variables,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "ConversationContext":
        ctx = cls(
            session_id=data["session_id"],
            state=ConversationState(data["state"]),
            variables=data.get("variables", {}),
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"])
        )
        ctx.messages = [Message.from_dict(m) for m in data.get("messages", [])]
        return ctx


class ConversationManager:
    """对话管理器"""

    def __init__(self, storage_path: Optional[str] = None):
        self.logger = get_logger()
        self.sessions: Dict[str, ConversationContext] = {}
        self.storage_path = Path(storage_path) if storage_path else None
        self.active_session: Optional[str] = None

        if self.storage_path:
            self.storage_path.parent.mkdir(parents=True, exist_ok=True)
            self._load_sessions()

    def create_session(self, session_id: Optional[str] = None) -> ConversationContext:
        """创建新会话"""
        sid = session_id or str(uuid.uuid4())[:8]
        ctx = ConversationContext(session_id=sid)
        self.sessions[sid] = ctx
        self.active_session = sid
        self.logger.info(f"创建会话: {sid}")
        return ctx

    def get_session(self, session_id: str) -> Optional[ConversationContext]:
        """获取会话"""
        return self.sessions.get(session_id)

    def get_or_create(self, session_id: str) -> ConversationContext:
        """获取或创建会话"""
        if session_id not in self.sessions:
            return self.create_session(session_id)
        return self.sessions[session_id]

    def switch_session(self, session_id: str) -> bool:
        """切换会话"""
        if session_id in self.sessions:
            self.active_session = session_id
            return True
        return False

    def delete_session(self, session_id: str) -> bool:
        """删除会话"""
        if session_id in self.sessions:
            del self.sessions[session_id]
            if self.active_session == session_id:
                self.active_session = None
            return True
        return False

    def list_sessions(self) -> List[Dict]:
        """列出所有会话"""
        return [
            {
                "session_id": sid,
                "message_count": len(ctx.messages),
                "state": ctx.state.value,
                "updated_at": ctx.updated_at.isoformat(),
                "is_active": sid == self.active_session
            }
            for sid, ctx in self.sessions.items()
        ]

    def get_active(self) -> Optional[ConversationContext]:
        """获取当前活动会话"""
        if self.active_session:
            return self.sessions.get(self.active_session)
        return None

    def save(self):
        """保存会话到文件"""
        if not self.storage_path:
            return

        data = {
            "active_session": self.active_session,
            "sessions": {sid: ctx.to_dict() for sid, ctx in self.sessions.items()}
        }

        with open(self.storage_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        self.logger.info(f"保存 {len(self.sessions)} 个会话到 {self.storage_path}")

    def _load_sessions(self):
        """从文件加载会话"""
        if not self.storage_path or not self.storage_path.exists():
            return

        try:
            with open(self.storage_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            self.active_session = data.get("active_session")
            for sid, ctx_data in data.get("sessions", {}).items():
                self.sessions[sid] = ConversationContext.from_dict(ctx_data)

            self.logger.info(f"加载 {len(self.sessions)} 个会话")
        except Exception as e:
            self.logger.error(f"加载会话失败: {e}")

    def compress_context(self, session_id: str, keep_recent: int = 5) -> str:
        """
        压缩上下文 - 保留关键信息，总结早期对话

        Args:
            session_id: 会话ID
            keep_recent: 保留的最近消息数

        Returns:
            压缩后的摘要
        """
        ctx = self.sessions.get(session_id)
        if not ctx or len(ctx.messages) <= keep_recent:
            return ctx.get_history() if ctx else ""

        # 保留最近的消息
        recent = ctx.messages[-keep_recent:]

        # 总结早期消息（简化实现）
        early = ctx.messages[:-keep_recent]
        summary = self._summarize_messages(early)

        # 组合
        result = f"[历史摘要]\n{summary}\n\n[最近对话]\n"
        for msg in recent:
            result += f"{msg.role.value}: {msg.content}\n"

        return result

    def _summarize_messages(self, messages: List[Message]) -> str:
        """总结消息（简化版）"""
        if not messages:
            return "无"

        # 统计信息
        user_msgs = [m for m in messages if m.role == MessageRole.USER]
        assistant_msgs = [m for m in messages if m.role == MessageRole.ASSISTANT]

        # 提取关键主题（简单关键词提取）
        all_content = " ".join([m.content for m in messages])
        keywords = self._extract_keywords(all_content)

        return (
            f"对话轮数: {len(messages)}\n"
            f"用户消息: {len(user_msgs)}\n"
            f"助手回复: {len(assistant_msgs)}\n"
            f"关键词: {', '.join(keywords[:5])}"
        )

    def _extract_keywords(self, text: str) -> List[str]:
        """提取关键词（简化版）"""
        # 简单的关键词提取
        words = text.lower().split()
        # 过滤常见词
        stop_words = {"the", "a", "an", "is", "are", "was", "were", "的", "是", "在", "和"}
        keywords = [w for w in words if len(w) > 3 and w not in stop_words]
        # 去重并返回最常见的
        from collections import Counter
        return [word for word, _ in Counter(keywords).most_common(10)]


class IntentRecognizer:
    """意图识别器"""

    # 意图模式
    PATTERNS = {
        "code_generation": [
            "写", "创建", "生成", "code", "write", "create", "generate",
            "实现", "implement", "开发", "develop"
        ],
        "file_operation": [
            "读", "写", "打开", "保存", "文件", "read", "write", "file",
            "打开", "查看", "edit", "modify"
        ],
        "execution": [
            "运行", "执行", "测试", "run", "execute", "test", "start",
            "调用", "call", "invoke"
        ],
        "search": [
            "搜索", "查找", "查询", "search", "find", "query", "look for"
        ],
        "explanation": [
            "解释", "说明", "什么", "为什么", "explain", "what", "why",
            "how", "怎么做"
        ],
        "debug": [
            "调试", "修复", "错误", "bug", "debug", "fix", "error",
            "问题", "problem"
        ]
    }

    def recognize(self, text: str) -> Dict[str, float]:
        """
        识别意图

        Returns:
            {意图: 置信度}
        """
        text_lower = text.lower()
        scores = {}

        for intent, patterns in self.PATTERNS.items():
            score = 0
            for pattern in patterns:
                if pattern in text_lower:
                    score += 1
            scores[intent] = min(score / max(len(patterns) * 0.3, 1), 1.0)

        # 归一化
        total = sum(scores.values())
        if total > 0:
            scores = {k: v/total for k, v in scores.items()}

        return scores

    def get_primary_intent(self, text: str) -> tuple:
        """获取主要意图"""
        scores = self.recognize(text)
        if not scores:
            return "unknown", 0.0
        intent = max(scores, key=scores.get)
        return intent, scores[intent]


# ========== 便捷函数 ==========

def create_conversation_manager(storage_path: Optional[str] = None) -> ConversationManager:
    """创建对话管理器"""
    return ConversationManager(storage_path)


if __name__ == "__main__":
    # 测试
    manager = create_conversation_manager("./test_conversations.json")

    # 创建会话
    ctx = manager.create_session()
    print(f"创建会话: {ctx.session_id}")

    # 添加消息
    ctx.add_message(MessageRole.USER, "帮我写一个快速排序算法")
    ctx.add_message(MessageRole.ASSISTANT, "好的，我来为你实现快速排序...")
    ctx.add_message(MessageRole.USER, "再写一个归并排序")

    # 意图识别
    recognizer = IntentRecognizer()
    intent, confidence = recognizer.get_primary_intent("帮我写一个快速排序算法")
    print(f"\n意图识别: {intent} (置信度: {confidence:.2f})")

    # 获取历史
    print(f"\n对话历史:\n{ctx.get_history()}")

    # 保存
    manager.save()
    print(f"\n会话已保存")
