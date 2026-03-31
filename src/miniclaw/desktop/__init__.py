"""
MiniClaw - 桌面操控模块

跨平台抽象层，v1 只实现 macOS。

对应 PRD：F5 桌面操控
"""

from miniclaw.desktop.base import DesktopController
from miniclaw.desktop.factory import create_controller

__all__ = ["DesktopController", "create_controller"]
