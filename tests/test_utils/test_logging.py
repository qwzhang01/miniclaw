"""
MiniClaw - 结构化日志系统测试

测试 utils/logging.py 的日志格式化和初始化功能。
"""

import logging

from miniclaw.utils.logging import StructuredLogger, get_logger, setup_logging


class TestStructuredLogger:
    """测试结构化日志封装"""

    def test_get_logger_returns_structured_logger(self):
        """get_logger 应返回 StructuredLogger 实例"""
        logger = get_logger("test_module")
        assert isinstance(logger, StructuredLogger)

    def test_format_kwargs_empty(self):
        """无结构化字段时返回空字符串"""
        logger = get_logger("test")
        result = logger._format_kwargs({})
        assert result == ""

    def test_format_kwargs_with_fields(self):
        """有结构化字段时格式化为 key=value"""
        logger = get_logger("test")
        result = logger._format_kwargs({"role": "default", "tokens": 100})
        assert "role=default" in result
        assert "tokens=100" in result
        assert result.startswith(" | ")

    def test_info_logs_message(self, caplog):
        """info 方法应记录 INFO 级别日志"""
        with caplog.at_level(logging.INFO):
            logger = get_logger("test.info")
            logger.info("测试消息", key="value")
        assert "测试消息" in caplog.text
        assert "key=value" in caplog.text

    def test_debug_logs_message(self, caplog):
        """debug 方法应记录 DEBUG 级别日志"""
        with caplog.at_level(logging.DEBUG):
            logger = get_logger("test.debug")
            logger.debug("调试信息", prompt_len=1000)
        assert "调试信息" in caplog.text
        assert "prompt_len=1000" in caplog.text

    def test_warning_logs_message(self, caplog):
        """warning 方法应记录 WARNING 级别日志"""
        with caplog.at_level(logging.WARNING):
            logger = get_logger("test.warn")
            logger.warning("警告信息", tool="shell_exec")
        assert "警告信息" in caplog.text

    def test_error_logs_message(self, caplog):
        """error 方法应记录 ERROR 级别日志"""
        with caplog.at_level(logging.ERROR):
            logger = get_logger("test.error")
            logger.error("错误信息", provider="openai")
        assert "错误信息" in caplog.text


class TestSetupLogging:
    """测试日志初始化"""

    def test_setup_logging_sets_level(self, reset_logging):
        """setup_logging 应正确设置日志级别"""
        setup_logging(level="DEBUG")
        root = logging.getLogger()
        assert root.level == logging.DEBUG

    def test_setup_logging_default_level(self, reset_logging):
        """默认日志级别应为 INFO"""
        setup_logging()
        root = logging.getLogger()
        assert root.level == logging.INFO

    def test_setup_logging_with_file(self, reset_logging, tmp_path):
        """支持输出到日志文件"""
        log_file = str(tmp_path / "logs" / "test.log")
        setup_logging(level="INFO", log_file=log_file)

        logger = get_logger("test.file")
        logger.info("文件日志测试")

        # 验证日志文件被创建
        from pathlib import Path

        assert Path(log_file).exists()
        content = Path(log_file).read_text()
        assert "文件日志测试" in content
