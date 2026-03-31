"""
MiniClaw - LLM 提供方层

自己用 httpx 封装，支持 OpenAI 兼容 API 和 Anthropic Claude API。
按 PRD F2 设计，不依赖 openai/anthropic SDK。

对应 PRD：F2 四模型角色调度系统
"""

from miniclaw.llm.base import BaseProvider, LLMResponse

__all__ = ["BaseProvider", "LLMResponse"]
