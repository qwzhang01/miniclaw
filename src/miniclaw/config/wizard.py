"""
MiniClaw - 首次运行配置引导

检测配置文件是否存在，不存在则交互式引导用户完成配置。
引导流程：检测 → 询问 API Key → 生成 config.yaml + .env。

对应 PRD：F9 配置管理 / 架构文档 §2.1
"""

from pathlib import Path

from rich.console import Console
from rich.panel import Panel

from miniclaw.config.settings import DEFAULT_CONFIG_PATH
from miniclaw.utils.logging import get_logger

logger = get_logger(__name__)
console = Console()

# .env 模板
ENV_TEMPLATE = """# MiniClaw 环境变量配置
# 切换平台/模型只改这里，config.yaml 不用动

# LLM API 配置（必填）
LLM_BASE_URL={base_url}
LLM_API_KEY={api_key}
LLM_MODEL={model}
"""

# config.yaml 最简模板
CONFIG_TEMPLATE = """# MiniClaw 配置文件
# 详细说明见 docs/configuration.md

llm:
  default:
    provider: openai_compatible
    base_url: ${{LLM_BASE_URL}}
    api_key: ${{LLM_API_KEY}}
    model: ${{LLM_MODEL}}
    temperature: 0.7
    max_tokens: 4096

security:
  auto_approve_low_risk: true
  confirm_high_risk: true
  allowed_directories:
    - ~/git/
    - ~/Documents/

browser:
  headless: false
  use_system_chrome: true

logging:
  level: info
"""

# 平台选项
PLATFORMS = [
    ("DeepSeek", "https://api.deepseek.com/v1", "deepseek-chat"),
    ("硅基流动 (SiliconFlow)", "https://api.siliconflow.cn/v1", "deepseek-ai/DeepSeek-V3"),
    ("OpenAI", "https://api.openai.com/v1", "gpt-4o-mini"),
    ("Ollama (本地)", "http://localhost:11434/v1", "qwen2.5:14b"),
    ("自定义", "", ""),
]


def needs_setup() -> bool:
    """检查是否需要首次配置引导"""
    return not DEFAULT_CONFIG_PATH.exists()


def run_wizard() -> bool:
    """运行首次配置引导

    Returns:
        True 表示配置完成，False 表示用户跳过
    """
    console.print()
    console.print(
        Panel(
            "[bold yellow]🦞 首次运行配置引导[/bold yellow]\n\n"
            "检测到尚未配置 MiniClaw，需要填写 LLM API 信息。\n"
            "只需 3 步，1 分钟完成！",
            border_style="yellow",
            expand=False,
        )
    )

    # 步骤 1：选择平台
    console.print("\n[bold]步骤 1/3：选择 LLM 平台[/bold]\n")
    for i, (name, url, _model) in enumerate(PLATFORMS, 1):
        hint = f" ({url})" if url else ""
        console.print(f"  [cyan]{i}[/cyan]. {name}{hint}")

    try:
        choice_str = console.input("\n请选择 [1-5]，直接回车选 1 (DeepSeek): ").strip()
        choice = int(choice_str) if choice_str else 1
        if choice < 1 or choice > len(PLATFORMS):
            choice = 1
    except (ValueError, EOFError, KeyboardInterrupt):
        console.print("[dim]已跳过配置引导，使用默认配置[/dim]")
        return False

    platform_name, base_url, model = PLATFORMS[choice - 1]

    # 自定义平台需要手动输入
    if platform_name == "自定义":
        try:
            base_url = console.input("请输入 base_url: ").strip()
            model = console.input("请输入 model 名称: ").strip()
        except (EOFError, KeyboardInterrupt):
            return False

    # 步骤 2：填写 API Key
    console.print(f"\n[bold]步骤 2/3：填写 API Key[/bold] ({platform_name})\n")

    if platform_name == "Ollama (本地)":
        api_key = "ollama"
        console.print("[dim]Ollama 本地运行，无需 API Key[/dim]")
    else:
        try:
            api_key = console.input("请输入 API Key: ").strip()
            if not api_key:
                console.print("[red]API Key 不能为空，已跳过配置[/red]")
                return False
        except (EOFError, KeyboardInterrupt):
            return False

    # 步骤 3：确认并生成文件
    console.print("\n[bold]步骤 3/3：确认配置[/bold]\n")
    console.print(f"  平台: [cyan]{platform_name}[/cyan]")
    console.print(f"  base_url: [cyan]{base_url}[/cyan]")
    console.print(f"  model: [cyan]{model}[/cyan]")
    masked_key = api_key[:8] + ("*" * (len(api_key) - 8) if len(api_key) > 8 else "")
    console.print(f"  api_key: [cyan]{masked_key}[/cyan]")

    try:
        confirm = console.input("\n确认生成配置？(y/n, 直接回车确认): ").strip().lower()
        if confirm and confirm not in ("y", "yes", ""):
            console.print("[dim]已取消配置[/dim]")
            return False
    except (EOFError, KeyboardInterrupt):
        return False

    # 生成文件
    _generate_files(base_url, api_key, model)

    console.print(
        Panel(
            "[bold green]✅ 配置完成！[/bold green]\n\n"
            f"  配置文件: [cyan]{DEFAULT_CONFIG_PATH}[/cyan]\n"
            f"  环境变量: [cyan]{Path.cwd() / '.env'}[/cyan]\n\n"
            "[dim]之后可通过 /config 查看配置，编辑文件修改配置[/dim]",
            border_style="green",
            expand=False,
        )
    )
    return True


def _generate_files(base_url: str, api_key: str, model: str) -> None:
    """生成 config.yaml 和 .env 文件"""
    # 创建 ~/.miniclaw 目录
    config_dir = DEFAULT_CONFIG_PATH.parent
    config_dir.mkdir(parents=True, exist_ok=True)

    # 生成 config.yaml
    DEFAULT_CONFIG_PATH.write_text(CONFIG_TEMPLATE, encoding="utf-8")
    logger.info("生成配置文件", path=str(DEFAULT_CONFIG_PATH))

    # 生成 .env（仅当不存在时）
    env_path = Path.cwd() / ".env"
    if not env_path.exists():
        env_content = ENV_TEMPLATE.format(
            base_url=base_url, api_key=api_key, model=model
        )
        env_path.write_text(env_content, encoding="utf-8")
        logger.info("生成环境变量文件", path=str(env_path))
    else:
        console.print(f"[dim].env 文件已存在，跳过生成: {env_path}[/dim]")
