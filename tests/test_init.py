"""
MiniClaw - 包导入和版本测试
"""

from miniclaw import __version__


def test_version_format():
    """版本号应为有效的语义化版本"""
    parts = __version__.split(".")
    assert len(parts) == 3
    assert all(p.isdigit() for p in parts)


def test_version_value():
    """当前版本应为 0.1.0"""
    assert __version__ == "0.1.0"
