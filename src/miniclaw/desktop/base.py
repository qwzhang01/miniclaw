"""
MiniClaw - 桌面操控抽象基类

定义 6 个接口：capture_screen / click / type_text / hotkey /
get_active_window_title / list_windows。
v2 加 Windows 只需新增实现类，不改此文件。

对应 PRD：F5 桌面操控
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class WindowInfo:
    """窗口信息"""
    name: str
    owner: str
    bounds: tuple[int, int, int, int] | None = None  # x, y, w, h


class DesktopController(ABC):
    """桌面操控的跨平台抽象基类（PRD F5）"""

    @abstractmethod
    async def capture_screen(self, region: tuple[int, int, int, int] | None = None) -> bytes:
        """截取屏幕，返回 PNG bytes。region=(x, y, w, h) 为 None 时全屏。"""
        ...

    @abstractmethod
    async def click(self, x: int, y: int, button: str = "left") -> None:
        """在指定坐标点击鼠标"""
        ...

    @abstractmethod
    async def type_text(self, text: str) -> None:
        """模拟键盘输入文字"""
        ...

    @abstractmethod
    async def hotkey(self, *keys: str) -> None:
        """模拟组合键（如 command+c）"""
        ...

    @abstractmethod
    async def get_active_window_title(self) -> str:
        """获取当前活动窗口标题"""
        ...

    @abstractmethod
    async def list_windows(self) -> list[WindowInfo]:
        """列出当前可见窗口列表"""
        ...

    async def check_permissions(self) -> bool:
        """检查系统权限，默认返回 True（子类覆写）"""
        return True
