"""
MiniClaw - AgentContext 测试
"""

from miniclaw.agent.context import SYSTEM_PROMPT, AgentContext
from miniclaw.tools.registry import ToolRegistry


class TestAgentContext:
    def test_init_with_system_prompt(self):
        """初始化应包含系统提示词"""
        ctx = AgentContext(tool_registry=ToolRegistry())
        assert len(ctx.messages) == 1
        assert ctx.messages[0]["role"] == "system"
        assert ctx.messages[0]["content"] == SYSTEM_PROMPT

    def test_add_user_message(self):
        ctx = AgentContext(tool_registry=ToolRegistry())
        ctx.add_user_message("hello")
        assert ctx.messages[-1]["role"] == "user"
        assert ctx.messages[-1]["content"] == "hello"

    def test_add_assistant_message(self):
        ctx = AgentContext(tool_registry=ToolRegistry())
        ctx.add_assistant_message("hi there")
        assert ctx.messages[-1]["role"] == "assistant"

    def test_add_tool_result(self):
        ctx = AgentContext(tool_registry=ToolRegistry())
        ctx.add_tool_result("call_1", "shell_exec", "output")
        assert ctx.messages[-1]["role"] == "tool"
        assert ctx.messages[-1]["tool_call_id"] == "call_1"

    def test_build_messages(self):
        ctx = AgentContext(tool_registry=ToolRegistry())
        ctx.add_user_message("test")
        msgs = ctx.build_messages()
        assert len(msgs) == 2  # system + user
        # 应该是副本
        assert msgs is not ctx.messages

    def test_get_available_tools(self):
        from miniclaw.tools.registry import RiskLevel, ToolInfo

        reg = ToolRegistry()

        async def dummy(x: str) -> str:
            return x

        reg.register(
            ToolInfo("test", "desc", RiskLevel.LOW, dummy, {"type": "object"})
        )
        ctx = AgentContext(tool_registry=reg)
        tools = ctx.get_available_tools()
        assert len(tools) == 1
        assert tools[0]["function"]["name"] == "test"

    def test_clear(self):
        ctx = AgentContext(tool_registry=ToolRegistry())
        ctx.add_user_message("hi")
        ctx.current_round = 5
        ctx.clear()
        assert len(ctx.messages) == 1  # 只剩系统提示
        assert ctx.current_round == 0

    def test_max_rounds_default(self):
        ctx = AgentContext(tool_registry=ToolRegistry())
        assert ctx.max_rounds == 10
