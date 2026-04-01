"""
MiniClaw - 模型角色注册器

管理四个模型角色（default/planner/reasoner/maker）到具体 Provider 的映射。
支持按 role 参数路由、超时自动重试（3 次）、不可用时降级到 default。

对应 PRD：F2 四模型角色调度系统
"""

import asyncio
from collections.abc import AsyncIterator

from miniclaw.llm.base import (
    BaseProvider,
    LLMResponse,
    MessageDict,
    StreamChunk,
    ToolSchema,
)
from miniclaw.utils.logging import get_logger
from miniclaw.utils.tokens import get_token_counter

logger = get_logger(__name__)

# 四个模型角色（PRD F2）
MODEL_ROLES = ("default", "planner", "reasoner", "maker")
MAX_RETRIES = 3
RETRY_DELAY = 1.0  # 重试间隔（秒）


class ModelRoleRegistry:
    """四模型角色注册器

    将 default/planner/reasoner/maker 四个角色映射到具体的 LLM Provider 实例。
    支持自动重试和 fallback 机制。

    使用方式：
        registry = ModelRoleRegistry()
        registry.register("default", openai_provider)
        registry.register("reasoner", anthropic_provider)
        response = await registry.chat(messages, tools, role="reasoner")
    """

    def __init__(self) -> None:
        self._providers: dict[str, BaseProvider] = {}

    def register(self, role: str, provider: BaseProvider) -> None:
        """注册模型角色到 Provider"""
        if role not in MODEL_ROLES:
            raise ValueError(f"无效的模型角色: {role}，可选: {MODEL_ROLES}")
        self._providers[role] = provider
        logger.info("注册模型角色", role=role, model=provider.model)

    def get_provider(self, role: str) -> BaseProvider | None:
        """获取指定角色的 Provider"""
        return self._providers.get(role)

    def _get_provider_with_fallback(
        self, role: str
    ) -> tuple[BaseProvider, str]:
        """获取 Provider，不可用时 fallback 到 default（PRD F2 降级规则）

        Returns:
            (provider, actual_role) 元组，actual_role 可能因降级而变为 "default"
        """
        provider = self._providers.get(role)
        if provider is not None:
            return provider, role

        # 降级到 default
        if role != "default":
            logger.warning("模型角色不可用，降级到 default", role=role)
            default_provider = self._providers.get("default")
            if default_provider is not None:
                return default_provider, "default"

        raise RuntimeError(
            f"模型角色 '{role}' 不可用，且没有 default 角色可降级。"
            f"已注册: {list(self._providers.keys())}"
        )

    async def chat(
        self,
        messages: list[MessageDict],
        tools: list[ToolSchema] | None = None,
        role: str = "default",
    ) -> LLMResponse:
        """发送对话请求，支持自动重试和 fallback

        Args:
            messages: 对话消息列表
            tools: 工具 Schema 列表
            role: 模型角色

        Returns:
            标准化的 LLMResponse
        """
        provider, actual_role = self._get_provider_with_fallback(role)
        last_error: Exception | None = None

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                response = await provider.chat(messages, tools)
                response.role = actual_role

                # 记录 token 计数（PRD F2 Token 计数）
                counter = get_token_counter()
                counter.record(actual_role, response.token_usage)

                return response
            except Exception as e:
                last_error = e
                logger.warning(
                    "LLM 调用失败，正在重试",
                    role=role,
                    actual_role=actual_role,
                    attempt=attempt,
                    error=repr(e),
                )
                if attempt < MAX_RETRIES:
                    await asyncio.sleep(RETRY_DELAY * attempt)

        # 所有重试失败，尝试 fallback 到 default
        if role != "default" and "default" in self._providers:
            logger.warning("重试耗尽，尝试 fallback 到 default", role=role)
            try:
                default_provider = self._providers["default"]
                response = await default_provider.chat(messages, tools)
                response.role = "default"
                counter = get_token_counter()
                counter.record("default", response.token_usage)
                return response
            except Exception as fallback_error:
                logger.error(
                    "fallback 到 default 也失败",
                    error=repr(fallback_error),
                )

        raise RuntimeError(
            f"LLM 调用失败（角色={role}，重试 {MAX_RETRIES} 次）: {last_error}"
        )

    async def chat_stream(
        self,
        messages: list[MessageDict],
        tools: list[ToolSchema] | None = None,
        role: str = "default",
    ) -> AsyncIterator[StreamChunk]:
        """发送流式对话请求"""
        provider, actual_role = self._get_provider_with_fallback(role)
        async for chunk in provider.chat_stream(messages, tools):
            # 最终 chunk 记录 token 计数
            if chunk.is_final and chunk.token_usage:
                counter = get_token_counter()
                counter.record(actual_role, chunk.token_usage)
            yield chunk

    @property
    def registered_roles(self) -> list[str]:
        """已注册的角色列表"""
        return list(self._providers.keys())

    async def close_all(self) -> None:
        """关闭所有 Provider"""
        for provider in self._providers.values():
            await provider.close()
