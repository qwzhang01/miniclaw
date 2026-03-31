"""
MiniClaw - 桌面操控工厂测试
"""

import sys
from unittest.mock import patch

import pytest

from miniclaw.desktop.factory import create_controller


class TestCreateController:
    def test_macos_returns_macos_controller(self):
        """macOS 平台返回 MacOSController"""
        with patch.object(sys, "platform", "darwin"):
            ctrl = create_controller()
        from miniclaw.desktop.macos import MacOSController
        assert isinstance(ctrl, MacOSController)

    def test_unsupported_platform_raises(self):
        """不支持的平台抛出 NotImplementedError"""
        with patch.object(sys, "platform", "linux"), pytest.raises(
            NotImplementedError, match="暂不支持"
        ):
            create_controller()
