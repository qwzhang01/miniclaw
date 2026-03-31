"""
MiniClaw - OpenAI Provider 测试

使用 httpx mock 测试 OpenAI 兼容 API 的请求和响应解析。
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from miniclaw.llm.openai_provider import OpenAIProvider


@pytest.fixture
def provider():
    return OpenAIProvider(
        base_url="https://api.test.com/v1",
        api_key="test-key",
        model="test-model",
    )


class TestOpenAIProviderInit:
    """测试 Provider 初始化"""

    def test_default_values(self):
        p = OpenAIProvider()
        assert p.base_url == "https://api.deepseek.com/v1"
        assert p.model == "deepseek-chat"
        assert p.temperature == 0.7
        assert p.max_tokens == 4096

    def test_custom_values(self, provider):
        assert provider.base_url == "https://api.test.com/v1"
        assert provider.api_key == "test-key"
        assert provider.model == "test-model"


class TestBuildRequestBody:
    """测试请求体构建"""

    def test_basic_body(self, provider):
        body = provider._build_request_body(
            messages=[{"role": "user", "content": "hi"}]
        )
        assert body["model"] == "test-model"
        assert body["messages"] == [{"role": "user", "content": "hi"}]
        assert body["stream"] is False
        assert "tools" not in body

    def test_body_with_tools(self, provider):
        tools = [{"type": "function", "function": {"name": "test"}}]
        body = provider._build_request_body(
            messages=[{"role": "user", "content": "hi"}],
            tools=tools,
        )
        assert body["tools"] == tools
        assert body["tool_choice"] == "auto"

    def test_stream_body(self, provider):
        body = provider._build_request_body(
            messages=[{"role": "user", "content": "hi"}],
            stream=True,
        )
        assert body["stream"] is True


class TestParseToolCalls:
    """测试工具调用解析"""

    def test_parse_valid_tool_calls(self, provider):
        raw = [{
            "id": "call_1",
            "function": {
                "name": "shell_exec",
                "arguments": '{"command": "ls -la"}',
            },
        }]
        calls = provider._parse_tool_calls(raw)
        assert len(calls) == 1
        assert calls[0].name == "shell_exec"
        assert calls[0].arguments == {"command": "ls -la"}

    def test_parse_invalid_json_arguments(self, provider):
        """无效 JSON 参数应返回空字典"""
        raw = [{
            "id": "call_1",
            "function": {
                "name": "test",
                "arguments": "invalid json",
            },
        }]
        calls = provider._parse_tool_calls(raw)
        assert calls[0].arguments == {}


class TestOpenAIChat:
    """测试 chat 方法"""

    @pytest.mark.asyncio
    async def test_chat_text_response(self, provider):
        """测试纯文本响应"""
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {
            "choices": [{
                "message": {
                    "content": "Hello!",
                    "role": "assistant",
                },
            }],
            "usage": {
                "prompt_tokens": 10,
                "completion_tokens": 5,
            },
        }

        with patch.object(provider, "_get_client") as mock_client:
            mock_client.return_value.post = AsyncMock(return_value=mock_response)
            resp = await provider.chat([{"role": "user", "content": "hi"}])

        assert resp.text == "Hello!"
        assert resp.has_tool_calls is False
        assert resp.token_usage.input_tokens == 10
        assert resp.token_usage.output_tokens == 5

    @pytest.mark.asyncio
    async def test_chat_tool_call_response(self, provider):
        """测试工具调用响应"""
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {
            "choices": [{
                "message": {
                    "content": None,
                    "role": "assistant",
                    "tool_calls": [{
                        "id": "call_1",
                        "function": {
                            "name": "shell_exec",
                            "arguments": '{"command": "ls"}',
                        },
                    }],
                },
            }],
            "usage": {"prompt_tokens": 20, "completion_tokens": 10},
        }

        with patch.object(provider, "_get_client") as mock_client:
            mock_client.return_value.post = AsyncMock(return_value=mock_response)
            resp = await provider.chat(
                [{"role": "user", "content": "list files"}],
                tools=[{"type": "function", "function": {"name": "shell_exec"}}],
            )

        assert resp.has_tool_calls is True
        assert resp.tool_calls[0].name == "shell_exec"
        assert resp.tool_calls[0].arguments == {"command": "ls"}


class TestOpenAIClose:
    """测试资源释放"""

    @pytest.mark.asyncio
    async def test_close_client(self, provider):
        """close 应关闭 httpx 客户端"""
        # 初始时没有客户端，close 不应报错
        await provider.close()
