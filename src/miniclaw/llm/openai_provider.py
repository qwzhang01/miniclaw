"""
MiniClaw - OpenAI 兼容 API Provider

支持所有 OpenAI 兼容 API：DeepSeek、Qwen、硅基流动、Ollama 本地模型等。
使用 httpx 直接调用，不依赖 openai SDK。

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

# 默认超时：连接 10s，读取 120s（LLM 响应可能较慢）
DEFAULT_TIMEOUT = httpx.Timeout(connect=10.0, read=120.0, write=10.0, pool=10.0)


class OpenAIProvider(BaseProvider):
    """OpenAI 兼容 API Provider

    覆盖 DeepSeek / Qwen / 硅基流动 / Ollama 等所有 OpenAI 兼容服务。
    使用 httpx 异步客户端直接调用 API。
    """

    def __init__(
        self,
        base_url: str = "https://api.deepseek.com/v1",
        api_key: str = "",
        model: str = "deepseek-chat",
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
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                timeout=DEFAULT_TIMEOUT,
            )
        return self._client

    def _build_request_body(
        self,
        messages: list[MessageDict],
        tools: list[ToolSchema] | None = None,
        stream: bool = False,
    ) -> dict[str, Any]:
        """构建 API 请求体"""
        body: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "stream": stream,
        }
        if tools:
            body["tools"] = tools
            body["tool_choice"] = "auto"
        return body

    def _parse_tool_calls(
        self, raw_calls: list[dict[str, Any]]
    ) -> list[ToolCall]:
        """解析 OpenAI 格式的工具调用"""
        result = []
        for call in raw_calls:
            try:
                args = json.loads(call["function"]["arguments"])
            except (json.JSONDecodeError, KeyError):
                args = {}
            result.append(
                ToolCall(
                    id=call.get("id", ""),
                    name=call["function"]["name"],
                    arguments=args,
                )
            )
        return result

    async def chat(
        self,
        messages: list[MessageDict],
        tools: list[ToolSchema] | None = None,
    ) -> LLMResponse:
        """发送对话请求，返回完整响应"""
        client = self._get_client()
        body = self._build_request_body(messages, tools, stream=False)

        logger.debug("OpenAI API 请求", model=self.model, messages_count=len(messages))

        response = await client.post("/chat/completions", json=body)
        response.raise_for_status()
        data = response.json()

        choice = data["choices"][0]
        message = choice["message"]

        # 解析 token 使用量
        usage_data = data.get("usage", {})
        token_usage = TokenUsage(
            input_tokens=usage_data.get("prompt_tokens", 0),
            output_tokens=usage_data.get("completion_tokens", 0),
        )

        # 解析工具调用
        tool_calls = []
        if message.get("tool_calls"):
            tool_calls = self._parse_tool_calls(message["tool_calls"])

        return LLMResponse(
            text=message.get("content") or "",
            tool_calls=tool_calls,
            token_usage=token_usage,
            model=self.model,
        )

    async def chat_stream(
        self,
        messages: list[MessageDict],
        tools: list[ToolSchema] | None = None,
    ) -> AsyncIterator[StreamChunk]:
        """发送对话请求，返回流式响应（SSE）"""
        client = self._get_client()
        body = self._build_request_body(messages, tools, stream=True)

        logger.debug("OpenAI API 流式请求", model=self.model)

        async with client.stream("POST", "/chat/completions", json=body) as response:
            response.raise_for_status()
            # 累积工具调用的片段
            tool_call_buffers: dict[int, dict[str, str]] = {}

            async for line in response.aiter_lines():
                if not line.startswith("data: "):
                    continue
                data_str = line[6:]
                if data_str == "[DONE]":
                    break

                try:
                    data = json.loads(data_str)
                except json.JSONDecodeError:
                    continue

                choice = data["choices"][0]
                delta = choice.get("delta", {})

                # 文本片段
                if delta.get("content"):
                    yield StreamChunk(text=delta["content"])

                # 工具调用片段
                if delta.get("tool_calls"):
                    for tc in delta["tool_calls"]:
                        idx = tc.get("index", 0)
                        if idx not in tool_call_buffers:
                            tool_call_buffers[idx] = {
                                "id": tc.get("id", ""),
                                "name": tc.get("function", {}).get("name", ""),
                                "arguments": "",
                            }
                        if tc.get("function", {}).get("arguments"):
                            tool_call_buffers[idx]["arguments"] += tc[
                                "function"
                            ]["arguments"]

                # 最后一个 chunk 可能包含 usage
                if choice.get("finish_reason"):
                    usage_data = data.get("usage", {})
                    token_usage = None
                    if usage_data:
                        token_usage = TokenUsage(
                            input_tokens=usage_data.get("prompt_tokens", 0),
                            output_tokens=usage_data.get("completion_tokens", 0),
                        )
                    yield StreamChunk(is_final=True, token_usage=token_usage)

    async def close(self) -> None:
        """关闭 httpx 客户端"""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None
