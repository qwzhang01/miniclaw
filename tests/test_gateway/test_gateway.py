"""
MiniClaw - Gateway 路由测试

覆盖 OP5 LongTermMemory 集成（保存/恢复/记忆注入）。
"""

from unittest.mock import AsyncMock

import pytest

from miniclaw.agent.context import AgentContext
from miniclaw.agent.loop import AgentLoop
from miniclaw.channels.base import ChannelProtocol
from miniclaw.gateway.router import Gateway
from miniclaw.gateway.session import SessionManager
from miniclaw.memory.short_term import ShortTermMemory
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


class TestGatewayLongTermMemory:
    """OP5: LongTermMemory 集成测试"""

    @pytest.mark.asyncio
    async def test_save_session(self):
        """save_session 将会话消息保存到长期记忆"""
        mock_loop = AsyncMock(spec=AgentLoop)
        mock_loop.run = AsyncMock(return_value="ok")

        tool_reg = ToolRegistry()
        session_mgr = SessionManager(tool_reg)

        mock_ltm = AsyncMock()
        mock_ltm.save_session = AsyncMock()
        gateway = Gateway(mock_loop, session_mgr, long_term_memory=mock_ltm)

        # 创建会话并添加一些消息
        channel = MockChannel()
        await gateway.handle_message("hello", channel, session_id="s1")

        await gateway.save_session("s1")
        mock_ltm.save_session.assert_called_once()
        call_args = mock_ltm.save_session.call_args
        assert call_args[0][0] == "s1"  # session_id
        assert len(call_args[0][1]) > 1  # messages（至少 system + user）

    @pytest.mark.asyncio
    async def test_save_session_skips_empty(self):
        """只有 system prompt 时不保存"""
        mock_loop = AsyncMock(spec=AgentLoop)
        tool_reg = ToolRegistry()
        session_mgr = SessionManager(tool_reg)

        mock_ltm = AsyncMock()
        mock_ltm.save_session = AsyncMock()
        gateway = Gateway(mock_loop, session_mgr, long_term_memory=mock_ltm)

        # 创建会话但不发消息
        session_mgr.get_or_create("s1")
        await gateway.save_session("s1")
        mock_ltm.save_session.assert_not_called()

    @pytest.mark.asyncio
    async def test_save_session_no_ltm(self):
        """没有 LongTermMemory 时不报错"""
        mock_loop = AsyncMock(spec=AgentLoop)
        tool_reg = ToolRegistry()
        session_mgr = SessionManager(tool_reg)
        gateway = Gateway(mock_loop, session_mgr)  # 无 ltm

        await gateway.save_session("s1")  # 不应抛异常

    @pytest.mark.asyncio
    async def test_restore_session(self):
        """restore_session 恢复消息到 ShortTermMemory"""
        mock_loop = AsyncMock(spec=AgentLoop)
        tool_reg = ToolRegistry()
        session_mgr = SessionManager(tool_reg)

        saved_messages = [
            {"role": "system", "content": "MiniClaw prompt"},
            {"role": "user", "content": "之前的问题"},
            {"role": "assistant", "content": "之前的回答"},
        ]

        mock_ltm = AsyncMock()
        mock_ltm.load_session = AsyncMock(return_value=saved_messages)
        gateway = Gateway(mock_loop, session_mgr, long_term_memory=mock_ltm)

        result = await gateway.restore_session("s1")
        assert result is True
        session = session_mgr.get("s1")
        assert session is not None
        assert session.context.short_term_memory.message_count == 3

    @pytest.mark.asyncio
    async def test_restore_session_not_found(self):
        """没有保存的会话时返回 False"""
        mock_loop = AsyncMock(spec=AgentLoop)
        tool_reg = ToolRegistry()
        session_mgr = SessionManager(tool_reg)

        mock_ltm = AsyncMock()
        mock_ltm.load_session = AsyncMock(return_value=None)
        gateway = Gateway(mock_loop, session_mgr, long_term_memory=mock_ltm)

        result = await gateway.restore_session("nonexistent")
        assert result is False

    @pytest.mark.asyncio
    async def test_shutdown_saves_and_closes(self):
        """shutdown 保存会话并关闭长期记忆"""
        mock_loop = AsyncMock(spec=AgentLoop)
        mock_loop.run = AsyncMock(return_value="ok")

        tool_reg = ToolRegistry()
        session_mgr = SessionManager(tool_reg)

        mock_ltm = AsyncMock()
        mock_ltm.save_session = AsyncMock()
        mock_ltm.close = AsyncMock()
        gateway = Gateway(mock_loop, session_mgr, long_term_memory=mock_ltm)

        # 创建会话
        channel = MockChannel()
        await gateway.handle_message("hello", channel)

        await gateway.shutdown()
        mock_ltm.save_session.assert_called_once()
        mock_ltm.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_memory_injection_on_first_message(self):
        """首轮消息时注入相关记忆（OP5.4）"""
        mock_loop = AsyncMock(spec=AgentLoop)
        mock_loop.run = AsyncMock(return_value="回复")

        tool_reg = ToolRegistry()
        session_mgr = SessionManager(tool_reg)

        mock_ltm = AsyncMock()
        mock_ltm.search = AsyncMock(return_value=[
            {"content": "用户偏好：喜欢简洁回答", "category": "general"},
            {"content": "用户常用 Python", "category": "preference"},
        ])
        gateway = Gateway(mock_loop, session_mgr, long_term_memory=mock_ltm)

        channel = MockChannel()
        await gateway.handle_message("帮我写代码", channel, session_id="s1")

        # 检查是否注入了记忆
        session = session_mgr.get("s1")
        assert session is not None
        # 消息中应有 [相关记忆] 段
        memory_msgs = [
            m for m in session.context.messages
            if m.get("role") == "system" and "相关记忆" in (m.get("content") or "")
        ]
        assert len(memory_msgs) == 1
        assert "简洁回答" in memory_msgs[0]["content"]

    @pytest.mark.asyncio
    async def test_no_memory_injection_without_ltm(self):
        """没有 LongTermMemory 时不注入记忆"""
        mock_loop = AsyncMock(spec=AgentLoop)
        mock_loop.run = AsyncMock(return_value="ok")

        tool_reg = ToolRegistry()
        session_mgr = SessionManager(tool_reg)
        gateway = Gateway(mock_loop, session_mgr)  # 无 ltm

        channel = MockChannel()
        await gateway.handle_message("hello", channel, session_id="s1")

        session = session_mgr.get("s1")
        memory_msgs = [
            m for m in session.context.messages
            if m.get("role") == "system" and "相关记忆" in (m.get("content") or "")
        ]
        assert len(memory_msgs) == 0
