"""
MiniClaw - Agent 主循环

实现 ReAct（Reasoning + Acting）模式的 Agent 执行引擎。
每一轮循环：组装上下文 → 调用 LLM → 解析响应 → 执行工具 → 注入结果。
OP6: 支持流式输出模式（chat_stream）。

对应 PRD：F1 Agent 核心循环
参考：OpenClaw 的 Agent Runtime 设计
"""

import json
from collections.abc import AsyncIterator, Callable
from typing import Any

from miniclaw.agent.context import AgentContext
from miniclaw.agent.model_router import ModelRouter
from miniclaw.llm.base import LLMResponse, StreamChunk, ToolCall
from miniclaw.llm.registry import ModelRoleRegistry
from miniclaw.skills.matcher import SkillMatcher
from miniclaw.tools.executor import ToolExecutor
from miniclaw.utils.logging import get_logger

logger = get_logger(__name__)

# 每轮工具调用/文本回复的回调类型
ToolCallCallback = Callable[[str, dict[str, Any]], None]
TextCallback = Callable[[str], None]
# OP6.1: 流式输出回调（每个 token 片段）
StreamCallback = Callable[[str], Any]


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
        skill_matcher: SkillMatcher | None = None,
    ) -> None:
        self.llm_registry = llm_registry
        self.tool_executor = tool_executor
        self.model_router = model_router or ModelRouter()
        self.skill_matcher = skill_matcher

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

        # OP4.2: 匹配 Skill 并注入上下文
        self._match_and_inject_skill(user_input, context)

        for round_num in range(1, context.max_rounds + 1):
            context.current_round = round_num

            # OP2.2: 每轮循环前检查是否需要压缩上下文
            await self._check_and_compress(context)

            # OP7.2: Token 预算检查（压缩后仍超 95% 则警告）
            self._check_token_budget(context)

            # 2. 选择本轮使用的模型角色
            role = self.model_router.select_role(context)

            # 3. 组装 prompt + 动态工具列表
            messages = context.build_messages()
            tools = context.get_available_tools()

            # OP7.3: Debug 日志输出 token 预算
            logger.info(
                "Agent Loop 轮次",
                round=round_num,
                role=role,
                messages_count=len(messages),
                tools_count=len(tools),
                tokens_used=context.estimated_tokens,
                tokens_max=context.max_context_tokens,
                tokens_ratio=f"{context.token_usage_ratio:.0%}",
            )

            # 4. 调用 LLM
            try:
                response = await self.llm_registry.chat(
                    messages, tools, role=role
                )
            except Exception as e:
                logger.error("LLM 调用失败", error=repr(e))
                error_msg = f"抱歉，AI 模型调用失败：{e!r}"
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

    async def run_stream(
        self,
        user_input: str,
        context: AgentContext,
        on_stream: StreamCallback | None = None,
        on_stream_end: StreamCallback | None = None,
        on_tool_call: ToolCallCallback | None = None,
    ) -> str:
        """运行 Agent 主循环（流式模式 OP6.1）

        使用 chat_stream() 替代 chat()，逐 token 通过 on_stream 回调输出。
        工具调用在流式模式下需要累积 delta 后解析（OP6.2）。

        Args:
            user_input: 用户输入文本
            context: Agent 上下文
            on_stream: 每个文本片段的回调（用于逐 token 输出）
            on_stream_end: 流式输出结束时的回调
            on_tool_call: 工具调用时的回调

        Returns:
            Agent 的最终完整文本回复
        """
        context.add_user_message(user_input)
        context.current_round = 0

        # OP4.2: 匹配 Skill 并注入上下文
        self._match_and_inject_skill(user_input, context)

        for round_num in range(1, context.max_rounds + 1):
            context.current_round = round_num
            await self._check_and_compress(context)

            # OP7.2: Token 预算检查
            self._check_token_budget(context)

            role = self.model_router.select_role(context)
            messages = context.build_messages()
            tools = context.get_available_tools()

            # OP7.3: Debug 日志输出 token 预算
            logger.info(
                "Agent Loop 轮次（流式）",
                round=round_num, role=role,
                messages_count=len(messages),
                tokens_used=context.estimated_tokens,
                tokens_max=context.max_context_tokens,
                tokens_ratio=f"{context.token_usage_ratio:.0%}",
            )

            try:
                stream = self.llm_registry.chat_stream(
                    messages, tools, role=role
                )
                result = await self._collect_stream(
                    stream, context, on_stream, on_stream_end, on_tool_call
                )
            except Exception as e:
                logger.error("LLM 流式调用失败", error=repr(e))
                error_msg = f"抱歉，AI 模型调用失败：{e!r}"
                context.add_assistant_message(error_msg)
                return error_msg

            if result is not None:
                # 纯文本回复完成
                logger.info("Agent Loop 完成（流式）", rounds=round_num)
                return result
            # 否则是工具调用，继续循环

        max_msg = (
            f"已达到最大轮次限制（{context.max_rounds} 轮），请简化你的请求。"
        )
        context.add_assistant_message(max_msg)
        return max_msg

    async def _collect_stream(
        self,
        stream: AsyncIterator[StreamChunk],
        context: AgentContext,
        on_stream: StreamCallback | None,
        on_stream_end: StreamCallback | None,
        on_tool_call: ToolCallCallback | None,
    ) -> str | None:
        """收集流式输出，区分文本回复和工具调用（OP6.2）

        Returns:
            纯文本回复时返回完整文本；工具调用时返回 None（已处理）。
        """
        full_text = ""
        tool_call_parts: dict[int, dict[str, str]] = {}  # index → {id, name, arguments}

        async for chunk in stream:
            # 文本片段
            if chunk.text:
                full_text += chunk.text
                if on_stream:
                    on_stream(chunk.text)

            # 工具调用 delta 累积（OP6.2）
            if chunk.tool_call_delta:
                delta = chunk.tool_call_delta
                idx = delta.get("index", 0)
                if idx not in tool_call_parts:
                    tool_call_parts[idx] = {"id": "", "name": "", "arguments": ""}
                part = tool_call_parts[idx]
                if "id" in delta:
                    part["id"] += delta["id"]
                if "name" in delta:
                    part["name"] += delta["name"]
                if "arguments" in delta:
                    part["arguments"] += delta["arguments"]

        # 流结束
        if on_stream_end:
            on_stream_end("")

        if tool_call_parts:
            # 解析累积的工具调用
            tool_calls: list[ToolCall] = []
            for _idx, part in sorted(tool_call_parts.items()):
                try:
                    args = json.loads(part["arguments"]) if part["arguments"] else {}
                except json.JSONDecodeError:
                    args = {"raw": part["arguments"]}
                tool_calls.append(ToolCall(
                    id=part["id"], name=part["name"], arguments=args,
                ))

            # 构建 LLMResponse 并执行工具
            response = LLMResponse(tool_calls=tool_calls)
            await self._handle_tool_calls(response, context, on_tool_call)
            return None

        # 纯文本回复
        context.add_assistant_message(full_text)
        return full_text

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

    def _check_token_budget(self, context: AgentContext) -> None:
        """检查 Token 预算，接近上限时记录警告（OP7.2）

        当 token 使用率超过 95% 时发出警告，提示用户上下文即将耗尽。
        这与 _check_and_compress 的 80% 压缩阈值配合使用：
        80% → 触发压缩 → 95% → 压缩后仍然很满，发出警告。
        """
        ratio = context.token_usage_ratio
        if ratio >= 0.95:
            logger.warning(
                "Token 预算即将耗尽",
                tokens_used=context.estimated_tokens,
                tokens_max=context.max_context_tokens,
                usage_ratio=f"{ratio:.0%}",
            )

    async def _check_and_compress(self, context: AgentContext) -> None:
        """检查并触发上下文压缩（OP2.2）

        当 ShortTermMemory 判断 token 接近阈值（80%）时，
        调用 default 模型生成历史摘要，再压缩上下文。
        """
        if not context.needs_compression():
            return

        logger.info("上下文接近 token 上限，触发压缩")
        try:
            # 用 default 模型生成历史摘要（省钱优先）
            messages = context.build_messages()
            summary_prompt = [
                {"role": "system", "content": "请用简洁的中文总结以下对话的关键信息和结论，不超过 200 字。"},
                {"role": "user", "content": str(messages[1:-4]) if len(messages) > 5 else str(messages[1:])},
            ]
            response = await self.llm_registry.chat(
                summary_prompt, tools=[], role="default"
            )
            summary = response.text or "（压缩失败，无摘要）"
            context.compress(summary)
            logger.info("上下文压缩完成", summary_len=len(summary))
        except Exception as e:
            logger.warning("上下文压缩失败，继续使用完整历史", error=repr(e))

    def _match_and_inject_skill(
        self, user_input: str, context: AgentContext
    ) -> None:
        """匹配 Skill 并注入上下文（OP4.2）

        每次用户输入后检查是否匹配新 Skill。
        仅在匹配到不同于当前活跃 Skill 时更新。
        """
        if self.skill_matcher is None:
            return

        matched = self.skill_matcher.match_best(user_input)
        if matched is not None:
            # 仅在 Skill 变化时注入（避免重复更新 prompt）
            if context.active_skill is None or context.active_skill.name != matched.name:
                context.inject_skill_context(matched)
                logger.info("Skill 激活", skill=matched.name)
