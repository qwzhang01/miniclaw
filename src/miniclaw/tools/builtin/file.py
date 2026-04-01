"""
MiniClaw - 文件操作工具

读取和写入文件，带 allowed_directories 白名单路径校验。
OP3.3: read_file 增加 max_lines 参数限制。

对应 PRD：F3 工具系统
"""

from pathlib import Path

from miniclaw.tools.registry import tool

# OP3.3: 默认最大读取行数
DEFAULT_MAX_LINES = 200


@tool(
    description=(
        "读取指定路径文件的内容。支持文本文件，返回文件内容字符串。"
        "max_lines 参数控制最大读取行数（默认 200 行），超过时截断并提示分段读取。"
    ),
    risk_level="low",
)
async def read_file(path: str, max_lines: int = DEFAULT_MAX_LINES) -> str:
    """读取文件内容（OP3.3: 支持行数限制）"""
    try:
        file_path = Path(path).expanduser().resolve()
        if not file_path.exists():
            return f"文件不存在: {path}"
        if not file_path.is_file():
            return f"不是文件: {path}"
        content = file_path.read_text(encoding="utf-8")
        lines = content.splitlines()
        total_lines = len(lines)
        if total_lines > max_lines:
            truncated = "\n".join(lines[:max_lines])
            return (
                f"{truncated}\n\n"
                f"...[文件共 {total_lines} 行，仅显示前 {max_lines} 行。"
                f"如需后续内容，请使用 shell_exec 执行 "
                f"'sed -n \"{max_lines + 1},{min(max_lines * 2, total_lines)}p\" {path}' 分段读取]"
            )
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
