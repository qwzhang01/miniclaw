"""
MiniClaw - CLI 通道实现

使用 Rich 美化输出 + prompt_toolkit 处理输入。
prompt_toolkit 正确处理 Unicode 宽字符（中文退格/删除），
支持历史记录（↑↓翻页）和完整的行编辑（Home/End/Ctrl+A 等）。

非 TTY 环境（管道、测试）自动回退到内置 input()。

对应 PRD：F6 CLI 交互界面
"""

import sys

from rich.console import Console
from rich.panel import Panel

from miniclaw.channels.base import ChannelProtocol
from miniclaw.tools.registry import RiskLevel

console = Console()


def _is_tty() -> bool:
    """检测当前 stdin 是否为真实终端（TTY）"""
    return hasattr(sys.stdin, "isatty") and sys.stdin.isatty()


class CLIChannel(ChannelProtocol):
    """CLI 通道 — Rich 输出 + prompt_toolkit 输入

    输出：Rich 彩色（用户白/Agent绿/工具黄/错误红）
    输入：
      - TTY 环境 → prompt_toolkit（Unicode 宽字符 + 历史记录 + 行编辑）
      - 非 TTY 环境 → 内置 input()（兼容管道和测试）
    支持 OP6.3 流式逐 token 输出。
    """

    def __init__(self) -> None:
        self._stream_started = False
        self._prompt_session = None  # 延迟初始化 prompt_toolkit
        if _is_tty():
            try:
                from prompt_toolkit import PromptSession
                from prompt_toolkit.history import InMemoryHistory
                self._prompt_session = PromptSession(history=InMemoryHistory())
            except ImportError:
                pass  # prompt_toolkit 不可用时回退到 input()

    async def receive(self) -> str | None:
        """接收用户输入

        TTY 环境使用 prompt_toolkit（正确处理中文退格/删除 + 历史记录），
        非 TTY 环境回退到内置 input()。
        """
        try:
            if self._prompt_session is not None:
                from prompt_toolkit.formatted_text import HTML
                user_input = await self._prompt_session.prompt_async(
                    HTML("<b>You:</b> "),
                )
            else:
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
                if self._prompt_session is not None:
                    from prompt_toolkit.formatted_text import HTML
                    answer = await self._prompt_session.prompt_async(
                        HTML("<ansired>输入 CONFIRM 确认执行，其他取消: </ansired>"),
                    )
                else:
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
            if self._prompt_session is not None:
                from prompt_toolkit.formatted_text import HTML
                answer = await self._prompt_session.prompt_async(
                    HTML("<ansiyellow>确认执行？(y/n): </ansiyellow>"),
                )
            else:
                answer = console.input("[yellow]确认执行？(y/n): [/yellow]")
            return answer.strip().lower() in ("y", "yes")
        except (EOFError, KeyboardInterrupt):
            return False

    async def send_stream_chunk(self, text: str) -> None:
        """流式输出片段（OP6.3 真正的逐 token 打字机效果）"""
        if not self._stream_started:
            # 首个 chunk：输出前缀
            console.print("[green]🦞 [/green]", end="")
            self._stream_started = True
        # 逐片段输出（不换行）
        console.print(f"[green]{text}[/green]", end="")

    async def send_stream_end(self) -> None:
        """流式输出结束（OP6.3）"""
        if self._stream_started:
            console.print()  # 换行
            self._stream_started = False
