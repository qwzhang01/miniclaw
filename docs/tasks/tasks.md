# MiniClaw 开发任务

> 版本：v1.2 ｜ 日期：2026-04-01 ｜ 作者：avinzhang
>
> 按里程碑组织，每个任务有明确的完成标准。
> 以 [PRD-v1](../requirements/PRD-v1.md) 为唯一真相源，所有任务可追溯到 PRD 需求。

---

## 任务状态说明

| 状态 | 含义 |
|------|------|
| ⬜ TODO | 未开始 |
| 🔵 IN PROGRESS | 进行中 |
| ✅ DONE | 已完成 |
| ⏸️ BLOCKED | 被阻塞 |
| 🚫 CANCELLED | 已取消 |

---

## M0: 项目基建（预计 1 天）

| # | 任务 | 状态 | 完成标准 | 对应 PRD |
|---|------|------|---------|---------|
| 0.1 | 初始化项目结构 + pyproject.toml | ✅ DONE | 目录结构与架构文档一致，10 个依赖配好 | §6 |
| 0.2 | 配置 ruff + mypy | ✅ DONE | `ruff check` 和 `mypy` 通过 | §5.4 |
| 0.3 | 创建 .env.example | ✅ DONE | 列出所有 API Key 环境变量（DEEPSEEK/OPENAI/ANTHROPIC） | F9 |
| 0.4 | 编写需求文档 | ✅ DONE | PRD-v1.md 定稿 | — |
| 0.5 | 编写架构文档 | ✅ DONE | architecture.md 完成 | — |
| 0.6 | 编写代码规范 | ✅ DONE | conventions.md 完成 | — |
| 0.7 | 编写 README | ✅ DONE | README.md 完成 | §8 |
| 0.8 | 入口文件 `__main__.py` + `cli.py` | ✅ DONE | `python -m miniclaw` 和 `miniclaw` 命令能启动 | §7 M1 |
| 0.9 | 结构化日志系统 `utils/logging.py` | ✅ DONE | 统一日志格式，支持 info/debug/error，debug 输出完整 prompt | §5.3 |
| 0.10 | Token 计数 `utils/tokens.py` | ✅ DONE | 按角色统计 input/output token 数，debug 日志输出 | F2 |

---

## M1: 能对话、能执行命令（预计 3-4 天）

> **交付物**：在终端跟 Agent 对话，它能帮你执行 Shell 命令和文件操作
> **对应 PRD**：F1 + F2 + F3 + F6 + F6.5 + F9

### M1.1 LLM Provider 层（PRD F2）

| # | 任务 | 状态 | 完成标准 |
|---|------|------|---------|
| 1.1.1 | 实现 `BaseProvider` 抽象基类 | ✅ DONE | 定义 `chat()` / `chat_stream()` 接口，支持 messages + tools + role 参数 |
| 1.1.2 | 实现 `OpenAIProvider` | ✅ DONE | 能调用 DeepSeek/Qwen/Ollama API 完成对话 + 工具调用（OpenAI 兼容协议） |
| 1.1.3 | 实现 `AnthropicProvider` | ✅ DONE | 能调用 Claude API，tool_use 协议兼容（处理协议差异） |
| 1.1.4 | 实现四模型角色注册 `ModelRoleRegistry` | ✅ DONE | 配置 4 个角色（default/planner/reasoner/maker），按 role 参数路由到对应 Provider |
| 1.1.5 | 流式输出支持 | ✅ DONE | `chat_stream()` 返回 AsyncIterator，支持逐 token 输出 |
| 1.1.6 | 重试 + fallback 机制 | ✅ DONE | 超时自动重试（3 次），任何角色不可用时降级到 default |
| 1.1.7 | Token 计数集成 | ✅ DONE | 每次 chat() 调用后记录 input/output token，按角色累计，debug 日志输出 |

### M1.2 工具系统（PRD F3）

| # | 任务 | 状态 | 完成标准 |
|---|------|------|---------|
| 1.2.1 | 实现 `@tool` 装饰器 + `ToolRegistry` | ✅ DONE | 装饰器注册工具，自动从函数签名生成 JSON Schema（供 LLM 使用） |
| 1.2.2 | 实现 `ToolExecutor`（执行引擎） | ✅ DONE | 完整流程：参数校验 → 安全审批 → 执行 → 格式化结果 → 返回 ToolResult |
| 1.2.3 | 实现安全审批流程 | ✅ DONE | low=自动执行 / high=用户确认(y/n) / critical=二次确认(输入 CONFIRM) |
| 1.2.4 | 实现用户拒绝处理 | ✅ DONE | 拒绝时返回 `ToolResult(success=False, output="用户拒绝执行此操作")`，不中断 Agent Loop |
| 1.2.5 | 内置工具：`shell_exec` | ✅ DONE | risk=high，执行 Shell 命令，返回 stdout，超时 30s |
| 1.2.6 | 内置工具：`read_file` / `write_file` | ✅ DONE | read=low / write=high，带 `allowed_directories` 白名单路径校验 |
| 1.2.7 | 内置工具：`web_search` | ✅ DONE | risk=low，使用 DuckDuckGo（duckduckgo-search 库，免费无 key），备选 Tavily |
| 1.2.8 | 内置工具：`http_request` | ✅ DONE | risk=low，基于 httpx，支持 GET/POST，返回响应文本 |

### M1.3 Agent 核心（PRD F1）

| # | 任务 | 状态 | 完成标准 |
|---|------|------|---------|
| 1.3.1 | 实现 `AgentContext`（上下文管理器） | ✅ DONE | 管理消息历史、动态工具列表（全局+Skill）、活跃 Skill 上下文 |
| 1.3.2 | 实现 `AgentLoop`（ReAct 主循环） | ✅ DONE | 完整流程：组装上下文 → 调 LLM → 解析 → 工具调用/文本回复 → 循环 |
| 1.3.3 | 实现 `ModelRouter`（模型路由器） | ✅ DONE | 按优先级判断：有图→reasoner / 首轮复杂→planner / 产出→maker / 其他→default |
| 1.3.4 | 最大循环次数限制 | ✅ DONE | 默认 10 轮自动停止，返回友好提示 |
| 1.3.5 | 错误恢复机制 | ✅ DONE | 工具失败/超时/拒绝后 Agent 能自行决策（重试/换方案/告知用户） |

### M1.4 Gateway 消息网关（PRD F6.5）

| # | 任务 | 状态 | 完成标准 |
|---|------|------|---------|
| 1.4.1 | 实现 `Gateway.handle_message()` | ✅ DONE | 接收 Channel 消息 → 路由给 Agent → 回传响应 |
| 1.4.2 | 实现 `Session` 管理 | ✅ DONE | 创建/查找/恢复 Session，包含 AgentContext + 时间戳 |
| 1.4.3 | 消息标准化 | ✅ DONE | 将 Channel 原始输入转为内部 `Message(role, content, images, ...)` 格式 |

### M1.5 CLI 通道（PRD F6）

| # | 任务 | 状态 | 完成标准 |
|---|------|------|---------|
| 1.5.1 | 实现 `ChannelProtocol` 抽象接口 | ✅ DONE | 定义 receive / send / confirm / confirm_critical 接口 |
| 1.5.2 | 实现 `CLIChannel`（Rich + Prompt Toolkit） | ✅ DONE | 美观终端交互，彩色区分：用户(白)/Agent(绿)/工具(黄)/错误(红) |
| 1.5.3 | 流式输出展示（打字机效果） | ✅ DONE | Agent 回复逐字显示（对接 chat_stream） |
| 1.5.4 | 工具调用过程可视化 | ✅ DONE | 展示 `[调用工具] xxx → [结果] yyy` |
| 1.5.5 | 实现全部 9 个特殊命令 | ✅ DONE | /help /tools /skills /history /clear /screen /config /reload /exit |

### M1.6 配置管理（PRD F9）

| # | 任务 | 状态 | 完成标准 |
|---|------|------|---------|
| 1.6.1 | Pydantic Settings 配置定义 | ✅ DONE | 覆盖 PRD F9 完整 config.yaml：四模型角色 + 安全 + 浏览器 + 平台 + 日志 |
| 1.6.2 | YAML 配置文件加载 | ✅ DONE | 从 `~/.miniclaw/config.yaml` 加载，支持 `${ENV_VAR}` 变量替换 |
| 1.6.3 | 首次运行引导 | ✅ DONE | 交互式引导：检测配置文件 → 不存在则引导填写 API Key → 生成 config.yaml |

### M1.7 应用组装层 — 端到端集成

> **说明**：这是一个横向的"集成任务"，负责把 M1.1 ~ M1.6 的所有模块串联起来，使整个应用能端到端运行。
> 架构文档 §3.7 "一次完整交互的数据流" 已隐含此需求，但原始任务拆解时遗漏了此项。

| # | 任务 | 状态 | 完成标准 |
|---|------|------|---------|
| 1.7.1 | 实现 `bootstrap.py` 应用组装层 | ✅ DONE | 完整串联：.env 加载 → config → LLM Provider × 4 角色 → ToolRegistry → ToolExecutor → AgentLoop → Gateway → CLIChannel，返回可运行的 (gateway, channel) |
| 1.7.2 | CLI 入口接入 bootstrap | ✅ DONE | `cli.py` 的 `_async_main()` 调用 `bootstrap()` 获取组件，进入异步交互循环，启动失败有友好错误提示 |

### M1 完成检查点 ✓

```
□ miniclaw 命令能启动 CLI 界面（欢迎横幅 + 模型信息）
□ 能与 Agent 正常对话（调用 DeepSeek/Claude）
□ Agent 能自主决定调用 shell_exec 并返回结果
□ 高风险工具（shell_exec）执行前有确认提示
□ 用户拒绝工具执行后 Agent 能正常继续（换方案或告知用户）
□ Gateway 正确路由消息（Channel → Gateway → Agent → Channel）
□ /tools 命令能列出所有可用工具
□ /reload 命令能重新加载 Skill
□ 四模型路由在日志中可观测（--debug 模式）
□ Token 计数在 debug 日志中可见（按角色）
□ 首次运行时自动引导配置
```

---

## M2: 能操控浏览器（预计 2-3 天）

> **交付物**：Agent 能打开浏览器搜索、点击、截图、抓取内容 —— 第一个「炸裂 demo」
> **对应 PRD**：F4 + F7（browser-research Skill）

| # | 任务 | 状态 | 完成标准 |
|---|------|------|---------|
| 2.1 | Playwright 驱动封装 `playwright_driver.py` | ✅ DONE | 统一 browser driver，管理浏览器生命周期（启动/复用/关闭） |
| 2.2 | 内置工具：`browser_open` | ✅ DONE | risk=high，打开指定 URL，使用系统 Chrome（channel="chrome"），返回页面标题和内容摘要 |
| 2.3 | 内置工具：`browser_action` | ✅ DONE | risk=high，点击（CSS选择器/文本）、输入、选择、滚动、等待元素 |
| 2.4 | 内置工具：`page_screenshot` | ✅ DONE | risk=low，截取页面截图（全页/指定区域），返回 base64 |
| 2.5 | 网页内容提取 | ✅ DONE | 提取页面核心文本，去除导航/广告噪音，结构化输出 |
| 2.6 | `browser-research` Skill | ✅ DONE | SKILL.md（调研 SOP）+ tools.py（浏览器调研高级封装） |
| 2.7 | 浏览器复用机制 | ✅ DONE | 多次操作复用同一浏览器实例，避免重复启动 |
| 2.8 | 有头/无头模式切换 | ✅ DONE | 从 config.yaml `browser.headless` 读取，默认 false（PRD Q3） |

### M2 完成检查点 ✓

```
□ "帮我打开掘金搜索 OpenClaw" → 浏览器打开并搜索（有头模式，能看到操作）
□ Agent 能从搜索结果中提取标题和链接，格式化为 Markdown 表格
□ 截图功能正常工作（全页 + 区域）
□ 浏览器复用：多次操作不重复启动 Chrome
□ browser-research Skill 激活后能引导完整调研流程
```

---

## M3: 能看屏幕、能操控桌面（预计 2-3 天）

> **交付物**：Agent 能截屏、看懂屏幕、操控鼠标键盘 —— 第二个「炸裂 demo」
> **对应 PRD**：F5 + F7（desktop-assistant Skill）

| # | 任务 | 状态 | 完成标准 |
|---|------|------|---------|
| 3.1 | `DesktopController` 抽象基类 | ✅ DONE | 定义 6 个接口：capture_screen / click / type_text / hotkey / get_active_window_title / list_windows |
| 3.2 | `MacOSController` 实现 | ✅ DONE | pyautogui + Pillow + osascript + Quartz，实现全部 6 个接口 |
| 3.3 | 平台检测 + 工厂函数 `factory.py` | ✅ DONE | `create_controller()` 自动检测 macOS，非 macOS 抛 NotImplementedError |
| 3.4 | 内置工具：`screen_capture` | ✅ DONE | risk=low，全屏/区域截图，返回 base64 |
| 3.5 | 内置工具：`screen_analyze`（复合工具） | ✅ DONE | risk=low，截图 → 内部调 reasoner LLM → 返回文字描述（唯一允许工具内调 LLM 的特例） |
| 3.6 | 内置工具：`mouse_click` | ✅ DONE | risk=high，在指定坐标 (x, y) 点击，支持 left/right 按钮 |
| 3.7 | 内置工具：`keyboard_type` | ✅ DONE | risk=high，模拟键盘输入文字 |
| 3.8 | 内置工具：`list_windows` | ✅ DONE | risk=low，列出当前可见窗口列表（osascript） |
| 3.9 | macOS 权限检测与引导 | ✅ DONE | 检测辅助功能权限，无权限时输出友好引导（系统设置路径） |
| 3.10 | `desktop-assistant` Skill | ✅ DONE | SKILL.md（桌面操控 SOP）+ 操控工作流 |
| 3.11 | 多模态 LLM 集成 | ✅ DONE | Provider 的 chat() 支持 images 参数（base64 编码），reasoner 角色自动使用 |

### M3 完成检查点 ✓

```
□ "截屏看看桌面有什么" → 截屏 + 分析 + 文字描述
□ "帮我看看企微有没有消息" → 截屏 + 识别企微 + 报告未读数
□ 鼠标点击操作前有确认提示（risk=high）
□ 没有辅助功能权限时有友好引导（非报错崩溃）
□ screen_analyze 能正确调用 reasoner 模型分析截图
```

---

## M4: 完整框架 + 文档（预计 3-4 天）

> **交付物**：可发布的 v0.1.0
> **对应 PRD**：F7（完善）+ F8 + §8

### M4.1 Skill 系统完善（PRD F7）

| # | 任务 | 状态 | 完成标准 |
|---|------|------|---------|
| 4.1.1 | Skill 加载器完善 | ✅ DONE | 扫描 3 个目录（内置/全局/项目），解析 SKILL.md，注册 Skill 工具；支持 `/reload` 手动重载 |
| 4.1.2 | Skill 匹配器 | ✅ DONE | 关键词 + LLM 意图判断，自动激活相关 Skill，动态注入 Skill 工具到 tools 列表 |
| 4.1.3 | `shell` Skill | ✅ DONE | SKILL.md（系统管理 SOP）+ 工具（进程管理、文件操作高级封装） |
| 4.1.4 | `coder` Skill | ✅ DONE | SKILL.md（编程助手 SOP）+ 工具（代码分析、run_tests、git 操作） |
| 4.1.5 | `github` Skill | ✅ DONE | SKILL.md（GitHub 操作 SOP）+ 工具（Issue/PR 管理，依赖 gh CLI） |

### M4.2 记忆系统（PRD F8）

| # | 任务 | 状态 | 完成标准 |
|---|------|------|---------|
| 4.2.1 | 短期记忆 `short_term.py` | ✅ DONE | 内存中维护当前会话的对话历史（Message 列表） |
| 4.2.2 | 长期记忆 `long_term.py` | ✅ DONE | SQLite FTS5 全文搜索，跨会话持久化用户偏好和重要信息 |
| 4.2.3 | 上下文窗口管理 | ✅ DONE | 历史接近 token 上限时，调用 `default` 模型自动摘要压缩（省钱优先） |
| 4.2.4 | 会话持久化 | ✅ DONE | Session 数据存入 SQLite，退出后下次可继续上次对话 |

### M4.3 文档 & 发布（PRD §8）

| # | 任务 | 状态 | 完成标准 |
|---|------|------|---------|
| 4.3.1 | README 最终打磨 | ✅ DONE | 包含 demo GIF、完整 Quick Start、对比表格、架构图 |
| 4.3.2 | 录制 demo GIF / 视频 | ⬜ TODO | 至少 2 个：① 浏览器调研 ② 截屏看企微消息 |
| 4.3.3 | 编写 CONTRIBUTING.md | ✅ DONE | 贡献指南（开发环境搭建、代码规范、PR 流程） |
| 4.3.4 | PyPI 发布配置 | ✅ DONE | pyproject.toml 完善，`pip install miniclaw` 可用 |
| 4.3.5 | GitHub Release v0.1.0 | ⬜ TODO | 打 tag、写 changelog、发布 Release |

### M4 完成检查点 ✓

```
□ pip install miniclaw 安装成功
□ miniclaw 首次运行引导配置完成
□ 5 个内置 Skill 全部可用（shell / browser-research / desktop-assistant / coder / github）
□ 记忆系统能跨会话记住信息
□ /reload 命令能重新加载 Skill
□ README 中的所有示例都能正常运行
□ demo GIF 展示清晰（浏览器操控 + 桌面操控）
```

---

## 代码优化任务（v1 发布前打磨）

> **说明**：在 v1 功能已基本完成（97%）的基础上，对现有代码进行质量优化和规范性修复。
> 优先级说明：P0 = 必须在 v1 发布前修复 / P1 = 建议修复 / P2 = 可延后

### bootstrap.py 应用组装层优化

| # | 任务 | 状态 | 优先级 | 说明 |
|---|------|------|--------|------|
| OPT-1 | `_load_env_file()` 替换为 python-dotenv | ✅ DONE | P1 | 新增 `python-dotenv` 依赖（依赖数 10→11），用 `load_dotenv(override=False)` 替代手写解析，删除 `_load_env_file()` 函数 |
| OPT-2 | `bootstrap()` 返回值解耦 CLIChannel 具体类型 | ✅ DONE | P0 | 返回类型改为 `tuple[Gateway, ChannelProtocol]`，使 bootstrap 层不绑定具体通道实现 |

### 其他发现的可完善项

| # | 任务 | 状态 | 优先级 | 说明 |
|---|------|------|--------|------|
| OPT-3 | README 路线图状态同步 | ✅ DONE | P0 | M1-M3 路线图已更新为 `[x]` 完成状态 |
| OPT-4 | CLI 斜杠命令实现与任务状态不一致 | ✅ DONE | P1 | `/skills`、`/history`、`/screen`、`/config`、`/reload` 共 5 个命令已补充实际实现 |
| OPT-5 | `_create_provider()` 缺少 Anthropic 路由 | ✅ DONE | P1 | `_create_provider()` 现根据 `provider` 字段路由：`anthropic` → AnthropicProvider，其他 → OpenAIProvider |
| OPT-6 | `config/wizard.py` 首次运行引导缺失 | ✅ DONE | P1 | 已创建 `config/wizard.py`，交互式引导用户选择平台、填写 API Key、生成 config.yaml + .env，集成到 CLI 启动流程 |

---

## OP: 架构优化 — 借鉴 Claude Code 模式（预计 4 天）

> **背景**：基于 Claude Code 512K 行泄露源码的架构分析，识别出 MiniClaw 的 7 个关键优化点。
> 详细分析见 [optimization-plan.md](./optimization-plan.md)。
>
> **核心问题**：多个 M4 任务代码已写好但未真正接入（ShortTermMemory、LongTermMemory、Skill 注入），
> System Prompt 与实际工具不匹配，长对话无 token 保护。

---

### OP1: System Prompt 全面升级 [P0]

| # | 任务 | 状态 | 说明 |
|---|------|------|------|
| OP1.1 | 补全系统提示词工具描述 | ✅ DONE | 列出全部 11 个内置工具，按能力域分组 |
| OP1.2 | 注入环境上下文信息 | ✅ DONE | 动态注入 OS/CWD/时间/Python 版本 |
| OP1.3 | 添加行为约束指令 | ✅ DONE | 优先低风险工具、文件操作前检查路径 |
| OP1.4 | 系统提示词模板化 | ✅ DONE | 支持动态拼装（环境 + 工具 + Skill） |

### OP2: ShortTermMemory 接入 AgentContext [P0]

| # | 任务 | 状态 | 说明 |
|---|------|------|------|
| OP2.1 | AgentContext 集成 ShortTermMemory | ✅ DONE | 消息管理委托给 ShortTermMemory |
| OP2.2 | AgentLoop 压缩触发点 | ✅ DONE | 每轮循环前检查 needs_compression() |
| OP2.3 | bootstrap.py 创建 ShortTermMemory | ✅ DONE | 创建实例并注入 AgentContext |

### OP3: 工具输出截断 [P1]

| # | 任务 | 状态 | 说明 |
|---|------|------|------|
| OP3.1 | 工具输出最大长度限制 | ✅ DONE | 超 8000 字符截断 + 提示 |
| OP3.2 | 可配置截断阈值 | ✅ DONE | config.yaml 增加 agent.tool_output_max_chars |
| OP3.3 | read_file 增加行数限制参数 | ✅ DONE | 默认 200 行，超过提示分段 |

### OP4: Skill 提示词注入 [P1]

| # | 任务 | 状态 | 说明 |
|---|------|------|------|
| OP4.1 | AgentContext 增加 Skill 上下文注入 | ✅ DONE | inject_skill_context() 追加到 system prompt |
| OP4.2 | AgentLoop 匹配后触发注入 | ✅ DONE | Skill 激活时调用注入 |
| OP4.3 | Skill 上下文随 /clear 清除 | ✅ DONE | 清空时同步清除 Skill 内容 |

### OP5: LongTermMemory 接入 [P2]

| # | 任务 | 状态 | 说明 |
|---|------|------|------|
| OP5.1 | bootstrap.py 初始化 LongTermMemory | ✅ DONE | 创建实例 + await init() |
| OP5.2 | Gateway 退出时保存会话 | ✅ DONE | /exit 时调用 save_session() |
| OP5.3 | Gateway 启动时恢复会话 | ✅ DONE | --continue 参数恢复上次对话 |
| OP5.4 | 记忆检索注入对话 | ✅ DONE | 新对话开始时检索相关记忆注入 system prompt |

### OP6: 流式输出接入 AgentLoop [P2]

| # | 任务 | 状态 | 说明 |
|---|------|------|------|
| OP6.1 | AgentLoop 增加 stream 模式 | ✅ DONE | 使用 chat_stream() 替代 chat() |
| OP6.2 | 流式工具调用解析 | ✅ DONE | 正确累积并解析流式工具调用 |
| OP6.3 | CLIChannel 真正流式渲染 | ✅ DONE | 对接流式回调，逐 token 输出 |

### OP7: Token 预算管理 [P2]

| # | 任务 | 状态 | 说明 |
|---|------|------|------|
| OP7.1 | AgentContext 增加 token 统计 | ✅ DONE | 每次添加消息后累计 token 数 |
| OP7.2 | AgentLoop 预算检查 | ✅ DONE | 接近上限时触发压缩或警告 |
| OP7.3 | Debug 日志输出 token 预算 | ✅ DONE | --debug 输出已用/上限/剩余 |

### OP 进度概览

| 优化项 | 任务数 | 优先级 | 预计天数 |
|--------|--------|--------|---------|
| OP1: System Prompt 升级 | 4 | P0 | 0.5 天 |
| OP2: ShortTermMemory 接入 | 3 | P0 | 0.5 天 |
| OP3: 工具输出截断 | 3 | P1 | 0.5 天 |
| OP4: Skill 提示注入 | 3 | P1 | 0.5 天 |
| OP5: LongTermMemory 接入 | 4 | P2 | 1 天 |
| OP6: 流式输出接入 | 3 | P2 | 1 天 |
| OP7: Token 预算管理 | 3 | P2 | 0.5 天 |
| **合计** | **23** | — | **~4 天** |

### OP 建议开发顺序

```
第 1 天: OP1（System Prompt 升级）+ OP2（ShortTermMemory 接入）← P0 必须先做
第 2 天: OP3（工具输出截断）+ OP4（Skill 提示注入）← P1 让已写代码生效
第 3 天: OP5（LongTermMemory 接入）+ OP7（Token 预算管理）← P2 增强
第 4 天: OP6（流式输出接入）← P2 体验提升
```

---

## M5: 多渠道 + 主动能力 + 生产化（预计 10-14 天）

> **背景**：M0-M4 已完成核心框架（CLI 对话 + 浏览器操控 + 桌面操控 + Skill + 记忆）。
> M5 阶段借鉴 avin-kit/MiniClaw（V1 原型版本）中已验证的功能，补全多渠道接入、
> 主动调度、Web UI、Docker 部署等生产化能力。
>
> **对应 PRD**：F10 ~ F16

---

### M5.1 Telegram Bot 通道（PRD F10，预计 2 天）

| # | 任务 | 状态 | 完成标准 |
|---|------|------|---------|
| 5.1.1 | 新增 `channels/telegram_channel.py` 实现 `ChannelProtocol` | ⬜ TODO | 实现 receive/send/confirm/send_tool_call 四个接口，使用 `python-telegram-bot>=21` |
| 5.1.2 | 实现 Telegram Bot 命令处理 | ⬜ TODO | 支持 `/start`（欢迎）、`/help`（帮助）、`/clear`（清空会话）、`/status`（Agent 状态） |
| 5.1.3 | 实现普通文本消息处理 | ⬜ TODO | 文本消息 → `InboundMessage` → Gateway.handle_message() → 回复，发送 typing 状态 |
| 5.1.4 | 长消息分段发送 | ⬜ TODO | 超过 4000 字符自动分段，每段独立发送 |
| 5.1.5 | 多用户隔离 | ⬜ TODO | 每个 Telegram `user_id` 映射独立 Session（`tg-{user_id}`），不同用户互不干扰 |
| 5.1.6 | 主动推送接口 | ⬜ TODO | 暴露 `send_to_user(user_id, text)` 方法，供心跳/提醒模块调用 |
| 5.1.7 | Telegram 配置项 | ⬜ TODO | config.yaml 增加 `channels.telegram` 配置块，支持 `${TELEGRAM_BOT_TOKEN}` |
| 5.1.8 | 添加 `python-telegram-bot>=21` 依赖 | ⬜ TODO | pyproject.toml 中作为可选依赖 `[telegram]` |

**M5.1 完成检查点**：
```
□ TELEGRAM_BOT_TOKEN 配置后 miniclaw --mode telegram 能启动
□ 手机发消息给 Bot 能收到 Agent 回复
□ /start /help /clear /status 命令正常工作
□ 两个不同 Telegram 用户的会话互不干扰
□ Agent 回复超长文本时自动分段
```

---

### M5.2 Gradio Web UI（PRD F11，预计 2 天）

| # | 任务 | 状态 | 完成标准 |
|---|------|------|---------|
| 5.2.1 | 新增 `channels/gradio_channel.py` 实现 `ChannelProtocol` | ⬜ TODO | Gradio ChatInterface 封装，同步桥接异步调用 |
| 5.2.2 | 新增 `ui/app.py` 构建 Gradio 应用 | ⬜ TODO | 左侧聊天区 + 右侧状态面板（模型/工具/Skill），Soft 主题，红色品牌色 |
| 5.2.3 | 内置示例问题 | ⬜ TODO | 5 个示例：搜索新闻 / 写代码 / 设提醒 / 创建文件 / 截屏分析 |
| 5.2.4 | 状态面板实时刷新 | ⬜ TODO | 点击"刷新"按钮更新：活跃用户数、总消息数、Token 统计、启动时间 |
| 5.2.5 | Skill 列表展示 | ⬜ TODO | 右侧面板列出已加载 Skill 名称和描述 |
| 5.2.6 | 添加 `gradio>=4.30` 依赖 | ⬜ TODO | pyproject.toml 中作为可选依赖 `[web]` |

**M5.2 完成检查点**：
```
□ miniclaw --mode gradio 启动后浏览器打开 http://localhost:7860
□ 在 Web 界面能正常与 Agent 对话
□ 右侧面板显示模型配置和工具列表
□ 示例问题点击后自动发送
```

---

### M5.3 心跳调度 + Cron 定时任务（PRD F12，预计 2 天）

| # | 任务 | 状态 | 完成标准 |
|---|------|------|---------|
| 5.3.1 | 新增 `scheduler/heartbeat.py` | ⬜ TODO | 封装 APScheduler AsyncIOScheduler，支持 IntervalTrigger 和 CronTrigger |
| 5.3.2 | 提醒检查任务 | ⬜ TODO | 每分钟扫描 `~/.miniclaw/data/reminders.json`，到期提醒通过 Channel 推送 |
| 5.3.3 | 每日总结任务 | ⬜ TODO | 可配置 cron 表达式（默认每天 9:00），调用 default 模型生成当日摘要 |
| 5.3.4 | 自定义 cron 注册 | ⬜ TODO | 暴露 `add_cron_job(func, cron_expr, job_id)` API，解析 5 段 cron 格式 |
| 5.3.5 | 内置工具：`calendar`（add/list/delete） | ⬜ TODO | risk=low，提醒数据 JSON 持久化，支持 ISO 8601 时间格式 |
| 5.3.6 | 心跳回调接入 Channel | ⬜ TODO | 提醒到期时通过活跃 Channel（Telegram/CLI）推送消息 |
| 5.3.7 | 配置项 | ⬜ TODO | config.yaml 增加 `scheduler` 配置块（enabled/cron/interval） |
| 5.3.8 | 添加 `apscheduler>=3.10` 依赖 | ⬜ TODO | pyproject.toml 主依赖 |

**M5.3 完成检查点**：
```
□ "提醒我 5 分钟后喝水" → 5 分钟后收到提醒消息
□ /calendar list 能列出所有待办提醒
□ 每日总结 cron 任务能定时触发
□ Telegram 渠道能收到主动推送的提醒
```

---

### M5.4 向量语义记忆（PRD F13，预计 1-2 天）

| # | 任务 | 状态 | 完成标准 |
|---|------|------|---------|
| 5.4.1 | 新增 `memory/vector_memory.py` | ⬜ TODO | 封装 ChromaDB PersistentClient，支持 add/search/delete，cosine 相似度 |
| 5.4.2 | 统一记忆管理器 `MemoryManager` | ⬜ TODO | 整合三层记忆：短期（内存）+ 长期（SQLite FTS5）+ 向量（ChromaDB），统一接口 |
| 5.4.3 | 对话前记忆检索注入 | ⬜ TODO | AgentContext.build_messages() 前自动检索相关记忆，注入 system prompt |
| 5.4.4 | 内置工具：`memory`（save/search/list_recent） | ⬜ TODO | risk=low，Agent 可主动保存重要信息到长期记忆 |
| 5.4.5 | ChromaDB 作为可选依赖 | ⬜ TODO | `pip install miniclaw[vector]`，未安装时自动降级到 FTS5 |
| 5.4.6 | 按 user_id 隔离记忆 | ⬜ TODO | ChromaDB where 条件按 user_id 过滤 |

**M5.4 完成检查点**：
```
□ "记住我喜欢用 Vim" → 保存成功
□ 下次对话 "我喜欢用什么编辑器" → 能检索到 Vim
□ 未安装 ChromaDB 时自动降级到 FTS5，不报错
```

---

### M5.5 Docker 一键部署（PRD F14，预计 1 天）

| # | 任务 | 状态 | 完成标准 |
|---|------|------|---------|
| 5.5.1 | 编写 `Dockerfile` | ⬜ TODO | 多阶段构建，基于 python:3.12-slim，可选安装 Playwright（`INSTALL_BROWSER` 参数） |
| 5.5.2 | 编写 `docker-compose.yml` | ⬜ TODO | 两个服务：miniclaw-web（Gradio，默认启动）+ miniclaw-telegram（可选 profile） |
| 5.5.3 | 数据 volume 挂载 | ⬜ TODO | `~/.miniclaw/data` 挂载持久化，包含 SQLite + ChromaDB + reminders.json |
| 5.5.4 | 健康检查 | ⬜ TODO | Dockerfile HEALTHCHECK + docker-compose healthcheck 配置 |
| 5.5.5 | 环境变量注入 | ⬜ TODO | docker-compose 通过 `env_file: .env` 和 `environment` 注入配置 |

**M5.5 完成检查点**：
```
□ docker compose up -d 一键启动
□ http://localhost:7860 能访问 Gradio UI
□ docker compose --profile telegram up 同时启动 Telegram Bot
□ 重启容器后数据不丢失
```

---

### M5.6 多渠道同时运行（PRD F15，预计 1 天）

| # | 任务 | 状态 | 完成标准 |
|---|------|------|---------|
| 5.6.1 | CLI 入口增加 `--mode` 参数 | ⬜ TODO | 支持 `cli`（默认）/ `telegram` / `gradio` / `all` |
| 5.6.2 | `all` 模式多渠道共享 Gateway | ⬜ TODO | 所有渠道共享同一个 Gateway/AgentLoop/ToolRegistry/Memory 实例 |
| 5.6.3 | Session ID 渠道前缀隔离 | ⬜ TODO | CLI: `cli-default`，Telegram: `tg-{user_id}`，Gradio: `gradio-{session_id}` |
| 5.6.4 | bootstrap.py 扩展 | ⬜ TODO | 按 mode 参数创建对应 Channel 组合，返回 (gateway, channels_list) |

**M5.6 完成检查点**：
```
□ miniclaw --mode all 同时启动 CLI + Telegram + Gradio
□ 三个渠道共享工具和 Skill 列表
□ 不同渠道的用户会话互不干扰
```

---

### M5.7 代码执行沙箱（PRD F16，预计 1 天）

| # | 任务 | 状态 | 完成标准 |
|---|------|------|---------|
| 5.7.1 | 新增内置工具 `code_exec` | ⬜ TODO | risk=critical，支持 Python 和 Shell 代码执行，超时 30s |
| 5.7.2 | 正则危险模式检测 | ⬜ TODO | 拦截 `rm -rf /`、`sudo`、`fork bomb`、`eval()`、`__import__()` 等 |
| 5.7.3 | Docker 沙箱执行（可选） | ⬜ TODO | 配置 `sandbox_enabled=true` 时通过 Docker 容器执行（无网络/256MB/0.5CPU/50进程） |
| 5.7.4 | 配置项 | ⬜ TODO | config.yaml `security.sandbox_enabled` + `security.code_exec_timeout` |

**M5.7 完成检查点**：
```
□ "帮我写个斐波那契函数并运行" → 代码生成 + 执行 + 返回结果
□ "rm -rf /" 被安全拦截
□ 代码执行前需用户输入 CONFIRM 确认（risk=critical）
□ sandbox_enabled=true 时使用 Docker 容器执行
```

---

### M5 进度概览

| 子任务 | 任务数 | 对应 PRD | 预计天数 |
|--------|--------|---------|---------|
| M5.1: Telegram Bot | 8 | F10 | 2 天 |
| M5.2: Gradio Web UI | 6 | F11 | 2 天 |
| M5.3: 心跳 + Cron | 8 | F12 | 2 天 |
| M5.4: 向量记忆 | 6 | F13 | 1-2 天 |
| M5.5: Docker 部署 | 5 | F14 | 1 天 |
| M5.6: 多渠道运行 | 4 | F15 | 1 天 |
| M5.7: 代码执行沙箱 | 4 | F16 | 1 天 |
| **合计** | **41** | — | **10-14 天** |

---

### M5 建议开发顺序

```
第 1-2 天: M5.3 心跳 + Cron（核心功能，不依赖其他模块）
第 3-4 天: M5.1 Telegram Bot（多渠道基础，需先验证 ChannelProtocol 扩展性）
第 5-6 天: M5.2 Gradio Web UI（有了 Telegram 经验后快速复用）
第 7 天:   M5.6 多渠道同时运行（串联 M5.1 + M5.2）
第 8-9 天: M5.4 向量记忆（独立模块，随时可做）
第 10 天:  M5.7 代码执行沙箱（安全增强）
第 11 天:  M5.5 Docker 部署（打包发布，最后做）
```

---

## M6+: 未来任务（M5 之后）— PRD §4.3 P3

| # | 任务 | 优先级 | 说明 |
|---|------|--------|------|
| 6.1 | 多 Agent 协作 | P3 | Supervisor 调度模式 |
| 6.2 | 企微 API 集成 | P3 | 通过机器人 API 直接收发消息 |
| 6.3 | Windows 支持 | P3 | 实现 WindowsController（只需加一个文件） |
| 6.4 | Token 费用估算 | P3 | 基于 token 计数的实时费用展示 |
| 6.5 | HTTP API 通道 | P3 | FastAPI WebSocket，支持前端 UI 或第三方集成 |
| 6.6 | RAG 文档问答 | P3 | 基于向量记忆的本地文档问答 |
| 6.7 | 语音输入 | P3 | Whisper 语音识别 |
| 6.8 | 技能市场 Hub | P3 | 在线分享和下载自定义 Skill |
| 6.9 | 可视化工作区 | P3 | WebCanvas 风格的任务执行可视化 |

---

## 进度概览

| 里程碑 | 任务数 | 完成数 | 进度 |
|--------|--------|--------|------|
| M0: 项目基建 | 10 | 10 | ███████████████ 100% |
| M1: 能对话 | 33 | 33 | ███████████████ 100% |
| M2: 能操控浏览器 | 8 | 8 | ███████████████ 100% |
| M3: 能操控桌面 | 11 | 11 | ███████████████ 100% |
| M4: 完整框架 | 14 | 12 | █████████████░░ 86% |
| OP: 架构优化 | 23 | 23 | ███████████████ 100% |
| M5: 多渠道+主动+生产化 | 41 | 0 | ░░░░░░░░░░░░░░░ 0% |
| **总计** | **140** | **97** | **██████████░░░░░ 69%** |

---

## PRD 需求覆盖检查

| PRD 需求 | 优先级 | 覆盖任务 | 状态 |
|----------|--------|---------|------|
| F1: Agent 核心循环 | P0 | M1.3 (1.3.1-1.3.5) | ✅ 已覆盖 |
| F2: 四模型调度 | P0 | M1.1 (1.1.1-1.1.7) | ✅ 已覆盖 |
| F3: 工具系统 | P0 | M1.2 (1.2.1-1.2.8) | ✅ 已覆盖（含用户拒绝处理） |
| F4: 浏览器操控 | P0 | M2 (2.1-2.8) | ✅ 已覆盖 |
| F5: 桌面操控 | P0 | M3 (3.1-3.11) | ✅ 已覆盖（含跨平台抽象 + macOS 权限） |
| F6: CLI 交互 | P0 | M1.5 (1.5.1-1.5.5) | ✅ 已覆盖（9 个命令全部列出） |
| F6.5: Gateway | P0 | M1.4 (1.4.1-1.4.3) | ✅ 已覆盖 |
| F7: Skill 系统 | P1 | M4.1 (4.1.1-4.1.5) | ✅ 已覆盖（含 /reload + 工具共存规则） |
| F8: 记忆系统 | P1 | M4.2 (4.2.1-4.2.4) | ✅ 已覆盖（含 default 模型摘要） |
| F9: 配置管理 | P1 | M1.6 (1.6.1-1.6.3) | ✅ 已覆盖 |
| F10: Telegram Bot | P2 | M5.1 (5.1.1-5.1.8) | ⬜ 待开发 |
| F11: Gradio Web UI | P2 | M5.2 (5.2.1-5.2.6) | ⬜ 待开发 |
| F12: 心跳 + Cron | P2 | M5.3 (5.3.1-5.3.8) | ⬜ 待开发 |
| F13: 向量语义记忆 | P2 | M5.4 (5.4.1-5.4.6) | ⬜ 待开发 |
| F14: Docker 部署 | P2 | M5.5 (5.5.1-5.5.5) | ⬜ 待开发 |
| F15: 多渠道运行 | P2 | M5.6 (5.6.1-5.6.4) | ⬜ 待开发 |
| F16: 代码执行沙箱 | P2 | M5.7 (5.7.1-5.7.4) | ⬜ 待开发 |
| §5.3: 可观测性 | — | M0.9 + M1.1.7 | ✅ 已覆盖（日志 + token） |
| §3.7: 端到端集成 | — | M1.7 (1.7.1-1.7.2) | ✅ 已覆盖（bootstrap 组装层） |

---

## 架构优化覆盖检查

> 基于 Claude Code 泄露源码分析，识别出的 MiniClaw 优化点。
> 详细分析文档：[optimization-plan.md](./optimization-plan.md)

| 优化点 | 优先级 | 覆盖任务 | 状态 |
|--------|--------|---------|------|
| System Prompt 与实际工具不匹配 | P0 | OP1 (OP1.1-OP1.4) | ✅ 已完成 |
| ShortTermMemory 未接入 AgentContext | P0 | OP2 (OP2.1-OP2.3) | ✅ 已完成 |
| 工具输出无截断保护 | P1 | OP3 (OP3.1-OP3.3) | ✅ 已完成 |
| Skill SKILL.md 内容未注入 prompt | P1 | OP4 (OP4.1-OP4.3) | ✅ 已完成 |
| LongTermMemory 未初始化 | P2 | OP5 (OP5.1-OP5.4) | ✅ 已完成 |
| 流式输出未接入 AgentLoop | P2 | OP6 (OP6.1-OP6.3) | ✅ 已完成 |
| Token 预算无感知 | P2 | OP7 (OP7.1-OP7.3) | ✅ 已完成 |
