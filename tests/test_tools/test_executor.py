"""
MiniClaw - 工具执行引擎测试

测试工具执行、安全审批、超时处理、用户拒绝。
"""

import asyncio

import pytest

from miniclaw.tools.executor import ToolExecutor, ToolResult
from miniclaw.tools.registry import RiskLevel, ToolInfo, ToolRegistry


@pytest.fixture
def registry():
    """创建带测试工具的注册中心"""
    reg = ToolRegistry()

    async def echo(message: str) -> str:
        return f"echo: {message}"

    async def slow_tool(seconds: str) -> str:
        await asyncio.sleep(float(seconds))
        return "done"

    async def failing_tool() -> str:
        raise ValueError("工具内部错误")

    async def risky_tool(target: str) -> str:
        return f"risky: {target}"

    reg.register(
        ToolInfo("echo", "回显", RiskLevel.LOW, echo, {})
    )
    reg.register(
        ToolInfo("slow_tool", "慢工具", RiskLevel.LOW, slow_tool, {})
    )
    reg.register(
        ToolInfo("failing_tool", "会失败", RiskLevel.LOW, failing_tool, {})
    )
    reg.register(
        ToolInfo("risky_tool", "高风险", RiskLevel.HIGH, risky_tool, {})
    )
    return reg


class TestToolExecutor:
    @pytest.mark.asyncio
    async def test_execute_low_risk_tool(self, registry):
        """低风险工具自动执行"""
        executor = ToolExecutor(registry)
        result = await executor.execute("echo", {"message": "hello"})
        assert result.success is True
        assert result.output == "echo: hello"
        assert result.tool_name == "echo"

    @pytest.mark.asyncio
    async def test_execute_nonexistent_tool(self, registry):
        """不存在的工具返回错误"""
        executor = ToolExecutor(registry)
        result = await executor.execute("nonexistent", {})
        assert result.success is False
        assert "不存在" in result.output

    @pytest.mark.asyncio
    async def test_execute_failing_tool(self, registry):
        """工具执行失败返回错误"""
        executor = ToolExecutor(registry)
        result = await executor.execute("failing_tool", {})
        assert result.success is False
        assert "执行失败" in result.output

    @pytest.mark.asyncio
    async def test_execute_timeout(self, registry):
        """工具执行超时"""
        executor = ToolExecutor(registry, timeout=1)
        result = await executor.execute("slow_tool", {"seconds": "10"})
        assert result.success is False
        assert "超时" in result.output


class TestSecurityApproval:
    @pytest.mark.asyncio
    async def test_high_risk_approved(self, registry):
        """高风险工具审批通过时正常执行"""

        async def approve_all(name, desc, risk):
            return True

        executor = ToolExecutor(registry, approval_callback=approve_all)
        result = await executor.execute("risky_tool", {"target": "test"})
        assert result.success is True
        assert "risky: test" in result.output

    @pytest.mark.asyncio
    async def test_high_risk_rejected(self, registry):
        """用户拒绝高风险工具"""

        async def reject_all(name, desc, risk):
            return False

        executor = ToolExecutor(registry, approval_callback=reject_all)
        result = await executor.execute("risky_tool", {"target": "test"})
        assert result.success is False
        assert "用户拒绝" in result.output

    @pytest.mark.asyncio
    async def test_default_auto_approve_low_risk(self, registry):
        """默认审批策略自动通过低风险"""
        executor = ToolExecutor(registry)
        result = await executor.execute("echo", {"message": "auto"})
        assert result.success is True

    @pytest.mark.asyncio
    async def test_default_reject_high_risk(self, registry):
        """默认审批策略拒绝高风险"""
        executor = ToolExecutor(registry)
        result = await executor.execute("risky_tool", {"target": "test"})
        assert result.success is False
        assert "用户拒绝" in result.output


class TestToolResult:
    def test_tool_result_creation(self):
        result = ToolResult(success=True, output="ok", tool_name="test")
        assert result.success is True
        assert result.output == "ok"
        assert result.tool_name == "test"
