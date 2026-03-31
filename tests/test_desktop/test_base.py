"""
MiniClaw - 桌面操控基类测试
"""

import pytest

from miniclaw.desktop.base import DesktopController, WindowInfo


class TestWindowInfo:
    def test_create(self):
        w = WindowInfo(name="Chrome", owner="Google Chrome")
        assert w.name == "Chrome"
        assert w.owner == "Google Chrome"
        assert w.bounds is None

    def test_create_with_bounds(self):
        w = WindowInfo(name="VS Code", owner="Code", bounds=(0, 0, 1280, 800))
        assert w.bounds == (0, 0, 1280, 800)


class TestDesktopControllerAbstract:
    def test_cannot_instantiate(self):
        """抽象类不能直接实例化"""
        with pytest.raises(TypeError):
            DesktopController()  # type: ignore[abstract]

    @pytest.mark.asyncio
    async def test_check_permissions_default(self):
        """默认 check_permissions 返回 True"""
        # 创建一个具体子类来测试默认方法
        class DummyController(DesktopController):
            async def capture_screen(self, region=None):
                return b""
            async def click(self, x, y, button="left"):
                pass
            async def type_text(self, text):
                pass
            async def hotkey(self, *keys):
                pass
            async def get_active_window_title(self):
                return ""
            async def list_windows(self):
                return []

        ctrl = DummyController()
        assert await ctrl.check_permissions() is True
