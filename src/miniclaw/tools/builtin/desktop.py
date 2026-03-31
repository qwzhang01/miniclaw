"""
MiniClaw - 桌面操控工具

screen_capture / screen_analyze（复合） / mouse_click / keyboard_type / list_windows

对应 PRD：F5 桌面操控
"""

import base64
from typing import Any

from miniclaw.desktop.base import DesktopController
from miniclaw.desktop.factory import create_controller
from miniclaw.tools.registry import tool
from miniclaw.utils.logging import get_logger

logger = get_logger(__name__)

# 延迟初始化的全局 controller
_controller: DesktopController | None = None


def _get_controller() -> DesktopController:
    global _controller
    if _controller is None:
        _controller = create_controller()
    return _controller


@tool(
    description="截取屏幕截图。返回 base64 编码的 PNG 图片。region 参数可指定区域(x,y,w,h)。",
    risk_level="low",
)
async def screen_capture(region: str = "") -> str:
    """截取屏幕"""
    ctrl = _get_controller()
    # 权限检测
    if not await ctrl.check_permissions():
        from miniclaw.desktop.macos import MacOSController
        if isinstance(ctrl, MacOSController):
            return MacOSController.get_permission_guide()
        return "缺少桌面操控权限"
    try:
        parsed_region = None
        if region:
            parts = [int(x.strip()) for x in region.split(",")]
            if len(parts) == 4:
                parsed_region = (parts[0], parts[1], parts[2], parts[3])
        data = await ctrl.capture_screen(parsed_region)
        b64 = base64.b64encode(data).decode("utf-8")
        size_kb = len(data) // 1024
        logger.info("屏幕截图", region=region or "全屏", size_kb=size_kb)
        return f"[截图完成，{size_kb}KB，base64 长度: {len(b64)}]"
    except Exception as e:
        return f"截屏失败: {e}"


@tool(
    description=(
        "截屏并分析内容（复合工具）。截取屏幕后调用视觉 AI 分析截图内容，"
        "返回屏幕上有什么应用、文字、元素的描述。"
    ),
    risk_level="low",
)
async def screen_analyze(region: str = "") -> str:
    """复合工具：截屏 → 调用 reasoner LLM 分析 → 返回文字描述"""
    ctrl = _get_controller()
    if not await ctrl.check_permissions():
        from miniclaw.desktop.macos import MacOSController
        if isinstance(ctrl, MacOSController):
            return MacOSController.get_permission_guide()
        return "缺少桌面操控权限"
    try:
        parsed_region = None
        if region:
            parts = [int(x.strip()) for x in region.split(",")]
            if len(parts) == 4:
                parsed_region = (parts[0], parts[1], parts[2], parts[3])
        data = await ctrl.capture_screen(parsed_region)
        b64 = base64.b64encode(data).decode("utf-8")
        # 特例：工具内部调用 LLM（PRD F3 唯一允许的特例）
        try:
            if _llm_registry is not None:
                resp = await _llm_registry.chat(
                    messages=[{
                        "role": "user",
                        "content": "请详细描述这张屏幕截图中的内容。",
                        "images": [b64],
                    }],
                    role="reasoner",
                )
                return str(resp.text)
        except Exception:
            pass
        # 无 LLM 可用时返回基本信息
        return f"[截图已完成（{len(data) // 1024}KB），但无法分析：未配置 reasoner 模型]"
    except Exception as e:
        return f"截屏分析失败: {e}"


# screen_analyze 需要的 LLM registry 引用（运行时注入）
_llm_registry: Any = None


def set_llm_registry(registry: Any) -> None:
    """注入 LLM registry（由 Agent 启动时调用）"""
    global _llm_registry
    _llm_registry = registry


@tool(
    description="在屏幕指定坐标 (x, y) 点击鼠标。button 可选 left/right。",
    risk_level="high",
)
async def mouse_click(x: int, y: int, button: str = "left") -> str:
    """在指定坐标点击鼠标"""
    ctrl = _get_controller()
    try:
        await ctrl.click(x, y, button)
        return f"已点击 ({x}, {y}) [{button}]"
    except Exception as e:
        return f"点击失败: {e}"


@tool(
    description="模拟键盘输入文字。将文字逐字符输入到当前焦点位置。",
    risk_level="high",
)
async def keyboard_type(text: str) -> str:
    """模拟键盘输入"""
    ctrl = _get_controller()
    try:
        await ctrl.type_text(text)
        return f"已输入: {text}"
    except Exception as e:
        return f"键盘输入失败: {e}"


@tool(
    description="列出当前 macOS 上可见的应用窗口列表。",
    risk_level="low",
)
async def list_windows() -> str:
    """列出当前可见窗口"""
    ctrl = _get_controller()
    try:
        windows = await ctrl.list_windows()
        if not windows:
            return "未检测到可见窗口"
        lines = [f"{i + 1}. {w.name}" for i, w in enumerate(windows)]
        return "当前可见窗口：\n" + "\n".join(lines)
    except Exception as e:
        return f"获取窗口列表失败: {e}"
