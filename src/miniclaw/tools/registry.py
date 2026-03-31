"""
MiniClaw - 工具注册中心 + @tool 装饰器

装饰器注册工具，自动从函数签名生成 JSON Schema（供 LLM 使用）。
所有工具必须通过 @tool 装饰器注册。

对应 PRD：F3 工具系统
"""

import inspect
from collections.abc import Callable
from enum import Enum
from typing import Any

from miniclaw.utils.logging import get_logger

logger = get_logger(__name__)

# Python 类型到 JSON Schema 类型的映射
_TYPE_MAP: dict[type, str] = {
    str: "string",
    int: "integer",
    float: "number",
    bool: "boolean",
}


class RiskLevel(Enum):
    """工具风险等级（PRD F3 安全模型）"""

    LOW = "low"  # 只读操作，自动执行
    HIGH = "high"  # 有副作用，需用户确认
    CRITICAL = "critical"  # 不可逆操作，需二次确认


class ToolInfo:
    """工具的元信息"""

    def __init__(
        self,
        name: str,
        description: str,
        risk_level: RiskLevel,
        func: Callable[..., Any],
        parameters_schema: dict[str, Any],
    ) -> None:
        self.name = name
        self.description = description
        self.risk_level = risk_level
        self.func = func
        self.parameters_schema = parameters_schema

    def to_openai_schema(self) -> dict[str, Any]:
        """生成 OpenAI 格式的工具 JSON Schema（供 LLM 使用）"""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters_schema,
            },
        }


def _generate_schema(func: Callable[..., Any]) -> dict[str, Any]:
    """从函数签名自动生成 JSON Schema

    只支持基础类型：str, int, float, bool（PRD F3 约束）
    """
    sig = inspect.signature(func)
    properties: dict[str, Any] = {}
    required: list[str] = []

    for param_name, param in sig.parameters.items():
        if param_name in ("self", "cls"):
            continue

        # 获取类型注解
        annotation = param.annotation
        if annotation is inspect.Parameter.empty:
            json_type = "string"  # 默认 string
        else:
            json_type = _TYPE_MAP.get(annotation, "string")

        prop: dict[str, str] = {"type": json_type}

        # 从 docstring 提取参数描述（简化版）
        prop["description"] = f"参数 {param_name}"

        properties[param_name] = prop

        # 没有默认值的参数为 required
        if param.default is inspect.Parameter.empty:
            required.append(param_name)

    schema: dict[str, Any] = {
        "type": "object",
        "properties": properties,
    }
    if required:
        schema["required"] = required

    return schema


class ToolRegistry:
    """工具注册中心

    管理所有已注册的工具，支持按名称查找和列表展示。

    使用方式：
        registry = ToolRegistry()

        @registry.tool(description="执行命令", risk_level=RiskLevel.HIGH)
        async def shell_exec(command: str) -> str: ...

        tool_info = registry.get("shell_exec")
        schemas = registry.get_all_schemas()
    """

    def __init__(self) -> None:
        self._tools: dict[str, ToolInfo] = {}

    def register(self, tool_info: ToolInfo) -> None:
        """注册一个工具"""
        self._tools[tool_info.name] = tool_info
        logger.info("注册工具", name=tool_info.name, risk=tool_info.risk_level.value)

    def get(self, name: str) -> ToolInfo | None:
        """按名称获取工具"""
        return self._tools.get(name)

    def get_all(self) -> dict[str, ToolInfo]:
        """获取所有已注册工具"""
        return dict(self._tools)

    def get_all_schemas(self) -> list[dict[str, Any]]:
        """获取所有工具的 OpenAI JSON Schema（传给 LLM）"""
        return [t.to_openai_schema() for t in self._tools.values()]

    @property
    def tool_names(self) -> list[str]:
        """已注册的工具名称列表"""
        return list(self._tools.keys())

    def remove(self, name: str) -> None:
        """移除工具（用于 Skill 动态注入/卸载）"""
        self._tools.pop(name, None)


# 全局工具注册中心
_global_registry: ToolRegistry | None = None


def get_global_registry() -> ToolRegistry:
    """获取全局工具注册中心单例"""
    global _global_registry
    if _global_registry is None:
        _global_registry = ToolRegistry()
    return _global_registry


def tool(
    description: str,
    risk_level: RiskLevel | str = RiskLevel.LOW,
) -> Callable[..., Any]:
    """@tool 装饰器 — 注册工具到全局注册中心

    Args:
        description: 工具描述（让 LLM 理解何时该调用）
        risk_level: 风险等级（low/high/critical）

    示例：
        @tool(description="执行 Shell 命令", risk_level="high")
        async def shell_exec(command: str) -> str: ...
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        # 支持字符串形式的 risk_level
        actual_risk = (
            RiskLevel(risk_level) if isinstance(risk_level, str) else risk_level
        )
        # 自动生成 JSON Schema
        schema = _generate_schema(func)
        # 创建工具信息
        info = ToolInfo(
            name=func.__name__,
            description=description,
            risk_level=actual_risk,
            func=func,
            parameters_schema=schema,
        )
        # 注册到全局注册中心
        registry = get_global_registry()
        registry.register(info)
        # 在函数上附加工具信息
        func._tool_info = info  # type: ignore[attr-defined]
        return func

    return decorator
