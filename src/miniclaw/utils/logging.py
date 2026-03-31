"""
MiniClaw - 结构化日志系统

统一日志格式，支持 info/debug/error 级别。
debug 模式输出完整 prompt、模型路由决策和 token 计数。

对应 PRD：§5.3 可观测/可调试
"""

import logging
import sys
from typing import Any


class StructuredLogger:
    """结构化日志封装，支持 key=value 格式的结构化字段"""

    def __init__(self, name: str) -> None:
        self._logger = logging.getLogger(name)

    def _format_kwargs(self, kwargs: dict[str, Any]) -> str:
        """将关键字参数格式化为结构化字段"""
        if not kwargs:
            return ""
        parts = [f"{k}={v}" for k, v in kwargs.items()]
        return " | " + ", ".join(parts)

    def info(self, msg: str, **kwargs: Any) -> None:
        """记录 info 级别日志"""
        self._logger.info(f"{msg}{self._format_kwargs(kwargs)}")

    def debug(self, msg: str, **kwargs: Any) -> None:
        """记录 debug 级别日志（--debug 模式下输出完整 prompt 和 token 计数）"""
        self._logger.debug(f"{msg}{self._format_kwargs(kwargs)}")

    def warning(self, msg: str, **kwargs: Any) -> None:
        """记录 warning 级别日志"""
        self._logger.warning(f"{msg}{self._format_kwargs(kwargs)}")

    def error(self, msg: str, **kwargs: Any) -> None:
        """记录 error 级别日志"""
        self._logger.error(f"{msg}{self._format_kwargs(kwargs)}")


def setup_logging(level: str = "INFO", log_file: str | None = None) -> None:
    """初始化日志系统

    Args:
        level: 日志级别（DEBUG/INFO/WARNING/ERROR）
        log_file: 日志文件路径，为 None 时只输出到控制台
    """
    log_format = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"

    handlers: list[logging.Handler] = [
        logging.StreamHandler(sys.stderr),
    ]

    if log_file:
        from pathlib import Path

        Path(log_file).parent.mkdir(parents=True, exist_ok=True)
        handlers.append(logging.FileHandler(log_file, encoding="utf-8"))

    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format=log_format,
        datefmt=date_format,
        handlers=handlers,
        force=True,
    )


def get_logger(name: str) -> StructuredLogger:
    """获取结构化日志实例

    Args:
        name: 模块名称，通常传 __name__

    Returns:
        StructuredLogger 实例
    """
    return StructuredLogger(name)
