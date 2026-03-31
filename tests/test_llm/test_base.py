"""
MiniClaw - LLM 基础模块测试
"""

from miniclaw.llm.base import LLMResponse, StreamChunk, ToolCall
from miniclaw.utils.tokens import TokenUsage


class TestToolCall:
    """测试工具调用数据类"""

    def test_tool_call_creation(self):
        tc = ToolCall(id="call_1", name="shell_exec", arguments={"command": "ls"})
        assert tc.id == "call_1"
        assert tc.name == "shell_exec"
        assert tc.arguments == {"command": "ls"}


class TestLLMResponse:
    """测试 LLM 响应"""

    def test_text_response(self):
        resp = LLMResponse(text="Hello")
        assert resp.text == "Hello"
        assert resp.has_tool_calls is False

    def test_tool_call_response(self):
        resp = LLMResponse(
            tool_calls=[ToolCall(id="1", name="test", arguments={})]
        )
        assert resp.has_tool_calls is True

    def test_default_values(self):
        resp = LLMResponse()
        assert resp.text == ""
        assert resp.tool_calls == []
        assert resp.model == ""
        assert resp.role == "default"
        assert resp.token_usage.total_tokens == 0


class TestStreamChunk:
    """测试流式片段"""

    def test_text_chunk(self):
        chunk = StreamChunk(text="Hello")
        assert chunk.text == "Hello"
        assert chunk.is_final is False

    def test_final_chunk_with_usage(self):
        usage = TokenUsage(input_tokens=100, output_tokens=50)
        chunk = StreamChunk(is_final=True, token_usage=usage)
        assert chunk.is_final is True
        assert chunk.token_usage is not None
        assert chunk.token_usage.total_tokens == 150
