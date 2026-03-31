"""
MiniClaw - 通道层

对应 PRD：F6 CLI 交互界面
"""

from miniclaw.channels.base import ChannelProtocol
from miniclaw.channels.cli_channel import CLIChannel

__all__ = ["ChannelProtocol", "CLIChannel"]
