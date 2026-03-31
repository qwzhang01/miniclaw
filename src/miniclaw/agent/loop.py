"""
MiniClaw - Agent 主循环

实现 ReAct（Reasoning + Acting）模式的 Agent 执行引擎。
每一轮循环：组装上下文 → 调用 LLM → 解析响应 → 执行工具 → 注入结果。

对应 PRD：F1 Agent 核心循环
参考：OpenClaw 的 Agent Runtime 设计
"""

from collections.abc import Callable
from typing import Any

from miniclaw.agent.context import AgentContext
from miniclaw.agent.model_router import ModelRouter
from miniclaw.llm.registry import ModelRoleRegistry
from miniclaw.tools.executor import ToolExecutor
from miniclaw.utils.logging import get_logger

logger = get_logger(__name__)

# 每轮工具调用/文本回复的回调类型
ToolCallCallback = Callable[[str, dict[str, Any]], None]
TextCallback = Callable[[str], None]


class AgentLoop:
    """Agent 主循环 — MiniClaw 最核心的模块

    实现完整的 ReAct 流程：
    1. 组装上下文（消息历史 + 动态工具列表）
    2. 选择模型角色（四模型路由）
    3. 调用 LLM
    4. 解析响应（文本 or 工具调用）
    5. 工具调用 → 安全审批 → 执行 → 结果注入上下文
    6. 循环直到文本回复或达到最大轮次

    Attributes:
        llm_registry: 四模型角色注册器
        tool_executor: 工具执行引擎
        model_router: 四模型路由器
    """

    def __init__(
        self,
        llm_registry: ModelRoleRegistry,
        tool_executor: ToolExecutor,
        model_router: ModelRouter | None = None,
    ) -> None:
        self.llm_registry = llm_registry
        self.tool_executor = tool_executor
        self.model_router = model_router or ModelRouter()

    async def run(
        self,
        user_input: str,
        context: AgentContext,
        on_tool_call: ToolCallCallback | None = None,
        on_text: TextCallback | None = None,
    ) -> str:
        """运行 Agent 主循环

        Args:
            user_input: 用户输入文本
            context: Agent 上下文
            on_tool_call: 工具调用时的回调（用于 UI 展示）
            on_text: 文本回复时的回调（用于流式输出）

        Returns:
            Agent 的最终文本回复
        """
        # 1. 将用户输入加入上下文
        context.add_user_message(user_input)
        context.current_round = 0

        for round_num in range(1, context.max_rounds + 1):
            context.current_round = round_num

            # 2. 选择本轮使用的模型角色
            role = self.model_router.select_role(context)

            # 3. 组装 prompt + 动态工具列表
            messages = context.build_messages()
            tools = context.get_available_tools()

            logger.info(
                "Agent Loop 轮次",
                round=round_num,
                role=role,
                messages_count=len(messages),
                tools_count=len(tools),
            )

            # 4. 调用 LLM
            try:
                response = await self.llm_registry.chat(
                    messages, tools, role=role
                )
            except Exception as e:
                logger.error("LLM 调用失败", error=str(e))
                error_msg = f"抱歉，AI 模型调用失败：{e}"
                context.add_assistant_message(error_msg)
                return error_msg

            # 5. 解析响应
            if response.has_tool_calls:
                # 5a. 有工具调用 → 执行
                await self._handle_tool_calls(
                    response, context, on_tool_call
                )
            else:
                # 5b. 纯文本回复 → 结束循环
                text = response.text
                context.add_assistant_message(text)
                if on_text:
                    on_text(text)
                logger.info("Agent Loop 完成", rounds=round_num)
                return text

        # 达到最大轮次
        max_msg = (
            f"已达到最大轮次限制（{context.max_rounds} 轮），请简化你的请求。"
        )
        context.add_assistant_message(max_msg)
        return max_msg

    async def _handle_tool_calls(
        self,
        response: Any,
        context: AgentContext,
        on_tool_call: ToolCallCallback | None,
    ) -> None:
        """处理工具调用"""
        # 构建 OpenAI 格式的 tool_calls 消息
        raw_calls = []
        for tc in response.tool_calls:
            raw_calls.append({
                "id": tc.id,
                "type": "function",
                "function": {
                    "name": tc.name,
                    "arguments": str(tc.arguments),
                },
            })
        context.add_tool_call_message(raw_calls)

        # 逐个执行工具
        for tc in response.tool_calls:
            if on_tool_call:
                on_tool_call(tc.name, tc.arguments)

            result = await self.tool_executor.execute(
                tc.name, tc.arguments, tc.id
            )

            # 更新上下文状态
            context.last_tool_failed = not result.success

            # 将工具结果注入上下文
            context.add_tool_result(tc.id, tc.name, result.output)

            logger.info(
                "工具执行",
                tool=tc.name,
                success=result.success,
                output_len=len(result.output),
            )
