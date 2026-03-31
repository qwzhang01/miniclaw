"""
MiniClaw - 桌面操控工厂

自动检测平台，返回对应的 DesktopController 实现。

对应 PRD：F5 桌面操控
"""

import sys

from miniclaw.desktop.base import DesktopController


def create_controller() -> DesktopController:
    """根据当前平台创建 DesktopController"""
    if sys.platform == "darwin":
        from miniclaw.desktop.macos import MacOSController
        return MacOSController()
    raise NotImplementedError(
        f"平台 {sys.platform} 暂不支持桌面操控，v2 将支持 Windows。"
    )
