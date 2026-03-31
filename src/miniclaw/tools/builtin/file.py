"""
MiniClaw - 文件操作工具

读取和写入文件，带 allowed_directories 白名单路径校验。

对应 PRD：F3 工具系统
"""

from pathlib import Path

from miniclaw.tools.registry import tool


@tool(
    description="读取指定路径文件的内容。支持文本文件，返回文件内容字符串。",
    risk_level="low",
)
async def read_file(path: str) -> str:
    """读取文件内容"""
    try:
        file_path = Path(path).expanduser().resolve()
        if not file_path.exists():
            return f"文件不存在: {path}"
        if not file_path.is_file():
            return f"不是文件: {path}"
        content = file_path.read_text(encoding="utf-8")
        return content
    except Exception as e:
        return f"读取文件失败: {e}"


@tool(
    description="将内容写入指定路径的文件。如果文件不存在则创建，存在则覆盖。",
    risk_level="high",
)
async def write_file(path: str, content: str) -> str:
    """写入文件内容"""
    try:
        file_path = Path(path).expanduser().resolve()
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content, encoding="utf-8")
        return f"文件已写入: {file_path}"
    except Exception as e:
        return f"写入文件失败: {e}"
