"""
MiniClaw - 浏览器操控工具

browser_open: 打开指定 URL
browser_action: 在页面执行操作（点击/输入/滚动/等待/按键）
page_screenshot: 截取页面截图

对应 PRD：F4 浏览器操控
"""

from miniclaw.browser.playwright_driver import PlaywrightDriver
from miniclaw.tools.registry import tool
from miniclaw.utils.logging import get_logger

logger = get_logger(__name__)

# 全局浏览器驱动实例（复用机制，PRD 2.7）
_driver: PlaywrightDriver | None = None


def get_browser_driver(
    headless: bool = False,
    use_system_chrome: bool = True,
) -> PlaywrightDriver:
    """获取全局浏览器驱动实例（复用）"""
    global _driver
    if _driver is None:
        _driver = PlaywrightDriver(
            headless=headless,
            use_system_chrome=use_system_chrome,
        )
    return _driver


@tool(
    description=(
        "打开浏览器访问指定 URL。返回页面标题和核心文本内容。"
        "适用于需要浏览网页、搜索信息、查看网站内容的场景。"
    ),
    risk_level="high",
)
async def browser_open(url: str) -> str:
    """打开浏览器访问 URL"""
    driver = get_browser_driver()
    try:
        result = await driver.open_url(url)
        title = result["title"]
        content = result["content"]
        # 格式化输出
        output = f"📄 页面标题: {title}\n📌 URL: {url}\n\n"
        output += f"--- 页面内容 ---\n{content}"
        return output
    except Exception as e:
        return f"打开浏览器失败: {e}"


@tool(
    description=(
        "在浏览器当前页面执行操作。支持的操作类型："
        "click（点击元素，需提供 selector 或 text）、"
        "type（输入文字，需提供 selector 和 text）、"
        "press（按键，如 Enter/Tab）、"
        "scroll（滚动，direction=up/down）、"
        "wait（等待元素出现，需提供 selector）、"
        "extract（提取页面文本内容）。"
    ),
    risk_level="high",
)
async def browser_action(
    action: str, selector: str = "", text: str = ""
) -> str:
    """在浏览器中执行操作"""
    driver = get_browser_driver()
    try:
        if action == "click":
            if text and not selector:
                return await driver.click(text=text)
            elif selector:
                return await driver.click(selector=selector)
            else:
                return "错误：click 操作需要 selector 或 text 参数"

        elif action == "type":
            if not selector or not text:
                return "错误：type 操作需要 selector 和 text 参数"
            return await driver.type_text(selector, text)

        elif action == "press":
            key = text or "Enter"
            return await driver.press_key(key)

        elif action == "scroll":
            direction = text if text in ("up", "down") else "down"
            return await driver.scroll(direction=direction)

        elif action == "wait":
            if not selector:
                return "错误：wait 操作需要 selector 参数"
            return await driver.wait_for(selector)

        elif action == "extract":
            content = await driver.extract_content()
            return content

        else:
            return (
                f"不支持的操作: {action}。"
                "可用操作：click/type/press/scroll/wait/extract"
            )
    except Exception as e:
        return f"浏览器操作失败: {e}"


@tool(
    description=(
        "截取浏览器当前页面的截图。返回 base64 编码的 PNG 图片。"
        "full_page 参数控制是否截取整个页面（默认只截取可见区域）。"
    ),
    risk_level="low",
)
async def page_screenshot(full_page: str = "false") -> str:
    """截取页面截图"""
    driver = get_browser_driver()
    try:
        is_full = full_page.lower() in ("true", "1", "yes")
        b64_data = await driver.screenshot(full_page=is_full)
        return f"[截图已完成，base64 长度: {len(b64_data)} 字符]"
    except Exception as e:
        return f"截图失败: {e}"
