"""
MiniClaw - CLI 命令定义

使用 click 框架定义命令行入口，支持 `miniclaw` 命令启动。
启动时展示欢迎横幅、加载配置、进入交互循环。

对应 PRD：F6 CLI 交互界面 / §7 M1
"""

import click
from rich.console import Console
from rich.panel import Panel

from miniclaw import __version__

console = Console()


def show_banner() -> None:
    """展示欢迎横幅（PRD F6 启动界面）"""
    banner_text = (
        f"[bold red]🦞 MiniClaw[/bold red] [dim]v{__version__}[/dim]\n"
        "[dim]本地 AI Agent · 能看屏幕 · 能操控电脑[/dim]\n"
        "[dim]输入 /help 查看帮助 · /exit 退出[/dim]"
    )
    console.print(Panel(banner_text, border_style="red", expand=False))


@click.command()
@click.option("--debug", is_flag=True, default=False, help="开启调试模式")
@click.version_option(version=__version__, prog_name="miniclaw")
def main(debug: bool) -> None:
    """🦞 MiniClaw — 你的 Mac 上的 AI 操控者"""
    from miniclaw.utils.logging import get_logger, setup_logging

    # 初始化日志系统
    log_level = "DEBUG" if debug else "INFO"
    setup_logging(level=log_level)
    logger = get_logger(__name__)
    logger.info("MiniClaw 启动", version=__version__, debug=debug)

    # 展示欢迎横幅
    show_banner()

    # v1: 简单的交互循环占位，后续由 Gateway + Channel 接管
    console.print()
    try:
        while True:
            try:
                user_input = console.input("[bold white]You:[/bold white] ")
            except EOFError:
                break

            user_input = user_input.strip()
            if not user_input:
                continue

            # 特殊命令处理
            if user_input == "/exit":
                console.print("[dim]👋 再见！[/dim]")
                break
            elif user_input == "/help":
                _show_help()
            elif user_input == "/tools":
                console.print("[yellow]📦 工具列表（尚未实现）[/yellow]")
            elif user_input == "/skills":
                console.print("[yellow]🧩 技能列表（尚未实现）[/yellow]")
            elif user_input == "/history":
                console.print("[yellow]📜 对话历史（尚未实现）[/yellow]")
            elif user_input == "/clear":
                console.print("[dim]🗑️ 会话已清空[/dim]")
            elif user_input == "/screen":
                console.print("[yellow]📸 截屏分析（尚未实现）[/yellow]")
            elif user_input == "/config":
                console.print("[yellow]⚙️ 配置查看（尚未实现）[/yellow]")
            elif user_input == "/reload":
                console.print("[yellow]🔄 重新加载 Skill（尚未实现）[/yellow]")
            elif user_input.startswith("/"):
                console.print(f"[red]❌ 未知命令: {user_input}，输入 /help 查看帮助[/red]")
            else:
                # Agent 对话占位
                console.print(
                    "[green]🦞 Agent 功能尚未实现，请等待 M1 里程碑完成。[/green]"
                )

    except KeyboardInterrupt:
        console.print("\n[dim]👋 再见！[/dim]")


def _show_help() -> None:
    """显示帮助信息（PRD F6 特殊命令）"""
    help_text = """[bold]可用命令：[/bold]

  [cyan]/help[/cyan]     显示帮助信息
  [cyan]/tools[/cyan]    列出所有可用工具
  [cyan]/skills[/cyan]   列出已加载的技能
  [cyan]/history[/cyan]  查看对话历史
  [cyan]/clear[/cyan]    清空当前会话
  [cyan]/screen[/cyan]   快捷截屏分析
  [cyan]/config[/cyan]   查看/修改配置
  [cyan]/reload[/cyan]   重新加载所有 Skill
  [cyan]/exit[/cyan]     退出 MiniClaw"""
    console.print(Panel(help_text, title="帮助", border_style="cyan", expand=False))
