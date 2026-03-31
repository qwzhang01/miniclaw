"""
MiniClaw - 桌面工具测试
"""

from unittest.mock import AsyncMock, patch

import pytest

from miniclaw.desktop.base import WindowInfo
from miniclaw.tools.builtin import desktop as desktop_tools


@pytest.fixture(autouse=True)
def reset_controller():
    """每个测试重置全局 controller"""
    desktop_tools._controller = None
    yield
    desktop_tools._controller = None


def _mock_controller():
    ctrl = AsyncMock()
    ctrl.check_permissions = AsyncMock(return_value=True)
    ctrl.capture_screen = AsyncMock(return_value=b"PNGDATA")
    ctrl.click = AsyncMock()
    ctrl.type_text = AsyncMock()
    ctrl.list_windows = AsyncMock(return_value=[
        WindowInfo("Chrome", "Google Chrome"),
        WindowInfo("Terminal", "Terminal"),
    ])
    return ctrl


class TestScreenCapture:
    @pytest.mark.asyncio
    async def test_capture_full(self):
        mock_ctrl = _mock_controller()
        with patch.object(desktop_tools, "_get_controller", return_value=mock_ctrl):
            result = await desktop_tools.screen_capture()
        assert "截图完成" in result

    @pytest.mark.asyncio
    async def test_capture_region(self):
        mock_ctrl = _mock_controller()
        with patch.object(desktop_tools, "_get_controller", return_value=mock_ctrl):
            result = await desktop_tools.screen_capture("0,0,100,100")
        assert "截图完成" in result

    @pytest.mark.asyncio
    async def test_capture_no_permission(self):
        mock_ctrl = _mock_controller()
        mock_ctrl.check_permissions = AsyncMock(return_value=False)
        # Mock 非 MacOSController 以走通用路径
        with patch.object(desktop_tools, "_get_controller", return_value=mock_ctrl):
            result = await desktop_tools.screen_capture()
        assert "权限" in result


class TestScreenAnalyze:
    @pytest.mark.asyncio
    async def test_analyze_no_llm(self):
        """没有 LLM 时返回基本信息"""
        mock_ctrl = _mock_controller()
        desktop_tools._llm_registry = None
        with patch.object(desktop_tools, "_get_controller", return_value=mock_ctrl):
            result = await desktop_tools.screen_analyze()
        assert "截图已完成" in result or "截屏" in result.lower() or "未配置" in result


class TestMouseClick:
    @pytest.mark.asyncio
    async def test_click(self):
        mock_ctrl = _mock_controller()
        with patch.object(desktop_tools, "_get_controller", return_value=mock_ctrl):
            result = await desktop_tools.mouse_click(100, 200, "left")
        assert "已点击" in result
        mock_ctrl.click.assert_called_once_with(100, 200, "left")

    @pytest.mark.asyncio
    async def test_click_failure(self):
        mock_ctrl = _mock_controller()
        mock_ctrl.click = AsyncMock(side_effect=Exception("点击异常"))
        with patch.object(desktop_tools, "_get_controller", return_value=mock_ctrl):
            result = await desktop_tools.mouse_click(0, 0)
        assert "失败" in result


class TestKeyboardType:
    @pytest.mark.asyncio
    async def test_type(self):
        mock_ctrl = _mock_controller()
        with patch.object(desktop_tools, "_get_controller", return_value=mock_ctrl):
            result = await desktop_tools.keyboard_type("hello")
        assert "已输入" in result

    @pytest.mark.asyncio
    async def test_type_failure(self):
        mock_ctrl = _mock_controller()
        mock_ctrl.type_text = AsyncMock(side_effect=Exception("输入异常"))
        with patch.object(desktop_tools, "_get_controller", return_value=mock_ctrl):
            result = await desktop_tools.keyboard_type("test")
        assert "失败" in result


class TestListWindows:
    @pytest.mark.asyncio
    async def test_list(self):
        mock_ctrl = _mock_controller()
        with patch.object(desktop_tools, "_get_controller", return_value=mock_ctrl):
            result = await desktop_tools.list_windows()
        assert "Chrome" in result
        assert "Terminal" in result

    @pytest.mark.asyncio
    async def test_list_empty(self):
        mock_ctrl = _mock_controller()
        mock_ctrl.list_windows = AsyncMock(return_value=[])
        with patch.object(desktop_tools, "_get_controller", return_value=mock_ctrl):
            result = await desktop_tools.list_windows()
        assert "未检测到" in result
