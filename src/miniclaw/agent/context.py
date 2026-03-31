"""
MiniClaw - Agent 上下文管理器

管理消息历史、动态工具列表（全局+Skill）、活跃 Skill 上下文。
负责组装传给 LLM 的 messages 和 tools 参数。

对应 PRD：F1 Agent 核心循环
"""

from dataclasses import dataclass, field
from typing import Any

from miniclaw.tools.registry import ToolRegistry

# 消息字典类型
MessageDict = dict[str, Any]

# 系统提示词
SYSTEM_PROMPT = """你是 MiniClaw 🦞，一个运行在用户本地电脑上的 AI 助手。

你的能力：
- 执行 Shell 命令（shell_exec）
- 读写文件（read_file / write_file）
- 搜索网络信息（web_search）
- 发送 HTTP 请求（http_request）

行为准则：
1. 用中文与用户交流
2. 执行操作前先告诉用户你打算做什么
3. 高风险操作会需要用户确认
4. 如果用户拒绝了某个操作，换一种方案或告知用户
5. 保持回答简洁实用"""


@dataclass
class AgentContext:
    """Agent 上下文

    管理一次对话的完整状态：消息历史、工具列表、轮次统计。

    Attributes:
        messages: 消息历史列表
        tool_registry: 工具注册中心
        max_rounds: 最大循环轮次（PRD F1：默认 10 轮）
        current_round: 当前轮次
        has_images: 是否包含图片（影响模型路由）
        last_tool_failed: 上一次工具调用是否失败
    """

    tool_registry: ToolRegistry
    max_rounds: int = 10
    messages: list[MessageDict] = field(default_factory=list)
    current_round: int = 0
    has_images: bool = False
    last_tool_failed: bool = False

    def __post_init__(self) -> None:
        """初始化时注入系统提示词"""
        if not self.messages:
            self.messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    def add_user_message(self, content: str) -> None:
        """添加用户消息"""
        self.messages.append({"role": "user", "content": content})

    def add_assistant_message(self, content: str) -> None:
        """添加 Assistant 消息"""
        self.messages.append({"role": "assistant", "content": content})

    def add_tool_call_message(
        self, tool_calls: list[dict[str, Any]]
    ) -> None:
        """添加带工具调用的 Assistant 消息"""
        self.messages.append({
            "role": "assistant",
            "content": None,
            "tool_calls": tool_calls,
        })

    def add_tool_result(
        self, tool_call_id: str, tool_name: str, result: str
    ) -> None:
        """添加工具执行结果消息"""
        self.messages.append({
            "role": "tool",
            "tool_call_id": tool_call_id,
            "content": result,
        })

    def build_messages(self) -> list[MessageDict]:
        """构建传给 LLM 的消息列表"""
        return list(self.messages)

    def get_available_tools(self) -> list[dict[str, Any]]:
        """获取当前可用的工具 Schema 列表

        工具列表 = 全局内置工具 + 当前激活 Skill 工具（PRD F7 共存规则）
        """
        return self.tool_registry.get_all_schemas()

    def clear(self) -> None:
        """清空上下文（保留系统提示词）"""
        self.messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        self.current_round = 0
        self.has_images = False
        self.last_tool_failed = False
