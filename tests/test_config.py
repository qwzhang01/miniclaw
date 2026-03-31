"""
MiniClaw - 配置管理测试
"""

import os
from pathlib import Path

from miniclaw.config.settings import (
    MiniClawConfig,
    _resolve_env_vars,
    load_config,
)


class TestEnvVarResolution:
    def test_resolve_env_var(self):
        os.environ["TEST_KEY_MC"] = "secret123"
        result = _resolve_env_vars("${TEST_KEY_MC}")
        assert result == "secret123"
        del os.environ["TEST_KEY_MC"]

    def test_resolve_missing_env_var(self):
        result = _resolve_env_vars("${NONEXISTENT_VAR_MC}")
        assert result == ""

    def test_no_env_var(self):
        result = _resolve_env_vars("plain text")
        assert result == "plain text"


class TestLoadConfig:
    def test_load_default_when_no_file(self):
        """配置文件不存在时使用默认值"""
        config = load_config(Path("/nonexistent/path/config.yaml"))
        assert isinstance(config, MiniClawConfig)
        assert config.llm_default.model == "deepseek-chat"

    def test_load_from_yaml(self, tmp_path):
        """从 YAML 文件加载配置"""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("""
llm:
  default:
    model: test-model
    api_key: test-key
security:
  auto_approve_low_risk: false
""")
        config = load_config(config_file)
        assert config.llm_default.model == "test-model"
        assert config.llm_default.api_key == "test-key"
        assert config.security.auto_approve_low_risk is False

    def test_load_with_env_vars(self, tmp_path):
        """支持 ${ENV_VAR} 环境变量替换"""
        os.environ["MC_TEST_API_KEY"] = "my-secret"
        config_file = tmp_path / "config.yaml"
        config_file.write_text("""
llm:
  default:
    api_key: ${MC_TEST_API_KEY}
""")
        config = load_config(config_file)
        assert config.llm_default.api_key == "my-secret"
        del os.environ["MC_TEST_API_KEY"]

    def test_load_invalid_yaml(self, tmp_path):
        """无效 YAML 使用默认配置"""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("invalid: [yaml: {broken")
        config = load_config(config_file)
        assert isinstance(config, MiniClawConfig)


class TestMiniClawConfig:
    def test_default_config(self):
        config = MiniClawConfig()
        assert config.llm_default.provider == "openai_compatible"
        assert config.security.auto_approve_low_risk is True
        assert config.browser.headless is False
        assert config.platform.desktop_controller == "auto"
