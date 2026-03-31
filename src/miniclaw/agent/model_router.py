"""
MiniClaw - 四模型角色路由器

根据当前上下文自动选择最合适的模型角色。
路由优先级：有图→reasoner / 首轮复杂→planner / 产出→maker / 其他→default。

对应 PRD：F2 四模型角色调度系统
"""

from miniclaw.agent.context import AgentContext
from miniclaw.utils.logging import get_logger

logger = get_logger(__name__)

# 产出类关键词（匹配到则使用 maker 角色）
_MAKER_KEYWORDS = (
    "写", "生成", "创建", "编写", "produce", "generate", "write", "create",
    "报告", "文档", "代码", "脚本", "report", "code", "script",
)

# 规划类关键词
_PLANNER_KEYWORDS = (
    "帮我", "分析", "调研", "部署", "规划", "plan", "analyze", "deploy",
    "步骤", "方案", "strategy",
)


class ModelRouter:
    """四模型角色路由器

    根据上下文自动选择模型角色（PRD F2 路由规则）：
    1. 有图片输入 → reasoner（多模态）
    2. 第一轮 + 复杂任务 → planner
    3. 上一次工具失败 → reasoner（分析错误）
    4. 需要产出内容 → maker
    5. 其他 → default（省钱）
    """

    def select_role(self, context: AgentContext) -> str:
        """根据上下文选择模型角色"""
        # 规则 1：有截图/图片 → reasoner
        if context.has_images:
            role = "reasoner"
            logger.debug("模型路由", role=role, reason="有图片输入")
            return role

        # 获取最新用户消息
        last_user_msg = self._get_last_user_message(context)

        # 规则 2：第一轮 + 复杂任务 → planner
        if context.current_round == 1 and self._is_complex_task(last_user_msg):
            role = "planner"
            logger.debug("模型路由", role=role, reason="首轮复杂任务")
            return role

        # 规则 3：上一次工具失败 → reasoner
        if context.last_tool_failed:
            role = "reasoner"
            logger.debug("模型路由", role=role, reason="上次工具失败")
            return role

        # 规则 4：需要产出 → maker
        if self._needs_production(last_user_msg):
            role = "maker"
            logger.debug("模型路由", role=role, reason="产出类任务")
            return role

        # 规则 5：默认 → default（省钱）
        role = "default"
        logger.debug("模型路由", role=role, reason="默认")
        return role

    def _get_last_user_message(self, context: AgentContext) -> str:
        """获取最近的用户消息内容"""
        for msg in reversed(context.messages):
            if msg.get("role") == "user":
                content = msg.get("content", "")
                return str(content)
        return ""

    def _is_complex_task(self, message: str) -> bool:
        """判断是否为复杂任务（需要规划）"""
        return any(kw in message.lower() for kw in _PLANNER_KEYWORDS)

    def _needs_production(self, message: str) -> bool:
        """判断是否需要产出内容"""
        return any(kw in message.lower() for kw in _MAKER_KEYWORDS)
