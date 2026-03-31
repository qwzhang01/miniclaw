# MiniClaw 🦞 — 你的 Mac 上的 AI 操控者

## 产品需求文档 (PRD v1.0)

> **一句话定位**：一个用 Python 写的、能真正操控你电脑的本地 AI Agent —— OpenClaw 的 Python 精神续作
>
> **作者**：avinzhang ｜ **日期**：2026-03-29 ｜ **状态**：v1 草稿

---

## 1. 这个项目到底要做什么

### 1.1 核心卖点（传播钩子）

```
一句话安装，一句话让 AI 操控你的 Mac。

$ pip install miniclaw
$ miniclaw

🦞 你好！我是 MiniClaw，你的本地 AI 助手。
🦞 我能帮你执行命令、操控浏览器、查看屏幕、操作桌面应用。
🦞 试试说：「帮我打开 Chrome 搜索一下 Python 3.14 的新特性，把结果整理成 Markdown 保存到桌面」

You: 帮我看看企微上有没有未读消息

🦞 正在截取屏幕...
🦞 [截图分析] 检测到企业微信窗口，发现 3 条未读消息：
   1. 张三（产品群）："明天评审会改到 10 点"
   2. 李四（技术群）："CI 挂了，@你看一下"
   3. 王五（私聊）："周末打球不"
🦞 第 2 条看起来比较紧急，要我帮你回复吗？
```

**为什么这个卖点能火**：
- OpenClaw 310K+ Star，但它是 TypeScript，Python 圈没有对标物
- 现有 Python Agent 框架（LangChain、CrewAI）都不能操控电脑
- 「能看屏幕、能点鼠标」的 demo 效果是最强的传播素材
- `pip install` 一行搞定，不需要 Docker / VM / 复杂配置

### 1.2 与竞品的差异

| 项目 | 语言 | 能操控电脑 | 轻量程度 | 学习友好 |
|------|------|-----------|---------|---------|
| **OpenClaw** | TypeScript | ✅ | ❌ 重 (1800+插件) | ❌ 源码庞大 |
| **open-computer-use** | TS + Python | ✅ | ❌ 需要 Docker VM | ❌ 架构复杂 |
| **Clawlet** | Python | ❌ 仅聊天 | ✅ | ✅ |
| **FreeClaw** | Python | ❌ 仅聊天 | ✅ | ✅ |
| **LangChain / CrewAI** | Python | ❌ | ❌ 抽象层太多 | ❌ |
| **MiniClaw（我们）** | **Python** | **✅** | **✅ pip install** | **✅ 每模块<500行** |

**MiniClaw 的独特定位**：

> Python 生态中**唯一**同时做到「能操控电脑 + 轻量可理解 + pip 一行安装」的 AI Agent 框架

### 1.3 项目的五重价值（对应我的五个目标）

| 目标 | 如何实现 |
|------|---------|
| ① 学习 Agent | 自己实现 Agent Loop、工具调用链、记忆系统，不套壳 |
| ② 学习 OpenClaw | 架构对标 OpenClaw（Gateway → Agent → Skill），用 Python 重写核心设计 |
| ③ 可能火 | 「Python 版能操控电脑的 AI Agent」这个定位在 Python 圈空白，demo 效果炸裂 |
| ④ 垂直 Agent 基础 | Skill 插件机制 → 可快速派生「代码审查 Agent」「运维 Agent」等垂直场景 |
| ⑤ 工作提效 | 自己就是第一个用户：操控浏览器做调研、截屏看消息、自动执行开发任务 |

---

## 2. 核心设计理念

### 2.1 借鉴 OpenClaw，但做减法

OpenClaw 的精华设计我们保留，臃肿部分我们砍掉：

| OpenClaw 设计 | MiniClaw 做法 |
|--------------|--------------|
| Gateway + Nodes 分布式 | ✂️ 简化为单进程，Gateway 变成消息路由器 |
| 30+ Channel Adapter | ✂️ v1 只做 CLI + HTTP，架构上预留扩展点 |
| 1800+ Skill 插件 | ✂️ v1 内置 5 个核心 Skill，但插件机制完整 |
| TypeScript 实现 | 🔄 Python 重写，对 Python 开发者友好 |
| SKILL.md 知识 + Plugin 代码分离 | ✅ 保留这个设计，这是精华 |
| Agent Loop（ReAct） | ✅ 保留，这是核心 |
| Heartbeat 心跳机制 | ⏳ v1 架构预留接口，v2 实现（见 §4.3 P2 功能列表） |
| 安全审批机制 | ✅ 保留，危险操作需确认 |

### 2.2 三条铁律

1. **每个模块 < 500 行代码** — 如果超了，说明设计有问题，拆
2. **任何人 clone 下来 10 分钟能跑起来** — 不依赖 Docker / VM / 外部服务（除了 LLM API）
3. **先能用，再好用** — 不追求完美抽象，追求可工作的代码

---

## 3. 架构总览

```
┌────────────────────────────────────────────────────────┐
│                    MiniClaw                             │
│                                                        │
│  ┌──────────┐   ┌──────────────────┐   ┌────────────┐ │
│  │ Channels │──▶│     Gateway      │──▶│   Agent    │ │
│  │ 通道层    │   │   消息路由+会话   │   │  Runtime   │ │
│  │          │◀──│                  │◀──│  运行时     │ │
│  │ • CLI    │   └──────────────────┘   └─────┬──────┘ │
│  │ • HTTP   │                                │        │
│  └──────────┘                                │        │
│                          ┌───────────────────┼────┐   │
│                          ▼         ▼         ▼    │   │
│                    ┌─────────┐┌────────┐┌───────┐ │   │
│                    │  Tools  ││ Memory ││ Skills│ │   │
│                    │  工具层  ││ 记忆   ││ 技能  │ │   │
│                    └────┬────┘└────────┘└───────┘ │   │
│                         │                         │   │
│              ┌──────────┼──────────┐              │   │
│              ▼          ▼          ▼              │   │
│        ┌──────────┐┌────────┐┌──────────┐        │   │
│        │  Shell   ││Browser ││ Desktop  │        │   │
│        │ 命令执行  ││ 浏览器  ││ 桌面操控  │        │   │
│        │ subprocess││Playwright│ pyautogui│        │   │
│        └──────────┘└────────┘│ +截图+LLM│        │   │
│                              └──────────┘        │   │
│                                                   │   │
│  ┌──────────────────────────────────────────────────┐  │
│  │          LLM Provider Layer（四模型调度）         │  │
│  │                                                  │  │
│  │  ┌──────────┐ ┌──────────┐ ┌────────┐ ┌──────┐  │  │
│  │  │ default  │ │ planner  │ │ reason │ │ maker│  │  │
│  │  │ 默认模型  │ │ 规划模型  │ │ 推理模型│ │产出模型│  │  │
│  │  │ 日常对话  │ │ 任务拆解  │ │ 逻辑分析│ │代码/文档│ │  │
│  │  └──────────┘ └──────────┘ └────────┘ └──────┘  │  │
│  │                                                  │  │
│  │  统一接口 · OpenAI兼容/Anthropic · 多模态 · 按任务自动路由 │
│  └──────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────┘
```

---

## 4. 功能需求（v1 范围）

> v1 目标：**一个能在终端对话、能执行命令、能操控浏览器、能看屏幕的本地 AI Agent**

### 4.1 第一优先级（P0）— 没有这些就不能叫 MiniClaw

#### F1: Agent 核心循环

实现 ReAct 模式的 Agent 主循环。这是整个框架的心脏。

**核心流程**：

```
用户输入 → 组装上下文 → 调用 LLM → 解析响应
                                        │
                                  ┌─────┴──────┐
                                  ▼            ▼
                             文本回复      工具调用请求
                             (结束)        │
                                          ▼
                                     安全审批
                                          │
                                   ┌──────┴──────┐
                                   ▼             ▼
                              用户拒绝       审批通过 → 执行工具
                                   │                      │
                                   ▼               ┌──────┴──────┐
                            ToolResult             ▼             ▼
                            (success=False,    执行成功      执行失败/超时
                             "用户拒绝")        │             │
                                   │            ▼             ▼
                                   │       ToolResult    ToolResult
                                   │       (success=     (success=False,
                                   │        True)         错误信息)
                                   │            │             │
                                   └────────────┴─────────────┘
                                                │
                                                ▼
                                         结果注入上下文 → 再次调用 LLM
                                         (Agent 根据结果自行决策：继续/换方案/告知用户)
                                         (循环，直到文本回复或达到最大轮次)
```

**关键设计点**：

- 最大循环次数限制（默认 10 轮，防止死循环）
- 流式输出（用户看到 Agent "思考中..." 的过程）
- 工具调用的中间状态展示（用户能看到 Agent 正在调用什么工具）
- 错误恢复（工具执行失败时，Agent 能自行决策：重试 / 换方案 / 告知用户）

**demo 效果**：

```
You: 帮我查一下我的 Python 项目有多少行代码

🦞 思考中...
🦞 [调用工具] shell_exec: find . -name "*.py" | xargs wc -l
🦞 [工具结果] 共 2,347 行
🦞 你的项目中有 2,347 行 Python 代码。要我分析一下各模块的代码量分布吗？
```

---

#### F2: LLM 四模型角色调度系统

MiniClaw 不是只接一个模型，而是**按任务类型自动路由到最合适的模型**。

**四种模型角色**：

| 角色 | 配置键 | 职责 | 典型场景 | 推荐模型 |
|------|--------|------|---------|---------|
| **default** | `llm.default` | 日常对话、简单问答、闲聊 | "你好"、"帮我解释下这个概念" | DeepSeek-Chat（便宜快速） |
| **planner** | `llm.planner` | 任务规划、步骤拆解、策略制定 | "帮我部署这个项目"（需要拆成多步） | Claude 3.5 Sonnet / GPT-4o |
| **reasoner** | `llm.reasoner` | 逻辑推理、代码调试、复杂分析 | "这段代码为什么报错"、截屏分析 | Claude 3.5 Sonnet / DeepSeek-R1 |
| **maker** | `llm.maker` | 内容产出：代码生成、报告撰写、文档整理 | "写一个 FastAPI 项目"、"生成调研报告" | Claude 3.5 Sonnet / GPT-4o |

**自动路由机制**：

Agent Loop 在每一轮循环中，根据当前任务阶段自动选择模型：

```
用户输入 "帮我调研 Python Web 框架，写一份对比报告"

Round 1 → [planner] 分析任务，拆解步骤：
           1. 搜索主流框架列表
           2. 逐个调研核心特性
           3. 整理对比表格
           4. 撰写总结报告

Round 2 → [default] 调用 web_search 工具搜索信息（简单工具调用，用便宜模型）

Round 3 → [reasoner] 分析搜索结果，提取关键信息（需要理解和推理）

Round 4 → [maker] 生成最终的 Markdown 对比报告（需要高质量文本产出）
```

**路由规则**（在 Agent Loop 中实现）：

```python
def select_model_role(context: AgentContext) -> str:
    """根据当前上下文自动选择模型角色"""
    # 第一轮 + 复杂任务 → planner
    if context.round == 1 and context.task_complexity == "high":
        return "planner"
    # 需要分析截图 / 调试错误 → reasoner
    if context.has_images or context.last_tool_failed:
        return "reasoner"
    # 需要生成代码 / 文档 / 报告 → maker
    if context.intent in ("generate_code", "write_report", "create_doc"):
        return "maker"
    # 其他情况 → default（省钱）
    return "default"
```

**支持的协议**：

- OpenAI 兼容 API（覆盖 OpenAI / DeepSeek / Qwen / 硅基流动 / Ollama 本地模型）
- Anthropic Claude API（tool use 协议兼容）
- 每个角色可独立配置 provider + model + 参数

**关键能力**：

- `chat(messages, tools, role="default")` — 文本对话 + 工具调用
- `chat(messages_with_images, tools, role="reasoner")` — 多模态输入（截图理解）
- 流式输出
- 自动重试 + fallback（如 planner 模型不可用时降级到 default）
- **Token 计数**（v1 简化方案）：按角色统计 input/output token 数，每轮循环结束后以 `debug` 级别写入日志。不做实时 UI 展示，不做费用估算——这些留给 v2。

**为什么不用 LiteLLM / openai SDK**：

自己写一层薄封装（<400 行），因为：
1. 学习目的 — 亲手实现 LLM 协议解析和模型路由
2. 更可控 — 自定义路由逻辑、重试策略、日志和 token 统计
3. 四模型调度是核心设计 — 第三方库不支持这种按任务角色路由的模式

---

#### F3: 工具系统

可注册、可发现、有安全审批的工具体系。

**工具注册**：

```python
from miniclaw.tools import tool

@tool(
    description="在本地终端执行 Shell 命令",
    risk_level="high",  # high = 需要用户确认, low = 自动执行
)
async def shell_exec(command: str) -> str:
    """执行一条 shell 命令并返回标准输出"""
    ...
```

**安全模型**（借鉴 OpenClaw 的审批机制）：

```
risk_level="low"   → 自动执行（如 read_file, web_search）
risk_level="high"  → 需要用户确认（如 shell_exec, write_file, 鼠标点击）
risk_level="critical" → 必须用户确认 + 二次确认（如 rm -rf, 发送消息）
```

**用户拒绝执行时的处理流程**：

当用户对 high / critical 工具操作选择「拒绝」时：
1. 工具执行引擎返回一个标准化的 `ToolResult(success=False, output="用户拒绝执行此操作")`
2. 该结果作为工具调用结果注入 Agent 上下文
3. Agent 根据拒绝信息自行决策：换一种方案、降级操作、或直接告知用户
4. **不中断 Agent Loop** — 拒绝等同于工具返回了一个错误结果

**v1 内置工具清单**：

| 工具 | 风险等级 | 用途 |
|------|---------|------|
| `shell_exec` | high | 执行 Shell 命令 |
| `read_file` | low | 读取文件内容 |
| `write_file` | high | 写入/创建文件 |
| `web_search` | low | 网页搜索（DuckDuckGo，免费无需 API Key；备选 Tavily） |
| `http_request` | low | 发送 HTTP 请求 |
| `browser_open` | high | 打开浏览器访问 URL |
| `browser_action` | high | 在浏览器中执行操作（点击/输入/截图） |
| `screen_capture` | low | 截取屏幕/指定区域 |
| `screen_analyze` | low | **复合工具**：截屏 → 内部调用 reasoner LLM 分析内容 → 返回文字描述（注：这是唯一允许工具内部调用 LLM 的特例） |
| `mouse_click` | high | 在指定坐标点击鼠标 |
| `keyboard_type` | high | 模拟键盘输入 |

---

#### F4: 浏览器操控（Playwright）

**这是 MiniClaw 的第一个杀手级能力**。

用 Playwright 驱动真实浏览器，Agent 能：

```
"帮我打开掘金，搜索 OpenClaw，把前 5 篇文章的标题和链接整理成表格"

→ 打开 Chrome → 导航到掘金 → 输入搜索词 → 提取搜索结果 → 格式化输出
```

**核心功能**：

- 打开/关闭浏览器页面
- 导航到指定 URL
- 点击元素（通过 CSS 选择器 / 文本内容）
- 输入文本
- 截取页面截图（全页 / 指定区域）
- 提取页面文本内容
- 等待元素出现
- 执行 JavaScript

**设计要点**：

- 使用用户已有的 Chrome（`channel="chrome"`），不另外安装浏览器
- 浏览器进程后台运行，多次操作复用同一实例
- 截图传给多模态 LLM 进行视觉理解（应对复杂页面）

---

#### F5: 桌面操控（截屏 + 视觉理解 + 鼠标键盘）

**这是 MiniClaw 的第二个杀手级能力**，也是「看企微消息」的基础。

**跨平台抽象设计**：

v1 只实现 macOS，但架构上做好跨平台抽象，后期加 Windows/Linux 只需新增实现类：

```python
# 平台抽象层
class DesktopController(ABC):
    """桌面操控的跨平台抽象基类"""

    @abstractmethod
    async def capture_screen(self, region=None) -> bytes: ...

    @abstractmethod
    async def click(self, x: int, y: int, button="left") -> None: ...

    @abstractmethod
    async def type_text(self, text: str) -> None: ...

    @abstractmethod
    async def hotkey(self, *keys: str) -> None: ...

    @abstractmethod
    async def get_active_window_title(self) -> str: ...

    @abstractmethod
    async def list_windows(self) -> list[WindowInfo]: ...

# v1 实现
class MacOSController(DesktopController):
    """macOS 实现：pyautogui + Quartz + osascript"""
    ...

# v2 待实现（只需加这个文件，不改任何已有代码）
# class WindowsController(DesktopController):
#     """Windows 实现：pyautogui + Win32 API + PowerShell"""
#     ...
```

**技术方案**：

```
截屏 (pyautogui / macOS Quartz API)
    │
    ▼
发给多模态 LLM（通过 reasoner 角色，自动选视觉能力最强的模型）
    │
    ▼
LLM 返回：屏幕上有什么、每个元素的位置
    │
    ▼
Agent 决策：需要点击哪里 / 输入什么
    │
    ▼
执行操作 (pyautogui 模拟鼠标键盘)
    │
    ▼
再次截屏，验证操作结果
```

**v1 scope（macOS 实现）**：

- [x] 全屏截图 / 指定区域截图（pyautogui + Pillow）
- [x] 截图发给 LLM 分析（走 reasoner 角色，支持多模态）
- [x] 在指定坐标点击鼠标
- [x] 模拟键盘输入文字
- [x] 获取当前活动窗口标题（osascript）
- [x] 列出所有可见窗口列表（osascript）
- [ ] ~~UI 元素树解析（Accessibility API）~~ → v2 再做
- [ ] ~~OCR 本地识别~~ → v2 再做

**macOS 权限说明**：

需要用户授予「辅助功能」权限（系统设置 → 隐私与安全 → 辅助功能），MiniClaw 首次运行时会引导用户开启。

**demo 效果**：

```
You: 帮我看看企微上有没有人找我

🦞 正在截取屏幕... [调用 screen_capture]
🦞 正在分析屏幕内容... [调用 screen_analyze]
🦞 我看到桌面上有以下窗口：
   - VS Code（当前焦点）
   - 企业微信（右下角有 3 个红点）
   - Chrome
🦞 企业微信有 3 条未读消息。要我点开看看具体内容吗？

You: 看看

🦞 正在点击企业微信图标... [调用 mouse_click(x=1200, y=750)]
🦞 正在等待窗口切换...
🦞 正在截取企微窗口... [调用 screen_capture(region="active_window")]
🦞 正在分析消息内容... [调用 screen_analyze]
🦞 未读消息如下：
   1. 产品群 - 张三："明天评审会改到 10 点"
   2. 技术群 - 李四："线上 CPU 告警了，@你看一下"  ⚠️ 看起来紧急
   3. 王五（私聊）："周末打球不"
🦞 建议优先处理第 2 条，要我帮你回复吗？
```

---

#### F6: CLI 交互界面

美观的命令行界面，作为 v1 的主交互通道。

```
$ miniclaw

╭─────────────────────────────────────────╮
│  🦞 MiniClaw v0.1.0                     │
│  本地 AI Agent · 能看屏幕 · 能操控电脑    │
│  模型: deepseek-chat · 输入 /help 查看帮助│
╰─────────────────────────────────────────╯

You: _
```

**特殊命令**：

| 命令 | 功能 |
|------|------|
| `/help` | 显示帮助信息 |
| `/tools` | 列出所有可用工具 |
| `/skills` | 列出已加载的技能 |
| `/history` | 查看对话历史 |
| `/clear` | 清空当前会话 |
| `/screen` | 快捷截屏分析 |
| `/config` | 查看/修改配置 |
| `/reload` | 重新加载所有 Skill（无需重启） |
| `/exit` | 退出 |

**交互体验要求**：

- 流式输出（打字机效果）
- 工具调用过程可视化（用户能看到 Agent 的「思考过程」）
- 彩色区分：用户输入（白）/ Agent 回复（绿）/ 工具调用（黄）/ 错误（红）
- 支持多行输入（Shift+Enter 或 `\` 续行）

---

#### F6.5: Gateway 消息网关

Channel 和 Agent 之间的桥梁层，负责消息路由和会话管理。

**v1 职责（轻量直通）**：

v1 为单用户单会话模式，Gateway 不做复杂的分布式路由，但承担以下职责：

```
Channel 消息 → Gateway → Agent Runtime
                │
                ├── 1. 会话管理：创建/查找/恢复 Session
                ├── 2. 消息标准化：将 Channel 原始输入转为内部 Message 格式
                ├── 3. 上下文注入：将 Session 的历史上下文传给 Agent
                └── 4. 响应回传：将 Agent 输出路由回对应 Channel
```

**核心接口**：

```python
class Gateway:
    async def handle_message(self, raw_input: str, channel: Channel) -> None:
        """接收 Channel 消息，路由给 Agent，回传响应"""
        session = self.get_or_create_session(channel.session_id)
        message = Message(role="user", content=raw_input)
        response = await self.agent.run(message, session.context)
        await channel.send(response)

    def get_or_create_session(self, session_id: str) -> Session:
        """查找已有会话或创建新会话"""
        ...
```

**Session 数据结构**：

```python
@dataclass
class Session:
    id: str                      # 会话唯一标识
    context: AgentContext         # 上下文（消息历史、活跃 Skill 等）
    created_at: datetime
    last_active_at: datetime
```

**为什么 v1 不能跳过 Gateway**：

即使是单用户模式，Gateway 也解耦了 Channel 和 Agent。未来加 Telegram/HTTP 通道时，只需让新 Channel 对接 Gateway 即可，不需要改 Agent 代码。这是架构扩展性的基础。

---

### 4.2 第二优先级（P1）— 让 MiniClaw 真正好用

#### F7: Skill 技能插件系统

借鉴 OpenClaw 的 SKILL.md + Plugin 分离设计，这是 MiniClaw 的扩展基础。

**一个 Skill 的结构**：

```
skills/
├── browser-research/          # 浏览器调研技能
│   ├── SKILL.md               # 角色定义 + Prompt 模板 + 使用场景
│   ├── tools.py               # 该技能专属的工具函数
│   └── config.yaml            # 配置项（可选）
│
├── desktop-assistant/         # 桌面助手技能
│   ├── SKILL.md               # "你是一个 macOS 桌面操控专家..."
│   └── tools.py               # screen_capture, mouse_click 的高级封装
│
└── coder/                     # 编程助手技能
    ├── SKILL.md               # "你是一个 Python 编程专家..."
    └── tools.py               # code_analyze, run_tests, git_commit...
```

**SKILL.md 格式示例**：

```markdown
# Browser Research Skill

## 角色
你是一个专业的浏览器调研助手，擅长使用浏览器搜索信息、
提取网页内容、整理和总结调研结果。

## 激活条件
当用户提到以下关键词时激活：搜索、调研、查一下、打开网页、浏览器...

## 可用工具
- browser_open: 打开网页
- browser_action: 浏览器操作
- screen_capture: 截取页面

## 工作流程
1. 理解用户的调研需求
2. 规划搜索策略（用什么关键词、访问哪些网站）
3. 打开浏览器执行搜索
4. 提取和整理信息
5. 以结构化格式返回结果

## 输出格式
调研结果使用 Markdown 表格或列表呈现，包含来源链接。
```

**Skill 加载机制**：

- 启动时自动扫描 `~/.miniclaw/skills/` + 项目目录 `./skills/`
- 根据用户输入自动匹配激活相关 Skill（关键词 + LLM 意图判断）
- 支持 `/reload` 命令手动重新加载所有 Skill（v1 不做文件监听热加载，避免复杂度）

**v1 内置 Skills**：

| Skill | 用途 |
|-------|------|
| `shell` | 系统命令执行、进程管理、文件操作 |
| `browser-research` | 浏览器搜索、网页信息抓取和整理 |
| `desktop-assistant` | 屏幕分析、桌面应用操控 |
| `coder` | 代码分析、生成、运行测试 |
| `github` | Issue/PR 管理、代码搜索、仓库操作 |

---

#### F8: 记忆系统

让 Agent 有「记性」，不再每次对话都从零开始。

**两层记忆**：

| 层级 | 存储 | 生命周期 | 用途 |
|------|------|---------|------|
| 短期记忆 | 内存 | 当前会话 | 对话历史、上下文 |
| 长期记忆 | SQLite | 永久 | 用户偏好、常用操作、重要信息 |

**上下文窗口管理**：

当对话历史接近 token 上限时，自动摘要压缩旧消息（调用 `default` 角色的 LLM 生成摘要，省钱优先），而不是简单截断。

**v1 不做向量检索**，用 SQLite FTS5 全文搜索就够了。v2 根据需要再加。

---

#### F9: 配置管理

首次运行时引导用户完成配置，之后通过配置文件管理。

**配置文件** `~/.miniclaw/config.yaml`：

```yaml
# ============================================================
# LLM 四模型角色配置
# 不同任务类型自动路由到最合适的模型
# ============================================================

llm:
  # 默认模型：日常对话、简单问答（便宜、快速）
  default:
    provider: openai_compatible
    base_url: https://api.deepseek.com/v1
    api_key: ${DEEPSEEK_API_KEY}
    model: deepseek-chat
    temperature: 0.7
    max_tokens: 4096

  # 规划模型：任务拆解、步骤规划、策略制定（需要全局视野）
  planner:
    provider: openai_compatible
    base_url: https://api.deepseek.com/v1
    api_key: ${DEEPSEEK_API_KEY}
    model: deepseek-chat
    temperature: 0.3         # 规划需要更确定性的输出
    max_tokens: 8192

  # 推理模型：逻辑分析、代码调试、截屏理解（需要多模态 + 强推理）
  reasoner:
    provider: openai_compatible
    base_url: https://api.openai.com/v1
    api_key: ${OPENAI_API_KEY}
    model: gpt-4o            # 视觉理解能力最强
    temperature: 0.2
    max_tokens: 4096

  # 产出模型：代码生成、报告撰写、文档整理（需要高质量输出）
  maker:
    provider: anthropic
    api_key: ${ANTHROPIC_API_KEY}
    model: claude-sonnet-4-20250514
    temperature: 0.5
    max_tokens: 8192

# ============================================================
# 安全配置
# ============================================================
security:
  auto_approve_low_risk: true    # 低风险工具自动执行
  confirm_high_risk: true        # 高风险工具需确认
  allowed_directories:           # 文件操作白名单
    - ~/git/
    - ~/Documents/

# ============================================================
# 浏览器配置
# ============================================================
browser:
  headless: false                # false = 能看到浏览器操作过程（demo 效果好）
  use_system_chrome: true        # 使用系统已安装的 Chrome

# ============================================================
# 平台配置（跨平台抽象，v1 只实现 macOS）
# ============================================================
platform:
  desktop_controller: auto       # auto = 自动检测系统，macOS → MacOSController

# ============================================================
# 日志
# ============================================================
logging:
  level: info                    # debug 模式会打印完整 prompt + 模型路由决策
  file: ~/.miniclaw/logs/miniclaw.log
```

---

### 4.3 第三优先级（P2）— M5 多渠道 + 主动能力 + 生产化

> **背景**：v1（M0-M4）已完成核心框架。M5 阶段借鉴 avin-kit/MiniClaw（V1 原型版本）中已验证的功能，
> 补全多渠道接入、主动调度、Web UI、Docker 部署等生产化能力，使 MiniClaw 从"能用"走向"好用"。

---

#### F10: Telegram Bot 通道

**目标**：在手机上给 MiniClaw 发消息，远程操控电脑。

**功能要求**：
- 使用 `python-telegram-bot>=21` 库接入 Telegram Bot API
- 支持 `/start`、`/help`、`/clear`、`/status` Bot 命令
- 普通文本消息直接转发给 Gateway → AgentLoop 处理
- 长消息自动分段发送（Telegram 限制 4096 字符）
- 支持主动推送（心跳提醒等场景通过 `bot.send_message()` 推送）
- 发送「正在思考」typing 状态，提升用户体验
- 通过 `TELEGRAM_BOT_TOKEN` 环境变量配置

**实现要点**：
- 复用现有 `ChannelProtocol` 抽象接口，新增 `TelegramChannel` 实现
- Gateway 层无需改动，自动支持新通道
- 多用户隔离：每个 Telegram `user_id` 维护独立 Session

**配置**：
```yaml
channels:
  telegram:
    enabled: false
    token: ${TELEGRAM_BOT_TOKEN}
```

---

#### F11: Gradio Web UI

**目标**：提供浏览器可访问的聊天界面，适合演示和日常使用。

**功能要求**：
- 基于 `gradio>=4.30` 构建聊天界面
- 左侧聊天区 + 右侧状态面板（模型信息、工具列表、Skill 列表）
- 内置示例问题（快速体验核心功能）
- 刷新按钮查看实时状态（活跃用户数、消息计数、Token 统计）
- 显示当前模型配置和温度参数

**实现要点**：
- 新增 `channels/gradio_channel.py`，实现 `ChannelProtocol`
- Gradio 需同步包装异步调用（`asyncio.run` 桥接）
- 默认端口 7860，支持配置

**配置**：
```yaml
channels:
  gradio:
    enabled: false
    port: 7860
    share: false
```

---

#### F12: 心跳调度 + Cron 定时任务

**目标**：Agent 不只被动回复，还能主动行动 —— 定时提醒、定时巡检、每日总结。

**功能要求**：
- 使用 `apscheduler>=3.10` 异步调度器
- 每分钟检查本地提醒列表（JSON 文件持久化），到期自动推送
- 每天定时生成每日总结（可配置 cron 表达式）
- 支持用户通过对话添加提醒（"提醒我明天下午3点开会"）
- 支持自定义 cron 任务注册

**实现要点**：
- 新增 `scheduler/heartbeat.py`，封装 APScheduler
- 新增内置工具 `calendar`（add / list / delete 提醒），risk=low
- 提醒数据存储在 `~/.miniclaw/data/reminders.json`
- 心跳回调接入 Channel 层（通过 Telegram / CLI 推送提醒）

**配置**：
```yaml
scheduler:
  heartbeat_enabled: true
  heartbeat_cron: "0 9 * * *"    # 每天 9 点生成每日总结
  reminder_check_interval: 60     # 每 60 秒检查提醒
```

---

#### F13: 向量语义记忆（ChromaDB）

**目标**：增强长期记忆能力，支持语义相似度检索，而不仅是关键词匹配。

**功能要求**：
- 集成 `chromadb>=0.5` 作为可选向量存储后端
- 用户可通过对话主动保存记忆（"记住我喜欢用 Vim"）
- Agent 每次对话前自动检索相关记忆，注入 system prompt
- 支持 cosine distance 语义相似度排序
- 按 `user_id` 隔离记忆空间

**实现要点**：
- 新增 `memory/vector_memory.py`，封装 ChromaDB
- `MemoryManager` 统一管理：短期记忆（内存）+ 长期记忆（SQLite FTS5）+ 向量记忆（ChromaDB）
- ChromaDB 作为可选依赖（`pip install miniclaw[vector]`），不安装时自动降级到 FTS5
- 新增内置工具 `memory`（save / search / list_recent），risk=low

**配置**：
```yaml
memory:
  vector_enabled: false
  chroma_persist_dir: ~/.miniclaw/data/chroma
```

---

#### F14: Docker 一键部署

**目标**：`docker compose up` 一键启动全部服务，适合服务器部署和快速体验。

**功能要求**：
- 提供 `Dockerfile`（多阶段构建，基于 `python:3.12-slim`）
- 提供 `docker-compose.yml`，包含：
  - `miniclaw-web`：Gradio Web UI 服务（默认启动）
  - `miniclaw-telegram`：Telegram Bot 服务（可选 profile）
- 数据目录 volume 挂载（`~/.miniclaw/data`）持久化
- 健康检查 endpoint
- 可选安装 Playwright 浏览器（构建参数 `INSTALL_BROWSER=true`）

**Dockerfile 要点**：
```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY . .
RUN pip install --no-cache-dir .
EXPOSE 7860
CMD ["miniclaw", "--mode", "gradio"]
```

---

#### F15: 多渠道同时运行

**目标**：支持 CLI + Telegram + Gradio 同时运行，共享同一个 Gateway 和 AgentLoop。

**功能要求**：
- CLI 入口增加 `--mode` 参数：`cli`（默认）/ `telegram` / `gradio` / `all`
- `all` 模式下所有渠道共享同一个 Gateway 实例
- Gateway 层通过 `session_id` 前缀区分不同渠道的用户（`cli-xxx`、`tg-xxx`、`gradio-xxx`）
- 所有渠道共享工具注册表、Skill、记忆系统

**实现要点**：
- `bootstrap.py` 扩展为按 mode 创建不同 Channel 组合
- Gateway.handle_message() 已支持 `session_id` 参数，无需改动核心逻辑

---

#### F16: 代码执行沙箱（可选 Docker 隔离）

**目标**：为代码执行工具提供更安全的沙箱环境。

**功能要求**：
- 新增 `code_exec` 工具，支持 Python 和 Shell 代码执行
- 双轨安全机制：
  - 正则危险模式检测（`rm -rf /`、`sudo`、`fork bomb` 等）
  - 可选 Docker 容器隔离（无网络、内存限制 256MB、CPU 限制、进程数限制）
- 代码执行超时限制（默认 30s）
- risk=critical（需要用户输入 CONFIRM 确认）

**配置**：
```yaml
security:
  sandbox_enabled: false          # 是否启用 Docker 沙箱
  code_exec_timeout: 30           # 代码执行超时（秒）
```

---

#### 其他 P3 延后功能

| 功能 | 说明 |
|------|------|
| **多 Agent 协作** | Supervisor 模式，一个 Agent 调度多个专业 Agent |
| **企微 API 集成** | 通过企微机器人 API 直接收发消息（比截屏更稳定） |
| **Windows 桌面支持** | 实现 WindowsController（只需加一个文件） |
| **Token 费用估算** | 基于 token 计数的实时费用展示 |
| **HTTP API 通道** | FastAPI WebSocket，支持前端 UI 或第三方集成 |
| **RAG 文档问答** | 基于向量记忆的本地文档问答能力 |
| **语音输入** | Whisper 语音识别，支持语音对话 |

---

## 5. 非功能需求

### 5.1 极致轻量

- 核心代码 < 3000 行（不含 Skills 目录）
- 安装依赖 < 10 个第三方包
- 内存占用 < 100MB（空载，不含浏览器）
- `pip install miniclaw` 一行安装，不需要额外系统依赖

### 5.2 安全第一

- 高风险操作（Shell、写文件、鼠标点击、发消息）**必须**用户确认
- 文件操作限制在白名单目录内
- API Key 通过环境变量管理，不硬编码
- 所有工具执行都有日志记录

### 5.3 可观测 / 可调试

- Agent 的每一步思考和工具调用都有日志
- `--debug` 模式输出完整的 LLM prompt 和响应
- 工具调用的耗时统计

### 5.4 代码可读性

- 每个模块一个文件，每个文件 < 500 行
- 详细的中文注释（这个项目本身就是教学材料）
- 完整的 type hints

---

## 6. 技术选型

| 领域 | 选型 | 理由 |
|------|------|------|
| 语言 | Python 3.12+ | 主力语言，AI 生态最好 |
| 异步 | asyncio | Agent 循环天然适合异步 |
| LLM 调用 | **httpx** (自己封装) | 学习目的 + 更可控，不依赖 openai SDK |
| 浏览器 | **Playwright** | 最强浏览器自动化方案，async API |
| 桌面操控 | **pyautogui** + **Pillow** | 截屏 + 鼠标键盘模拟 |
| 数据库 | **SQLite** (aiosqlite) | 本地存储，零配置 |
| 配置 | **Pydantic Settings** | 类型安全 + 环境变量 |
| CLI | **Rich** + **Prompt Toolkit** | 美观终端交互 |
| 包管理 | **uv** + pyproject.toml | 现代标准 |
| 测试 | **pytest** + pytest-asyncio | 异步测试 |

### 核心依赖（控制在 10 个以内）

```
httpx          # HTTP 客户端（调用 LLM API）
playwright     # 浏览器自动化
pyautogui      # 鼠标键盘模拟
Pillow         # 图像处理（截图）
rich           # 终端美化输出
prompt-toolkit # 交互式命令行
pydantic       # 数据验证 + 配置管理
aiosqlite      # 异步 SQLite
pyyaml         # 配置文件解析
click          # CLI 命令行框架
```

---

## 7. 里程碑计划

### M1: 能对话、能执行命令（第 3-4 天）

```
交付物：在终端跟 Agent 对话，它能帮你执行 Shell 命令和文件操作
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[x] 项目结构 + pyproject.toml
[ ] LLM Provider（OpenAI 兼容 API）
[ ] Agent Loop（ReAct 模式）
[ ] Gateway 消息网关（轻量直通 + 会话管理）
[ ] 工具系统框架 + @tool 装饰器
[ ] 内置工具：shell_exec, read_file, write_file
[ ] CLI 通道（Rich + Prompt Toolkit）
```

### M2: 能操控浏览器（第 5-7 天）

```
交付物：让 Agent 打开浏览器搜索信息、抓取内容 —— 这是第一个「炸裂 demo」
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[ ] Playwright 集成
[ ] 浏览器工具：browser_open, browser_action, page_screenshot
[ ] 网页内容提取 + 结构化
[ ] browser-research Skill
```

### M3: 能看屏幕、能操控桌面（第 8-10 天）

```
交付物：Agent 能截屏、看懂屏幕内容、操控鼠标键盘 —— 这是第二个「炸裂 demo」
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[ ] 多模态 LLM 接入（图片输入）
[ ] 截屏工具：screen_capture, screen_analyze
[ ] 鼠标键盘：mouse_click, keyboard_type
[ ] desktop-assistant Skill
[ ] macOS 权限引导
```

### M4: 完整框架 + 文档（第 11-14 天）

```
交付物：可发布的 v0.1.0，完整的 README、文档、示例
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[ ] Skill 插件系统完整实现
[ ] 记忆系统（短期 + 长期）
[ ] 配置管理 + 首次运行引导
[ ] 5 个内置 Skill 完善
[ ] README（精心打磨，这是门面）
[ ] 录制 demo GIF / 视频
[ ] 发布到 PyPI
```

---

## 8. 发布 & 传播策略

### 8.1 README 的关键元素

一个能火的 README 必须有：

1. **一行代码安装 + 一个 GIF 演示** — 3 秒内抓住注意力
2. **对比表格** — 跟 OpenClaw / LangChain / CrewAI 对比，突出差异
3. **"5 分钟上手" Quick Start** — 复制粘贴就能跑
4. **杀手级 demo**：Agent 操控浏览器搜索 + 截屏看企微消息

### 8.2 传播节奏

| 时间 | 动作 | 平台 |
|------|------|------|
| 发布当天 | 发 GitHub + README + demo GIF | GitHub |
| 第 1 天 | 中文介绍文章 | 掘金 / 知乎 |
| 第 2 天 | 英文介绍文章 | Dev.to / Reddit r/Python |
| 第 3 天 | 「从 OpenClaw 学 Agent 架构」深度技术文 | 掘金 / 知乎 |
| 第 1 周 | 发到 awesome-claws 列表 | GitHub |
| 持续 | 教程系列：「用 Python 从零实现 AI Agent」 | 掘金 / 知乎 |

---

## 9. 设计决策记录

> 以下问题已在讨论中确认：

### ✅ Q1: 模型策略 → 四模型角色调度（已确认）

不是只接一个模型，而是全局配置 4 个模型角色，按任务类型自动路由：

| 角色 | 职责 | 默认推荐 |
|------|------|---------|
| `default` | 日常对话、简单工具调用 | DeepSeek-Chat（便宜快速） |
| `planner` | 任务规划、步骤拆解 | DeepSeek-Chat / Claude Sonnet |
| `reasoner` | 逻辑推理、截屏分析、调试 | GPT-4o（多模态最强） |
| `maker` | 代码生成、报告撰写、文档产出 | Claude Sonnet（产出质量最高） |

每个角色可独立配置 provider、model、参数。用户可以全部配成同一个模型（省事），也可以按需分配（省钱 + 效果好）。

### ✅ Q2: 平台支持 → 跨平台抽象，v1 只实现 macOS（已确认）

- 架构层面：定义 `DesktopController` 抽象基类，所有桌面操控通过抽象接口调用
- v1 实现：只实现 `MacOSController`（pyautogui + osascript + Quartz）
- v2 扩展：新增 `WindowsController` 只需加一个文件，不改任何已有代码
- 浏览器操控（Playwright）天然跨平台，不需要额外处理

### ✅ Q3: 浏览器模式 → 默认有头模式（已确认）

- 默认 `headless: false`（用户能看到浏览器在操作，demo 效果好）
- 可通过配置文件切换为 `headless: true`（后台静默运行）

---

## 附录

### A. 项目名 & 品牌

- **名称**：MiniClaw（小龙虾）
- **Logo**：一只像素风/卡通风的小龙虾 🦞
- **Slogan**：「Your Local AI That Actually Does Things」/「能动手的本地 AI」
- **色调**：红色系（龙虾色）

### B. 参考项目

| 项目 | 参考点 |
|------|--------|
| [OpenClaw](https://github.com/open-claw/open-claw) | 整体架构、Skill 系统、Heartbeat、安全模型 |
| [open-computer-use](https://github.com/coasty-ai/open-computer-use) | 桌面操控方案、截屏+视觉理解工作流 |
| [browser-use](https://browser-use.com/) | Playwright 集成 AI 的方式 |
| [Clawlet](https://github.com/claw-project/clawlet) | 轻量 Python Agent 设计 |
| [Atombot](https://github.com/atombot-ai/atombot) | 500 行核心代码的极简设计 |

### C. 术语表

| 术语 | 含义 |
|------|------|
| Agent Loop | Agent 主循环：输入 → 思考 → 工具调用 → 观察 → 回复 |
| Channel | 交互通道（CLI / HTTP / Telegram） |
| Gateway | 消息路由 + 会话管理 |
| Skill | 技能模块 = SKILL.md（知识/SOP）+ tools.py（工具代码） |
| Tool | Agent 可调用的函数（Shell 执行、浏览器操作、截屏等） |
| Provider | LLM 服务提供方（DeepSeek / Claude / Qwen） |
| Computer Use | AI 通过视觉理解 + 模拟操控来使用电脑的能力 |
