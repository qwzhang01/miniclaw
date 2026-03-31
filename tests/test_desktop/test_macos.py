"""
MiniClaw - MacOSController 测试

使用 mock 测试，不依赖真实 macOS 环境。
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from miniclaw.desktop.macos import MacOSController

# pyautogui 在 macos 模块顶层导入，patch 路径是 miniclaw.desktop.macos.pyautogui
PAG = "miniclaw.desktop.macos.pyautogui"


@pytest.fixture
def controller():
    return MacOSController()


class TestCaptureScreen:
    @pytest.mark.asyncio
    async def test_capture_full_screen(self, controller):
        mock_img = MagicMock()
        mock_img.save = MagicMock(side_effect=lambda b, format: b.write(b"PNG"))

        with patch(PAG) as mock_pag:
            mock_pag.screenshot = MagicMock(return_value=mock_img)
            data = await controller.capture_screen()
        assert isinstance(data, bytes)

    @pytest.mark.asyncio
    async def test_capture_region(self, controller):
        mock_img = MagicMock()
        mock_img.save = MagicMock(side_effect=lambda b, format: b.write(b"PNG"))

        with patch(PAG) as mock_pag:
            mock_pag.screenshot = MagicMock(return_value=mock_img)
            data = await controller.capture_screen(region=(0, 0, 100, 100))
        assert isinstance(data, bytes)


class TestClick:
    @pytest.mark.asyncio
    async def test_click(self, controller):
        with patch(PAG) as mock_pag:
            mock_pag.click = MagicMock()
            await controller.click(100, 200, "left")
            # lambda 在 executor 中执行，验证无异常即成功


class TestTypeText:
    @pytest.mark.asyncio
    async def test_type_text(self, controller):
        with patch(PAG) as mock_pag:
            mock_pag.write = MagicMock()
            await controller.type_text("hello")
            # 验证无异常


class TestHotkey:
    @pytest.mark.asyncio
    async def test_hotkey(self, controller):
        with patch(PAG) as mock_pag:
            mock_pag.hotkey = MagicMock()
            await controller.hotkey("command", "c")
            # 验证无异常


class TestGetActiveWindowTitle:
    @pytest.mark.asyncio
    async def test_get_title(self, controller):
        with patch.object(
            controller, "_run_osascript", new_callable=AsyncMock
        ) as mock_os:
            mock_os.return_value = "Google Chrome"
            title = await controller.get_active_window_title()
        assert title == "Google Chrome"


class TestListWindows:
    @pytest.mark.asyncio
    async def test_list_windows(self, controller):
        with patch.object(
            controller, "_run_osascript", new_callable=AsyncMock
        ) as mock_os:
            mock_os.return_value = "Chrome||VS Code||Terminal||"
            windows = await controller.list_windows()
        assert len(windows) == 3
        assert windows[0].name == "Chrome"

    @pytest.mark.asyncio
    async def test_list_windows_empty(self, controller):
        with patch.object(
            controller, "_run_osascript", new_callable=AsyncMock
        ) as mock_os:
            mock_os.return_value = ""
            windows = await controller.list_windows()
        assert windows == []


class TestPermissions:
    @pytest.mark.asyncio
    async def test_check_permissions_success(self, controller):
        with patch(PAG) as mock_pag:
            mock_pag.position = MagicMock(return_value=(0, 0))
            result = await controller.check_permissions()
        assert result is True

    @pytest.mark.asyncio
    async def test_check_permissions_fail(self, controller):
        with patch(PAG) as mock_pag:
            mock_pag.position = MagicMock(side_effect=Exception("No perm"))
            result = await controller.check_permissions()
        assert result is False

    def test_permission_guide(self):
        guide = MacOSController.get_permission_guide()
        assert "辅助功能" in guide
        assert "系统设置" in guide
