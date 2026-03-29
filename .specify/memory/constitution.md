<!--
Sync Impact Report
- Version change: 0.0.0 → 1.0.0
- Modified principles: N/A (initial creation)
- Added sections: Core Principles (7), Architectural Constraints, Development Workflow, Governance
- Removed sections: N/A
- Templates requiring updates:
  - .specify/templates/plan-template.md ✅ no update needed (Constitution Check section is generic)
  - .specify/templates/spec-template.md ✅ no update needed (feature-level, not constitution-level)
  - .specify/templates/tasks-template.md ✅ no update needed (task format is generic)
- Follow-up TODOs: none
-->

# MiniClaw Constitution

## Core Principles

### I. Extreme Lightness (NON-NEGOTIABLE)

每个 `.py` 文件 MUST ≤ 500 行（含注释和空行）。超过即拆分，无例外。
`src/miniclaw/` 核心代码总行数 MUST ≤ 3000 行（不含 skills/builtin/ 的 SKILL.md 和测试）。
`pyproject.toml` 中的 dependencies MUST ≤ 10 个包。新增依赖必须替换现有的或有压倒性理由。

**理由**：MiniClaw 的核心定位是「轻量可理解」。如果代码膨胀，就丧失了与 LangChain/CrewAI 的差异化优势。这三条数字约束是项目的生命线。

### II. Async-First, Type-Safe

所有 I/O 操作 MUST 使用 `async/await`，不允许同步阻塞调用。
所有函数签名 MUST 有完整的 type hints。
Python 版本 MUST ≥ 3.12。

**理由**：Agent Loop 天然是异步的（LLM 调用、浏览器操作、截屏都是 I/O）。类型标注让代码自解释，降低阅读门槛——这个项目本身就是教学材料。

### III. Layered Architecture (STRICT)

分层依赖规则 MUST 严格遵守：

```
Channel → Gateway → Agent → Tools / Memory / Skills → LLM / Desktop / Browser
```

禁止反向依赖。唯一特例：`screen_analyze` 复合工具允许内部调用 LLM（仅此一处，已在架构文档中明确标注）。

**理由**：分层是可扩展性的基础。未来加 Telegram/HTTP 通道、加 Windows 桌面支持，都只需在对应层新增文件，不改其他层的代码。

### IV. Abstraction-First for Extensibility

以下模块 MUST 通过抽象基类（ABC）访问，不允许直接依赖具体实现：
- `ChannelProtocol` → `CLIChannel`（v2 加 HTTP/Telegram）
- `BaseProvider` → `OpenAIProvider` / `AnthropicProvider`
- `DesktopController` → `MacOSController`（v2 加 Windows 只需新增一个文件）

**理由**：抽象基类 + 工厂模式确保「加新平台/新通道/新模型只需加文件，不改已有代码」。这是 OpenClaw 架构精华的核心继承。

### V. Safety by Default

所有工具 MUST 通过 `@tool` 装饰器注册，MUST 声明 `risk_level`（low/high/critical）。
high 和 critical 操作 MUST 经过用户确认才能执行。
用户拒绝时 MUST 返回标准 `ToolResult(success=False)`，不中断 Agent Loop。
文件操作 MUST 限制在 `allowed_directories` 白名单内。
API Key MUST 通过环境变量管理，绝不硬编码。

**理由**：MiniClaw 能操控电脑（鼠标、键盘、Shell）——权力越大责任越大。安全审批机制是用户信任的底线。

### VI. Observability

每个模块 MUST 使用 `miniclaw.utils.logging` 的结构化日志。
`--debug` 模式 MUST 输出完整的 LLM prompt、模型路由决策和 token 计数。
Token 计数 MUST 按角色（default/planner/reasoner/maker）统计，以 debug 级别写入日志。

**理由**：Agent 的行为不可预测——你不知道它下一步会调什么工具。没有日志就无法调试，无法理解 Agent 的「思考过程」。

### VII. PRD as Single Source of Truth

所有架构决策和代码实现 MUST 可追溯到 PRD-v1.md 中的需求编号（F1-F9 / §x.x）。
代码文件头注释 MUST 标注对应的 PRD 需求。
架构文档和任务文档 MUST 包含 PRD 追溯表。
README.md MUST 在每次重大变动后同步更新。

**理由**：PRD 是需求、架构、代码之间的唯一真相源。丢失追溯链就会出现「文档说一套、代码做一套」的混乱。

## Architectural Constraints

### 技术选型锁定（v1）

| 领域 | 选型 | 锁定理由 |
|------|------|---------|
| LLM 调用 | httpx 自封装（≤400 行） | 学习目的 + 四模型调度是核心设计，三方库不支持 |
| 浏览器 | Playwright | 最强自动化、原生 async |
| 桌面操控 | pyautogui + Pillow | 跨平台基础 |
| CLI | Rich + Prompt Toolkit | 美观 + 交互 |
| 数据库 | aiosqlite（SQLite FTS5） | 零配置、本地优先 |
| 配置 | Pydantic Settings + YAML | 类型安全 |
| 搜索 | DuckDuckGo（免费无 key） | 零配置门槛 |

v1 不引入 LiteLLM、openai SDK、LangChain、向量数据库。

### 四模型调度（核心设计）

全局配置 4 个 LLM 角色（default / planner / reasoner / maker），按任务类型自动路由。每个角色可独立配置 provider + model + 参数。任何角色不可用时 MUST 降级到 default。

### 跨平台策略

v1 MUST 实现 macOS 桌面操控（MacOSController）。
v1 MUST 定义跨平台抽象接口（DesktopController ABC）。
v1 MUST NOT 实现 Windows/Linux（留给 v2）。
浏览器操控（Playwright）天然跨平台，无需额外处理。

## Development Workflow

### 代码质量门

1. `ruff check` MUST 零 error
2. `mypy --strict` MUST 通过
3. 每个模块 MUST 有对应测试文件
4. 外部依赖（LLM API、浏览器）MUST 使用 mock 测试

### Git 规范

- Commit 格式：`<type>(<scope>): <description>`
- type：feat / fix / refactor / docs / test / chore
- 分支策略：main ← dev ← feat/xxx

### 注释语言

- 代码注释和 docstring：中文
- 变量名和函数名：英文
- 注释 MUST 解释 WHY，不解释 WHAT

## Governance

1. 本宪法 MUST 优先于所有其他实践和约定。当宪法与其他文档冲突时，以宪法为准。
2. 修改宪法 MUST 附带版本变更说明、影响评估和迁移计划。
3. 所有 PR/代码审查 MUST 验证宪法合规性，特别是铁律 I（文件行数/代码总量/依赖数）。
4. 复杂度增加 MUST 有书面理由（为什么更简单的方案不可行）。
5. PRD-v1.md 是需求的唯一真相源；architecture.md 是架构的唯一真相源；本文档是约束的唯一真相源。

**Version**: 1.0.0 | **Ratified**: 2026-03-29 | **Last Amended**: 2026-03-29
