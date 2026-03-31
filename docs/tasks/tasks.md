# MiniClaw 开发任务

> 版本：v1.1 ｜ 日期：2026-03-29 ｜ 作者：avinzhang
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
| 1.1.1 | 实现 `BaseProvider` 抽象基类 | ⬜ TODO | 定义 `chat()` / `chat_stream()` 接口，支持 messages + tools + role 参数 |
| 1.1.2 | 实现 `OpenAIProvider` | ⬜ TODO | 能调用 DeepSeek/Qwen/Ollama API 完成对话 + 工具调用（OpenAI 兼容协议） |
| 1.1.3 | 实现 `AnthropicProvider` | ⬜ TODO | 能调用 Claude API，tool_use 协议兼容（处理协议差异） |
| 1.1.4 | 实现四模型角色注册 `ModelRoleRegistry` | ⬜ TODO | 配置 4 个角色（default/planner/reasoner/maker），按 role 参数路由到对应 Provider |
| 1.1.5 | 流式输出支持 | ⬜ TODO | `chat_stream()` 返回 AsyncIterator，支持逐 token 输出 |
| 1.1.6 | 重试 + fallback 机制 | ⬜ TODO | 超时自动重试（3 次），任何角色不可用时降级到 default |
| 1.1.7 | Token 计数集成 | ⬜ TODO | 每次 chat() 调用后记录 input/output token，按角色累计，debug 日志输出 |

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
| 1.3.1 | 实现 `AgentContext`（上下文管理器） | ⬜ TODO | 管理消息历史、动态工具列表（全局+Skill）、活跃 Skill 上下文 |
| 1.3.2 | 实现 `AgentLoop`（ReAct 主循环） | ⬜ TODO | 完整流程：组装上下文 → 调 LLM → 解析 → 工具调用/文本回复 → 循环 |
| 1.3.3 | 实现 `ModelRouter`（模型路由器） | ⬜ TODO | 按优先级判断：有图→reasoner / 首轮复杂→planner / 产出→maker / 其他→default |
| 1.3.4 | 最大循环次数限制 | ⬜ TODO | 默认 10 轮自动停止，返回友好提示 |
| 1.3.5 | 错误恢复机制 | ⬜ TODO | 工具失败/超时/拒绝后 Agent 能自行决策（重试/换方案/告知用户） |

### M1.4 Gateway 消息网关（PRD F6.5）

| # | 任务 | 状态 | 完成标准 |
|---|------|------|---------|
| 1.4.1 | 实现 `Gateway.handle_message()` | ⬜ TODO | 接收 Channel 消息 → 路由给 Agent → 回传响应 |
| 1.4.2 | 实现 `Session` 管理 | ⬜ TODO | 创建/查找/恢复 Session，包含 AgentContext + 时间戳 |
| 1.4.3 | 消息标准化 | ⬜ TODO | 将 Channel 原始输入转为内部 `Message(role, content, images, ...)` 格式 |

### M1.5 CLI 通道（PRD F6）

| # | 任务 | 状态 | 完成标准 |
|---|------|------|---------|
| 1.5.1 | 实现 `ChannelProtocol` 抽象接口 | ⬜ TODO | 定义 receive / send / confirm / confirm_critical 接口 |
| 1.5.2 | 实现 `CLIChannel`（Rich + Prompt Toolkit） | ⬜ TODO | 美观终端交互，彩色区分：用户(白)/Agent(绿)/工具(黄)/错误(红) |
| 1.5.3 | 流式输出展示（打字机效果） | ⬜ TODO | Agent 回复逐字显示（对接 chat_stream） |
| 1.5.4 | 工具调用过程可视化 | ⬜ TODO | 展示 `[调用工具] xxx → [结果] yyy` |
| 1.5.5 | 实现全部 9 个特殊命令 | ⬜ TODO | /help /tools /skills /history /clear /screen /config /reload /exit |

### M1.6 配置管理（PRD F9）

| # | 任务 | 状态 | 完成标准 |
|---|------|------|---------|
| 1.6.1 | Pydantic Settings 配置定义 | ⬜ TODO | 覆盖 PRD F9 完整 config.yaml：四模型角色 + 安全 + 浏览器 + 平台 + 日志 |
| 1.6.2 | YAML 配置文件加载 | ⬜ TODO | 从 `~/.miniclaw/config.yaml` 加载，支持 `${ENV_VAR}` 变量替换 |
| 1.6.3 | 首次运行引导 | ⬜ TODO | 交互式引导：检测配置文件 → 不存在则引导填写 API Key → 生成 config.yaml |

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
| 2.1 | Playwright 驱动封装 `playwright_driver.py` | ⬜ TODO | 统一 browser driver，管理浏览器生命周期（启动/复用/关闭） |
| 2.2 | 内置工具：`browser_open` | ⬜ TODO | risk=high，打开指定 URL，使用系统 Chrome（channel="chrome"），返回页面标题和内容摘要 |
| 2.3 | 内置工具：`browser_action` | ⬜ TODO | risk=high，点击（CSS选择器/文本）、输入、选择、滚动、等待元素 |
| 2.4 | 内置工具：`page_screenshot` | ⬜ TODO | risk=low，截取页面截图（全页/指定区域），返回 base64 |
| 2.5 | 网页内容提取 | ⬜ TODO | 提取页面核心文本，去除导航/广告噪音，结构化输出 |
| 2.6 | `browser-research` Skill | ⬜ TODO | SKILL.md（调研 SOP）+ tools.py（浏览器调研高级封装） |
| 2.7 | 浏览器复用机制 | ⬜ TODO | 多次操作复用同一浏览器实例，避免重复启动 |
| 2.8 | 有头/无头模式切换 | ⬜ TODO | 从 config.yaml `browser.headless` 读取，默认 false（PRD Q3） |

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
| 3.1 | `DesktopController` 抽象基类 | ⬜ TODO | 定义 6 个接口：capture_screen / click / type_text / hotkey / get_active_window_title / list_windows |
| 3.2 | `MacOSController` 实现 | ⬜ TODO | pyautogui + Pillow + osascript + Quartz，实现全部 6 个接口 |
| 3.3 | 平台检测 + 工厂函数 `factory.py` | ⬜ TODO | `create_controller()` 自动检测 macOS，非 macOS 抛 NotImplementedError |
| 3.4 | 内置工具：`screen_capture` | ⬜ TODO | risk=low，全屏/区域截图，返回 base64 |
| 3.5 | 内置工具：`screen_analyze`（复合工具） | ⬜ TODO | risk=low，截图 → 内部调 reasoner LLM → 返回文字描述（唯一允许工具内调 LLM 的特例） |
| 3.6 | 内置工具：`mouse_click` | ⬜ TODO | risk=high，在指定坐标 (x, y) 点击，支持 left/right 按钮 |
| 3.7 | 内置工具：`keyboard_type` | ⬜ TODO | risk=high，模拟键盘输入文字 |
| 3.8 | 内置工具：`list_windows` | ⬜ TODO | risk=low，列出当前可见窗口列表（osascript） |
| 3.9 | macOS 权限检测与引导 | ⬜ TODO | 检测辅助功能权限，无权限时输出友好引导（系统设置路径） |
| 3.10 | `desktop-assistant` Skill | ⬜ TODO | SKILL.md（桌面操控 SOP）+ 操控工作流 |
| 3.11 | 多模态 LLM 集成 | ⬜ TODO | Provider 的 chat() 支持 images 参数（base64 编码），reasoner 角色自动使用 |

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
| 4.1.1 | Skill 加载器完善 | ⬜ TODO | 扫描 3 个目录（内置/全局/项目），解析 SKILL.md，注册 Skill 工具；支持 `/reload` 手动重载 |
| 4.1.2 | Skill 匹配器 | ⬜ TODO | 关键词 + LLM 意图判断，自动激活相关 Skill，动态注入 Skill 工具到 tools 列表 |
| 4.1.3 | `shell` Skill | ⬜ TODO | SKILL.md（系统管理 SOP）+ 工具（进程管理、文件操作高级封装） |
| 4.1.4 | `coder` Skill | ⬜ TODO | SKILL.md（编程助手 SOP）+ 工具（代码分析、run_tests、git 操作） |
| 4.1.5 | `github` Skill | ⬜ TODO | SKILL.md（GitHub 操作 SOP）+ 工具（Issue/PR 管理，依赖 gh CLI） |

### M4.2 记忆系统（PRD F8）

| # | 任务 | 状态 | 完成标准 |
|---|------|------|---------|
| 4.2.1 | 短期记忆 `short_term.py` | ⬜ TODO | 内存中维护当前会话的对话历史（Message 列表） |
| 4.2.2 | 长期记忆 `long_term.py` | ⬜ TODO | SQLite FTS5 全文搜索，跨会话持久化用户偏好和重要信息 |
| 4.2.3 | 上下文窗口管理 | ⬜ TODO | 历史接近 token 上限时，调用 `default` 模型自动摘要压缩（省钱优先） |
| 4.2.4 | 会话持久化 | ⬜ TODO | Session 数据存入 SQLite，退出后下次可继续上次对话 |

### M4.3 文档 & 发布（PRD §8）

| # | 任务 | 状态 | 完成标准 |
|---|------|------|---------|
| 4.3.1 | README 最终打磨 | ⬜ TODO | 包含 demo GIF、完整 Quick Start、对比表格、架构图 |
| 4.3.2 | 录制 demo GIF / 视频 | ⬜ TODO | 至少 2 个：① 浏览器调研 ② 截屏看企微消息 |
| 4.3.3 | 编写 CONTRIBUTING.md | ⬜ TODO | 贡献指南（开发环境搭建、代码规范、PR 流程） |
| 4.3.4 | PyPI 发布配置 | ⬜ TODO | pyproject.toml 完善，`pip install miniclaw` 可用 |
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

## M5+: 未来任务（v1 之后）— PRD §4.3

| # | 任务 | 优先级 | 说明 |
|---|------|--------|------|
| 5.1 | Telegram 通道 | P2 | 手机远程操控电脑 |
| 5.2 | HTTP API 通道 | P2 | FastAPI WebSocket，支持前端 UI |
| 5.3 | Cron 定时任务 | P2 | 定时截屏巡检、消息汇总 |
| 5.4 | Heartbeat 心跳 | P2 | Agent 主动巡检机制（v1 已预留接口） |
| 5.5 | 多 Agent 协作 | P3 | Supervisor 调度模式 |
| 5.6 | 企微 API 集成 | P2 | 通过机器人 API 直接收发消息 |
| 5.7 | Windows 支持 | P2 | 实现 WindowsController（只需加一个文件） |
| 5.8 | 向量检索记忆 | P3 | ChromaDB 本地向量搜索（替代 FTS5） |
| 5.9 | Web UI | P3 | 可视化管理界面 |
| 5.10 | Token 费用估算 | P3 | 基于 token 计数的实时费用展示 |

---

## 进度概览

| 里程碑 | 任务数 | 完成数 | 进度 |
|--------|--------|--------|------|
| M0: 项目基建 | 10 | 10 | ███████████████ 100% |
| M1: 能对话 | 28 | 28 | ███████████████ 100% |
| M2: 能操控浏览器 | 8 | 0 | ░░░░░░░░░░░░░░░ 0% |
| M3: 能操控桌面 | 11 | 0 | ░░░░░░░░░░░░░░░ 0% |
| M4: 完整框架 | 14 | 0 | ░░░░░░░░░░░░░░░ 0% |
| **总计** | **71** | **38** | **████████░░░░░░░ 54%** |

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
| §5.3: 可观测性 | — | M0.9 + M1.1.7 | ✅ 已覆盖（日志 + token） |
