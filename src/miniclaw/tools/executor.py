"""
MiniClaw - 工具执行引擎

完整流程：参数校验 → 安全审批 → 执行 → 格式化结果 → 返回 ToolResult。
支持三级安全审批：low=自动 / high=确认 / critical=二次确认。
用户拒绝时返回标准化结果，不中断 Agent Loop。

对应 PRD：F3 工具系统
"""

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from miniclaw.tools.registry import RiskLevel, ToolInfo, ToolRegistry
from miniclaw.utils.logging import get_logger

logger = get_logger(__name__)

# 工具执行默认超时（秒）
DEFAULT_TIMEOUT = 30


@dataclass
class ToolResult:
    """工具执行结果（PRD F3 / architecture.md §5）"""

    success: bool
    output: str
    tool_name: str


# 审批回调类型：接收工具名和描述，返回是否批准
ApprovalCallback = Callable[[str, str, RiskLevel], Awaitable[bool]]


async def _auto_approve(name: str, desc: str, risk: RiskLevel) -> bool:
    """默认审批策略：low 自动通过，其他拒绝"""
    return risk == RiskLevel.LOW


class ToolExecutor:
    """工具执行引擎

    负责完整的工具调用流程：
    1. 查找工具
    2. 参数校验
    3. 安全审批（通过 Channel 回调）
    4. 执行工具
    5. 格式化结果

    Attributes:
        registry: 工具注册中心
        approval_callback: 审批回调（由 Channel 提供）
        timeout: 执行超时（秒）
    """

    def __init__(
        self,
        registry: ToolRegistry,
        approval_callback: ApprovalCallback | None = None,
        timeout: int = DEFAULT_TIMEOUT,
    ) -> None:
        self.registry = registry
        self.approval_callback = approval_callback or _auto_approve
        self.timeout = timeout

    async def execute(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        tool_call_id: str = "",
    ) -> ToolResult:
        """执行工具调用

        Args:
            tool_name: 工具名称
            arguments: 工具参数
            tool_call_id: 调用 ID（来自 LLM）

        Returns:
            ToolResult，所有路径都不中断循环
        """
        # 1. 查找工具
        tool_info = self.registry.get(tool_name)
        if tool_info is None:
            logger.warning("工具不存在", tool=tool_name)
            return ToolResult(
                success=False,
                output=f"工具 '{tool_name}' 不存在",
                tool_name=tool_name,
            )

        # 2. 安全审批
        try:
            approved = await self._approve(tool_info, arguments)
        except Exception as e:
            logger.error("审批过程异常", tool=tool_name, error=str(e))
            return ToolResult(
                success=False,
                output=f"审批过程异常: {e}",
                tool_name=tool_name,
            )

        if not approved:
            # 用户拒绝 → 返回标准化结果，不中断循环（PRD F3）
            logger.info("用户拒绝执行", tool=tool_name)
            return ToolResult(
                success=False,
                output="用户拒绝执行此操作",
                tool_name=tool_name,
            )

        # 3. 执行工具
        try:
            result = await asyncio.wait_for(
                self._run_tool(tool_info, arguments),
                timeout=self.timeout,
            )
            logger.info("工具执行成功", tool=tool_name)
            return ToolResult(
                success=True,
                output=str(result),
                tool_name=tool_name,
            )
        except TimeoutError:
            logger.warning("工具执行超时", tool=tool_name, timeout=self.timeout)
            return ToolResult(
                success=False,
                output=f"执行超时（{self.timeout}秒）",
                tool_name=tool_name,
            )
        except Exception as e:
            logger.error("工具执行失败", tool=tool_name, error=str(e))
            return ToolResult(
                success=False,
                output=f"执行失败: {e}",
                tool_name=tool_name,
            )

    async def _approve(
        self, tool_info: ToolInfo, arguments: dict[str, Any]
    ) -> bool:
        """安全审批流程（PRD F3 三级审批）"""
        if tool_info.risk_level == RiskLevel.LOW:
            return True

        # high 和 critical 都通过回调询问用户
        desc = f"{tool_info.name}({arguments})"
        return await self.approval_callback(
            tool_info.name, desc, tool_info.risk_level
        )

    async def _run_tool(
        self, tool_info: ToolInfo, arguments: dict[str, Any]
    ) -> str:
        """执行工具函数"""
        func = tool_info.func
        # 支持同步和异步函数
        if asyncio.iscoroutinefunction(func):
            result = await func(**arguments)
        else:
            result = func(**arguments)
        return str(result)
