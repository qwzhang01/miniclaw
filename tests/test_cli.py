"""
MiniClaw - CLI 入口测试

测试 cli.py 的命令行界面功能。
"""

from click.testing import CliRunner

from miniclaw import __version__
from miniclaw.cli import main, show_banner


class TestCLI:
    """测试 CLI 命令"""

    def test_version_option(self):
        """--version 应输出版本号"""
        runner = CliRunner()
        result = runner.invoke(main, ["--version"])
        assert result.exit_code == 0
        assert __version__ in result.output

    def test_help_option(self):
        """--help 应输出帮助信息"""
        runner = CliRunner()
        result = runner.invoke(main, ["--help"])
        assert result.exit_code == 0
        assert "MiniClaw" in result.output

    def test_exit_command(self):
        """/exit 命令应正常退出"""
        runner = CliRunner()
        result = runner.invoke(main, input="/exit\n")
        assert result.exit_code == 0
        assert "再见" in result.output

    def test_help_command(self):
        """/help 命令应显示帮助信息"""
        runner = CliRunner()
        result = runner.invoke(main, input="/help\n/exit\n")
        assert result.exit_code == 0
        assert "/tools" in result.output
        assert "/skills" in result.output

    def test_unknown_command(self):
        """未知命令应提示错误"""
        runner = CliRunner()
        result = runner.invoke(main, input="/unknown\n/exit\n")
        assert result.exit_code == 0
        assert "未知命令" in result.output

    def test_empty_input_ignored(self):
        """空输入应被忽略"""
        runner = CliRunner()
        result = runner.invoke(main, input="\n/exit\n")
        assert result.exit_code == 0

    def test_normal_input_shows_placeholder(self):
        """普通输入应显示占位提示"""
        runner = CliRunner()
        result = runner.invoke(main, input="你好\n/exit\n")
        assert result.exit_code == 0
        assert "Agent" in result.output

    def test_special_commands_placeholder(self):
        """所有 9 个特殊命令都应有响应"""
        runner = CliRunner()
        commands = ["/tools", "/skills", "/history", "/clear", "/screen", "/config", "/reload"]
        for cmd in commands:
            result = runner.invoke(main, input=f"{cmd}\n/exit\n")
            assert result.exit_code == 0, f"命令 {cmd} 执行失败"

    def test_show_banner_no_error(self, capsys):
        """show_banner 应无报错执行"""
        show_banner()
        # 不抛异常即可
