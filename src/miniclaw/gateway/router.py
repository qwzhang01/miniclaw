"""
MiniClaw - Gateway 消息路由

接收 Channel 消息 → 路由给 Agent → 回传响应。
v1 为单用户轻量直通模式。

对应 PRD：F6.5 Gateway 消息网关
"""

from miniclaw.agent.loop import AgentLoop
from miniclaw.channels.base import ChannelProtocol
from miniclaw.gateway.session import SessionManager
from miniclaw.utils.logging import get_logger

logger = get_logger(__name__)

# v1 单用户固定会话 ID
DEFAULT_SESSION_ID = "cli-default"


class Gateway:
    """消息网关

    Channel ↔ Gateway ↔ Agent 的消息路由层。
    v1 为单用户轻量直通，未来扩展多通道时只需在此层添加路由逻辑。
    """

    def __init__(
        self,
        agent_loop: AgentLoop,
        session_manager: SessionManager,
    ) -> None:
        self.agent_loop = agent_loop
        self.session_manager = session_manager

    async def handle_message(
        self,
        raw_input: str,
        channel: ChannelProtocol,
        session_id: str = DEFAULT_SESSION_ID,
    ) -> str:
        """处理一条用户消息

        完整流程：
        1. get_or_create Session
        2. 消息标准化
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
