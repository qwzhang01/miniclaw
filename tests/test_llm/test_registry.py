"""
MiniClaw - 模型角色注册器测试

测试四模型角色注册、路由、重试和 fallback 机制。
"""


import pytest

from miniclaw.llm.base import BaseProvider, LLMResponse
from miniclaw.llm.registry import ModelRoleRegistry
from miniclaw.utils.tokens import TokenUsage


class MockProvider(BaseProvider):
    """测试用的 mock Provider"""

    def __init__(self, model: str = "mock-model", should_fail: bool = False):
        super().__init__("http://mock", "key", model)
        self.should_fail = should_fail
        self.call_count = 0

    async def chat(self, messages, tools=None):
        self.call_count += 1
        if self.should_fail:
            raise RuntimeError("Mock error")
        return LLMResponse(
            text="mock response",
            model=self.model,
            token_usage=TokenUsage(input_tokens=10, output_tokens=5),
        )

    async def chat_stream(self, messages, tools=None):
        yield  # pragma: no cover


class TestModelRoleRegistry:
    """测试模型角色注册"""

    def test_register_valid_role(self):
        registry = ModelRoleRegistry()
        provider = MockProvider()
        registry.register("default", provider)
        assert "default" in registry.registered_roles

    def test_register_invalid_role(self):
        registry = ModelRoleRegistry()
        provider = MockProvider()
        with pytest.raises(ValueError, match="无效的模型角色"):
            registry.register("invalid_role", provider)

    def test_get_provider(self):
        registry = ModelRoleRegistry()
        provider = MockProvider()
        registry.register("default", provider)
        assert registry.get_provider("default") is provider
        assert registry.get_provider("planner") is None


class TestRegistryChat:
    """测试 chat 路由和重试"""

    @pytest.mark.asyncio
    async def test_chat_with_default_role(self):
        """使用 default 角色调用"""
        registry = ModelRoleRegistry()
        registry.register("default", MockProvider())
        resp = await registry.chat([{"role": "user", "content": "hi"}])
        assert resp.text == "mock response"
        assert resp.role == "default"

    @pytest.mark.asyncio
    async def test_chat_with_specific_role(self):
        """使用指定角色调用"""
        registry = ModelRoleRegistry()
        registry.register("default", MockProvider(model="default-model"))
        registry.register("reasoner", MockProvider(model="reasoner-model"))
        resp = await registry.chat(
            [{"role": "user", "content": "analyze"}],
            role="reasoner",
        )
        assert resp.role == "reasoner"

    @pytest.mark.asyncio
    async def test_fallback_to_default_when_role_missing(self):
        """角色不存在时 fallback 到 default"""
        registry = ModelRoleRegistry()
        registry.register("default", MockProvider(model="fallback"))
        resp = await registry.chat(
            [{"role": "user", "content": "hi"}],
            role="planner",
        )
        assert resp.role == "default"

    @pytest.mark.asyncio
    async def test_error_when_no_default(self):
        """没有 default 角色且请求的角色不存在时报错"""
        registry = ModelRoleRegistry()
        registry.register("reasoner", MockProvider())
        with pytest.raises(RuntimeError, match="不可用"):
            await registry.chat(
                [{"role": "user", "content": "hi"}],
                role="planner",
            )

    @pytest.mark.asyncio
    async def test_retry_on_failure(self):
        """失败时自动重试"""
        registry = ModelRoleRegistry()
        failing_provider = MockProvider(should_fail=True)
        fallback_provider = MockProvider(model="fallback")
        registry.register("planner", failing_provider)
        registry.register("default", fallback_provider)

        # planner 会失败 3 次，然后 fallback 到 default
        resp = await registry.chat(
            [{"role": "user", "content": "hi"}],
            role="planner",
        )
        assert failing_provider.call_count == 3  # 重试了 3 次
        assert resp.role == "default"  # fallback 到 default

    @pytest.mark.asyncio
    async def test_all_retries_and_fallback_fail(self):
        """所有重试和 fallback 都失败时抛出异常"""
        registry = ModelRoleRegistry()
        registry.register("default", MockProvider(should_fail=True))

        with pytest.raises(RuntimeError, match="LLM 调用失败"):
            await registry.chat(
                [{"role": "user", "content": "hi"}],
                role="default",
            )


class TestRegistryClose:
    """测试资源释放"""

    @pytest.mark.asyncio
    async def test_close_all(self):
        registry = ModelRoleRegistry()
        p1 = MockProvider()
        p2 = MockProvider()
        registry.register("default", p1)
        registry.register("reasoner", p2)
        await registry.close_all()  # 不应报错
