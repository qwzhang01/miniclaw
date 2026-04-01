"""
MiniClaw - 短期记忆

内存中维护当前会话的对话历史（Message 列表）。
支持上下文窗口管理：历史接近 token 上限时自动摘要压缩。

对应 PRD：F8 记忆系统
"""

from typing import Any

from miniclaw.utils.logging import get_logger

logger = get_logger(__name__)

MessageDict = dict[str, Any]

# 默认上下文窗口大小（token 数近似）
DEFAULT_MAX_TOKENS = 32000
# 每条消息平均 token 数（粗略估算：中文 ~2 字/token，英文 ~0.75 词/token）
AVG_CHARS_PER_TOKEN = 3


def _estimate_tokens(messages: list[MessageDict]) -> int:
    """粗略估算消息列表的 token 数"""
    total_chars = 0
    for msg in messages:
        content = msg.get("content") or ""
        if isinstance(content, str):
            total_chars += len(content)
    return total_chars // AVG_CHARS_PER_TOKEN


class ShortTermMemory:
    """短期记忆 — 当前会话的对话历史

    Attributes:
        messages: 消息列表
        max_tokens: 上下文窗口大小上限
    """

    def __init__(self, max_tokens: int = DEFAULT_MAX_TOKENS) -> None:
        self.messages: list[MessageDict] = []
        self.max_tokens = max_tokens

    def add(self, message: MessageDict) -> None:
        """添加一条消息"""
        self.messages.append(message)

    def get_messages(self) -> list[MessageDict]:
        """获取所有消息"""
        return list(self.messages)

    def needs_compression(self) -> bool:
        """判断是否需要压缩（token 数超过阈值的 80%）"""
        estimated = _estimate_tokens(self.messages)
        return estimated > int(self.max_tokens * 0.8)

    def compress(self, summary: str) -> None:
        """压缩历史：保留 system prompt + 最近 4 条消息，其余替换为摘要

        Args:
            summary: 由 LLM（default 角色）生成的历史摘要
        """
        if len(self.messages) <= 5:
            return

        # 保留 system prompt（第一条）
        system_msg = self.messages[0] if self.messages[0].get("role") == "system" else None
        # 保留最近 4 条消息
        recent = self.messages[-4:]

        compressed: list[MessageDict] = []
        if system_msg:
            compressed.append(system_msg)
        # 插入摘要作为 system 补充
        compressed.append({
            "role": "system",
            "content": f"[历史摘要] {summary}",
        })
        compressed.extend(recent)

        old_count = len(self.messages)
        self.messages = compressed
        logger.info(
            "上下文压缩",
            old_messages=old_count,
            new_messages=len(self.messages),
        )

    def clear(self) -> None:
        """清空所有消息"""
        self.messages.clear()

    def update_system_prompt(self, prompt: str) -> None:
        """更新系统提示词（OP4.1 Skill 注入/清除时使用）

        替换 messages[0] 的系统提示词内容。
        如果第一条消息不是 system 角色，则插入到开头。

        Args:
            prompt: 新的系统提示词内容
        """
        if self.messages and self.messages[0].get("role") == "system":
            self.messages[0] = {"role": "system", "content": prompt}
        else:
            self.messages.insert(0, {"role": "system", "content": prompt})

    @property
    def message_count(self) -> int:
        """消息数量"""
        return len(self.messages)

    @property
    def estimated_tokens(self) -> int:
        """估算当前 token 数"""
        return _estimate_tokens(self.messages)
