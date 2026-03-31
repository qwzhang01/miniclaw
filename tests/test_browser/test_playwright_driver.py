"""
MiniClaw - Playwright 驱动测试

使用 mock 测试浏览器驱动的逻辑，不依赖真实浏览器。
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from miniclaw.browser.playwright_driver import PlaywrightDriver


def _make_mock_page() -> MagicMock:
    """创建一个正确 mock 的 Page 对象"""
    page = MagicMock()
    page.is_closed = MagicMock(return_value=False)
    page.goto = AsyncMock()
    page.title = AsyncMock(return_value="Mock Title")
    page.evaluate = AsyncMock(return_value="Mock content")
    page.click = AsyncMock()
    page.fill = AsyncMock()
    page.screenshot = AsyncMock(return_value=b"fake_png")
    page.wait_for_selector = AsyncMock()
    page.url = "https://mock.com"
    page.close = AsyncMock()

    # keyboard / mouse
    page.keyboard = MagicMock()
    page.keyboard.press = AsyncMock()
    page.mouse = MagicMock()
    page.mouse.wheel = AsyncMock()

    # get_by_text
    mock_locator = MagicMock()
    mock_locator.first = MagicMock()
    mock_locator.first.click = AsyncMock()
    page.get_by_text = MagicMock(return_value=mock_locator)

    return page


class TestPlaywrightDriverInit:
    def test_default_config(self):
        driver = PlaywrightDriver()
        assert driver.headless is False
        assert driver.use_system_chrome is True
        assert driver.is_active is False

    def test_custom_config(self):
        driver = PlaywrightDriver(headless=True, use_system_chrome=False)
        assert driver.headless is True
        assert driver.use_system_chrome is False


class TestPlaywrightDriverMocked:
    @pytest.mark.asyncio
    async def test_open_url(self):
        driver = PlaywrightDriver()
        driver._page = _make_mock_page()

        result = await driver.open_url("https://example.com")
        assert result["title"] == "Mock Title"
        assert "Mock content" in result["content"]

    @pytest.mark.asyncio
    async def test_click_by_selector(self):
        driver = PlaywrightDriver()
        driver._page = _make_mock_page()

        result = await driver.click(selector="#btn")
        assert "已点击" in result

    @pytest.mark.asyncio
    async def test_click_by_text(self):
        driver = PlaywrightDriver()
        driver._page = _make_mock_page()

        result = await driver.click(text="提交")
        assert "已点击" in result

    @pytest.mark.asyncio
    async def test_click_no_params(self):
        driver = PlaywrightDriver()
        driver._page = _make_mock_page()

        result = await driver.click()
        assert "错误" in result

    @pytest.mark.asyncio
    async def test_type_text(self):
        driver = PlaywrightDriver()
        driver._page = _make_mock_page()

        result = await driver.type_text("input#q", "Python")
        assert "已输入" in result

    @pytest.mark.asyncio
    async def test_press_key(self):
        driver = PlaywrightDriver()
        driver._page = _make_mock_page()

        result = await driver.press_key("Enter")
        assert "已按下" in result

    @pytest.mark.asyncio
    async def test_scroll(self):
        driver = PlaywrightDriver()
        driver._page = _make_mock_page()

        result = await driver.scroll("down", 500)
        assert "已滚动" in result

    @pytest.mark.asyncio
    async def test_screenshot(self):
        driver = PlaywrightDriver()
        driver._page = _make_mock_page()

        result = await driver.screenshot()
        assert isinstance(result, str)
        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_extract_content(self):
        driver = PlaywrightDriver()
        driver._page = _make_mock_page()

        result = await driver.extract_content()
        assert "Mock content" in result

    @pytest.mark.asyncio
    async def test_extract_content_truncates(self):
        driver = PlaywrightDriver()
        page = _make_mock_page()
        page.evaluate = AsyncMock(return_value="x" * 10000)
        driver._page = page

        result = await driver.extract_content()
        assert len(result) < 6000
        assert "截断" in result

    @pytest.mark.asyncio
    async def test_get_current_url(self):
        driver = PlaywrightDriver()
        driver._page = _make_mock_page()

        result = await driver.get_current_url()
        assert result == "https://mock.com"

    @pytest.mark.asyncio
    async def test_wait_for(self):
        driver = PlaywrightDriver()
        driver._page = _make_mock_page()

        result = await driver.wait_for(".result")
        assert "已出现" in result

    @pytest.mark.asyncio
    async def test_close(self):
        driver = PlaywrightDriver()
        driver._page = _make_mock_page()

        mock_context = AsyncMock()
        mock_browser = MagicMock()
        mock_browser.is_connected = MagicMock(return_value=True)
        mock_browser.close = AsyncMock()
        mock_pw = AsyncMock()

        driver._context = mock_context
        driver._browser = mock_browser
        driver._playwright = mock_pw

        await driver.close()
        assert driver._page is None

    @pytest.mark.asyncio
    async def test_close_when_not_started(self):
        driver = PlaywrightDriver()
        await driver.close()  # 不应抛异常

    @pytest.mark.asyncio
    async def test_is_active_when_connected(self):
        driver = PlaywrightDriver()
        driver._page = _make_mock_page()

        mock_browser = MagicMock()
        mock_browser.is_connected = MagicMock(return_value=True)
        driver._browser = mock_browser

        assert driver.is_active is True
