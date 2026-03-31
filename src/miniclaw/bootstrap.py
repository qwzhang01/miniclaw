"""
MiniClaw - 应用组装层

把所有"积木块"串起来：
config → provider → registry → executor → loop → gateway

对应 PRD：F9 配置管理 / F1 Agent 核心循环
"""

from pathlib import Path

from dotenv import load_dotenv

from miniclaw.agent.loop import AgentLoop
from miniclaw.agent.model_router import ModelRouter
from miniclaw.channels.base import ChannelProtocol
from miniclaw.channels.cli_channel import CLIChannel
from miniclaw.config.settings import LLMRoleConfig, MiniClawConfig, load_config
from miniclaw.gateway.router import Gateway
from miniclaw.gateway.session import SessionManager
from miniclaw.llm.anthropic_provider import AnthropicProvider
from miniclaw.llm.base import BaseProvider
from miniclaw.llm.openai_provider import OpenAIProvider
from miniclaw.llm.registry import ModelRoleRegistry
from miniclaw.tools.builtin import register_all_builtin_tools
from miniclaw.tools.executor import ToolExecutor
from miniclaw.tools.registry import get_global_registry
from miniclaw.utils.logging import get_logger

logger = get_logger(__name__)


def _load_env() -> None:
    """加载 .env 文件到环境变量（使用 python-dotenv）

    按优先级从高到低查找：
    1. 当前工作目录 .env
    2. 项目源码根目录 .env（src/../.env）

    override=False 保证不覆盖已存在的环境变量。
    """
    env_paths = [
        Path.cwd() / ".env",
        Path(__file__).parent.parent.parent / ".env",  # src/../.env
    ]
    for env_path in env_paths:
        if env_path.exists():
            logger.info("加载环境变量", path=str(env_path))
            load_dotenv(env_path, override=False)
            return


def _create_provider(role_config: LLMRoleConfig) -> BaseProvider:
    """根据角色配置创建 LLM Provider

    根据 provider 字段路由到对应的 Provider 实现：
    - openai_compatible（默认）→ OpenAIProvider
    - anthropic → AnthropicProvider
    """
    if role_config.provider == "anthropic":
        return AnthropicProvider(
            base_url=role_config.base_url,
            api_key=role_config.api_key,
            model=role_config.model,
            temperature=role_config.temperature,
            max_tokens=role_config.max_tokens,
        )

    # 默认使用 OpenAI 兼容协议（覆盖 DeepSeek/Qwen/Ollama/OpenAI 等）
    return OpenAIProvider(
        base_url=role_config.base_url,
        api_key=role_config.api_key,
        model=role_config.model,
        temperature=role_config.temperature,
        max_tokens=role_config.max_tokens,
    )


def bootstrap(config_path: Path | None = None) -> tuple[Gateway, ChannelProtocol]:
    """组装整个应用，返回 (gateway, channel)

    返回 ChannelProtocol 抽象类型而非 CLIChannel 具体类型，
    使 bootstrap 层不绑定具体通道实现，为未来扩展做准备。

    完整流程：
    1. 加载 .env 环境变量
    2. 加载 config.yaml 配置
    3. 创建 LLM Provider 并注册到 ModelRoleRegistry
    4. 注册内置工具
    5. 创建 ToolExecutor + AgentLoop + Gateway
    """
    # 1. 加载 .env（python-dotenv，正确处理引号/转义/多行值）
    _load_env()

    # 2. 加载配置
    config: MiniClawConfig = load_config(config_path)

    # 3. 创建 LLM Registry + Provider
    llm_registry = ModelRoleRegistry()

    # 注册 default（必须）
    default_provider = _create_provider(config.llm_default)
    llm_registry.register("default", default_provider)

    # 注册其他角色（有配置且 api_key 非空时才注册，否则自动降级到 default）
    for role_name, role_config in [
        ("planner", config.llm_planner),
        ("reasoner", config.llm_reasoner),
        ("maker", config.llm_maker),
    ]:
        if role_config.api_key:
            provider = _create_provider(role_config)
            llm_registry.register(role_name, provider)

    logger.info("LLM 已就绪", roles=llm_registry.registered_roles)

    # 4. 注册内置工具
    register_all_builtin_tools()
    tool_registry = get_global_registry()
    logger.info("工具已注册", tools=tool_registry.tool_names)

    # 5. 创建 Channel
    channel = CLIChannel()

    # 6. 创建 ToolExecutor（审批回调接入 Channel）
    tool_executor = ToolExecutor(
        registry=tool_registry,
        approval_callback=channel.confirm,
    )

    # 7. 创建 AgentLoop
    agent_loop = AgentLoop(
        llm_registry=llm_registry,
        tool_executor=tool_executor,
        model_router=ModelRouter(),
    )

    # 8. 创建 Gateway
    session_manager = SessionManager(tool_registry=tool_registry)
    gateway = Gateway(
        agent_loop=agent_loop,
        session_manager=session_manager,
    )

    return gateway, channel
