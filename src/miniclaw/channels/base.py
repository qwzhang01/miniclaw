"""
MiniClaw - 通道抽象接口

定义 Channel 的标准接口：receive / send / confirm / confirm_critical。
所有通道（CLI / HTTP / Telegram）必须实现此接口。

对应 PRD：F6 CLI 交互界面
"""

from abc import ABC, abstractmethod

from miniclaw.tools.registry import RiskLevel


class ChannelProtocol(ABC):
    """通道抽象接口"""

    @abstractmethod
    async def receive(self) -> str | None:
        """接收用户输入，返回 None 表示退出"""
        ...

    @abstractmethod
    async def send(self, message: str) -> None:
        """发送消息给用户"""
        ...

    @abstractmethod
    async def send_tool_call(
        self, tool_name: str, arguments: dict[str, object]
    ) -> None:
        """展示工具调用信息"""
        ...

    @abstractmethod
    async def send_tool_result(
        self, tool_name: str, result: str, success: bool
    ) -> None:
        """展示工具执行结果"""
        ...

    @abstractmethod
    async def confirm(
        self, tool_name: str, description: str, risk_level: RiskLevel
    ) -> bool:
        """安全审批确认

        low → True（自动通过）
        high → 用户 y/n
        critical → 用户输入 CONFIRM
        """
        ...

    async def send_stream_chunk(self, text: str) -> None:
        """发送流式输出片段（OP6.3）

        默认无操作，子类可覆写实现逐 token 输出。
        """

    async def send_stream_end(self) -> None:
        """流式输出结束标记（OP6.3）

        默认无操作，子类可覆写实现换行等操作。
        """
