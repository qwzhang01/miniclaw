"""
MiniClaw - Gateway 路由测试
"""

from unittest.mock import AsyncMock

import pytest

from miniclaw.agent.loop import AgentLoop
from miniclaw.channels.base import ChannelProtocol
from miniclaw.gateway.router import Gateway
from miniclaw.gateway.session import SessionManager
from miniclaw.tools.registry import ToolRegistry


class MockChannel(ChannelProtocol):
    """测试用 Channel"""

    def __init__(self):
        self.sent_messages = []
        self.sent_tool_calls = []

    async def receive(self):
        return None

    async def send(self, message):
        self.sent_messages.append(message)

    async def send_tool_call(self, tool_name, arguments):
        self.sent_tool_calls.append((tool_name, arguments))

    async def send_tool_result(self, tool_name, result, success):
        pass

    async def confirm(self, tool_name, description, risk_level):
        return True


class TestGateway:
    @pytest.mark.asyncio
    async def test_handle_message_sends_response(self):
        """Gateway 应将 Agent 回复发送给 Channel"""
        # 创建 mock AgentLoop
        mock_loop = AsyncMock(spec=AgentLoop)
        mock_loop.run = AsyncMock(return_value="Agent 回复")

        tool_reg = ToolRegistry()
        session_mgr = SessionManager(tool_reg)
        gateway = Gateway(mock_loop, session_mgr)

        channel = MockChannel()
        result = await gateway.handle_message("你好", channel)

        assert result == "Agent 回复"
        assert "Agent 回复" in channel.sent_messages

    @pytest.mark.asyncio
    async def test_session_created(self):
        """Gateway 应创建 Session"""
        mock_loop = AsyncMock(spec=AgentLoop)
        mock_loop.run = AsyncMock(return_value="ok")

        tool_reg = ToolRegistry()
        session_mgr = SessionManager(tool_reg)
        gateway = Gateway(mock_loop, session_mgr)

        channel = MockChannel()
        await gateway.handle_message("hi", channel, session_id="test-session")

        session = session_mgr.get("test-session")
        assert session is not None

    @pytest.mark.asyncio
    async def test_session_reused(self):
        """同一 session_id 应复用 Session"""
        mock_loop = AsyncMock(spec=AgentLoop)
        mock_loop.run = AsyncMock(return_value="ok")

        tool_reg = ToolRegistry()
        session_mgr = SessionManager(tool_reg)
        gateway = Gateway(mock_loop, session_mgr)

        channel = MockChannel()
        await gateway.handle_message("hi", channel, session_id="s1")
        await gateway.handle_message("hi again", channel, session_id="s1")

        # mock_loop.run 应被调用 2 次，但使用同一个 session
        assert mock_loop.run.call_count == 2
