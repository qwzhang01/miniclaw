"""
MiniClaw - 浏览器操控模块

Playwright 驱动封装，支持有头/无头模式、浏览器复用。

对应 PRD：F4 浏览器操控
"""

from miniclaw.browser.playwright_driver import PlaywrightDriver

__all__ = ["PlaywrightDriver"]
