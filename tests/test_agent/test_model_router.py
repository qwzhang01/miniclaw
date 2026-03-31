"""
MiniClaw - 四模型路由器测试
"""

from miniclaw.agent.context import AgentContext
from miniclaw.agent.model_router import ModelRouter
from miniclaw.tools.registry import ToolRegistry


class TestModelRouter:
    def _make_context(self, user_msg: str = "", **kwargs) -> AgentContext:
        ctx = AgentContext(tool_registry=ToolRegistry(), **kwargs)
        if user_msg:
            ctx.add_user_message(user_msg)
        return ctx

    def test_default_role(self):
        """普通消息使用 default"""
        router = ModelRouter()
        ctx = self._make_context("你好")
        role = router.select_role(ctx)
        assert role == "default"

    def test_reasoner_for_images(self):
        """有图片时使用 reasoner"""
        router = ModelRouter()
        ctx = self._make_context("看看这张图")
        ctx.has_images = True
        role = router.select_role(ctx)
        assert role == "reasoner"

    def test_planner_for_complex_first_round(self):
        """首轮复杂任务使用 planner"""
        router = ModelRouter()
        ctx = self._make_context("帮我部署这个项目")
        ctx.current_round = 1
        role = router.select_role(ctx)
        assert role == "planner"

    def test_reasoner_for_tool_failure(self):
        """工具失败后使用 reasoner"""
        router = ModelRouter()
        ctx = self._make_context("重试一下")
        ctx.last_tool_failed = True
        role = router.select_role(ctx)
        assert role == "reasoner"

    def test_maker_for_production(self):
        """产出任务使用 maker"""
        router = ModelRouter()
        ctx = self._make_context("帮我写一个 Python 脚本")
        role = router.select_role(ctx)
        assert role == "maker"

    def test_maker_for_report(self):
        """生成报告使用 maker"""
        router = ModelRouter()
        ctx = self._make_context("生成一份调研报告")
        role = router.select_role(ctx)
        assert role == "maker"

    def test_priority_images_over_maker(self):
        """图片优先级高于 maker"""
        router = ModelRouter()
        ctx = self._make_context("帮我写代码")
        ctx.has_images = True
        role = router.select_role(ctx)
        assert role == "reasoner"
