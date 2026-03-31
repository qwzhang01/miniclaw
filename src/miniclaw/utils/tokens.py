"""
MiniClaw - Token 计数工具

按角色统计 input/output token 数，每轮循环结束后以 debug 级别写入日志。
v1 简化方案：不做实时 UI 展示，不做费用估算。

对应 PRD：F2 Token 计数
"""

from dataclasses import dataclass

from miniclaw.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class TokenUsage:
    """单次调用的 Token 使用量"""

    input_tokens: int = 0
    output_tokens: int = 0

    @property
    def total_tokens(self) -> int:
        """总 token 数"""
        return self.input_tokens + self.output_tokens


@dataclass
class RoleTokenStats:
    """单个角色的累计 Token 统计"""

    role: str
    total_input: int = 0
    total_output: int = 0
    call_count: int = 0

    @property
    def total_tokens(self) -> int:
        """累计总 token 数"""
        return self.total_input + self.total_output

    def record(self, usage: TokenUsage) -> None:
        """记录一次调用的 token 使用量"""
        self.total_input += usage.input_tokens
        self.total_output += usage.output_tokens
        self.call_count += 1


class TokenCounter:
    """Token 计数器，按角色统计所有 LLM 调用的 token 消耗

    使用方式：
        counter = TokenCounter()
        counter.record("default", TokenUsage(input_tokens=100, output_tokens=50))
        counter.log_usage()
    """

    def __init__(self) -> None:
        self._stats: dict[str, RoleTokenStats] = {}

    def record(self, role: str, usage: TokenUsage) -> None:
        """记录一次 LLM 调用的 token 使用量

        Args:
            role: 模型角色（default/planner/reasoner/maker）
            usage: 本次调用的 token 使用量
        """
        if role not in self._stats:
            self._stats[role] = RoleTokenStats(role=role)
        self._stats[role].record(usage)

        # debug 级别日志输出每次调用的 token 计数
        logger.debug(
            "token_usage",
            role=role,
            input_tokens=usage.input_tokens,
            output_tokens=usage.output_tokens,
            total=usage.total_tokens,
        )

    def get_stats(self, role: str) -> RoleTokenStats | None:
        """获取指定角色的累计统计"""
        return self._stats.get(role)

    def get_all_stats(self) -> dict[str, RoleTokenStats]:
        """获取所有角色的累计统计"""
        return dict(self._stats)

    @property
    def total_input(self) -> int:
        """所有角色的累计 input token 数"""
        return sum(s.total_input for s in self._stats.values())

    @property
    def total_output(self) -> int:
        """所有角色的累计 output token 数"""
        return sum(s.total_output for s in self._stats.values())

    @property
    def total_tokens(self) -> int:
        """所有角色的累计总 token 数"""
        return self.total_input + self.total_output

    def log_usage(self) -> None:
        """以 debug 级别输出所有角色的 token 统计摘要"""
        for role, stats in self._stats.items():
            logger.debug(
                "token_summary",
                role=role,
                input=stats.total_input,
                output=stats.total_output,
                total=stats.total_tokens,
                calls=stats.call_count,
            )
        logger.debug(
            "token_total",
            input=self.total_input,
            output=self.total_output,
            total=self.total_tokens,
        )

    def reset(self) -> None:
        """重置所有统计"""
        self._stats.clear()


# 全局 token 计数器实例
_global_counter: TokenCounter | None = None


def get_token_counter() -> TokenCounter:
    """获取全局 Token 计数器单例"""
    global _global_counter
    if _global_counter is None:
        _global_counter = TokenCounter()
    return _global_counter
