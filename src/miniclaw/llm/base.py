"""
MiniClaw - LLM Provider 抽象基类

定义统一的 LLM 调用接口，所有 Provider 必须实现 chat() 和 chat_stream() 方法。
支持 messages + tools + role 参数，返回标准化的 LLMResponse。

对应 PRD：F2 四模型角色调度系统
"""

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Any

from miniclaw.utils.tokens import TokenUsage


@dataclass
class ToolCall:
    """LLM 返回的工具调用请求"""

    id: str
    name: str
    arguments: dict[str, Any]


@dataclass
class LLMResponse:
    """LLM 调用返回的标准化响应"""

    text: str = ""
    tool_calls: list[ToolCall] = field(default_factory=list)
    token_usage: TokenUsage = field(default_factory=TokenUsage)
    model: str = ""
    role: str = "default"

    @property
    def has_tool_calls(self) -> bool:
        """是否包含工具调用请求"""
        return len(self.tool_calls) > 0


@dataclass
class StreamChunk:
    """流式输出的单个片段"""

    text: str = ""
    tool_call_delta: dict[str, Any] | None = None
    is_final: bool = False
    token_usage: TokenUsage | None = None


# 消息和工具 Schema 的类型别名
MessageDict = dict[str, Any]
ToolSchema = dict[str, Any]


class BaseProvider(ABC):
    """LLM Provider 抽象基类

    所有 Provider（OpenAI 兼容、Anthropic）必须实现此接口。
    使用 httpx 直接调用 API，不依赖第三方 SDK（PRD F2 设计理念）。

    Attributes:
        base_url: API 基础 URL
        api_key: API 密钥
        model: 模型名称
        temperature: 温度参数
        max_tokens: 最大输出 token 数
    """

    def __init__(
        self,
        base_url: str,
        api_key: str,
        model: str,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens

    @abstractmethod
    async def chat(
        self,
        messages: list[MessageDict],
        tools: list[ToolSchema] | None = None,
    ) -> LLMResponse:
        """发送对话请求，返回完整响应

        Args:
            messages: 对话消息列表
            tools: 可用工具的 JSON Schema 列表

        Returns:
            标准化的 LLMResponse
        """
        ...

    @abstractmethod
    async def chat_stream(
        self,
        messages: list[MessageDict],
        tools: list[ToolSchema] | None = None,
    ) -> AsyncIterator[StreamChunk]:
        """发送对话请求，返回流式响应

        Args:
            messages: 对话消息列表
            tools: 可用工具的 JSON Schema 列表

        Yields:
            StreamChunk 流式片段
        """
        ...
        # 确保是异步生成器
        yield StreamChunk()  # pragma: no cover

    async def close(self) -> None:  # noqa: B027
        """关闭 Provider 释放资源（子类可覆写，默认无操作）"""
