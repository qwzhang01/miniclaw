"""
MiniClaw - 内置工具

导入此模块会自动注册所有内置工具到全局注册中心。

对应 PRD：F3 工具系统
"""


def register_all_builtin_tools() -> None:
    """注册所有内置工具"""
    from miniclaw.tools.builtin import browser as _browser  # noqa: F401
    from miniclaw.tools.builtin import desktop as _desktop  # noqa: F401
    from miniclaw.tools.builtin import file as _file  # noqa: F401
    from miniclaw.tools.builtin import shell as _shell  # noqa: F401
    from miniclaw.tools.builtin import web as _web  # noqa: F401
