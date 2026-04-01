"""
MiniClaw - Agent 主循环测试

覆盖 OP2.2 压缩触发点。
覆盖 OP4.2 Skill 匹配注入。
"""

from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from miniclaw.agent.context import AgentContext
from miniclaw.agent.loop import AgentLoop
from miniclaw.llm.base import LLMResponse, StreamChunk, ToolCall
from miniclaw.llm.registry import ModelRoleRegistry
from miniclaw.memory.short_term import ShortTermMemory
from miniclaw.skills.loader import SkillInfo
from miniclaw.skills.matcher import SkillMatcher
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


class TestAgentLoopCompression:
    """OP2.2: 压缩触发点测试"""

    @pytest.mark.asyncio
    async def test_no_compression_when_not_needed(self):
        """token 未超阈值时不触发压缩"""
        registry = ModelRoleRegistry()
        mock_provider = AsyncMock()
        mock_provider.model = "test"
        mock_provider.chat = AsyncMock(
            return_value=_make_text_response("OK")
        )
        registry.register("default", mock_provider)

        tool_reg = ToolRegistry()
        executor = ToolExecutor(tool_reg)
        loop = AgentLoop(registry, executor)

        stm = ShortTermMemory(max_tokens=32000)
        ctx = AgentContext(tool_registry=tool_reg, short_term_memory=stm)

        await loop.run("你好", ctx)
        # chat 只调用了一次（正常对话），没有压缩摘要的额外调用
        assert mock_provider.chat.call_count == 1

    @pytest.mark.asyncio
    async def test_compression_triggered_when_needed(self):
        """token 超阈值时触发压缩"""
        registry = ModelRoleRegistry()
        mock_provider = AsyncMock()
        mock_provider.model = "test"
        # 第一次调用是压缩摘要，第二次是正常对话
        mock_provider.chat = AsyncMock(
            return_value=_make_text_response("压缩后的回复")
        )
        registry.register("default", mock_provider)

        tool_reg = ToolRegistry()
        executor = ToolExecutor(tool_reg)
        loop = AgentLoop(registry, executor)

        # 用很小的 max_tokens 并填充大量消息来触发压缩
        stm = ShortTermMemory(max_tokens=100)
        ctx = AgentContext(tool_registry=tool_reg, short_term_memory=stm)
        for i in range(20):
            ctx.add_user_message(f"长消息内容 {i}" * 20)
            ctx.add_assistant_message(f"长回复 {i}" * 20)

        await loop.run("触发压缩", ctx)
        # 应该调用了 2 次：1 次压缩摘要 + 1 次正常对话
        assert mock_provider.chat.call_count == 2

    @pytest.mark.asyncio
    async def test_compression_failure_continues(self):
        """压缩失败不影响正常对话"""
        registry = ModelRoleRegistry()
        mock_provider = AsyncMock()
        mock_provider.model = "test"

        call_count = 0

        async def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                # 第一次调用（压缩摘要）失败
                raise RuntimeError("压缩 API 失败")
            # 第二次调用（正常对话）成功
            return _make_text_response("正常回复")

        mock_provider.chat = AsyncMock(side_effect=side_effect)
        registry.register("default", mock_provider)

        tool_reg = ToolRegistry()
        executor = ToolExecutor(tool_reg)
        loop = AgentLoop(registry, executor)

        stm = ShortTermMemory(max_tokens=100)
        ctx = AgentContext(tool_registry=tool_reg, short_term_memory=stm)
        for i in range(20):
            ctx.add_user_message(f"长消息 {i}" * 20)
            ctx.add_assistant_message(f"长回复 {i}" * 20)

        result = await loop.run("测试", ctx)
        assert result == "正常回复"


def _make_skill(name: str = "coder", keywords: list[str] | None = None) -> SkillInfo:
    """创建测试用 SkillInfo"""
    return SkillInfo(
        name=name,
        path=Path("/tmp/skills") / name / "SKILL.md",
        role=f"{name} 角色",
        activation_keywords=keywords or ["编程", "代码"],
        available_tools=["shell_exec"],
        workflow="1. 步骤一",
    )


class TestAgentLoopSkillInjection:
    """OP4.2: Skill 匹配注入测试"""

    @pytest.mark.asyncio
    async def test_skill_matched_and_injected(self):
        """匹配到 Skill 时注入到 context"""
        registry = ModelRoleRegistry()
        mock_provider = AsyncMock()
        mock_provider.model = "test"
        mock_provider.chat = AsyncMock(
            return_value=_make_text_response("OK")
        )
        registry.register("default", mock_provider)

        tool_reg = ToolRegistry()
        executor = ToolExecutor(tool_reg)

        skill = _make_skill("coder", ["编程", "代码"])
        matcher = SkillMatcher({"coder": skill})
        loop = AgentLoop(registry, executor, skill_matcher=matcher)

        ctx = AgentContext(tool_registry=tool_reg)
        await loop.run("帮我写一段代码", ctx)

        assert ctx.active_skill is not None
        assert ctx.active_skill.name == "coder"
        assert "coder" in ctx.messages[0]["content"]

    @pytest.mark.asyncio
    async def test_no_skill_matched(self):
        """没有匹配到 Skill 时不注入"""
        registry = ModelRoleRegistry()
        mock_provider = AsyncMock()
        mock_provider.model = "test"
        mock_provider.chat = AsyncMock(
            return_value=_make_text_response("OK")
        )
        registry.register("default", mock_provider)

        tool_reg = ToolRegistry()
        executor = ToolExecutor(tool_reg)

        skill = _make_skill("coder", ["编程", "代码"])
        matcher = SkillMatcher({"coder": skill})
        loop = AgentLoop(registry, executor, skill_matcher=matcher)

        ctx = AgentContext(tool_registry=tool_reg)
        await loop.run("今天天气怎么样", ctx)

        assert ctx.active_skill is None
        assert "当前 Skill" not in ctx.messages[0]["content"]

    @pytest.mark.asyncio
    async def test_no_matcher_no_error(self):
        """没有 skill_matcher 时不报错"""
        registry = ModelRoleRegistry()
        mock_provider = AsyncMock()
        mock_provider.model = "test"
        mock_provider.chat = AsyncMock(
            return_value=_make_text_response("OK")
        )
        registry.register("default", mock_provider)

        tool_reg = ToolRegistry()
        executor = ToolExecutor(tool_reg)
        loop = AgentLoop(registry, executor)  # 无 skill_matcher

        ctx = AgentContext(tool_registry=tool_reg)
        result = await loop.run("测试", ctx)
        assert result == "OK"

    @pytest.mark.asyncio
    async def test_same_skill_not_reinjected(self):
        """同一 Skill 不重复注入"""
        registry = ModelRoleRegistry()
        mock_provider = AsyncMock()
        mock_provider.model = "test"
        mock_provider.chat = AsyncMock(
            return_value=_make_text_response("OK")
        )
        registry.register("default", mock_provider)

        tool_reg = ToolRegistry()
        executor = ToolExecutor(tool_reg)

        skill = _make_skill("coder", ["编程", "代码"])
        matcher = SkillMatcher({"coder": skill})
        loop = AgentLoop(registry, executor, skill_matcher=matcher)

        ctx = AgentContext(tool_registry=tool_reg)
        # 先手动激活 Skill
        ctx.inject_skill_context(skill)
        old_prompt = ctx.messages[0]["content"]

        await loop.run("帮我写代码", ctx)
        # prompt 内容应相同（没有重复注入）
        assert ctx.messages[0]["content"] == old_prompt


# ── OP6: 流式输出辅助 ──

async def _make_text_stream(text: str):
    """生成一个纯文本的流式响应"""
    for char in text:
        yield StreamChunk(text=char)
    yield StreamChunk(is_final=True)


async def _make_tool_call_stream(name: str, args_json: str, tool_id: str = "call_1"):
    """生成一个工具调用的流式响应"""
    # 先发 tool call delta
    yield StreamChunk(tool_call_delta={"index": 0, "id": tool_id, "name": name, "arguments": ""})
    # 分段发送 arguments
    mid = len(args_json) // 2
    yield StreamChunk(tool_call_delta={"index": 0, "arguments": args_json[:mid]})
    yield StreamChunk(tool_call_delta={"index": 0, "arguments": args_json[mid:]})
    yield StreamChunk(is_final=True)


class TestAgentLoopStream:
    """OP6.1 + OP6.2: 流式输出测试"""

    @pytest.mark.asyncio
    async def test_stream_text_response(self):
        """流式文本回复"""
        registry = ModelRoleRegistry()
        mock_provider = AsyncMock()
        mock_provider.model = "test"
        mock_provider.chat_stream = lambda msgs, tools: _make_text_stream("你好！")
        registry.register("default", mock_provider)

        tool_reg = ToolRegistry()
        executor = ToolExecutor(tool_reg)
        loop = AgentLoop(registry, executor)

        chunks_received: list[str] = []

        def on_stream(text: str):
            chunks_received.append(text)

        ctx = AgentContext(tool_registry=tool_reg)
        result = await loop.run_stream("你好", ctx, on_stream=on_stream)

        assert result == "你好！"
        assert len(chunks_received) == 3  # 你、好、！
        assert "".join(chunks_received) == "你好！"

    @pytest.mark.asyncio
    async def test_stream_end_callback(self):
        """流式结束回调被调用"""
        registry = ModelRoleRegistry()
        mock_provider = AsyncMock()
        mock_provider.model = "test"
        mock_provider.chat_stream = lambda msgs, tools: _make_text_stream("OK")
        registry.register("default", mock_provider)

        tool_reg = ToolRegistry()
        executor = ToolExecutor(tool_reg)
        loop = AgentLoop(registry, executor)

        end_called = []

        def on_end(text: str):
            end_called.append(True)

        ctx = AgentContext(tool_registry=tool_reg)
        await loop.run_stream("test", ctx, on_stream_end=on_end)
        assert len(end_called) == 1

    @pytest.mark.asyncio
    async def test_stream_tool_call(self):
        """流式工具调用解析（OP6.2）"""
        registry = ModelRoleRegistry()
        mock_provider = AsyncMock()
        mock_provider.model = "test"

        call_count = 0

        def make_stream(msgs, tools):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return _make_tool_call_stream("echo", '{"message": "hi"}')
            return _make_text_stream("工具完成")

        mock_provider.chat_stream = make_stream
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
        result = await loop.run_stream("测试", ctx)
        assert result == "工具完成"

    @pytest.mark.asyncio
    async def test_stream_error_recovery(self):
        """流式调用失败时返回错误信息"""
        registry = ModelRoleRegistry()
        mock_provider = AsyncMock()
        mock_provider.model = "test"

        async def failing_stream(msgs, tools):
            raise RuntimeError("流式 API 失败")
            yield StreamChunk()  # 使其成为 async generator  # noqa: B027

        mock_provider.chat_stream = failing_stream
        registry.register("default", mock_provider)

        tool_reg = ToolRegistry()
        executor = ToolExecutor(tool_reg)
        loop = AgentLoop(registry, executor)

        ctx = AgentContext(tool_registry=tool_reg)
        result = await loop.run_stream("测试", ctx)
        assert "失败" in result


class TestAgentLoopTokenBudget:
    """OP7.2 + OP7.3: Token 预算检查测试"""

    @pytest.mark.asyncio
    async def test_token_budget_logged_in_run(self):
        """run() 方法中日志包含 token 预算信息"""
        registry = ModelRoleRegistry()
        mock_provider = AsyncMock()
        mock_provider.model = "test"
        mock_provider.chat = AsyncMock(
            return_value=_make_text_response("OK")
        )
        registry.register("default", mock_provider)

        tool_reg = ToolRegistry()
        executor = ToolExecutor(tool_reg)
        loop = AgentLoop(registry, executor)

        stm = ShortTermMemory(max_tokens=32000)
        ctx = AgentContext(tool_registry=tool_reg, short_term_memory=stm)

        with patch("miniclaw.agent.loop.logger") as mock_logger:
            await loop.run("你好", ctx)
            # 验证 logger.info 被调用且包含 token 预算参数
            found = False
            for call_args in mock_logger.info.call_args_list:
                args, kwargs = call_args
                if "Agent Loop 轮次" in args[0]:
                    assert "tokens_used" in kwargs
                    assert "tokens_max" in kwargs
                    assert "tokens_ratio" in kwargs
                    found = True
                    break
            assert found, "日志中未找到 token 预算信息"

    @pytest.mark.asyncio
    async def test_token_budget_warning_at_95_percent(self):
        """token 使用率超 95% 时触发警告"""
        registry = ModelRoleRegistry()
        mock_provider = AsyncMock()
        mock_provider.model = "test"
        mock_provider.chat = AsyncMock(
            return_value=_make_text_response("OK")
        )
        registry.register("default", mock_provider)

        tool_reg = ToolRegistry()
        executor = ToolExecutor(tool_reg)
        loop = AgentLoop(registry, executor)

        # 用极小的 max_tokens 来制造超 95% 的情况
        stm = ShortTermMemory(max_tokens=50)
        ctx = AgentContext(tool_registry=tool_reg, short_term_memory=stm)
        # 系统提示词本身就会超 95%

        with patch("miniclaw.agent.loop.logger") as mock_logger:
            await loop.run("测试", ctx)
            # 验证 warning 被调用
            warning_found = False
            for call_args in mock_logger.warning.call_args_list:
                args, kwargs = call_args
                if "Token 预算即将耗尽" in args[0]:
                    assert "tokens_used" in kwargs
                    assert "tokens_max" in kwargs
                    assert "usage_ratio" in kwargs
                    warning_found = True
                    break
            assert warning_found, "未触发 token 预算警告"

    @pytest.mark.asyncio
    async def test_no_warning_when_budget_ok(self):
        """token 使用率正常时不触发警告"""
        registry = ModelRoleRegistry()
        mock_provider = AsyncMock()
        mock_provider.model = "test"
        mock_provider.chat = AsyncMock(
            return_value=_make_text_response("OK")
        )
        registry.register("default", mock_provider)

        tool_reg = ToolRegistry()
        executor = ToolExecutor(tool_reg)
        loop = AgentLoop(registry, executor)

        stm = ShortTermMemory(max_tokens=100000)  # 很大的窗口
        ctx = AgentContext(tool_registry=tool_reg, short_term_memory=stm)

        with patch("miniclaw.agent.loop.logger") as mock_logger:
            await loop.run("你好", ctx)
            # 验证 warning 没有被调用
            for call_args in mock_logger.warning.call_args_list:
                args, _kwargs = call_args
                assert "Token 预算即将耗尽" not in args[0]

    @pytest.mark.asyncio
    async def test_token_budget_in_stream_mode(self):
        """run_stream() 方法中也包含 token 预算信息"""
        registry = ModelRoleRegistry()
        mock_provider = AsyncMock()
        mock_provider.model = "test"
        mock_provider.chat_stream = lambda msgs, tools: _make_text_stream("OK")
        registry.register("default", mock_provider)

        tool_reg = ToolRegistry()
        executor = ToolExecutor(tool_reg)
        loop = AgentLoop(registry, executor)

        stm = ShortTermMemory(max_tokens=32000)
        ctx = AgentContext(tool_registry=tool_reg, short_term_memory=stm)

        with patch("miniclaw.agent.loop.logger") as mock_logger:
            await loop.run_stream("你好", ctx)
            found = False
            for call_args in mock_logger.info.call_args_list:
                args, kwargs = call_args
                if "Agent Loop 轮次" in args[0]:
                    assert "tokens_used" in kwargs
                    assert "tokens_max" in kwargs
                    assert "tokens_ratio" in kwargs
                    found = True
                    break
            assert found, "流式模式日志中未找到 token 预算信息"
