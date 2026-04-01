# MiniClaw 代码约束规范

> 版本：v1.2 ｜ 日期：2026-04-01 ｜ 作者：avinzhang
>
> 本文档定义 MiniClaw 项目的所有代码规范和约束，所有代码必须遵守。
> 以 [PRD-v1](../requirements/PRD-v1.md) 为唯一真相源。

---

## 1. 铁律（不可违反）

### 1.1 文件行数限制（PRD §2.2 铁律 1）

```
每个 .py 文件 ≤ 500 行（含注释和空行）
```

如果超过 500 行，必须拆分。这不是建议，是硬约束。

### 1.2 核心代码总量（PRD §5.1）

```
src/miniclaw/ 目录下所有 .py 文件总行数 ≤ 3000 行（不含 skills/builtin/ 的 SKILL.md 和测试）
```

### 1.3 外部依赖限制（PRD §5.1）

```
pyproject.toml 中的 dependencies ≤ 10 个包
```

v1 的 10 个依赖已确定（PRD §6 核心依赖列表）：
httpx, playwright, pyautogui, Pillow, rich, prompt-toolkit, pydantic, aiosqlite, pyyaml, click

新增依赖必须替换现有的或有压倒性理由。

---

## 2. Python 代码规范

### 2.1 版本与基础

- **Python 版本**：3.12+（使用新语法特性如 `type` 语句、改进的 f-string）
- **异步优先**：所有 I/O 操作使用 `async/await`，不用同步阻塞调用（PRD §6 asyncio）
- **类型标注**：所有函数签名必须有完整的 type hints（PRD §5.4）

```python
# ✅ 正确
async def chat(
    messages: list[Message],
    tools: list[ToolSchema] | None = None,
    role: str = "default",
) -> LLMResponse:
    ...

# ❌ 错误：缺少类型标注
async def chat(messages, tools=None, role="default"):
    ...
```

### 2.2 命名规范

| 类型 | 规范 | 示例 |
|------|------|------|
| 模块/文件 | snake_case | `model_router.py` |
| 类 | PascalCase | `MacOSController`, `AgentLoop` |
| 函数/方法 | snake_case | `select_model_role()` |
| 常量 | UPPER_SNAKE_CASE | `MAX_ROUNDS = 10` |
| 私有成员 | 单下划线前缀 | `_build_prompt()` |
| 类型别名 | PascalCase | `ToolSchema = dict[str, Any]` |

### 2.3 导入顺序

```python
# 1. 标准库
import asyncio
import sys
from pathlib import Path
from abc import ABC, abstractmethod

# 2. 第三方库
import httpx
from rich.console import Console
from pydantic import BaseModel

# 3. 项目内部
from miniclaw.tools.registry import ToolRegistry
from miniclaw.llm.base import BaseProvider
```

每组之间空一行。通过 ruff 的 isort 规则自动排序。

### 2.4 错误处理

```python
# ✅ 正确：明确捕获特定异常，有有意义的错误信息
try:
    response = await provider.chat(messages, tools)
except httpx.TimeoutException:
    logger.warning("LLM 请求超时，正在重试...")
    response = await provider.chat(messages, tools)
except httpx.HTTPStatusError as e:
    raise LLMProviderError(f"LLM API 返回错误: {e.response.status_code}") from e

# ❌ 错误：裸 except，吞掉异常
try:
    response = await provider.chat(messages, tools)
except:
    pass
```

### 2.5 日志规范（PRD §5.3）

```python
from miniclaw.utils.logging import get_logger

logger = get_logger(__name__)

# 使用结构化日志
logger.info("模型路由", role=role, model=model, round=round_num)
logger.debug("LLM 请求", messages_count=len(messages), tools_count=len(tools))
logger.debug("token_usage", role=role, input_tokens=100, output_tokens=50)
logger.warning("工具执行超时", tool=tool_name, timeout=timeout)
logger.error("LLM 调用失败", error=str(e), provider=provider_name)
```

`--debug` 模式输出完整的 LLM prompt、模型路由决策和 token 计数。

---

## 3. 架构约束

### 3.1 分层依赖规则

```
层级依赖关系（上层可依赖下层，不可反向）：

Channel → Gateway → Agent → Tools / Memory / Skills → LLM / Desktop / Browser

禁止：
- Tools 不能依赖 Agent（唯一特例：screen_analyze 可调用 LLM，见 §3.4）
- LLM 不能依赖 Tools
- Desktop 不能依赖 Browser
- Channel 不能直接依赖 Tools
- Gateway 不能直接依赖 Tools / Memory
```

### 3.2 抽象基类约束

以下模块必须通过抽象基类访问，不能直接依赖具体实现（PRD F5 跨平台设计）：

| 抽象 | 实现 | 说明 |
|------|------|------|
| `ChannelProtocol` | `CLIChannel` | 通道层，v2 加 HTTP/Telegram |
| `BaseProvider` | `OpenAIProvider`, `AnthropicProvider` | LLM 层 |
| `DesktopController` | `MacOSController` | 桌面操控层，v2 加 Windows |

```python
# ✅ 正确：依赖抽象
def __init__(self, controller: DesktopController):
    self.controller = controller

# ❌ 错误：直接依赖具体实现
def __init__(self):
    self.controller = MacOSController()
```

### 3.3 工具注册约束（PRD F3）

所有工具必须通过 `@tool` 装饰器注册，不允许其他方式：

```python
from miniclaw.tools import tool, RiskLevel

@tool(
    description="描述必须清晰，让 LLM 能理解何时该调用",
    risk_level=RiskLevel.HIGH,
)
async def shell_exec(command: str) -> str:
    """函数 docstring 作为详细说明"""
    ...
```

**约束**：
- `description` 必填，不能为空
- `risk_level` 必填，不能省略（PRD F3 安全模型：low/high/critical）
- 工具函数必须是 `async`
- 返回值必须是 `str`（统一格式，方便注入 LLM 上下文）
- 参数类型只能是基础类型：`str`, `int`, `float`, `bool`

### 3.4 复合工具特例（PRD F3 screen_analyze）

```
唯一允许工具内部调用 LLM 的特例：screen_analyze

其他任何工具如需 LLM 能力，必须由 Agent Loop 层协调，不允许在工具内部直接调用 LLM。
```

### 3.5 Skill 工具共存规则（PRD F7）

```
工具列表 = 全局内置工具（始终可用） + 当前激活 Skill 的工具（动态注入）

- 全局内置工具在 ToolRegistry 中始终存在
- Skill 工具仅在 Skill 激活时注入当前轮次的 tools 列表
- 同名冲突：Skill 工具优先覆盖全局工具
- Skill 激活后，其 SKILL.md 中的角色定义和工作流程必须注入 system prompt
```

### 3.6 上下文管理约束

```
所有消息管理必须通过 ShortTermMemory，不允许直接操作 messages 列表。

- AgentContext.messages 委托给 ShortTermMemory 实例管理
- 每轮 AgentLoop 开始前必须检查 needs_compression()
- 压缩使用 default 模型（省钱优先），保留 system prompt + 摘要 + 最近 4 条
- 工具输出超过阈值（默认 8000 字符）必须截断
```

### 3.7 系统提示词约束

```
系统提示词必须动态拼装，包含以下段落：

1. 身份定位（固定文本）
2. 环境信息（OS / CWD / 时间，每次动态生成）
3. 完整工具列表（从 ToolRegistry 自动生成，按能力域分组）
4. 行为准则（固定文本）
5. 活跃 Skill 上下文（可选，Skill 激活时注入）

禁止：
- 在系统提示词中硬编码工具列表（必须从注册中心动态获取）
- 遗漏任何已注册工具的描述
```

---

## 4. 注释规范

### 4.1 语言（PRD §5.4）

- **代码注释**：中文（本项目本身是教学材料）
- **docstring**：中文
- **变量/函数名**：英文

### 4.2 文件头注释

每个 `.py` 文件开头必须有模块说明：

```python
"""
MiniClaw - Agent 主循环

实现 ReAct（Reasoning + Acting）模式的 Agent 执行引擎。
每一轮循环：组装上下文 → 调用 LLM → 解析响应 → 执行工具 → 注入结果。

对应 PRD：F1 Agent 核心循环
参考：OpenClaw 的 Agent Runtime 设计
"""
```

### 4.3 关键逻辑注释

对于核心逻辑，必须有 "为什么" 的注释，而不只是 "做什么"：

```python
# ✅ 正确：解释 WHY
# 截图后等待 500ms 再分析，因为窗口切换动画需要时间完成
await asyncio.sleep(0.5)

# ❌ 错误：只说 WHAT（代码本身已经表达了）
# 等待 500 毫秒
await asyncio.sleep(0.5)
```

---

## 5. 配置约束（PRD F9 / §5.2）

### 5.1 敏感信息

```
API Key、密码等敏感信息：
  ✅ 通过环境变量：${DEEPSEEK_API_KEY}
  ✅ 写在 .env 文件中（已在 .gitignore）
  ❌ 绝不硬编码在源码中
  ❌ 绝不提交到 Git
```

### 5.2 配置定义

所有配置项必须通过 Pydantic Settings 定义，带类型和默认值：

```python
class LLMRoleConfig(BaseModel):
    """单个 LLM 角色的配置（PRD F2 四模型角色）"""
    provider: str = "openai_compatible"
    base_url: str = "https://api.deepseek.com/v1"
    api_key: str  # 必填，无默认值
    model: str = "deepseek-chat"
    temperature: float = 0.7
    max_tokens: int = 4096
```

配置文件位置：`~/.miniclaw/config.yaml`（PRD F9 完整配置示例）。

---

## 6. 测试约束

### 6.1 测试文件结构

```
tests/
├── conftest.py              # 公共 fixtures
├── test_agent/
│   ├── test_loop.py
│   └── test_model_router.py
├── test_llm/
│   ├── test_openai_provider.py
│   └── test_anthropic_provider.py
├── test_tools/
│   ├── test_registry.py
│   └── test_executor.py
├── test_gateway/
│   └── test_router.py
└── test_desktop/
    └── test_macos.py
```

### 6.2 测试规范

- 每个模块至少有对应的测试文件
- 测试函数名以 `test_` 开头，描述行为而非实现
- 使用 `pytest-asyncio` 测试异步代码
- 外部依赖（LLM API、浏览器）使用 mock

```python
# ✅ 正确：测试行为
async def test_agent_loop_calls_tool_when_llm_requests(): ...
async def test_model_router_selects_reasoner_for_images(): ...
async def test_tool_executor_returns_rejection_when_user_denies(): ...
async def test_gateway_creates_session_for_new_channel(): ...

# ❌ 错误：测试实现细节
async def test_internal_state_changes(): ...
```

---

## 7. Git 规范

### 7.1 Commit Message

格式：`<type>(<scope>): <description>`

```
feat(agent): 实现 ReAct Agent Loop 主循环
feat(gateway): 实现轻量直通消息网关
fix(llm): 修复 Anthropic tool_use 响应解析
refactor(tools): 将工具注册逻辑抽取为 ToolRegistry 类
docs(readme): 更新快速开始指南
test(desktop): 添加 MacOSController 截屏测试
chore: 更新依赖版本
```

**type 取值**：
- `feat`：新功能
- `fix`：修复 bug
- `refactor`：重构（不改变行为）
- `docs`：文档变更
- `test`：测试
- `chore`：构建/工具/依赖

### 7.2 分支策略

```
main         ← 稳定版本，可发布
└── dev      ← 开发分支
    ├── feat/agent-loop
    ├── feat/gateway
    ├── feat/browser-control
    └── fix/llm-timeout
```

---

## 8. 文档约束

### 8.1 README 同步规则

```
⚠️ 铁律：每次重大变动后必须同步更新 README.md

触发条件：
- 新增/删除功能模块
- 架构调整
- 技术选型变更
- 里程碑完成
- 配置格式变更
```

### 8.2 文档目录结构

```
docs/
├── architecture/    # 技术架构（系统设计、模块关系、数据流）
├── conventions/     # 代码规范（本文档）
├── requirements/    # 需求文档（PRD、设计决策）
└── tasks/           # 开发任务（待办、进度追踪）
```

### 8.3 PRD 追溯要求

架构文档和代码中的关键设计，必须注明对应的 PRD 需求编号（F1-F9 / §x.x），方便追溯。

---

## 9. 工具链

### 9.1 必须配置的工具

| 工具 | 用途 | 配置 |
|------|------|------|
| **ruff** | Lint + Format | `pyproject.toml` 中配置 |
| **mypy** | 类型检查 | strict mode |
| **pytest** | 测试 | pytest-asyncio |
| **uv** | 包管理 | 替代 pip/poetry |

### 9.2 pyproject.toml 中的 ruff 配置

```toml
[tool.ruff]
target-version = "py312"
line-length = 100

[tool.ruff.lint]
select = [
    "E",   # pycodestyle errors
    "W",   # pycodestyle warnings
    "F",   # pyflakes
    "I",   # isort
    "N",   # pep8-naming
    "UP",  # pyupgrade
    "B",   # flake8-bugbear
    "SIM", # flake8-simplify
    "TCH", # flake8-type-checking
]

[tool.mypy]
python_version = "3.12"
strict = true
```
