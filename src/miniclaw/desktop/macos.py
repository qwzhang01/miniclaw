"""
MiniClaw - macOS 桌面操控实现

pyautogui + Pillow + osascript 实现全部 6 个接口。
含辅助功能权限检测与引导。

对应 PRD：F5 桌面操控
"""

import asyncio
import io
import sys

import pyautogui

from miniclaw.desktop.base import DesktopController, WindowInfo
from miniclaw.utils.logging import get_logger

logger = get_logger(__name__)


class MacOSController(DesktopController):
    """macOS 桌面操控实现"""

    async def capture_screen(
        self, region: tuple[int, int, int, int] | None = None
    ) -> bytes:
        """截取屏幕，返回 PNG bytes"""
        import pyautogui
        loop = asyncio.get_event_loop()
        if region:
            img = await loop.run_in_executor(None, lambda: pyautogui.screenshot(region=region))
        else:
            img = await loop.run_in_executor(None, pyautogui.screenshot)
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()

    async def click(self, x: int, y: int, button: str = "left") -> None:
        """在指定坐标点击"""
        import pyautogui
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, lambda: pyautogui.click(x, y, button=button))

    async def type_text(self, text: str) -> None:
        """模拟键盘输入"""
        import pyautogui
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, lambda: pyautogui.write(text, interval=0.02))

    async def hotkey(self, *keys: str) -> None:
        """模拟组合键"""
        import pyautogui
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, lambda: pyautogui.hotkey(*keys))

    async def get_active_window_title(self) -> str:
        """获取当前活动窗口标题（osascript）"""
        script = (
            'tell application "System Events" to get name of first '
            "application process whose frontmost is true"
        )
        return await self._run_osascript(script)

    async def list_windows(self) -> list[WindowInfo]:
        """列出当前可见窗口（osascript）"""
        script = (
            'tell application "System Events"\n'
            "  set windowList to {}\n"
            "  repeat with proc in (every application process "
            "whose visible is true)\n"
            '    set end of windowList to (name of proc) & "||"\n'
            "  end repeat\n"
            "  return windowList as text\n"
            "end tell"
        )
        raw = await self._run_osascript(script)
        windows: list[WindowInfo] = []
        for name in raw.split("||"):
            name = name.strip().rstrip(",")
            if name:
                windows.append(WindowInfo(name=name, owner=name))
        return windows

    async def check_permissions(self) -> bool:
        """检测辅助功能权限"""
        if sys.platform != "darwin":
            return True
        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, pyautogui.position)
            return True
        except Exception:
            return False

    @staticmethod
    async def _run_osascript(script: str) -> str:
        """执行 osascript 命令"""
        proc = await asyncio.create_subprocess_exec(
            "osascript", "-e", script,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=10)
        return stdout.decode("utf-8", errors="replace").strip()

    @staticmethod
    def get_permission_guide() -> str:
        """返回 macOS 辅助功能权限引导文本"""
        return (
            "⚠️ MiniClaw 需要「辅助功能」权限来操控桌面。\n\n"
            "请按以下步骤开启：\n"
            "1. 打开「系统设置」→「隐私与安全性」→「辅助功能」\n"
            "2. 点击 + 号，添加你的终端应用（Terminal / iTerm / VS Code）\n"
            "3. 重启 MiniClaw\n\n"
            "或者运行命令快速打开设置面板：\n"
            "  open x-apple.systempreferences:com.apple.preference"
            ".security?Privacy_Accessibility"
        )
