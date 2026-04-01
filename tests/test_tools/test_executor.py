"""
MiniClaw - 工具执行引擎测试

测试工具执行、安全审批、超时处理、用户拒绝。
OP3.1: 测试工具输出截断。
"""

import asyncio

import pytest

from miniclaw.tools.executor import ToolExecutor, ToolResult, _truncate_output
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

    async def long_output_tool() -> str:
        return "x" * 20000  # 超长输出

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
    reg.register(
        ToolInfo("long_output_tool", "超长输出", RiskLevel.LOW, long_output_tool, {})
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


class TestOutputTruncation:
    """OP3.1: 工具输出截断测试"""

    def test_short_output_not_truncated(self):
        """短输出不截断"""
        output = "hello world"
        result = _truncate_output(output, 8000)
        assert result == output

    def test_long_output_truncated(self):
        """超长输出被截断"""
        output = "x" * 20000
        result = _truncate_output(output, 8000)
        assert len(result) < 20000
        assert "输出已截断" in result
        assert "20000" in result  # 显示原始字符数

    def test_exact_limit_not_truncated(self):
        """刚好等于限制时不截断"""
        output = "x" * 8000
        result = _truncate_output(output, 8000)
        assert result == output
        assert "截断" not in result

    @pytest.mark.asyncio
    async def test_executor_truncates_long_output(self, registry):
        """OP3.1: ToolExecutor 自动截断超长输出"""
        executor = ToolExecutor(registry, max_output_chars=100)
        result = await executor.execute("long_output_tool", {})
        assert result.success is True
        assert "输出已截断" in result.output
        assert len(result.output) < 20000

    @pytest.mark.asyncio
    async def test_executor_custom_max_chars(self, registry):
        """OP3.2: 可配置截断阈值"""
        executor = ToolExecutor(registry, max_output_chars=50)
        result = await executor.execute("long_output_tool", {})
        assert "仅显示前 50 字符" in result.output
