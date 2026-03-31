"""
MiniClaw - 工具系统

可注册、可发现、有安全审批的工具体系。
支持 @tool 装饰器注册，自动从函数签名生成 JSON Schema。

对应 PRD：F3 工具系统
"""

from miniclaw.tools.registry import RiskLevel, ToolRegistry, tool

__all__ = ["RiskLevel", "ToolRegistry", "tool"]
