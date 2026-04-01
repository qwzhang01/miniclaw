"""
MiniClaw - Agent 上下文管理器

管理消息历史、动态工具列表（全局+Skill）、活跃 Skill 上下文。
负责组装传给 LLM 的 messages 和 tools 参数。
支持动态系统提示词（OP1: 工具描述 + 环境上下文 + 行为约束 + 模板化）。

对应 PRD：F1 Agent 核心循环
"""

from __future__ import annotations

import os
import platform
import sys
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Any

from miniclaw.tools.registry import ToolRegistry

if TYPE_CHECKING:
    from miniclaw.memory.short_term import ShortTermMemory
    from miniclaw.skills.loader import SkillInfo

# 消息字典类型
MessageDict = dict[str, Any]

# ── 工具能力域分组（OP1.1：按能力域分组描述全部工具） ──

_TOOL_GROUPS: dict[str, list[str]] = {
    "命令执行": ["shell_exec"],
    "文件操作": ["read_file", "write_file"],
    "网络": ["web_search", "http_request"],
    "浏览器": ["browser_open", "browser_action", "page_screenshot"],
    "桌面操控": [
        "screen_capture", "screen_analyze",
        "mouse_click", "keyboard_type", "list_windows",
    ],
}


def _build_tool_section(registry: ToolRegistry) -> str:
    """从 ToolRegistry 动态生成工具描述段（OP1.1）

    按能力域分组列出每个工具的名称、风险等级和简要说明。
    如果 registry 中有不在分组中的工具（如 Skill 工具），追加到「其他」组。
    """
    all_tools = registry.get_all()
    grouped_names: set[str] = set()
    sections: list[str] = []

    for group_name, tool_names in _TOOL_GROUPS.items():
        items: list[str] = []
        for name in tool_names:
            info = all_tools.get(name)
            if info:
                items.append(
                    f"  - {info.name}（{info.risk_level.value}）：{info.description}"
                )
                grouped_names.add(name)
        if items:
            sections.append(f"【{group_name}】\n" + "\n".join(items))

    # 追加未分组工具（Skill 动态注入等）
    ungrouped = [t for n, t in all_tools.items() if n not in grouped_names]
    if ungrouped:
        items = [
            f"  - {t.name}（{t.risk_level.value}）：{t.description}"
            for t in ungrouped
        ]
        sections.append("【其他】\n" + "\n".join(items))

    return "\n".join(sections) if sections else "（暂无可用工具）"


def _build_env_section() -> str:
    """动态生成环境上下文段（OP1.2）"""
    return (
        f"- 操作系统：{platform.system()} {platform.release()}\n"
        f"- 工作目录：{os.getcwd()}\n"
        f"- 当前时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"- Python：{sys.version.split()[0]}"
    )


# ── 行为约束（OP1.3） ──

_BEHAVIOR_RULES = """\
1. 用中文与用户交流
2. 执行操作前先告诉用户你打算做什么
3. 高风险操作会需要用户确认，critical 操作需要二次确认
4. 如果用户拒绝了某个操作，换一种方案或告知用户
5. 优先使用低风险（low）工具；能用 read_file 解决的不要 shell_exec
6. 文件操作前先确认路径是否存在，避免误覆盖
7. 大文件先分段读取（head/tail），不要一次性读取全部内容
8. 保持回答简洁实用，避免冗长的解释"""


def _build_skill_section(skill_info: "SkillInfo") -> str:
    """将 SkillInfo 格式化为系统提示词的 Skill 段（OP4.1）

    包含角色定义、工作流程和可用工具说明。
    """
    parts: list[str] = []
    if skill_info.role:
        parts.append(f"**角色**：{skill_info.role}")
    if skill_info.workflow:
        parts.append(f"**工作流程**：\n{skill_info.workflow}")
    if skill_info.available_tools:
        tools_str = "、".join(f"`{t}`" for t in skill_info.available_tools)
        parts.append(f"**Skill 工具**：{tools_str}")
    return "\n\n".join(parts)


def build_system_prompt(
    registry: ToolRegistry,
    active_skill: "SkillInfo | None" = None,
) -> str:
    """组装完整的系统提示词（OP1.4 模板化 + OP4.1 Skill 注入）

    结构：身份 → 环境 → 工具清单 → 行为准则 → [当前 Skill]
    """
    tool_section = _build_tool_section(registry)
    env_section = _build_env_section()

    prompt = (
        "你是 MiniClaw 🦞，一个运行在用户本地电脑上的 AI 助手。\n\n"
        "## 环境信息\n"
        f"{env_section}\n\n"
        "## 可用工具\n"
        f"{tool_section}\n\n"
        "## 行为准则\n"
        f"{_BEHAVIOR_RULES}"
    )

    # OP4.1: 追加激活的 Skill 上下文
    if active_skill is not None:
        skill_section = _build_skill_section(active_skill)
        prompt += f"\n\n## 当前 Skill：{active_skill.name}\n{skill_section}"

    return prompt


@dataclass
class AgentContext:
    """Agent 上下文

    管理一次对话的完整状态：消息历史、工具列表、轮次统计。
    消息存储委托给 ShortTermMemory（OP2.1）。

    Attributes:
        tool_registry: 工具注册中心
        max_rounds: 最大循环轮次（PRD F1：默认 10 轮）
        current_round: 当前轮次
        has_images: 是否包含图片（影响模型路由）
        last_tool_failed: 上一次工具调用是否失败
        short_term_memory: 短期记忆实例（OP2.1 消息管理委托）
    """

    tool_registry: ToolRegistry
    max_rounds: int = 10
    current_round: int = 0
    has_images: bool = False
    last_tool_failed: bool = False
    short_term_memory: "ShortTermMemory | None" = None
    _active_skill: "SkillInfo | None" = None

    def __post_init__(self) -> None:
        """初始化：创建 ShortTermMemory 并注入系统提示词（OP1.4 + OP2.1）"""
        if self.short_term_memory is None:
            from miniclaw.memory.short_term import ShortTermMemory
            self.short_term_memory = ShortTermMemory()
        # 如果记忆为空，注入系统提示词
        if self.short_term_memory.message_count == 0:
            prompt = build_system_prompt(self.tool_registry)
            self.short_term_memory.add({"role": "system", "content": prompt})

    @property
    def messages(self) -> list[MessageDict]:
        """消息列表的只读属性（兼容旧接口）"""
        assert self.short_term_memory is not None
        return self.short_term_memory.messages

    def add_user_message(self, content: str) -> None:
        """添加用户消息"""
        assert self.short_term_memory is not None
        self.short_term_memory.add({"role": "user", "content": content})

    def add_assistant_message(self, content: str) -> None:
        """添加 Assistant 消息"""
        assert self.short_term_memory is not None
        self.short_term_memory.add({"role": "assistant", "content": content})

    def add_tool_call_message(
        self, tool_calls: list[dict[str, Any]]
    ) -> None:
        """添加带工具调用的 Assistant 消息"""
        assert self.short_term_memory is not None
        self.short_term_memory.add({
            "role": "assistant",
            "content": None,
            "tool_calls": tool_calls,
        })

    def add_tool_result(
        self, tool_call_id: str, tool_name: str, result: str
    ) -> None:
        """添加工具执行结果消息"""
        assert self.short_term_memory is not None
        self.short_term_memory.add({
            "role": "tool",
            "tool_call_id": tool_call_id,
            "content": result,
        })

    @property
    def estimated_tokens(self) -> int:
        """当前上下文估算 token 数（OP7.1 委托给 ShortTermMemory）"""
        assert self.short_term_memory is not None
        return self.short_term_memory.estimated_tokens

    @property
    def max_context_tokens(self) -> int:
        """上下文窗口 token 上限（OP7.1 委托给 ShortTermMemory）"""
        assert self.short_term_memory is not None
        return self.short_term_memory.max_tokens

    @property
    def token_usage_ratio(self) -> float:
        """Token 使用率（已用/上限）（OP7.1）"""
        max_tokens = self.max_context_tokens
        if max_tokens <= 0:
            return 0.0
        return self.estimated_tokens / max_tokens

    def needs_compression(self) -> bool:
        """判断是否需要压缩上下文（OP2.1 委托给 ShortTermMemory）"""
        assert self.short_term_memory is not None
        return self.short_term_memory.needs_compression()

    def compress(self, summary: str) -> None:
        """压缩上下文（OP2.1 委托给 ShortTermMemory）"""
        assert self.short_term_memory is not None
        self.short_term_memory.compress(summary)

    def build_messages(self) -> list[MessageDict]:
        """构建传给 LLM 的消息列表"""
        assert self.short_term_memory is not None
        return self.short_term_memory.get_messages()

    def get_available_tools(self) -> list[dict[str, Any]]:
        """获取当前可用的工具 Schema 列表

        工具列表 = 全局内置工具 + 当前激活 Skill 工具（PRD F7 共存规则）
        """
        return self.tool_registry.get_all_schemas()

    def clear(self) -> None:
        """清空上下文（保留系统提示词，清除 Skill 上下文）（OP4.3）"""
        assert self.short_term_memory is not None
        self.short_term_memory.clear()
        self._active_skill = None  # OP4.3: 清除活跃 Skill
        prompt = build_system_prompt(self.tool_registry)
        self.short_term_memory.add({"role": "system", "content": prompt})
        self.current_round = 0
        self.has_images = False
        self.last_tool_failed = False

    @property
    def active_skill(self) -> "SkillInfo | None":
        """当前激活的 Skill（只读）"""
        return self._active_skill

    def inject_skill_context(self, skill_info: "SkillInfo") -> None:
        """注入 Skill 上下文到系统提示词（OP4.1）

        将 Skill 的角色定义、工作流程和工具说明追加到系统提示词末尾。
        如果已有活跃 Skill，先替换为新 Skill。

        Args:
            skill_info: 要注入的 SkillInfo 实例
        """
        assert self.short_term_memory is not None
        self._active_skill = skill_info
        # 重建系统提示词（包含 Skill 段）
        prompt = build_system_prompt(self.tool_registry, active_skill=skill_info)
        self.short_term_memory.update_system_prompt(prompt)

    def clear_skill_context(self) -> None:
        """清除当前 Skill 上下文（OP4.3）

        恢复系统提示词到无 Skill 状态。
        """
        if self._active_skill is None:
            return
        assert self.short_term_memory is not None
        self._active_skill = None
        prompt = build_system_prompt(self.tool_registry)
        self.short_term_memory.update_system_prompt(prompt)
