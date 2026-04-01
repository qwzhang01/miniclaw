"""
MiniClaw - AgentContext 测试

覆盖 OP1.1-OP1.4 动态系统提示词升级。
覆盖 OP2.1 ShortTermMemory 集成。
覆盖 OP4.1-OP4.3 Skill 提示词注入。
"""

from pathlib import Path

from miniclaw.agent.context import (
    AgentContext,
    _build_env_section,
    _build_skill_section,
    _build_tool_section,
    build_system_prompt,
)
from miniclaw.memory.short_term import ShortTermMemory
from miniclaw.skills.loader import SkillInfo
from miniclaw.tools.registry import RiskLevel, ToolInfo, ToolRegistry


def _make_registry_with_tools() -> ToolRegistry:
    """创建一个包含测试工具的 registry"""
    reg = ToolRegistry()

    async def dummy(x: str) -> str:
        return x

    # 注册一个命令执行域工具
    reg.register(
        ToolInfo("shell_exec", "执行 Shell 命令", RiskLevel.HIGH, dummy, {"type": "object"})
    )
    # 注册一个文件操作域工具
    reg.register(
        ToolInfo("read_file", "读取文件内容", RiskLevel.LOW, dummy, {"type": "object"})
    )
    return reg


class TestBuildToolSection:
    """OP1.1: 工具描述段动态生成"""

    def test_empty_registry(self):
        """空 registry 返回提示文字"""
        reg = ToolRegistry()
        result = _build_tool_section(reg)
        assert "暂无可用工具" in result

    def test_grouped_tools(self):
        """注册的工具按能力域分组显示"""
        reg = _make_registry_with_tools()
        result = _build_tool_section(reg)
        assert "【命令执行】" in result
        assert "shell_exec" in result
        assert "【文件操作】" in result
        assert "read_file" in result

    def test_ungrouped_tools(self):
        """不在分组中的工具归到「其他」"""
        reg = ToolRegistry()

        async def dummy(x: str) -> str:
            return x

        reg.register(
            ToolInfo("custom_tool", "自定义工具", RiskLevel.LOW, dummy, {"type": "object"})
        )
        result = _build_tool_section(reg)
        assert "【其他】" in result
        assert "custom_tool" in result

    def test_risk_level_shown(self):
        """工具描述中包含风险等级"""
        reg = _make_registry_with_tools()
        result = _build_tool_section(reg)
        assert "high" in result  # shell_exec 是 high
        assert "low" in result   # read_file 是 low


class TestBuildEnvSection:
    """OP1.2: 环境上下文注入"""

    def test_contains_os_info(self):
        result = _build_env_section()
        assert "操作系统" in result

    def test_contains_cwd(self):
        result = _build_env_section()
        assert "工作目录" in result

    def test_contains_time(self):
        result = _build_env_section()
        assert "当前时间" in result

    def test_contains_python_version(self):
        result = _build_env_section()
        assert "Python" in result


class TestBuildSystemPrompt:
    """OP1.3 + OP1.4: 行为约束 + 模板化"""

    def test_contains_identity(self):
        reg = ToolRegistry()
        prompt = build_system_prompt(reg)
        assert "MiniClaw" in prompt

    def test_contains_behavior_rules(self):
        reg = ToolRegistry()
        prompt = build_system_prompt(reg)
        assert "行为准则" in prompt
        assert "低风险" in prompt

    def test_contains_env_info(self):
        reg = ToolRegistry()
        prompt = build_system_prompt(reg)
        assert "环境信息" in prompt
        assert "操作系统" in prompt

    def test_contains_tool_section(self):
        reg = _make_registry_with_tools()
        prompt = build_system_prompt(reg)
        assert "可用工具" in prompt
        assert "shell_exec" in prompt


class TestAgentContext:
    def test_init_with_dynamic_system_prompt(self):
        """初始化应包含动态系统提示词"""
        reg = _make_registry_with_tools()
        ctx = AgentContext(tool_registry=reg)
        assert len(ctx.messages) == 1
        assert ctx.messages[0]["role"] == "system"
        content = ctx.messages[0]["content"]
        assert "MiniClaw" in content
        assert "shell_exec" in content
        assert "read_file" in content

    def test_add_user_message(self):
        ctx = AgentContext(tool_registry=ToolRegistry())
        ctx.add_user_message("hello")
        assert ctx.messages[-1]["role"] == "user"
        assert ctx.messages[-1]["content"] == "hello"

    def test_add_assistant_message(self):
        ctx = AgentContext(tool_registry=ToolRegistry())
        ctx.add_assistant_message("hi there")
        assert ctx.messages[-1]["role"] == "assistant"

    def test_add_tool_result(self):
        ctx = AgentContext(tool_registry=ToolRegistry())
        ctx.add_tool_result("call_1", "shell_exec", "output")
        assert ctx.messages[-1]["role"] == "tool"
        assert ctx.messages[-1]["tool_call_id"] == "call_1"

    def test_build_messages(self):
        ctx = AgentContext(tool_registry=ToolRegistry())
        ctx.add_user_message("test")
        msgs = ctx.build_messages()
        assert len(msgs) == 2  # system + user
        # 应该是副本
        assert msgs is not ctx.messages

    def test_get_available_tools(self):
        reg = _make_registry_with_tools()
        ctx = AgentContext(tool_registry=reg)
        tools = ctx.get_available_tools()
        assert len(tools) == 2
        names = {t["function"]["name"] for t in tools}
        assert "shell_exec" in names
        assert "read_file" in names

    def test_clear(self):
        """清空后重新生成动态 prompt"""
        reg = _make_registry_with_tools()
        ctx = AgentContext(tool_registry=reg)
        ctx.add_user_message("hi")
        ctx.current_round = 5
        ctx.clear()
        assert len(ctx.messages) == 1
        assert ctx.current_round == 0
        assert "shell_exec" in ctx.messages[0]["content"]

    def test_max_rounds_default(self):
        ctx = AgentContext(tool_registry=ToolRegistry())
        assert ctx.max_rounds == 10

    def test_system_prompt_has_env_context(self):
        ctx = AgentContext(tool_registry=ToolRegistry())
        content = ctx.messages[0]["content"]
        assert "操作系统" in content
        assert "工作目录" in content
        assert "Python" in content

    def test_system_prompt_has_behavior_constraints(self):
        ctx = AgentContext(tool_registry=ToolRegistry())
        content = ctx.messages[0]["content"]
        assert "低风险" in content
        assert "文件操作前" in content


class TestAgentContextShortTermMemory:
    """OP2.1: ShortTermMemory 集成测试"""

    def test_auto_creates_stm_if_none(self):
        """不传 ShortTermMemory 时自动创建"""
        ctx = AgentContext(tool_registry=ToolRegistry())
        assert ctx.short_term_memory is not None
        assert ctx.short_term_memory.message_count == 1  # system prompt

    def test_uses_injected_stm(self):
        """传入 ShortTermMemory 实例时使用它"""
        stm = ShortTermMemory(max_tokens=16000)
        ctx = AgentContext(tool_registry=ToolRegistry(), short_term_memory=stm)
        assert ctx.short_term_memory is stm
        assert stm.max_tokens == 16000

    def test_messages_delegated_to_stm(self):
        """消息管理委托给 ShortTermMemory"""
        stm = ShortTermMemory()
        ctx = AgentContext(tool_registry=ToolRegistry(), short_term_memory=stm)
        ctx.add_user_message("hello")
        # 消息应该在 stm 中
        assert stm.message_count == 2  # system + user
        assert ctx.messages[-1]["content"] == "hello"

    def test_needs_compression_delegates(self):
        """needs_compression 委托给 ShortTermMemory"""
        stm = ShortTermMemory(max_tokens=100)  # 很小的阈值
        ctx = AgentContext(tool_registry=ToolRegistry(), short_term_memory=stm)
        # 初始应该不需要压缩（只有 system prompt）
        # 添加很多消息使其超过阈值
        for i in range(50):
            ctx.add_user_message(f"这是第 {i} 条非常长的消息内容" * 10)
        assert ctx.needs_compression() is True

    def test_compress_delegates(self):
        """compress 委托给 ShortTermMemory"""
        stm = ShortTermMemory()
        ctx = AgentContext(tool_registry=ToolRegistry(), short_term_memory=stm)
        # 添加足够多的消息
        for i in range(10):
            ctx.add_user_message(f"消息 {i}")
            ctx.add_assistant_message(f"回复 {i}")
        old_count = stm.message_count
        ctx.compress("这是历史摘要")
        # 压缩后消息数应该减少
        assert stm.message_count < old_count

    def test_clear_resets_stm(self):
        """clear 重置 ShortTermMemory"""
        stm = ShortTermMemory()
        ctx = AgentContext(tool_registry=ToolRegistry(), short_term_memory=stm)
        ctx.add_user_message("hello")
        assert stm.message_count == 2
        ctx.clear()
        assert stm.message_count == 1  # 只有 system prompt
        assert stm.messages[0]["role"] == "system"


# ── OP4 辅助函数 ──

def _make_skill_info(
    name: str = "test-skill",
    role: str = "测试角色",
    workflow: str = "1. 步骤一\n2. 步骤二",
    tools: list[str] | None = None,
) -> SkillInfo:
    """创建测试用 SkillInfo"""
    return SkillInfo(
        name=name,
        path=Path("/tmp/skills") / name / "SKILL.md",
        role=role,
        activation_keywords=["测试", "test"],
        available_tools=tools or ["shell_exec"],
        workflow=workflow,
    )


class TestBuildSkillSection:
    """OP4.1: Skill 段构建"""

    def test_contains_role(self):
        skill = _make_skill_info(role="编程助手")
        result = _build_skill_section(skill)
        assert "编程助手" in result

    def test_contains_workflow(self):
        skill = _make_skill_info(workflow="1. 分析需求\n2. 编写代码")
        result = _build_skill_section(skill)
        assert "分析需求" in result
        assert "编写代码" in result

    def test_contains_tools(self):
        skill = _make_skill_info(tools=["shell_exec", "read_file"])
        result = _build_skill_section(skill)
        assert "`shell_exec`" in result
        assert "`read_file`" in result

    def test_empty_fields(self):
        """空字段不会产生内容"""
        skill = SkillInfo(name="empty", path=Path("/tmp"), role="", workflow="")
        result = _build_skill_section(skill)
        assert "角色" not in result
        assert "工作流程" not in result


class TestBuildSystemPromptWithSkill:
    """OP4.1: 系统提示词 + Skill 注入"""

    def test_no_skill_no_section(self):
        """无 Skill 时不包含 Skill 段"""
        reg = ToolRegistry()
        prompt = build_system_prompt(reg, active_skill=None)
        assert "当前 Skill" not in prompt

    def test_with_skill_has_section(self):
        """有 Skill 时包含 Skill 段"""
        reg = ToolRegistry()
        skill = _make_skill_info(name="coder", role="编程助手")
        prompt = build_system_prompt(reg, active_skill=skill)
        assert "## 当前 Skill：coder" in prompt
        assert "编程助手" in prompt

    def test_skill_section_at_end(self):
        """Skill 段在行为准则之后"""
        reg = ToolRegistry()
        skill = _make_skill_info()
        prompt = build_system_prompt(reg, active_skill=skill)
        rules_pos = prompt.index("行为准则")
        skill_pos = prompt.index("当前 Skill")
        assert skill_pos > rules_pos


class TestAgentContextSkillInjection:
    """OP4.1 + OP4.3: Skill 上下文注入和清除"""

    def test_inject_skill_updates_system_prompt(self):
        """inject_skill_context 更新系统提示词"""
        ctx = AgentContext(tool_registry=ToolRegistry())
        skill = _make_skill_info(name="coder", role="编程助手")
        ctx.inject_skill_context(skill)
        system_msg = ctx.messages[0]["content"]
        assert "当前 Skill：coder" in system_msg
        assert "编程助手" in system_msg

    def test_inject_skill_sets_active_skill(self):
        """inject_skill_context 设置 active_skill"""
        ctx = AgentContext(tool_registry=ToolRegistry())
        skill = _make_skill_info(name="coder")
        ctx.inject_skill_context(skill)
        assert ctx.active_skill is not None
        assert ctx.active_skill.name == "coder"

    def test_inject_different_skill_replaces(self):
        """注入不同 Skill 替换之前的"""
        ctx = AgentContext(tool_registry=ToolRegistry())
        skill1 = _make_skill_info(name="coder", role="编程助手")
        skill2 = _make_skill_info(name="shell", role="运维专家")
        ctx.inject_skill_context(skill1)
        ctx.inject_skill_context(skill2)
        assert ctx.active_skill.name == "shell"
        system_msg = ctx.messages[0]["content"]
        assert "运维专家" in system_msg
        assert "编程助手" not in system_msg

    def test_clear_skill_context(self):
        """clear_skill_context 恢复无 Skill 状态"""
        ctx = AgentContext(tool_registry=ToolRegistry())
        skill = _make_skill_info(name="coder", role="编程助手")
        ctx.inject_skill_context(skill)
        assert "当前 Skill" in ctx.messages[0]["content"]
        ctx.clear_skill_context()
        assert ctx.active_skill is None
        assert "当前 Skill" not in ctx.messages[0]["content"]

    def test_clear_skill_context_noop_when_none(self):
        """无活跃 Skill 时 clear_skill_context 是 no-op"""
        ctx = AgentContext(tool_registry=ToolRegistry())
        old_content = ctx.messages[0]["content"]
        ctx.clear_skill_context()  # 不应抛异常
        assert ctx.messages[0]["content"] == old_content

    def test_full_clear_resets_skill(self):
        """clear() 同时清除 Skill 上下文（OP4.3）"""
        ctx = AgentContext(tool_registry=ToolRegistry())
        skill = _make_skill_info(name="coder")
        ctx.inject_skill_context(skill)
        assert ctx.active_skill is not None
        ctx.clear()
        assert ctx.active_skill is None
        assert "当前 Skill" not in ctx.messages[0]["content"]

    def test_inject_preserves_message_count(self):
        """注入 Skill 不增加消息数量（只更新 system prompt）"""
        ctx = AgentContext(tool_registry=ToolRegistry())
        ctx.add_user_message("hello")
        assert len(ctx.messages) == 2  # system + user
        ctx.inject_skill_context(_make_skill_info())
        assert len(ctx.messages) == 2  # 没有新增消息


class TestAgentContextTokenBudget:
    """OP7.1: Token 预算管理测试"""

    def test_estimated_tokens_delegates_to_stm(self):
        """estimated_tokens 委托给 ShortTermMemory"""
        stm = ShortTermMemory(max_tokens=32000)
        ctx = AgentContext(tool_registry=ToolRegistry(), short_term_memory=stm)
        # 两者应该返回相同值
        assert ctx.estimated_tokens == stm.estimated_tokens

    def test_max_context_tokens_delegates_to_stm(self):
        """max_context_tokens 委托给 ShortTermMemory.max_tokens"""
        stm = ShortTermMemory(max_tokens=16000)
        ctx = AgentContext(tool_registry=ToolRegistry(), short_term_memory=stm)
        assert ctx.max_context_tokens == 16000

    def test_token_usage_ratio(self):
        """token_usage_ratio 正确计算使用率"""
        stm = ShortTermMemory(max_tokens=1000)
        ctx = AgentContext(tool_registry=ToolRegistry(), short_term_memory=stm)
        # 初始只有 system prompt，使用率应大于 0
        assert 0 < ctx.token_usage_ratio < 1

    def test_token_usage_ratio_increases_with_messages(self):
        """添加消息后使用率增加"""
        stm = ShortTermMemory(max_tokens=10000)
        ctx = AgentContext(tool_registry=ToolRegistry(), short_term_memory=stm)
        initial_ratio = ctx.token_usage_ratio
        for i in range(20):
            ctx.add_user_message(f"这是一条很长的消息 {i}" * 10)
        assert ctx.token_usage_ratio > initial_ratio

    def test_token_usage_ratio_zero_when_max_zero(self):
        """max_tokens=0 时使用率返回 0（避免除零）"""
        stm = ShortTermMemory(max_tokens=0)
        # 手动设置，绕过 __post_init__ 的自动初始化
        ctx = AgentContext.__new__(AgentContext)
        ctx.tool_registry = ToolRegistry()
        ctx.max_rounds = 10
        ctx.current_round = 0
        ctx.has_images = False
        ctx.last_tool_failed = False
        ctx.short_term_memory = stm
        ctx._active_skill = None
        assert ctx.token_usage_ratio == 0.0

    def test_estimated_tokens_auto_created_stm(self):
        """自动创建的 ShortTermMemory 也能获取 token 统计"""
        ctx = AgentContext(tool_registry=ToolRegistry())
        # 不应抛异常
        assert ctx.estimated_tokens > 0
        assert ctx.max_context_tokens > 0
