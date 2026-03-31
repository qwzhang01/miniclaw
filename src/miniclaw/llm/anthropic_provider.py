"""
MiniClaw - Anthropic Claude API Provider

处理 Anthropic 特有的 tool_use 协议差异。
使用 httpx 直接调用，不依赖 anthropic SDK。

对应 PRD：F2 四模型角色调度系统
"""

import json
from collections.abc import AsyncIterator
from typing import Any

import httpx

from miniclaw.llm.base import (
    BaseProvider,
    LLMResponse,
    MessageDict,
    StreamChunk,
    ToolCall,
    ToolSchema,
)
from miniclaw.utils.logging import get_logger
from miniclaw.utils.tokens import TokenUsage

logger = get_logger(__name__)

DEFAULT_TIMEOUT = httpx.Timeout(connect=10.0, read=120.0, write=10.0, pool=10.0)
ANTHROPIC_API_URL = "https://api.anthropic.com"
ANTHROPIC_VERSION = "2023-06-01"


class AnthropicProvider(BaseProvider):
    """Anthropic Claude API Provider

    处理 Claude 特有的消息格式和 tool_use 协议。
    Anthropic 的 tool_use 响应格式与 OpenAI 不同，需要特殊解析。
    """

    def __init__(
        self,
        base_url: str = ANTHROPIC_API_URL,
        api_key: str = "",
        model: str = "claude-sonnet-4-20250514",
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> None:
        super().__init__(base_url, api_key, model, temperature, max_tokens)
        self._client: httpx.AsyncClient | None = None

    def _get_client(self) -> httpx.AsyncClient:
        """获取或创建 httpx 异步客户端"""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                headers={
                    "x-api-key": self.api_key,
                    "anthropic-version": ANTHROPIC_VERSION,
                    "Content-Type": "application/json",
                },
                timeout=DEFAULT_TIMEOUT,
            )
        return self._client

    def _convert_messages(
        self, messages: list[MessageDict]
    ) -> tuple[str, list[dict[str, Any]]]:
        """将 OpenAI 格式消息转为 Anthropic 格式

        Anthropic 要求 system 消息单独传递，不能在 messages 列表中。

        Returns:
            (system_prompt, converted_messages)
        """
        system_prompt = ""
        converted: list[dict[str, Any]] = []

        for msg in messages:
            role = msg["role"]
            if role == "system":
                system_prompt = msg.get("content", "")
            elif role == "assistant":
                # 处理带工具调用的 assistant 消息
                content_blocks: list[dict[str, Any]] = []
                if msg.get("content"):
                    content_blocks.append({"type": "text", "text": msg["content"]})
                if msg.get("tool_calls"):
                    for tc in msg["tool_calls"]:
                        content_blocks.append({
                            "type": "tool_use",
                            "id": tc.get("id", ""),
                            "name": tc.get("function", {}).get("name", ""),
                            "input": json.loads(
                                tc.get("function", {}).get("arguments", "{}")
                            ),
                        })
                converted.append({
                    "role": "assistant",
                    "content": content_blocks or msg.get("content", ""),
                })
            elif role == "tool":
                # OpenAI 的 tool 结果消息 → Anthropic 的 tool_result
                converted.append({
                    "role": "user",
                    "content": [{
                        "type": "tool_result",
                        "tool_use_id": msg.get("tool_call_id", ""),
                        "content": msg.get("content", ""),
                    }],
                })
            else:
                # user 消息，处理多模态（图片）
                if msg.get("images"):
                    content_parts: list[dict[str, Any]] = []
                    for img in msg["images"]:
                        content_parts.append({
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/png",
                                "data": img,
                            },
                        })
                    if msg.get("content"):
                        content_parts.append(
                            {"type": "text", "text": msg["content"]}
                        )
                    converted.append({"role": "user", "content": content_parts})
                else:
                    converted.append({
                        "role": "user",
                        "content": msg.get("content", ""),
                    })

        return system_prompt, converted

    def _convert_tools(
        self, tools: list[ToolSchema] | None
    ) -> list[dict[str, Any]] | None:
        """将 OpenAI 格式的工具 Schema 转为 Anthropic 格式"""
        if not tools:
            return None
        converted = []
        for tool in tools:
            func = tool.get("function", tool)
            converted.append({
                "name": func["name"],
                "description": func.get("description", ""),
                "input_schema": func.get("parameters", {"type": "object"}),
            })
        return converted

    async def chat(
        self,
        messages: list[MessageDict],
        tools: list[ToolSchema] | None = None,
    ) -> LLMResponse:
        """发送对话请求"""
        client = self._get_client()
        system_prompt, converted_msgs = self._convert_messages(messages)
        converted_tools = self._convert_tools(tools)

        body: dict[str, Any] = {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "messages": converted_msgs,
        }
        if system_prompt:
            body["system"] = system_prompt
        if converted_tools:
            body["tools"] = converted_tools

        logger.debug("Anthropic API 请求", model=self.model)

        response = await client.post("/v1/messages", json=body)
        response.raise_for_status()
        data = response.json()

        # 解析响应
        text_parts: list[str] = []
        tool_calls: list[ToolCall] = []

        for block in data.get("content", []):
            if block["type"] == "text":
                text_parts.append(block["text"])
            elif block["type"] == "tool_use":
                tool_calls.append(ToolCall(
                    id=block["id"],
                    name=block["name"],
                    arguments=block.get("input", {}),
                ))

        usage = data.get("usage", {})
        token_usage = TokenUsage(
            input_tokens=usage.get("input_tokens", 0),
            output_tokens=usage.get("output_tokens", 0),
        )

        return LLMResponse(
            text="\n".join(text_parts),
            tool_calls=tool_calls,
            token_usage=token_usage,
            model=self.model,
        )

    async def chat_stream(
        self,
        messages: list[MessageDict],
        tools: list[ToolSchema] | None = None,
    ) -> AsyncIterator[StreamChunk]:
        """发送流式对话请求"""
        client = self._get_client()
        system_prompt, converted_msgs = self._convert_messages(messages)
        converted_tools = self._convert_tools(tools)

        body: dict[str, Any] = {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "messages": converted_msgs,
            "stream": True,
        }
        if system_prompt:
            body["system"] = system_prompt
        if converted_tools:
            body["tools"] = converted_tools

        async with client.stream("POST", "/v1/messages", json=body) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if not line.startswith("data: "):
                    continue
                try:
                    data = json.loads(line[6:])
                except json.JSONDecodeError:
                    continue

                event_type = data.get("type", "")
                if event_type == "content_block_delta":
                    delta = data.get("delta", {})
                    if delta.get("type") == "text_delta":
                        yield StreamChunk(text=delta.get("text", ""))
                elif event_type == "message_delta":
                    usage = data.get("usage", {})
                    token_usage = TokenUsage(
                        output_tokens=usage.get("output_tokens", 0),
                    )
                    yield StreamChunk(is_final=True, token_usage=token_usage)

    async def close(self) -> None:
        """关闭 httpx 客户端"""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None
