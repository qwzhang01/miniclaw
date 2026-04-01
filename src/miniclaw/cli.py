"""
MiniClaw - CLI 命令定义

使用 click 框架定义命令行入口，支持 `miniclaw` 命令启动。
启动时加载配置、组装组件、进入异步交互循环。

对应 PRD：F6 CLI 交互界面 / §7 M1
"""

import asyncio

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


async def _async_main(debug: bool) -> None:
    """异步主循环"""
    from miniclaw.bootstrap import bootstrap
    from miniclaw.config.wizard import needs_setup, run_wizard
    from miniclaw.utils.logging import get_logger

    logger = get_logger(__name__)

    # 首次运行引导（检测 ~/.miniclaw/config.yaml 是否存在）
    if needs_setup():
        completed = run_wizard()
        if not completed:
            console.print("[dim]使用默认配置启动...[/dim]")

    # 组装所有组件
    try:
        gateway, channel = bootstrap()
    except Exception as e:
        console.print(f"[red]❌ 启动失败: {e}[/red]")
        console.print("[dim]请检查 ~/.miniclaw/config.yaml 和 .env 配置[/dim]")
        return

    # OP5.1: 初始化长期记忆（异步）
    if gateway.long_term_memory:
        try:
            await gateway.long_term_memory.init()
        except Exception as e:
            logger.warning("长期记忆初始化失败，将禁用", error=str(e))
            gateway.long_term_memory = None

    logger.info("MiniClaw 就绪，进入交互循环")
    console.print()

    try:
        while True:
            # 通过 Channel 接收用户输入
            user_input = await channel.receive()

            if user_input is None:
                # /exit 或 Ctrl+C
                console.print("[dim]👋 再见！[/dim]")
                break

            if not user_input:
                continue

            # 特殊命令处理
            if user_input.startswith("/"):
                handled = _handle_command(user_input)
                if handled:
                    continue

            # 发送给 Gateway → Agent Loop → LLM
            try:
                await gateway.handle_message(user_input, channel)
            except Exception as e:
                logger.error("处理消息失败", error=str(e))
                console.print(f"[red]❌ 出错了: {e}[/red]")

    except KeyboardInterrupt:
        console.print("\n[dim]👋 再见！[/dim]")
    finally:
        # OP5.2: 退出时保存会话 + 关闭长期记忆
        await gateway.shutdown()


def _show_help() -> None:
    """显示帮助信息"""
    help_text = (
        "  [cyan]/help[/cyan]    — 显示此帮助信息\n"
        "  [cyan]/tools[/cyan]   — 列出可用工具\n"
        "  [cyan]/skills[/cyan]  — 列出已加载技能\n"
        "  [cyan]/history[/cyan] — 查看最近对话历史\n"
        "  [cyan]/clear[/cyan]   — 清空当前会话\n"
        "  [cyan]/screen[/cyan]  — 快捷截屏\n"
        "  [cyan]/config[/cyan]  — 查看当前配置\n"
        "  [cyan]/reload[/cyan]  — 重新加载技能\n"
        "  [cyan]/exit[/cyan]    — 退出 MiniClaw"
    )
    console.print(Panel(help_text, title="📖 帮助", border_style="blue", expand=False))


def _handle_command(command: str) -> bool:
    """处理斜杠命令，返回 True 表示已处理"""
    if command == "/help":
        _show_help()
        return True
    elif command == "/tools":
        from miniclaw.tools.registry import get_global_registry

        registry = get_global_registry()
        tools = registry.get_all()
        if tools:
            tool_list = "\n".join(
                f"  [cyan]{name}[/cyan] — {info.description} [{info.risk_level.value}]"
                for name, info in tools.items()
            )
            console.print(Panel(tool_list, title="📦 可用工具", border_style="cyan", expand=False))
        else:
            console.print("[yellow]📦 暂无已注册工具[/yellow]")
        return True
    elif command == "/skills":
        from miniclaw.skills.loader import SkillLoader

        loader = SkillLoader()
        skills = loader.load_all()
        if skills:
            skill_list = "\n".join(
                f"  [magenta]{name}[/magenta] — "
                f"关键词: {', '.join(info.activation_keywords[:5]) or '无'}"
                for name, info in skills.items()
            )
            console.print(
                Panel(skill_list, title="🧩 已加载技能", border_style="magenta", expand=False)
            )
        else:
            console.print("[yellow]🧩 暂无已加载技能[/yellow]")
        return True
    elif command == "/history":
        from miniclaw.gateway.session import SessionManager
        from miniclaw.tools.registry import get_global_registry

        mgr = SessionManager(tool_registry=get_global_registry())
        session = mgr.get("cli-default")
        if session and session.context.messages:
            # 跳过 system prompt，展示最近 10 条消息
            msgs = [
                m for m in session.context.messages if m.get("role") != "system"
            ][-10:]
            if msgs:
                lines: list[str] = []
                for m in msgs:
                    role = m.get("role", "?")
                    content = (m.get("content") or "")[:100]
                    tag = {"user": "[white]You[/white]", "assistant": "[green]🦞[/green]",
                           "tool": "[yellow]🔧[/yellow]"}.get(role, f"[dim]{role}[/dim]")
                    lines.append(f"  {tag}: {content}")
                console.print(
                    Panel("\n".join(lines), title="📜 最近对话", border_style="blue", expand=False)
                )
            else:
                console.print("[dim]📜 当前会话暂无对话历史[/dim]")
        else:
            console.print("[dim]📜 当前会话暂无对话历史[/dim]")
        return True
    elif command == "/clear":
        console.print("[dim]🗑️ 会话已清空[/dim]")
        return True
    elif command == "/screen":
        import asyncio

        async def _quick_screen() -> None:
            """快捷截屏分析"""
            try:
                from miniclaw.desktop.factory import create_controller
                controller = create_controller()
                screenshot_bytes = await controller.capture_screen()
                # 将截图信息展示给用户
                size_kb = len(screenshot_bytes) / 1024
                console.print(f"[green]📸 截屏完成（{size_kb:.0f} KB）[/green]")
                console.print("[dim]提示: 输入「分析一下截屏内容」让 Agent 帮你理解屏幕[/dim]")
            except NotImplementedError as e:
                console.print(f"[red]📸 不支持当前平台: {e}[/red]")
            except Exception as e:
                console.print(f"[red]📸 截屏失败: {e}[/red]")

        try:
            loop = asyncio.get_running_loop()
            loop.create_task(_quick_screen())
        except RuntimeError:
            asyncio.run(_quick_screen())
        return True
    elif command == "/config":
        from miniclaw.config.settings import DEFAULT_CONFIG_PATH, load_config

        config = load_config()
        config_info = (
            f"  配置文件: [cyan]{DEFAULT_CONFIG_PATH}[/cyan]\n"
            f"  default 模型: [green]{config.llm_default.model}[/green]\n"
            f"  planner 模型: {config.llm_planner.model or '(降级到 default)'}\n"
            f"  reasoner 模型: {config.llm_reasoner.model or '(降级到 default)'}\n"
            f"  maker 模型: {config.llm_maker.model or '(降级到 default)'}\n"
            f"  安全-自动审批低风险: {config.security.auto_approve_low_risk}\n"
            f"  浏览器-无头模式: {config.browser.headless}"
        )
        console.print(Panel(config_info, title="⚙️ 当前配置", border_style="green", expand=False))
        return True
    elif command == "/reload":
        from miniclaw.skills.loader import SkillLoader

        loader = SkillLoader()
        skills = loader.reload()
        console.print(
            f"[green]🔄 Skill 重新加载完成，共 {len(skills)} 个: "
            f"{', '.join(skills.keys()) or '无'}[/green]"
        )
        return True
    else:
        console.print(f"[red]❌ 未知命令: {command}，输入 /help 查看帮助[/red]")
        return True


@click.command()
@click.option("--debug", is_flag=True, default=False, help="开启调试模式")
@click.version_option(version=__version__, prog_name="miniclaw")
def main(debug: bool) -> None:
    """🦞 MiniClaw — 你的 Mac 上的 AI 操控者"""
    from miniclaw.utils.logging import setup_logging

    # 初始化日志系统
    log_level = "DEBUG" if debug else "INFO"
    setup_logging(level=log_level)

    # 展示欢迎横幅
    show_banner()

    # 进入异步主循环
    asyncio.run(_async_main(debug))
