"""
MiniClaw - 配置管理

使用 Pydantic Settings 定义所有配置项，支持 YAML 文件和环境变量。
覆盖 PRD F9 完整 config.yaml 配置。

对应 PRD：F9 配置管理
"""

import os
import re
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel

from miniclaw.utils.logging import get_logger

logger = get_logger(__name__)

# 默认配置文件路径
DEFAULT_CONFIG_PATH = Path.home() / ".miniclaw" / "config.yaml"


class LLMRoleConfig(BaseModel):
    """单个 LLM 角色的配置（PRD F2 四模型角色）"""

    provider: str = "openai_compatible"
    base_url: str = "https://api.deepseek.com/v1"
    api_key: str = ""
    model: str = "deepseek-chat"
    temperature: float = 0.7
    max_tokens: int = 4096


class SecurityConfig(BaseModel):
    """安全配置"""

    auto_approve_low_risk: bool = True
    confirm_high_risk: bool = True
    allowed_directories: list[str] = [
        "~/git/",
        "~/Documents/",
    ]


class BrowserConfig(BaseModel):
    """浏览器配置"""

    headless: bool = False
    use_system_chrome: bool = True


class PlatformConfig(BaseModel):
    """平台配置"""

    desktop_controller: str = "auto"


class LoggingConfig(BaseModel):
    """日志配置"""

    level: str = "info"
    file: str = str(Path.home() / ".miniclaw" / "logs" / "miniclaw.log")


class AgentConfig(BaseModel):
    """Agent 配置（OP3.2）"""

    tool_output_max_chars: int = 8000  # 工具输出最大字符数
    max_context_tokens: int = 32000    # 上下文窗口最大 token 数


class MiniClawConfig(BaseModel):
    """MiniClaw 完整配置"""

    llm_default: LLMRoleConfig = LLMRoleConfig()
    llm_planner: LLMRoleConfig = LLMRoleConfig()
    llm_reasoner: LLMRoleConfig = LLMRoleConfig()
    llm_maker: LLMRoleConfig = LLMRoleConfig()
    security: SecurityConfig = SecurityConfig()
    browser: BrowserConfig = BrowserConfig()
    platform: PlatformConfig = PlatformConfig()
    logging: LoggingConfig = LoggingConfig()
    agent: AgentConfig = AgentConfig()


def _resolve_env_vars(value: str) -> str:
    """解析 ${ENV_VAR} 格式的环境变量"""
    pattern = r"\$\{(\w+)\}"

    def replacer(match: re.Match[str]) -> str:
        var_name = match.group(1)
        return os.environ.get(var_name, "")

    return re.sub(pattern, replacer, value)


def _resolve_dict_env_vars(data: dict[str, Any]) -> dict[str, Any]:
    """递归解析字典中的环境变量"""
    result: dict[str, Any] = {}
    for key, value in data.items():
        if isinstance(value, str):
            result[key] = _resolve_env_vars(value)
        elif isinstance(value, dict):
            result[key] = _resolve_dict_env_vars(value)
        else:
            result[key] = value
    return result


def load_config(config_path: Path | None = None) -> MiniClawConfig:
    """从 YAML 文件加载配置

    Args:
        config_path: 配置文件路径，默认 ~/.miniclaw/config.yaml

    Returns:
        MiniClawConfig 配置实例
    """
    path = config_path or DEFAULT_CONFIG_PATH

    if not path.exists():
        logger.info("配置文件不存在，使用默认配置", path=str(path))
        return MiniClawConfig()

    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
        if not raw:
            return MiniClawConfig()

        # 解析环境变量
        data = _resolve_dict_env_vars(raw)

        # 解析 LLM 角色配置
        llm = data.get("llm", {})
        config = MiniClawConfig(
            llm_default=LLMRoleConfig(**llm.get("default", {})),
            llm_planner=LLMRoleConfig(**llm.get("planner", {})),
            llm_reasoner=LLMRoleConfig(**llm.get("reasoner", {})),
            llm_maker=LLMRoleConfig(**llm.get("maker", {})),
            security=SecurityConfig(**data.get("security", {})),
            browser=BrowserConfig(**data.get("browser", {})),
            platform=PlatformConfig(**data.get("platform", {})),
            logging=LoggingConfig(**data.get("logging", {})),
            agent=AgentConfig(**data.get("agent", {})),
        )
        logger.info("配置已加载", path=str(path))
        return config

    except Exception as e:
        logger.warning("配置文件解析失败，使用默认配置", error=repr(e))
        return MiniClawConfig()
