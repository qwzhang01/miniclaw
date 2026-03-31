"""
MiniClaw - 工具注册中心测试

测试 @tool 装饰器、ToolRegistry、Schema 生成。
"""


from miniclaw.tools.registry import (
    RiskLevel,
    ToolInfo,
    ToolRegistry,
    _generate_schema,
)


class TestRiskLevel:
    def test_risk_levels(self):
        assert RiskLevel.LOW.value == "low"
        assert RiskLevel.HIGH.value == "high"
        assert RiskLevel.CRITICAL.value == "critical"

    def test_from_string(self):
        assert RiskLevel("low") == RiskLevel.LOW
        assert RiskLevel("high") == RiskLevel.HIGH


class TestGenerateSchema:
    def test_string_param(self):
        async def func(name: str) -> str:
            return name

        schema = _generate_schema(func)
        assert schema["properties"]["name"]["type"] == "string"
        assert "name" in schema["required"]

    def test_int_param(self):
        async def func(count: int) -> str:
            return str(count)

        schema = _generate_schema(func)
        assert schema["properties"]["count"]["type"] == "integer"

    def test_optional_param(self):
        async def func(name: str, count: int = 10) -> str:
            return f"{name}:{count}"

        schema = _generate_schema(func)
        assert "name" in schema["required"]
        assert "count" not in schema.get("required", [])

    def test_bool_param(self):
        async def func(verbose: bool) -> str:
            return str(verbose)

        schema = _generate_schema(func)
        assert schema["properties"]["verbose"]["type"] == "boolean"

    def test_no_annotation(self):
        """无类型注解默认为 string"""

        async def func(x) -> str:
            return str(x)

        schema = _generate_schema(func)
        assert schema["properties"]["x"]["type"] == "string"


class TestToolInfo:
    def test_to_openai_schema(self):
        async def dummy(cmd: str) -> str:
            return cmd

        info = ToolInfo(
            name="test_tool",
            description="A test tool",
            risk_level=RiskLevel.LOW,
            func=dummy,
            parameters_schema={
                "type": "object",
                "properties": {"cmd": {"type": "string"}},
                "required": ["cmd"],
            },
        )
        schema = info.to_openai_schema()
        assert schema["type"] == "function"
        assert schema["function"]["name"] == "test_tool"
        assert schema["function"]["description"] == "A test tool"


class TestToolRegistry:
    def test_register_and_get(self):
        registry = ToolRegistry()

        async def dummy(x: str) -> str:
            return x

        info = ToolInfo("test", "desc", RiskLevel.LOW, dummy, {})
        registry.register(info)

        assert registry.get("test") is info
        assert registry.get("nonexistent") is None

    def test_get_all(self):
        registry = ToolRegistry()

        async def f1(x: str) -> str:
            return x

        async def f2(x: str) -> str:
            return x

        registry.register(ToolInfo("t1", "d1", RiskLevel.LOW, f1, {}))
        registry.register(ToolInfo("t2", "d2", RiskLevel.HIGH, f2, {}))
        assert len(registry.get_all()) == 2

    def test_tool_names(self):
        registry = ToolRegistry()

        async def f(x: str) -> str:
            return x

        registry.register(ToolInfo("a", "d", RiskLevel.LOW, f, {}))
        registry.register(ToolInfo("b", "d", RiskLevel.HIGH, f, {}))
        assert set(registry.tool_names) == {"a", "b"}

    def test_remove(self):
        registry = ToolRegistry()

        async def f(x: str) -> str:
            return x

        registry.register(ToolInfo("test", "d", RiskLevel.LOW, f, {}))
        registry.remove("test")
        assert registry.get("test") is None

    def test_get_all_schemas(self):
        registry = ToolRegistry()

        async def f(x: str) -> str:
            return x

        registry.register(
            ToolInfo(
                "test",
                "desc",
                RiskLevel.LOW,
                f,
                {"type": "object", "properties": {}},
            )
        )
        schemas = registry.get_all_schemas()
        assert len(schemas) == 1
        assert schemas[0]["function"]["name"] == "test"
