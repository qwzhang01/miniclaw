"""
MiniClaw - Gateway 消息路由

接收 Channel 消息 → 路由给 Agent → 回传响应。
OP5: 集成 LongTermMemory（会话保存/恢复 + 记忆检索注入）。
v1 为单用户轻量直通模式。

对应 PRD：F6.5 Gateway 消息网关
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from miniclaw.agent.loop import AgentLoop
from miniclaw.channels.base import ChannelProtocol
from miniclaw.gateway.session import SessionManager
from miniclaw.utils.logging import get_logger

if TYPE_CHECKING:
    from miniclaw.agent.context import AgentContext
    from miniclaw.memory.long_term import LongTermMemory

logger = get_logger(__name__)

# v1 单用户固定会话 ID
DEFAULT_SESSION_ID = "cli-default"


class Gateway:
    """消息网关

    Channel ↔ Gateway ↔ Agent 的消息路由层。
    OP5: 集成 LongTermMemory（会话保存/恢复 + 记忆检索注入）。
    v1 为单用户轻量直通，未来扩展多通道时只需在此层添加路由逻辑。
    """

    def __init__(
        self,
        agent_loop: AgentLoop,
        session_manager: SessionManager,
        long_term_memory: "LongTermMemory | None" = None,
    ) -> None:
        self.agent_loop = agent_loop
        self.session_manager = session_manager
        self.long_term_memory = long_term_memory

    async def handle_message(
        self,
        raw_input: str,
        channel: ChannelProtocol,
        session_id: str = DEFAULT_SESSION_ID,
    ) -> str:
        """处理一条用户消息

        完整流程：
        1. get_or_create Session
        2. OP5.4: 首次消息时从长期记忆检索相关上下文注入
        3. AgentLoop.run()
        4. Channel.send() 回传响应

        Args:
            raw_input: 用户原始输入
            channel: 消息来源通道
            session_id: 会话 ID

        Returns:
            Agent 的文本回复
        """
        # 1. 获取或创建会话
        session = self.session_manager.get_or_create(session_id)

        logger.info("Gateway 收到消息", session=session_id, input_len=len(raw_input))

        # OP5.4: 首轮消息（只有 system prompt）时注入相关记忆
        if self.long_term_memory and session.context.current_round == 0:
            await self._inject_relevant_memories(raw_input, session.context)

        # 2. 定义回调（展示工具调用过程）
        async def on_tool_call(name: str, args: dict[str, object]) -> None:
            await channel.send_tool_call(name, args)

        def sync_on_tool_call(name: str, args: dict[str, object]) -> None:
            import asyncio

            try:
                loop = asyncio.get_running_loop()
                loop.create_task(on_tool_call(name, args))
            except RuntimeError:
                pass  # 没有事件循环时忽略

        # 3. 运行 Agent Loop
        response = await self.agent_loop.run(
            user_input=raw_input,
            context=session.context,
            on_tool_call=sync_on_tool_call,
        )

        # 4. 发送回复
        await channel.send(response)

        return response

    async def save_session(self, session_id: str = DEFAULT_SESSION_ID) -> None:
        """保存会话到长期记忆（OP5.2）

        在 /exit 或 Gateway 关闭时调用。
        """
        if not self.long_term_memory:
            return
        session = self.session_manager.get(session_id)
        if session is None:
            return
        messages = session.context.build_messages()
        if len(messages) <= 1:  # 只有 system prompt，不保存
            return
        try:
            await self.long_term_memory.save_session(session_id, messages)
            logger.info("会话已保存", session=session_id, messages=len(messages))
        except Exception as e:
            logger.warning("会话保存失败", session=session_id, error=repr(e))

    async def restore_session(self, session_id: str = DEFAULT_SESSION_ID) -> bool:
        """从长期记忆恢复会话（OP5.3）

        Args:
            session_id: 要恢复的会话 ID

        Returns:
            是否成功恢复
        """
        if not self.long_term_memory:
            return False
        try:
            messages = await self.long_term_memory.load_session(session_id)
            if not messages:
                return False
            session = self.session_manager.get_or_create(session_id)
            # 恢复消息历史到 ShortTermMemory
            assert session.context.short_term_memory is not None
            session.context.short_term_memory.clear()
            for msg in messages:
                session.context.short_term_memory.add(msg)
            logger.info("会话已恢复", session=session_id, messages=len(messages))
            return True
        except Exception as e:
            logger.warning("会话恢复失败", session=session_id, error=repr(e))
            return False

    async def shutdown(self, session_id: str = DEFAULT_SESSION_ID) -> None:
        """优雅关闭：保存会话 + 关闭长期记忆（OP5.2）"""
        await self.save_session(session_id)
        if self.long_term_memory:
            await self.long_term_memory.close()
            logger.info("长期记忆已关闭")

    async def _inject_relevant_memories(
        self, user_input: str, context: "AgentContext"
    ) -> None:
        """从长期记忆检索相关片段注入上下文（OP5.4）

        最多注入 3 条最相关的记忆。
        """
        if not self.long_term_memory:
            return
        try:
            memories = await self.long_term_memory.search(user_input, limit=3)
            if not memories:
                return
            # 构建记忆片段文本
            snippets = [f"- {m['content']}" for m in memories]
            memory_text = "\n".join(snippets)
            # 作为 system 补充消息注入（不修改主 system prompt）
            assert context.short_term_memory is not None
            context.short_term_memory.add({
                "role": "system",
                "content": f"[相关记忆]\n{memory_text}",
            })
            logger.debug("记忆注入", count=len(memories))
        except Exception as e:
            logger.warning("记忆检索失败", error=repr(e))
