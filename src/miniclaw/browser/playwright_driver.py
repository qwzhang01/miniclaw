"""
MiniClaw - Playwright 驱动封装

统一 browser driver，管理浏览器生命周期（启动/复用/关闭）。
支持有头/无头模式切换，多次操作复用同一浏览器实例。

对应 PRD：F4 浏览器操控
"""

import base64
import re
from typing import Any

from playwright.async_api import Browser, BrowserContext, Page, async_playwright

from miniclaw.utils.logging import get_logger

logger = get_logger(__name__)


class PlaywrightDriver:
    """Playwright 浏览器驱动

    管理浏览器实例的完整生命周期，支持：
    - 有头/无头模式切换（从 config 读取）
    - 浏览器实例复用（多次操作不重复启动）
    - 页面导航、点击、输入、截图、内容提取

    Attributes:
        headless: 是否无头模式（默认 False，PRD Q3）
        use_system_chrome: 是否使用系统 Chrome
    """

    def __init__(
        self,
        headless: bool = False,
        use_system_chrome: bool = True,
    ) -> None:
        self.headless = headless
        self.use_system_chrome = use_system_chrome
        self._playwright: Any = None
        self._browser: Browser | None = None
        self._context: BrowserContext | None = None
        self._page: Page | None = None

    async def _ensure_browser(self) -> Page:
        """确保浏览器已启动，返回当前页面（复用机制）"""
        if self._page and not self._page.is_closed():
            return self._page

        # 启动 Playwright
        if self._playwright is None:
            self._playwright = await async_playwright().start()

        # 启动浏览器
        if self._browser is None or not self._browser.is_connected():
            launch_args: dict[str, Any] = {
                "headless": self.headless,
            }
            # 尝试使用系统 Chrome
            if self.use_system_chrome:
                launch_args["channel"] = "chrome"

            try:
                self._browser = await self._playwright.chromium.launch(
                    **launch_args
                )
            except Exception:
                # 如果系统 Chrome 不可用，回退到 Playwright 内置浏览器
                logger.warning("系统 Chrome 不可用，使用内置 Chromium")
                self._browser = await self._playwright.chromium.launch(
                    headless=self.headless
                )

            logger.info(
                "浏览器已启动",
                headless=self.headless,
            )

        # 创建上下文和页面
        if self._context is None:
            self._context = await self._browser.new_context(
                viewport={"width": 1280, "height": 800},
                user_agent=(
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
            )

        if self._page is None or self._page.is_closed():
            self._page = await self._context.new_page()

        return self._page

    async def open_url(self, url: str) -> dict[str, str]:
        """打开指定 URL，返回页面标题和内容摘要"""
        page = await self._ensure_browser()
        await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        title = await page.title()
        # 提取页面核心文本
        content = await self.extract_content()
        logger.info("页面已打开", url=url, title=title)
        return {"title": title, "url": url, "content": content}

    async def click(
        self, selector: str | None = None, text: str | None = None
    ) -> str:
        """点击元素（通过 CSS 选择器或文本内容）"""
        page = await self._ensure_browser()
        try:
            if text:
                await page.get_by_text(text, exact=False).first.click(
                    timeout=10000
                )
                return f"已点击文本: {text}"
            elif selector:
                await page.click(selector, timeout=10000)
                return f"已点击元素: {selector}"
            else:
                return "错误：需要提供 selector 或 text"
        except Exception as e:
            return f"点击失败: {e}"

    async def type_text(self, selector: str, text: str) -> str:
        """在输入框中输入文字"""
        page = await self._ensure_browser()
        try:
            await page.fill(selector, text, timeout=10000)
            return f"已输入: {text}"
        except Exception as e:
            return f"输入失败: {e}"

    async def press_key(self, key: str) -> str:
        """按下键盘按键（如 Enter, Tab）"""
        page = await self._ensure_browser()
        try:
            await page.keyboard.press(key)
            return f"已按下: {key}"
        except Exception as e:
            return f"按键失败: {e}"

    async def scroll(self, direction: str = "down", amount: int = 500) -> str:
        """滚动页面"""
        page = await self._ensure_browser()
        delta = amount if direction == "down" else -amount
        await page.mouse.wheel(0, delta)
        return f"已滚动 {direction} {amount}px"

    async def wait_for(self, selector: str, timeout: int = 10000) -> str:
        """等待元素出现"""
        page = await self._ensure_browser()
        try:
            await page.wait_for_selector(selector, timeout=timeout)
            return f"元素已出现: {selector}"
        except Exception as e:
            return f"等待超时: {e}"

    async def screenshot(self, full_page: bool = False) -> str:
        """截取页面截图，返回 base64 编码"""
        page = await self._ensure_browser()
        data = await page.screenshot(full_page=full_page, type="png")
        b64 = base64.b64encode(data).decode("utf-8")
        logger.info("页面截图", full_page=full_page, size_kb=len(data) // 1024)
        return b64

    async def extract_content(self) -> str:
        """提取页面核心文本，去除导航/广告噪音"""
        page = await self._ensure_browser()
        # 优先提取 main/article 区域，回退到 body
        content = await page.evaluate("""
            () => {
                const selectors = ['main', 'article', '[role="main"]', '.content', '#content'];
                for (const sel of selectors) {
                    const el = document.querySelector(sel);
                    if (el && el.innerText.trim().length > 100) {
                        return el.innerText.trim();
                    }
                }
                // 回退：去除 nav/header/footer/aside 后提取 body
                const body = document.body.cloneNode(true);
                const remove = ['nav', 'header', 'footer', 'aside', 'script',
                                'style', 'noscript', '[role="navigation"]',
                                '[role="banner"]', '[role="contentinfo"]'];
                remove.forEach(sel => {
                    body.querySelectorAll(sel).forEach(el => el.remove());
                });
                return body.innerText.trim();
            }
        """)
        # 清理：压缩多余空白行
        cleaned = re.sub(r"\n{3,}", "\n\n", str(content))
        # 截断过长内容
        if len(cleaned) > 5000:
            cleaned = cleaned[:5000] + "\n\n... (内容已截断)"
        return cleaned

    async def get_current_url(self) -> str:
        """获取当前页面 URL"""
        page = await self._ensure_browser()
        return page.url

    async def close(self) -> None:
        """关闭浏览器，释放资源"""
        if self._page and not self._page.is_closed():
            await self._page.close()
            self._page = None
        if self._context:
            await self._context.close()
            self._context = None
        if self._browser and self._browser.is_connected():
            await self._browser.close()
            self._browser = None
        if self._playwright:
            await self._playwright.stop()
            self._playwright = None
        logger.info("浏览器已关闭")

    @property
    def is_active(self) -> bool:
        """浏览器是否处于活跃状态"""
        return (
            self._browser is not None
            and self._browser.is_connected()
            and self._page is not None
            and not self._page.is_closed()
        )
