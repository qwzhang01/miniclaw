"""
MiniClaw - 会话管理

创建/查找/恢复 Session，包含 AgentContext + 时间戳。
OP2.3: 创建 AgentContext 时注入 ShortTermMemory 实例。

对应 PRD：F6.5 Gateway 消息网关
"""

from dataclasses import dataclass, field
from datetime import datetime

from miniclaw.agent.context import AgentContext
from miniclaw.memory.short_term import ShortTermMemory
from miniclaw.tools.registry import ToolRegistry


@dataclass
class Session:
    """会话数据结构"""

    id: str
    context: AgentContext
    created_at: datetime = field(default_factory=datetime.now)
    last_active_at: datetime = field(default_factory=datetime.now)

    def touch(self) -> None:
        """更新最后活跃时间"""
        self.last_active_at = datetime.now()


class SessionManager:
    """会话管理器

    v1 单用户模式，只维护一个活跃会话。
    OP2.3: 创建会话时为 AgentContext 注入 ShortTermMemory。
    """

    def __init__(
        self,
        tool_registry: ToolRegistry,
        max_context_tokens: int = 32000,
    ) -> None:
        self._sessions: dict[str, Session] = {}
        self._tool_registry = tool_registry
        self._max_context_tokens = max_context_tokens

    def get_or_create(self, session_id: str) -> Session:
        """获取已有会话或创建新会话"""
        if session_id in self._sessions:
            session = self._sessions[session_id]
            session.touch()
            return session

        # OP2.3: 创建 ShortTermMemory 实例并注入 AgentContext
        stm = ShortTermMemory(max_tokens=self._max_context_tokens)
        context = AgentContext(
            tool_registry=self._tool_registry,
            short_term_memory=stm,
        )
        session = Session(id=session_id, context=context)
        self._sessions[session_id] = session
        return session

    def get(self, session_id: str) -> Session | None:
        """获取会话"""
        return self._sessions.get(session_id)

    def clear(self, session_id: str) -> None:
        """清空会话"""
        session = self._sessions.get(session_id)
        if session:
            session.context.clear()
