"""
MiniClaw - Shell 执行工具

在本地终端执行 Shell 命令，返回标准输出。

对应 PRD：F3 工具系统
"""

import asyncio

from miniclaw.tools.registry import tool


@tool(
    description="在本地终端执行 Shell 命令并返回标准输出。适用于文件操作、系统管理等场景。",
    risk_level="high",
)
async def shell_exec(command: str) -> str:
    """执行一条 shell 命令并返回标准输出"""
    try:
        proc = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=30)

        output_parts: list[str] = []
        if stdout:
            output_parts.append(stdout.decode("utf-8", errors="replace"))
        if stderr:
            output_parts.append(f"[stderr] {stderr.decode('utf-8', errors='replace')}")
        if proc.returncode != 0:
            output_parts.append(f"[exit code: {proc.returncode}]")

        return "\n".join(output_parts) if output_parts else "(无输出)"

    except TimeoutError:
        return "命令执行超时（30秒）"
    except Exception as e:
        return f"命令执行失败: {e}"
