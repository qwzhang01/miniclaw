"""
MiniClaw - 文件工具测试

OP3.3: read_file max_lines 参数限制。
"""

import pytest

from miniclaw.tools.builtin.file import read_file


class TestReadFile:
    @pytest.mark.asyncio
    async def test_read_existing_file(self, tmp_path):
        """正常读取文件"""
        f = tmp_path / "test.txt"
        f.write_text("hello\nworld\n")
        result = await read_file(str(f))
        assert "hello" in result
        assert "world" in result

    @pytest.mark.asyncio
    async def test_read_nonexistent_file(self):
        """读取不存在的文件"""
        result = await read_file("/tmp/nonexistent_miniclaw_test_file.txt")
        assert "不存在" in result

    @pytest.mark.asyncio
    async def test_max_lines_truncation(self, tmp_path):
        """OP3.3: 超过 max_lines 时截断"""
        f = tmp_path / "big.txt"
        lines = [f"line {i}" for i in range(500)]
        f.write_text("\n".join(lines))
        result = await read_file(str(f), max_lines=10)
        assert "line 0" in result
        assert "line 9" in result
        assert "line 10" not in result.split("...")[0] if "..." in result else True
        assert "500 行" in result
        assert "仅显示前 10 行" in result

    @pytest.mark.asyncio
    async def test_small_file_no_truncation(self, tmp_path):
        """小文件不截断"""
        f = tmp_path / "small.txt"
        f.write_text("just a few lines\nline 2\nline 3\n")
        result = await read_file(str(f), max_lines=200)
        assert "截断" not in result
        assert "just a few lines" in result

    @pytest.mark.asyncio
    async def test_default_max_lines(self, tmp_path):
        """默认 200 行截断"""
        f = tmp_path / "medium.txt"
        lines = [f"line {i}" for i in range(300)]
        f.write_text("\n".join(lines))
        result = await read_file(str(f))  # 使用默认 max_lines=200
        assert "300 行" in result
        assert "仅显示前 200 行" in result
