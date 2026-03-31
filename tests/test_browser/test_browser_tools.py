"""
MiniClaw - 浏览器工具测试

测试 browser_open, browser_action, page_screenshot 工具。
"""

from unittest.mock import AsyncMock, patch

import pytest

from miniclaw.tools.builtin import browser as browser_tools


class TestBrowserOpen:
    @pytest.mark.asyncio
    async def test_browser_open_success(self):
        """browser_open 应返回页面标题和内容"""
        mock_driver = AsyncMock()
        mock_driver.open_url = AsyncMock(return_value={
            "title": "Test Page",
            "url": "https://example.com",
            "content": "Hello World",
        })

        with patch.object(browser_tools, "get_browser_driver", return_value=mock_driver):
            result = await browser_tools.browser_open("https://example.com")
        assert "Test Page" in result
        assert "Hello World" in result

    @pytest.mark.asyncio
    async def test_browser_open_failure(self):
        """browser_open 失败时返回错误信息"""
        mock_driver = AsyncMock()
        mock_driver.open_url = AsyncMock(side_effect=Exception("连接超时"))

        with patch.object(browser_tools, "get_browser_driver", return_value=mock_driver):
            result = await browser_tools.browser_open("https://bad-url.com")
        assert "失败" in result


class TestBrowserAction:
    @pytest.mark.asyncio
    async def test_action_click_by_text(self):
        """click 操作通过文本"""
        mock_driver = AsyncMock()
        mock_driver.click = AsyncMock(return_value="已点击文本: 提交")

        with patch.object(browser_tools, "get_browser_driver", return_value=mock_driver):
            result = await browser_tools.browser_action("click", text="提交")
        assert "已点击" in result

    @pytest.mark.asyncio
    async def test_action_click_by_selector(self):
        """click 操作通过选择器"""
        mock_driver = AsyncMock()
        mock_driver.click = AsyncMock(return_value="已点击元素: #btn")

        with patch.object(browser_tools, "get_browser_driver", return_value=mock_driver):
            result = await browser_tools.browser_action("click", selector="#btn")
        assert "已点击" in result

    @pytest.mark.asyncio
    async def test_action_type(self):
        """type 操作"""
        mock_driver = AsyncMock()
        mock_driver.type_text = AsyncMock(return_value="已输入: Python")

        with patch.object(browser_tools, "get_browser_driver", return_value=mock_driver):
            result = await browser_tools.browser_action(
                "type", selector="input#q", text="Python"
            )
        assert "已输入" in result

    @pytest.mark.asyncio
    async def test_action_type_missing_params(self):
        """type 缺参数时返回错误"""
        mock_driver = AsyncMock()
        with patch.object(browser_tools, "get_browser_driver", return_value=mock_driver):
            result = await browser_tools.browser_action("type")
        assert "错误" in result

    @pytest.mark.asyncio
    async def test_action_press(self):
        """press 操作"""
        mock_driver = AsyncMock()
        mock_driver.press_key = AsyncMock(return_value="已按下: Enter")

        with patch.object(browser_tools, "get_browser_driver", return_value=mock_driver):
            result = await browser_tools.browser_action("press", text="Enter")
        assert "已按下" in result

    @pytest.mark.asyncio
    async def test_action_scroll(self):
        """scroll 操作"""
        mock_driver = AsyncMock()
        mock_driver.scroll = AsyncMock(return_value="已滚动 down 500px")

        with patch.object(browser_tools, "get_browser_driver", return_value=mock_driver):
            result = await browser_tools.browser_action("scroll", text="down")
        assert "已滚动" in result

    @pytest.mark.asyncio
    async def test_action_wait(self):
        """wait 操作"""
        mock_driver = AsyncMock()
        mock_driver.wait_for = AsyncMock(return_value="元素已出现: .result")

        with patch.object(browser_tools, "get_browser_driver", return_value=mock_driver):
            result = await browser_tools.browser_action("wait", selector=".result")
        assert "已出现" in result

    @pytest.mark.asyncio
    async def test_action_extract(self):
        """extract 操作"""
        mock_driver = AsyncMock()
        mock_driver.extract_content = AsyncMock(return_value="Page text")

        with patch.object(browser_tools, "get_browser_driver", return_value=mock_driver):
            result = await browser_tools.browser_action("extract")
        assert "Page text" in result

    @pytest.mark.asyncio
    async def test_action_unsupported(self):
        """不支持的操作返回提示"""
        mock_driver = AsyncMock()
        with patch.object(browser_tools, "get_browser_driver", return_value=mock_driver):
            result = await browser_tools.browser_action("fly")
        assert "不支持" in result

    @pytest.mark.asyncio
    async def test_action_click_no_params(self):
        """click 无 selector 和 text 返回错误"""
        mock_driver = AsyncMock()
        with patch.object(browser_tools, "get_browser_driver", return_value=mock_driver):
            result = await browser_tools.browser_action("click")
        assert "错误" in result


class TestPageScreenshot:
    @pytest.mark.asyncio
    async def test_screenshot_default(self):
        """默认截图可见区域"""
        mock_driver = AsyncMock()
        mock_driver.screenshot = AsyncMock(return_value="base64data")

        with patch.object(browser_tools, "get_browser_driver", return_value=mock_driver):
            result = await browser_tools.page_screenshot()
        assert "截图已完成" in result

    @pytest.mark.asyncio
    async def test_screenshot_full_page(self):
        """全页截图"""
        mock_driver = AsyncMock()
        mock_driver.screenshot = AsyncMock(return_value="base64full")

        with patch.object(browser_tools, "get_browser_driver", return_value=mock_driver):
            result = await browser_tools.page_screenshot("true")
        assert "截图已完成" in result

    @pytest.mark.asyncio
    async def test_screenshot_failure(self):
        """截图失败返回错误"""
        mock_driver = AsyncMock()
        mock_driver.screenshot = AsyncMock(side_effect=Exception("No page"))

        with patch.object(browser_tools, "get_browser_driver", return_value=mock_driver):
            result = await browser_tools.page_screenshot()
        assert "失败" in result


class TestGetBrowserDriver:
    def test_singleton(self):
        """get_browser_driver 应返回单例"""
        # 重置全局变量
        browser_tools._driver = None
        d1 = browser_tools.get_browser_driver()
        d2 = browser_tools.get_browser_driver()
        assert d1 is d2
        browser_tools._driver = None  # 清理
