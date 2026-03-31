"""
MiniClaw - Agent 主循环测试
"""

from unittest.mock import AsyncMock

import pytest

from miniclaw.agent.context import AgentContext
from miniclaw.agent.loop import AgentLoop
from miniclaw.llm.base import LLMResponse, ToolCall
from miniclaw.llm.registry import ModelRoleRegistry
from miniclaw.tools.executor import ToolExecutor
from miniclaw.tools.registry import RiskLevel, ToolInfo, ToolRegistry
from miniclaw.utils.tokens import TokenUsage


def _make_text_response(text: str) -> LLMResponse:
    return LLMResponse(text=text, token_usage=TokenUsage(10, 5))


def _make_tool_call_response(name: str, args: dict) -> LLMResponse:
    return LLMResponse(
        tool_calls=[ToolCall(id="call_1", name=name, arguments=args)],
        token_usage=TokenUsage(20, 10),
    )


class TestAgentLoop:
    @pytest.mark.asyncio
    async def test_simple_text_response(self):
        """LLM 直接返回文本时结束循环"""
        registry = ModelRoleRegistry()
        mock_provider = AsyncMock()
        mock_provider.chat = AsyncMock(
            return_value=_make_text_response("你好！")
        )
        mock_provider.model = "test"
        registry.register("default", mock_provider)

        tool_reg = ToolRegistry()
        executor = ToolExecutor(tool_reg)
        loop = AgentLoop(registry, executor)

        ctx = AgentContext(tool_registry=tool_reg)
        result = await loop.run("你好", ctx)
        assert result == "你好！"

    @pytest.mark.asyncio
    async def test_tool_call_then_text(self):
        """工具调用后返回文本"""
        registry = ModelRoleRegistry()
        mock_provider = AsyncMock()
        mock_provider.model = "test"

        # 第一次返回工具调用，第二次返回文本
        mock_provider.chat = AsyncMock(
            side_effect=[
                _make_tool_call_response("echo", {"message": "hi"}),
                _make_text_response("工具调用完成"),
            ]
        )
        registry.register("default", mock_provider)

        tool_reg = ToolRegistry()

        async def echo(message: str) -> str:
            return f"echo: {message}"

        tool_reg.register(
            ToolInfo("echo", "回显", RiskLevel.LOW, echo, {})
        )
        executor = ToolExecutor(tool_reg)
        loop = AgentLoop(registry, executor)

        ctx = AgentContext(tool_registry=tool_reg)
        result = await loop.run("测试", ctx)
        assert result == "工具调用完成"

    @pytest.mark.asyncio
    async def test_max_rounds_limit(self):
        """达到最大轮次时自动停止"""
        registry = ModelRoleRegistry()
        mock_provider = AsyncMock()
        mock_provider.model = "test"
        # 始终返回工具调用（不会自然结束）
        mock_provider.chat = AsyncMock(
            return_value=_make_tool_call_response("echo", {"message": "loop"})
        )
        registry.register("default", mock_provider)

        tool_reg = ToolRegistry()

        async def echo(message: str) -> str:
            return "ok"

        tool_reg.register(
            ToolInfo("echo", "回显", RiskLevel.LOW, echo, {})
        )
        executor = ToolExecutor(tool_reg)
        loop = AgentLoop(registry, executor)

        ctx = AgentContext(tool_registry=tool_reg, max_rounds=3)
        result = await loop.run("测试", ctx)
        assert "最大轮次" in result

    @pytest.mark.asyncio
    async def test_llm_error_recovery(self):
        """LLM 调用失败时返回错误信息"""
        registry = ModelRoleRegistry()
        mock_provider = AsyncMock()
        mock_provider.model = "test"
        mock_provider.chat = AsyncMock(side_effect=RuntimeError("API 错误"))
        registry.register("default", mock_provider)

        tool_reg = ToolRegistry()
        executor = ToolExecutor(tool_reg)
        loop = AgentLoop(registry, executor)

        ctx = AgentContext(tool_registry=tool_reg)
        result = await loop.run("测试", ctx)
        assert "失败" in result

    @pytest.mark.asyncio
    async def test_on_tool_call_callback(self):
        """工具调用回调被触发"""
        registry = ModelRoleRegistry()
        mock_provider = AsyncMock()
        mock_provider.model = "test"
        mock_provider.chat = AsyncMock(
            side_effect=[
                _make_tool_call_response("echo", {"message": "hi"}),
                _make_text_response("done"),
            ]
        )
        registry.register("default", mock_provider)

        tool_reg = ToolRegistry()

        async def echo(message: str) -> str:
            return "ok"

        tool_reg.register(
            ToolInfo("echo", "回显", RiskLevel.LOW, echo, {})
        )
        executor = ToolExecutor(tool_reg)
        loop = AgentLoop(registry, executor)

        callback_calls = []

        def on_tool(name, args):
            callback_calls.append((name, args))

        ctx = AgentContext(tool_registry=tool_reg)
        await loop.run("测试", ctx, on_tool_call=on_tool)
        assert len(callback_calls) == 1
        assert callback_calls[0][0] == "echo"
