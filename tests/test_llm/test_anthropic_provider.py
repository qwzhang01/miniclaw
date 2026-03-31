"""
MiniClaw - Anthropic Provider 测试

测试 Anthropic Claude API 的消息格式转换和响应解析。
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from miniclaw.llm.anthropic_provider import AnthropicProvider


@pytest.fixture
def provider():
    return AnthropicProvider(
        api_key="test-key",
        model="claude-test",
    )


class TestConvertMessages:
    """测试消息格式转换"""

    def test_system_message_extracted(self, provider):
        """system 消息应单独提取"""
        messages = [
            {"role": "system", "content": "You are helpful"},
            {"role": "user", "content": "Hello"},
        ]
        system, converted = provider._convert_messages(messages)
        assert system == "You are helpful"
        assert len(converted) == 1
        assert converted[0]["role"] == "user"

    def test_user_message(self, provider):
        """普通 user 消息直接转换"""
        messages = [{"role": "user", "content": "Hello"}]
        _, converted = provider._convert_messages(messages)
        assert converted[0]["content"] == "Hello"

    def test_tool_result_message(self, provider):
        """tool 结果消息转为 Anthropic tool_result 格式"""
        messages = [{
            "role": "tool",
            "tool_call_id": "call_1",
            "content": "command output",
        }]
        _, converted = provider._convert_messages(messages)
        assert converted[0]["role"] == "user"
        content = converted[0]["content"]
        assert content[0]["type"] == "tool_result"
        assert content[0]["tool_use_id"] == "call_1"

    def test_user_message_with_images(self, provider):
        """带图片的 user 消息应转为多模态格式"""
        messages = [{
            "role": "user",
            "content": "What's this?",
            "images": ["base64data"],
        }]
        _, converted = provider._convert_messages(messages)
        content = converted[0]["content"]
        assert content[0]["type"] == "image"
        assert content[1]["type"] == "text"


class TestConvertTools:
    """测试工具 Schema 转换"""

    def test_convert_openai_tools(self, provider):
        """OpenAI 格式工具应转为 Anthropic 格式"""
        tools = [{
            "type": "function",
            "function": {
                "name": "shell_exec",
                "description": "Execute shell command",
                "parameters": {
                    "type": "object",
                    "properties": {"command": {"type": "string"}},
                },
            },
        }]
        converted = provider._convert_tools(tools)
        assert converted is not None
        assert converted[0]["name"] == "shell_exec"
        assert "input_schema" in converted[0]

    def test_convert_none_tools(self, provider):
        """None 工具列表返回 None"""
        assert provider._convert_tools(None) is None

    def test_convert_empty_tools(self, provider):
        """空工具列表返回 None"""
        assert provider._convert_tools([]) is None


class TestAnthropicChat:
    """测试 chat 方法"""

    @pytest.mark.asyncio
    async def test_chat_text_response(self, provider):
        """测试纯文本响应"""
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {
            "content": [{"type": "text", "text": "Hello!"}],
            "usage": {"input_tokens": 15, "output_tokens": 8},
        }

        with patch.object(provider, "_get_client") as mock_client:
            mock_client.return_value.post = AsyncMock(return_value=mock_response)
            resp = await provider.chat([{"role": "user", "content": "hi"}])

        assert resp.text == "Hello!"
        assert resp.token_usage.input_tokens == 15

    @pytest.mark.asyncio
    async def test_chat_tool_use_response(self, provider):
        """测试 tool_use 响应"""
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {
            "content": [
                {"type": "text", "text": "I'll run that command."},
                {
                    "type": "tool_use",
                    "id": "toolu_1",
                    "name": "shell_exec",
                    "input": {"command": "ls"},
                },
            ],
            "usage": {"input_tokens": 20, "output_tokens": 15},
        }

        with patch.object(provider, "_get_client") as mock_client:
            mock_client.return_value.post = AsyncMock(return_value=mock_response)
            resp = await provider.chat(
                [{"role": "user", "content": "list files"}],
                tools=[{
                    "type": "function",
                    "function": {"name": "shell_exec"},
                }],
            )

        assert resp.has_tool_calls is True
        assert resp.tool_calls[0].name == "shell_exec"
        assert resp.text == "I'll run that command."
