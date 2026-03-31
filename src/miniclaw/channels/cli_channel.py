"""
MiniClaw - CLI 通道实现

使用 Rich 美化输出，彩色区分不同消息类型。
支持工具调用过程可视化和安全审批交互。

对应 PRD：F6 CLI 交互界面
"""

from rich.console import Console
from rich.panel import Panel

from miniclaw.channels.base import ChannelProtocol
from miniclaw.tools.registry import RiskLevel

console = Console()


class CLIChannel(ChannelProtocol):
    """CLI 通道 — Rich 美化终端交互

    彩色区分：用户(白) / Agent(绿) / 工具(黄) / 错误(红)
    """

    async def receive(self) -> str | None:
        """接收用户输入"""
        try:
            user_input = console.input("[bold white]You:[/bold white] ")
            stripped = user_input.strip()
            if stripped == "/exit":
                return None
            return stripped if stripped else ""
        except (EOFError, KeyboardInterrupt):
            return None

    async def send(self, message: str) -> None:
        """发送 Agent 回复（绿色）"""
        console.print(f"[green]🦞 {message}[/green]")

    async def send_tool_call(
        self, tool_name: str, arguments: dict[str, object]
    ) -> None:
        """展示工具调用过程（黄色）"""
        args_str = ", ".join(f"{k}={v}" for k, v in arguments.items())
        console.print(
            f"[yellow]🔧 [调用工具] {tool_name}({args_str})[/yellow]"
        )

    async def send_tool_result(
        self, tool_name: str, result: str, success: bool
    ) -> None:
        """展示工具结果"""
        if success:
            # 截断过长的结果
            display = result[:500] + "..." if len(result) > 500 else result
            console.print(f"[dim]📋 [结果] {display}[/dim]")
        else:
            console.print(f"[red]❌ [失败] {result}[/red]")

    async def confirm(
        self, tool_name: str, description: str, risk_level: RiskLevel
    ) -> bool:
        """安全审批交互"""
        if risk_level == RiskLevel.LOW:
            return True

        if risk_level == RiskLevel.CRITICAL:
            console.print(
                Panel(
                    f"[bold red]⚠️ 危险操作[/bold red]\n{description}",
                    border_style="red",
                )
            )
            try:
                answer = console.input(
                    "[red]输入 CONFIRM 确认执行，其他取消: [/red]"
                )
                return answer.strip() == "CONFIRM"
            except (EOFError, KeyboardInterrupt):
                return False

        # HIGH risk
        console.print(
            f"[yellow]⚡ 即将执行: {description}[/yellow]"
        )
        try:
            answer = console.input("[yellow]确认执行？(y/n): [/yellow]")
            return answer.strip().lower() in ("y", "yes")
        except (EOFError, KeyboardInterrupt):
            return False
