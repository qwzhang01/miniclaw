# MiniClaw 技术架构设计

> 版本：v1.1 ｜ 日期：2026-03-29 ｜ 作者：avinzhang
>
> 本文档以 [PRD-v1](../requirements/PRD-v1.md) 为唯一真相源，所有设计决策均可追溯到 PRD。

---

## 1. 架构总览

MiniClaw 采用 **分层架构**，借鉴 OpenClaw 的 Gateway → Agent → Skill 设计，简化为单进程模型。

```
┌──────────────────────────────────────────────────────────┐
│                       MiniClaw                           │
│                                                          │
│  ┌─────────────────────────────────────────────────────┐ │
│  │                   Channel Layer                     │ │
│  │  ┌─────────┐  ┌─────────────┐                      │ │
│  │  │   CLI   │  │  HTTP (v2)  │   ← 可扩展更多通道    │ │
│  │  └────┬────┘  └──────┬──────┘                      │ │
│  │       └──────┬───────┘                              │ │
│  │              ▼                                      │ │
│  │  ┌───────────────────┐                              │ │
│  │  │ Channel Protocol  │  ← 通道抽象接口              │ │
│  │  └────────┬──────────┘                              │ │
│  └───────────┼─────────────────────────────────────────┘ │
│              ▼                                           │
│  ┌───────────────────────────────┐                       │
│  │          Gateway              │                       │
│  │  消息路由 + 会话管理 + 消息标准化│                       │
│  │  v1: 单用户轻量直通模式         │                       │
│  └────────────┬──────────────────┘                       │
│               ▼                                          │
│  ┌─────────────────────────────────────────────────────┐ │
│  │                  Agent Runtime                      │ │
│  │                                                     │ │
│  │  ┌───────────┐  ┌──────────────┐  ┌──────────────┐ │ │
│  │  │   Agent   │  │   Model      │  │   Context     │ │ │
│  │  │   Loop    │  │   Router     │  │   Manager     │ │ │
│  │  │  (ReAct)  │  │ (四模型调度)  │  │  (上下文组装)  │ │ │
│  │  └─────┬─────┘  └──────────────┘  └──────────────┘ │ │
│  │        │                                            │ │
│  │  ┌─────┼────────────────────────┐                   │ │
│  │  ▼     ▼           ▼           ▼                    │ │
│  │ ┌────────┐  ┌──────────┐  ┌─────────┐              │ │
│  │ │ Tools  │  │  Memory  │  │  Skills │              │ │
│  │ └───┬────┘  └──────────┘  └─────────┘              │ │
│  │     │                                               │ │
│  └─────┼───────────────────────────────────────────────┘ │
│        │                                                 │
│  ┌─────┼───────────────────────────────────────────────┐ │
│  │     ▼        Capability Layer                       │ │
│  │  ┌────────┐  ┌───────────┐  ┌────────────────────┐ │ │
│  │  │ Shell  │  │  Browser  │  │  Desktop Control   │ │ │
│  │  │        │  │(Playwright)│  │  (跨平台抽象层)     │ │ │
│  │  │ sub-   │  │           │  │  ┌──────────────┐  │ │ │
│  │  │ process│  │ • 导航    │  │  │MacOSController│  │ │ │
│  │  │        │  │ • 点击    │  │  │(v1 实现)      │  │ │ │
│  │  │        │  │ • 截图    │  │  ├──────────────┤  │ │ │
│  │  │        │  │ • 抓取    │  │  │WinController │  │ │ │
│  │  │        │  │           │  │  │(v2 预留)      │  │ │ │
│  │  └────────┘  └───────────┘  │  └──────────────┘  │ │ │
│  │                             └────────────────────┘ │ │
│  └─────────────────────────────────────────────────────┘ │
│                                                          │
│  ┌─────────────────────────────────────────────────────┐ │
│  │              LLM Provider Layer                     │ │
│  │                                                     │ │
│  │  ┌────────────────┐   ┌────────────────────────┐   │ │
│  │  │ BaseProvider   │   │ Model Role Registry    │   │ │
│  │  │ (抽象基类)      │   │                        │   │ │
│  │  ├────────────────┤   │ default  → DeepSeek    │   │ │
│  │  │ OpenAIProvider │   │ planner  → Claude      │   │ │
│  │  │ AnthropicProv. │   │ reasoner → GPT-4o      │   │ │
│  │  └────────────────┘   │ maker    → Claude      │   │ │
│  │                       └────────────────────────┘   │ │
│  └─────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────┘
```

---

## 2. 模块划分与职责

### 2.1 源码目录结构

```
src/miniclaw/
├── __init__.py
├── __main__.py              # 入口：python -m miniclaw
├── cli.py                   # CLI 命令定义（click）
│
├── channels/                # 通道层（PRD F6）
│   ├── __init__.py
│   ├── base.py              # ChannelProtocol 抽象接口
│   └── cli_channel.py       # CLI 通道实现（Rich + Prompt Toolkit）
│
├── gateway/                 # 网关层（PRD F6.5）
│   ├── __init__.py
│   ├── router.py            # 消息路由 + 消息标准化
│   └── session.py           # 会话管理（Session 创建/查找/恢复）
│
├── agent/                   # Agent 运行时（PRD F1）
│   ├── __init__.py
│   ├── loop.py              # Agent 主循环（ReAct）★ 核心
│   ├── context.py           # 上下文组装与管理（含动态工具列表）
│   └── model_router.py      # 四模型角色路由 ★ 核心（PRD F2）
│
├── llm/                     # LLM 提供方（PRD F2）
│   ├── __init__.py
│   ├── base.py              # BaseProvider 抽象接口
│   ├── openai_provider.py   # OpenAI 兼容 API（含 DeepSeek/Qwen/Ollama）
│   └── anthropic_provider.py # Anthropic Claude API
│
├── tools/                   # 工具系统（PRD F3）
│   ├── __init__.py
│   ├── registry.py          # 工具注册中心 + @tool 装饰器
│   ├── executor.py          # 工具执行引擎（参数校验、超时、安全审批、用户拒绝处理）
│   └── builtin/             # 内置工具（PRD F3 表格中的 11 个）
│       ├── __init__.py
│       ├── shell.py         # shell_exec
│       ├── file.py          # read_file, write_file
│       ├── web.py           # web_search（DuckDuckGo）, http_request
│       ├── browser.py       # browser_open, browser_action
│       └── desktop.py       # screen_capture, screen_analyze（复合工具）,
│                            # mouse_click, keyboard_type
│
├── desktop/                 # 桌面操控（PRD F5，跨平台抽象）
│   ├── __init__.py
│   ├── base.py              # DesktopController 抽象基类
│   ├── macos.py             # MacOSController（v1 实现：pyautogui + osascript + Quartz）
│   └── factory.py           # 平台检测 + Controller 工厂
│
├── browser/                 # 浏览器操控（PRD F4）
│   ├── __init__.py
│   └── playwright_driver.py # Playwright 封装（有头/无头可配置）
│
├── memory/                  # 记忆系统（PRD F8）
│   ├── __init__.py
│   ├── short_term.py        # 短期记忆（会话内，内存）
│   └── long_term.py         # 长期记忆（SQLite FTS5，v1 不做向量检索）
│
├── skills/                  # Skill 技能系统（PRD F7）
│   ├── __init__.py
│   ├── loader.py            # Skill 加载器（扫描目录、解析 SKILL.md、/reload 重载）
│   └── matcher.py           # Skill 匹配器（关键词 + LLM 意图判断）
│
├── config/                  # 配置管理（PRD F9）
│   ├── __init__.py
│   ├── settings.py          # Pydantic Settings 定义（四模型角色 + 安全 + 浏览器 + 日志）
│   └── wizard.py            # 首次运行配置引导
│
└── utils/                   # 工具函数
    ├── __init__.py
    ├── logging.py            # 结构化日志（info/debug/error，debug 输出完整 prompt）
    └── tokens.py             # Token 计数（按角色统计，debug 级别日志输出）
```

### 2.2 模块职责一览

| 模块 | 文件数 | 预估行数 | 对应 PRD | 职责 |
|------|--------|---------|---------|------|
| **channels** | 2 | ~300 | F6 | 通道抽象 + CLI 实现（9 个特殊命令） |
| **gateway** | 2 | ~200 | F6.5 | 消息路由 + 会话管理 + 消息标准化（v1 轻量直通） |
| **agent** | 3 | ~500 | F1, F2 | Agent Loop + 上下文 + 四模型路由（核心） |
| **llm** | 3 | ~400 | F2 | LLM 调用封装（OpenAI 兼容 + Anthropic），自己用 httpx 封装 |
| **tools** | 7 | ~600 | F3 | 工具注册/执行 + 11 个内置工具 + 安全审批 + 用户拒绝处理 |
| **desktop** | 3 | ~300 | F5 | 桌面操控抽象 + macOS 实现（v2 加 Windows 只需新增一个文件） |
| **browser** | 1 | ~200 | F4 | Playwright 封装（默认有头模式） |
| **memory** | 2 | ~250 | F8 | 短期（内存）+ 长期（SQLite FTS5），摘要压缩用 default 模型 |
| **skills** | 2 | ~200 | F7 | Skill 加载 + 匹配，/reload 手动重载 |
| **config** | 2 | ~150 | F9 | 配置管理 + 首次运行引导 |
| **utils** | 2 | ~100 | — | 日志 + Token 计数 |
| **合计** | ~29 | **~3200** | | 每个文件 ≤ 500 行 |

---

## 3. 核心流程

### 3.1 Agent Loop（ReAct 模式）— 对应 PRD F1

这是整个系统的心脏，伪代码如下：

```python
async def run_agent_loop(user_input: str, context: AgentContext) -> str:
    """Agent 主循环 —— MiniClaw 最核心的 50 行代码"""

    # 1. 将用户输入加入上下文
    context.add_message(role="user", content=user_input)

    for round_num in range(context.max_rounds):  # 默认 10 轮
        # 2. 选择本轮使用的模型角色
        role = model_router.select_role(context)

        # 3. 组装 prompt + 动态工具列表
        #    工具列表 = 全局内置工具 + 当前激活 Skill 的工具（PRD F7 共存规则）
        messages = context.build_messages()
        tools = context.get_available_tools()

        # 4. 调用 LLM
        response = await llm.chat(messages, tools, role=role)

        # 5. Token 计数（PRD F2：按角色统计，debug 级别日志）
        logger.debug("token_usage", role=role, input=response.input_tokens, output=response.output_tokens)

        # 6. 解析响应
        if response.has_tool_calls:
            # 6a. 有工具调用 → 安全审批 → 执行/拒绝 → 结果注入上下文
            for tool_call in response.tool_calls:
                result = await tool_executor.execute(tool_call)
                # result 可能是：成功结果 / 执行失败 / 用户拒绝（PRD F3）
                context.add_tool_result(tool_call, result)
        else:
            # 6b. 纯文本回复 → 结束循环
            context.add_message(role="assistant", content=response.text)
            return response.text

    return "达到最大轮次限制，请简化你的请求。"
```

### 3.2 四模型路由流程 — 对应 PRD F2

```
                    用户输入
                       │
                       ▼
              ┌─────────────────┐
              │  分析任务上下文   │
              └────────┬────────┘
                       │
          ┌────────────┼────────────┬─────────────┐
          ▼            ▼            ▼             ▼
     有截图/调试   第1轮+复杂任务  需要产出代码/文档  其他情况
          │            │            │             │
          ▼            ▼            ▼             ▼
      [reasoner]   [planner]    [maker]      [default]
      视觉理解     任务拆解      高质量生成     省钱快速
```

路由判断优先级（代码中的 if-elif 顺序）：
1. 有图片输入 → `reasoner`（需要多模态能力）
2. 第一轮 + 复杂任务 → `planner`（先规划再执行）
3. 工具调用失败需重试 → `reasoner`（需要分析错误）
4. 需要生成代码/文档/报告 → `maker`（高质量产出）
5. 其他情况 → `default`（省钱）

fallback 规则：任何角色模型不可用时，降级到 `default`。

### 3.3 工具执行流程 — 对应 PRD F3

```
Agent 请求调用工具
       │
       ▼
┌──────────────┐
│ 参数校验      │ → 失败 → ToolResult(success=False, "参数校验失败")
└──────┬───────┘
       ▼
┌──────────────┐
│ 安全审批      │
│              │
│ low → 直接执行│
│ high → 用户确认│ → 拒绝 → ToolResult(success=False, "用户拒绝执行此操作")
│ critical → 二次│ → 拒绝 → ToolResult(success=False, "用户拒绝执行此操作")
└──────┬───────┘
       │ 审批通过
       ▼
┌──────────────┐
│ 执行工具      │ → 超时 → ToolResult(success=False, "执行超时")
│              │ → 异常 → ToolResult(success=False, 错误信息)
└──────┬───────┘
       │ 执行成功
       ▼
┌──────────────┐
│ 格式化结果    │ → ToolResult(success=True, 输出内容)
└──────┬───────┘
       ▼
  返回给 Agent Loop（所有路径都不中断循环，Agent 自行决策下一步）
```

### 3.4 Gateway 消息流 — 对应 PRD F6.5

```
用户在 CLI 输入 → CLIChannel.receive()
    │
    ▼
Gateway.handle_message(raw_input, channel)
    │
    ├── 1. get_or_create_session() → Session
    ├── 2. 消息标准化 → Message(role="user", content=...)
    ├── 3. AgentLoop.run(message, session.context)
    │      └── [多轮 ReAct 循环]
    ├── 4. channel.send(response) → Rich 格式化输出
    │
    ▼
Memory.save() → 保存对话历史到 SQLite
```

### 3.5 桌面操控流程（Computer Use）— 对应 PRD F5

```
用户："帮我看看企微有没有消息"
       │
       ▼
Agent Loop [reasoner] 决定需要截屏
       │
       ▼
调用 screen_capture 工具（risk=low，自动执行）
       │
       ▼
DesktopController.capture_screen()
  └── MacOSController 实际执行（pyautogui/Quartz）
       │
       ▼
截图 bytes → Base64 编码
       │
       ▼
调用 screen_analyze 工具（复合工具，risk=low）
  └── 截屏 → 内部调用 reasoner 模型（唯一允许工具内调 LLM 的特例）
       │
       ▼
LLM 返回屏幕内容描述 + 元素位置
       │
       ▼
Agent 决策："需要点击企微图标"
       │
       ▼
调用 mouse_click(x, y)（risk=high）→ 安全审批 → 用户确认/拒绝
       │
       ▼
再次截屏验证结果
```

### 3.6 Skill 工具共存机制 — 对应 PRD F7

```
Agent 每轮可用的工具列表 = 全局内置工具（始终可用）
                        + 当前激活 Skill 的工具（动态注入）

规则：
1. 全局内置工具（11 个，PRD F3 定义）：始终在 tools 列表中
2. Skill 工具（tools.py 定义）：仅在该 Skill 被匹配激活时注入
3. 同名冲突：Skill 工具优先覆盖全局工具
4. 对 LLM 的影响：每轮 chat() 传入的 tools 参数是动态组装的
```

### 3.7 一次完整交互的数据流

```
用户在 CLI 输入 "帮我搜索 Python Web 框架"
    │
    ▼
CLIChannel.receive() → Message(role="user", content="帮我搜索...")
    │
    ▼
Gateway.handle_message() → 找到/创建 Session
    │
    ▼
AgentLoop.run(message, session.context)
    │
    ├─ Round 1: ModelRouter → "planner"
    │  └─ LLM(planner): "需要分三步：1.搜索 2.分析 3.整理"
    │     └─ 返回 tool_call: web_search("Python Web 框架 2026")
    │
    ├─ Round 2: ToolExecutor.execute(web_search, ...)
    │  └─ risk_level=low → 自动执行（DuckDuckGo）→ 返回搜索结果
    │
    ├─ Round 3: ModelRouter → "reasoner"
    │  └─ LLM(reasoner): 分析搜索结果，提取关键信息
    │     └─ 返回 tool_call: browser_open("https://...")
    │
    ├─ Round 4: ToolExecutor.execute(browser_open, ...)
    │  └─ risk_level=high → 用户确认 → 执行 → 返回页面内容
    │
    ├─ Round 5: ModelRouter → "maker"
    │  └─ LLM(maker): 生成最终的 Markdown 对比报告
    │     └─ 返回纯文本（结束循环）
    │
    ▼
CLIChannel.send() → Rich 格式化输出到终端
    │
    ▼
Memory.save() → 保存对话历史到 SQLite
```

---

## 4. 关键设计决策

### 4.1 单进程 vs 分布式

**决策**：单进程（PRD §2.1）

OpenClaw 用 Gateway + Nodes 分布式架构，但对 MiniClaw 来说过度设计。单进程的好处：
- 部署简单：`pip install` + 一行命令
- 调试简单：所有状态在一个进程内
- 对学习者更友好：代码流程清晰

### 4.2 自己封装 LLM vs 用三方库

**决策**：自己用 httpx 封装（PRD F2 "为什么不用 LiteLLM / openai SDK"）

```python
# 大约 400 行代码覆盖：
# - OpenAI 兼容 API（chat + stream + tool_use）
# - Anthropic API（tool_use 协议差异处理）
# - 四角色路由 + 自动 fallback
# - 重试 + fallback
# - Token 计数（按角色，debug 日志）
```

### 4.3 跨平台抽象策略

**决策**：抽象基类 + 工厂模式（PRD F5 / Q2）

```python
# desktop/factory.py
def create_controller() -> DesktopController:
    if sys.platform == "darwin":
        return MacOSController()
    elif sys.platform == "win32":
        raise NotImplementedError("Windows support coming in v2")
    else:
        raise NotImplementedError(f"Unsupported platform: {sys.platform}")
```

v2 加 Windows 只需：1. 新增 `desktop/windows.py` → 2. 修改 `factory.py` 加一个 `elif` → 3. 不改任何其他代码。

### 4.4 Skill 加载策略

**决策**：目录扫描 + Markdown 解析，手动 `/reload` 命令重载（PRD F7）

```
加载顺序：
1. 内置 Skills（src/miniclaw/skills/builtin/）
2. 全局 Skills（~/.miniclaw/skills/）
3. 项目 Skills（./skills/）

后加载的覆盖先加载的（允许用户覆盖内置 Skill）
v1 不做文件监听热加载，通过 /reload 命令手动重载
```

### 4.5 复合工具模式（screen_analyze 特例）

**决策**：允许特定工具内部调用 LLM（PRD F3 screen_analyze 说明）

`screen_analyze` 是一个"复合工具"——它在执行过程中需要调用 reasoner 模型来理解截图内容。这违反了"工具层不应依赖 LLM 层"的常规分层规则，但作为 **明确标注的设计特例** 存在：

```python
# tools/builtin/desktop.py
@tool(description="截屏并分析内容", risk_level="low")
async def screen_analyze(region: str = "full") -> str:
    """复合工具：截屏 → 调用 reasoner LLM 分析 → 返回文字描述"""
    screenshot = await desktop_controller.capture_screen(region)
    # 特例：工具内部调用 LLM（仅此一处）
    description = await llm.chat(
        messages=[{"role": "user", "content": "描述截图中的内容", "images": [screenshot]}],
        role="reasoner"
    )
    return description
```

**约束**：只有 `screen_analyze` 允许这样做。其他工具如需 LLM 能力，应由 Agent Loop 层协调。

### 4.6 用户拒绝工具执行的处理

**决策**：拒绝 = 工具返回错误，不中断循环（PRD F3 用户拒绝流程）

```python
# tools/executor.py
async def execute(self, tool_call: ToolCall) -> ToolResult:
    approved = await self.approve(tool_call)
    if not approved:
        return ToolResult(
            success=False,
            output="用户拒绝执行此操作",
            tool_name=tool_call.name
        )
    # 正常执行...
```

Agent 收到拒绝结果后，可以：换一种低风险方案、降级操作、或直接告知用户无法完成。

### 4.7 Heartbeat 心跳

**决策**：v1 架构预留接口，v2 实现（PRD §2.1 / §4.3）

Gateway 层预留 heartbeat 调度入口，但 v1 不实现具体逻辑。

---

## 5. 消息格式

内部统一使用标准化消息格式：

```python
@dataclass
class Message:
    role: str            # "user" | "assistant" | "tool" | "system"
    content: str         # 文本内容
    images: list[bytes]  # 图片（截图等），用于多模态
    tool_calls: list[ToolCall]  # 工具调用请求
    tool_result: ToolResult | None  # 工具执行结果
    metadata: dict       # 额外信息（时间戳、model_role、token_count 等）

@dataclass
class Session:
    id: str                      # 会话唯一标识
    context: AgentContext         # 上下文（消息历史、活跃 Skill 等）
    created_at: datetime
    last_active_at: datetime

@dataclass
class ToolResult:
    success: bool                # 是否成功
    output: str                  # 输出内容 / 错误信息 / "用户拒绝执行此操作"
    tool_name: str               # 工具名称
```

---

## 6. 技术选型详解

| 领域 | 选型 | 理由 | 备选 |
|------|------|------|------|
| HTTP 客户端 | **httpx** | 原生 async、HTTP/2、流式支持 | aiohttp（API 不如 httpx 优雅） |
| 浏览器 | **Playwright** | 最强自动化、原生 async API、微软维护 | Selenium（老旧）、browser-use（太高层） |
| 桌面操控 | **pyautogui + Pillow** | 跨平台基础、社区成熟 | pyobjc（macOS only、太底层） |
| CLI | **Rich + Prompt Toolkit** | Rich 输出美观、PT 交互强大 | Textual（太重）、Click 单用（不够美观） |
| 数据库 | **aiosqlite** | 零配置、原生 async、FTS5 全文搜索 | TinyDB（无 SQL）、DuckDB（太重） |
| 配置 | **Pydantic Settings** | 类型安全、env 变量支持、校验 | dynaconf（功能多但学习成本高） |
| 搜索 | **DuckDuckGo** | 免费无需 API Key | Tavily（需要 Key，作为备选） |
| 包管理 | **uv** | 极快、现代、lockfile 支持 | poetry（慢）、pip（无 lock） |

---

## 7. 安全架构 — 对应 PRD F3 / §5.2

### 7.1 工具风险分级

```python
class RiskLevel(Enum):
    LOW = "low"           # 只读操作，无副作用（read_file, web_search, screen_capture）
    HIGH = "high"         # 有副作用，可逆（shell_exec, write_file, mouse_click, browser_open/action）
    CRITICAL = "critical" # 有副作用，不可逆或影响外部（rm -rf, 发送消息）
```

### 7.2 审批流程

```python
async def approve(tool_call: ToolCall) -> bool:
    if tool_call.risk_level == RiskLevel.LOW:
        return True  # 自动通过

    if tool_call.risk_level == RiskLevel.HIGH:
        # 向用户展示即将执行的操作，等待 y/n
        return await channel.confirm(f"即将执行: {tool_call}")

    if tool_call.risk_level == RiskLevel.CRITICAL:
        # 展示操作 + 风险警告，等待输入 "CONFIRM"
        return await channel.confirm_critical(f"⚠️ 危险操作: {tool_call}")
```

### 7.3 文件系统沙箱

配置 `allowed_directories` 白名单，file 类工具在执行前检查路径：

```python
def validate_path(path: str, allowed_dirs: list[str]) -> bool:
    resolved = Path(path).resolve()
    return any(resolved.is_relative_to(Path(d).expanduser()) for d in allowed_dirs)
```

---

## 8. PRD 需求追溯表

| 架构模块 | 对应 PRD 需求 | 优先级 |
|----------|-------------|--------|
| agent/loop.py | F1: Agent 核心循环 | P0 |
| agent/model_router.py | F2: 四模型角色调度 | P0 |
| llm/*.py | F2: LLM Provider 层 | P0 |
| tools/*.py | F3: 工具系统 | P0 |
| browser/*.py | F4: 浏览器操控 | P0 |
| desktop/*.py | F5: 桌面操控 | P0 |
| channels/*.py | F6: CLI 交互界面 | P0 |
| gateway/*.py | F6.5: Gateway 消息网关 | P0 |
| skills/*.py | F7: Skill 技能插件系统 | P1 |
| memory/*.py | F8: 记忆系统 | P1 |
| config/*.py | F9: 配置管理 | P1 |
| utils/logging.py | §5.3: 可观测/可调试 | P0 |
| utils/tokens.py | F2: Token 计数 | P0 |
