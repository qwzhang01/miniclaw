"""
MiniClaw 测试公共 fixtures
"""

import pytest


@pytest.fixture
def reset_logging():
    """重置日志配置，避免测试间干扰"""
    import logging

    # 移除所有 handler
    root = logging.getLogger()
    for handler in root.handlers[:]:
        root.removeHandler(handler)
    yield
    for handler in root.handlers[:]:
        root.removeHandler(handler)
