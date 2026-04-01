# MiniClaw 优化计划 — 借鉴 Claude Code 架构

> 版本：v1.0 ｜ 日期：2026-04-01 ｜ 作者：avinzhang
>
> 基于 Claude Code 512K 行泄露源码的架构分析，结合 MiniClaw 实际代码现状，
> 制定的务实优化路线图。
>
> **原则**：只借鉴适合 MiniClaw 体量的模式，拒绝过度工程。

---

## 1. 分析背景

### 1.1 Claude Code 关键架构模式

| 模式 | Claude Code 实现 | 规模 |
|------|-----------------|------|
| **QueryEngine** | 46K 行，统一 LLM 调用 + 流式 + 工具循环 + token 追踪 | 巨型核心 |
| **三层上下文压缩** | MicroCompact（本地裁剪） → AutoCompact（87% 触发） → FullCompact（全对话摘要，≤50K） | 精密系统 |
| **系统提示词工程** | 静态/动态分离，Prompt Cache 命中率 92%；工具约束 + 风险控制 + 输出规范 | 高度工程化 |
| **42 个工具 + 14 步治理** | Schema 校验 → 权限决策 → 沙箱执行 → 结果注入 → 输出截断 | 工业级 |
| **多 Agent 蜂群** | 6 个内建角色（通用/探索/计划/验证/Shell/Browser）+ Coordinator 模式 | 企业级 |
| **CLAUDE.md 分层记忆** | 全局 → 项目根 → 条件规则 → 子目录；AutoDream 自动整合 | 持久化体系 |
| **Permission Mailbox** | Worker 通过邮箱向 Coordinator 请求权限，原子认领机制 | 多 Agent 专用 |

### 1.2 MiniClaw 现状 vs Claude Code

| 维度 | MiniClaw 现状 | 差距分析 |
|------|--------------|----------|
| **上下文管理** | `build_messages()` 直接返回原始消息列表，零压缩 | 🔴 严重：长对话必爆 token |
| **系统提示词** | 硬编码 4 个工具，缺少 7+ 桌面/浏览器工具 | 🔴 严重：LLM 不知道有哪些工具可用 |
| **短期记忆** | `ShortTermMemory` 完整实现但未接入 AgentContext | 🟡 中等：代码写了但没用 |
| **长期记忆** | `LongTermMemory` 完整实现但未初始化 | 🟡 中等：代码写了但没用 |
| **Skill 提示注入** | SkillLoader/SkillMatcher 工作正常，但 SKILL.md 内容未注入 system prompt | 🟡 中等：匹配了但没效果 |
| **工具输出截断** | 工具执行结果无长度限制直接注入上下文 | 🟡 中等：大文件读取会爆 |
| **流式输出** | `chat_stream()` 已实现但 AgentLoop.run() 用同步 `chat()` | 🟢 轻微：功能存在但未接入 |
| **环境信息注入** | 系统提示词无 OS/CWD/时间等环境上下文 | 🟢 轻微：影响 Agent 决策质量 |
| **四模型路由** | 已完善，3x 重试 + fallback | ✅ 无需改动 |
| **工具安全审批** | 3 级审批已完善 | ✅ 无需改动 |

### 1.3 明确拒绝的模式

以下 Claude Code 模式不适合 MiniClaw 的体量，明确 **不做**：

| 模式 | 拒绝原因 |
|------|----------|
| **Coordinator + Permission Mailbox** | MiniClaw 是单用户本地 Agent，不需要多 Worker 协调 |
| **独立 QueryEngine 层** | MiniClaw 已有 ModelRoleRegistry 统一管理，再加一层是过度封装 |
| **三层压缩（MicroCompact/AutoCompact/FullCompact）** | 采用简化版：单层自动压缩即可（已有 ShortTermMemory.compress()） |
| **Prompt Cache 优化（静态/动态分离）** | MiniClaw 不直连 Anthropic API Cache，意义不大 |
| **6 个内建 Agent 角色** | MiniClaw 通过四模型路由已覆盖，不需要独立 Agent 进程 |
| **沙箱机制（bubblewrap/sandbox-exec）** | M5.7 已规划 Docker 沙箱，当前阶段不做系统级沙箱 |

---

## 2. 优化任务清单

### OP1: System Prompt 全面升级 [P0 — 必须立即修复]

> **问题**：当前 SYSTEM_PROMPT 只列出 4 个工具（shell_exec、read_file、write_file、web_search、http_request），
> 但 MiniClaw 实际有 11 个内置工具 + 桌面/浏览器能力。LLM 不知道有这些工具，自然不会调用。
>
> **参考**：Claude Code 的系统提示词包含完整的工具约束、风险控制和输出规范。

| # | 任务 | 状态 | 说明 |
|---|------|------|------|
| OP1.1 | 补全系统提示词工具描述 | ✅ DONE | 列出全部 11 个内置工具的名称和用途，按能力域分组（命令执行、文件操作、网络、浏览器、桌面） |
| OP1.2 | 注入环境上下文信息 | ✅ DONE | 在系统提示词中动态注入：OS 类型、当前工作目录、当前时间、Python 版本 |
| OP1.3 | 添加行为约束指令 | ✅ DONE | 参考 Claude Code 的"工具约束 + 风险控制 + 输出规范"模式，增加：优先使用低风险工具、文件操作前检查路径、大文件先 head 再决定 |
| OP1.4 | 系统提示词模板化 | ✅ DONE | 将 SYSTEM_PROMPT 从硬编码字符串改为模板，支持动态拼装（环境信息 + 工具列表 + 活跃 Skill 指令） |

**预计影响**：Agent 立刻能感知并调用桌面/浏览器工具，解决"看不见工具"的核心问题。

**改动文件**：`src/miniclaw/agent/context.py`

---

### OP2: ShortTermMemory 接入 AgentContext [P0 — 必须立即修复]

> **问题**：`ShortTermMemory` 已完整实现了 `needs_compression()` + `compress()`，但它是个孤儿模块——
> `AgentContext` 自己维护 `self.messages`，从不检查 token 上限，不调用压缩。
> 长对话 100% 会超出上下文窗口爆炸。
>
> **参考**：Claude Code 的 AutoCompact 在 token 消耗 ≥ 87% 时自动触发压缩。

| # | 任务 | 状态 | 说明 |
|---|------|------|------|
| OP2.1 | AgentContext 集成 ShortTermMemory | ✅ DONE | 将 `AgentContext.messages` 的管理委托给 `ShortTermMemory` 实例，消除重复的消息列表 |
| OP2.2 | AgentLoop 压缩触发点 | ✅ DONE | 在 `AgentLoop.run()` 每轮循环开始前检查 `needs_compression()`，超阈值时调用 default 模型生成摘要再 `compress()` |
| OP2.3 | bootstrap.py 创建 ShortTermMemory | ✅ DONE | 在 `bootstrap()` 中创建 `ShortTermMemory` 实例并注入到 `AgentContext` |

**预计影响**：消除长对话 token 爆炸风险，MiniClaw 可以进行长时间多轮对话。

**改动文件**：`src/miniclaw/agent/context.py`、`src/miniclaw/agent/loop.py`、`src/miniclaw/bootstrap.py`

---

### OP3: 工具输出截断 [P1 — 建议尽快修复]

> **问题**：`ToolExecutor.execute()` 的返回结果直接注入上下文，无长度限制。
> 如果 `read_file` 读了一个 10000 行的文件，整个文件内容会塞进上下文。
>
> **参考**：Claude Code 的 MicroCompact 会自动清理旧工具输出；工具结果有截断策略。

| # | 任务 | 状态 | 说明 |
|---|------|------|------|
| OP3.1 | 工具输出最大长度限制 | ✅ DONE | `ToolExecutor.execute()` 返回前，如果 `result.output` 超过阈值（默认 8000 字符），截断并附加 `"...[输出已截断，共 N 字符]"` |
| OP3.2 | 可配置截断阈值 | ✅ DONE | 在 `config.yaml` 中增加 `agent.tool_output_max_chars` 配置项 |
| OP3.3 | read_file 工具增加行数限制参数 | ✅ DONE | `read_file` 增加可选的 `max_lines` 参数，默认 200 行，超过时提示 Agent 分段读取 |

**预计影响**：防止单次工具调用吃掉大量上下文窗口，延长可用对话轮次。

**改动文件**：`src/miniclaw/tools/executor.py`、`src/miniclaw/tools/builtin/file.py`、`src/miniclaw/config/settings.py`

---

### OP4: Skill 提示词注入 [P1 — 建议尽快修复]

> **问题**：`SkillLoader` 加载 SKILL.md 成功，`SkillMatcher` 匹配到 Skill 后设置了标志，
> 但 SKILL.md 中的角色定义和工作流程从未注入到 AgentContext 的系统提示词中。
> 匹配了 Skill 等于没匹配。
>
> **参考**：Claude Code 的 Skills 内容在激活后直接注入对话上下文。

| # | 任务 | 状态 | 说明 |
|---|------|------|------|
| OP4.1 | AgentContext 增加 Skill 上下文注入方法 | ✅ DONE | 新增 `inject_skill_context(skill_info: SkillInfo)` 方法，将 Skill 的角色定义 + 工作流程 + 可用工具说明追加到 system prompt |
| OP4.2 | AgentLoop 在匹配 Skill 后触发注入 | ✅ DONE | Skill 被匹配激活时，调用 `context.inject_skill_context()` |
| OP4.3 | Skill 上下文随 /clear 一起清除 | ✅ DONE | `context.clear()` 时同步清除 Skill 注入的内容 |

**预计影响**：Skill 系统从"能匹配"进化到"真正生效"，Agent 在调研/编程/桌面操控场景中表现大幅提升。

**改动文件**：`src/miniclaw/agent/context.py`、`src/miniclaw/agent/loop.py`

---

### OP5: LongTermMemory 接入 [P2 — 可延后]

> **问题**：`LongTermMemory` 完整实现了 SQLite FTS5 搜索 + 会话持久化，
> 但 `bootstrap.py` 从未创建实例，整个长期记忆系统处于"写完代码放那"的状态。
>
> **参考**：Claude Code 的 CLAUDE.md 分层记忆 + AutoDream 自动整合。

| # | 任务 | 状态 | 说明 |
|---|------|------|------|
| OP5.1 | bootstrap.py 初始化 LongTermMemory | ✅ DONE | 创建 `LongTermMemory` 实例，调用 `await init()`，注入到 Gateway/SessionManager |
| OP5.2 | Gateway 退出时保存会话 | ✅ DONE | 在 Gateway 关闭或 /exit 时，调用 `memory.save_session()` 保存当前对话 |
| OP5.3 | Gateway 启动时恢复会话 | ✅ DONE | 可选恢复上次会话（`--continue` 参数或交互提示） |
| OP5.4 | 记忆检索注入对话 | ✅ DONE | 每次新对话开始时，从 LongTermMemory 检索相关记忆片段（最多 3 条），注入 system prompt 的 `[相关记忆]` 段 |

**预计影响**：MiniClaw 获得跨会话记忆能力，"记住"用户偏好和重要信息。

**改动文件**：`src/miniclaw/bootstrap.py`、`src/miniclaw/gateway/router.py`、`src/miniclaw/agent/context.py`

---

### OP6: 流式输出接入 AgentLoop [P2 — 可延后]

> **问题**：`chat_stream()` 在所有 Provider 中已完整实现（返回 AsyncIterator），
> 但 `AgentLoop.run()` 只调用同步的 `chat()`，流式能力被闲置。
> CLI 的"打字机效果"目前是模拟的，不是真正的流式。
>
> **参考**：Claude Code 的 QueryEngine 核心就是流式驱动的。

| # | 任务 | 状态 | 说明 |
|---|------|------|------|
| OP6.1 | AgentLoop 增加 stream 模式 | ✅ DONE | 在 `run()` 中增加 `stream=True` 参数，使用 `chat_stream()` 替代 `chat()`，逐 token 通过 `on_text` 回调输出 |
| OP6.2 | 流式工具调用解析 | ✅ DONE | 流式模式下正确累积并解析工具调用响应（工具调用通常不是逐 token 的，需要特殊处理） |
| OP6.3 | CLIChannel 真正流式渲染 | ✅ DONE | 对接流式回调，实现真正的逐 token 打字机效果 |

**预计影响**：用户体验大幅提升，从"等待整段回复"变为"实时看到 Agent 思考过程"。

**改动文件**：`src/miniclaw/agent/loop.py`、`src/miniclaw/channels/cli_channel.py`

---

### OP7: Token 预算管理 [P2 — 可延后]

> **问题**：当前没有任何 token 预算概念。AgentLoop 不知道已用多少 token，
> 也不知道距离上下文窗口上限还剩多少空间。
>
> **参考**：Claude Code 有独立的客户端预算控制，支持 200K 上下文窗口的动态分配与自动续期。

| # | 任务 | 状态 | 说明 |
|---|------|------|------|
| OP7.1 | AgentContext 增加 token 统计 | ✅ DONE | 利用 `utils/tokens.py` 在每次 `add_*_message()` 后累计 token 数 |
| OP7.2 | AgentLoop 预算检查 | ✅ DONE | 每轮循环前检查已用 token，接近上限时主动触发压缩或警告用户 |
| OP7.3 | Debug 日志输出 token 预算 | ✅ DONE | `--debug` 模式下每轮输出：已用 token / 上限 / 剩余百分比 |

**预计影响**：Agent 对自身资源有感知，避免"不知不觉超窗口"。

**改动文件**：`src/miniclaw/agent/context.py`、`src/miniclaw/agent/loop.py`

---

## 3. 优先级与开发顺序

```
第 1 天: OP1（System Prompt 升级）+ OP2（ShortTermMemory 接入）
         ↑ P0，不做的话 Agent 基本残废

第 2 天: OP3（工具输出截断）+ OP4（Skill 提示注入）
         ↑ P1，让已写好的代码真正生效

第 3 天: OP5（LongTermMemory 接入）+ OP7（Token 预算管理）
         ↑ P2，增强记忆和资源感知

第 4 天: OP6（流式输出接入）
         ↑ P2，用户体验提升
```

---

## 4. 与现有任务的关系

| 优化任务 | 关联的现有任务 | 说明 |
|----------|--------------|------|
| OP1 | M1.3.1 AgentContext | 对已完成任务的增强 |
| OP2 | M4.2.1 短期记忆 + M4.2.3 上下文窗口管理 | 任务标记 DONE 但实际未接入，需要修复 |
| OP3 | M1.2.2 ToolExecutor | 对已完成任务的安全增强 |
| OP4 | M4.1.2 Skill 匹配器 | 任务标记 DONE 但提示注入缺失，需要补全 |
| OP5 | M4.2.2 长期记忆 + M4.2.4 会话持久化 | 任务标记 DONE 但未初始化，需要接入 |
| OP6 | M1.1.5 流式输出 + M1.5.3 打字机效果 | 已实现 Provider 层，需要接入 AgentLoop |
| OP7 | M1.1.7 Token 计数 | 从统计扩展到预算管理 |

---

## 5. 技术约束提醒

- 所有改动必须遵守 **每文件 ≤ 500 行** 的铁律
- 不增加新的外部依赖（当前 11 个已满）
- 所有函数必须有完整的 type hints
- 改动涉及的模块需要有对应的单元测试更新

---

## 6. Claude Code 架构启示总结

**值得学习的**：
1. 系统提示词工程 — 完整的工具描述 + 行为约束 + 环境上下文
2. 上下文压缩 — 自动触发，不依赖用户手动操作
3. 工具输出治理 — 截断 + 清理，保护上下文窗口
4. Skill 真正注入 — 匹配后内容要进到 prompt 里才有效果
5. Token 预算意识 — Agent 要知道自己还有多少"弹药"

**不适合照搬的**：
1. 46K 行的 QueryEngine — MiniClaw 的 `loop.py` + `registry.py` 共 ~330 行已经够了
2. 6 个内建 Agent 角色 — 四模型路由已覆盖需求
3. 三层压缩 — 单层自动压缩 + 工具输出截断已足够
4. Coordinator + Mailbox — 单用户本地 Agent 不需要
5. Prompt Cache 优化 — 不直连 Anthropic API Cache 接口

> **一句话总结**：Claude Code 90% 的工作量在"AI 之外"——上下文经济学、信任工程、产品化打磨。
> MiniClaw 应该学的是这些"AI 之外"的工程智慧，而不是照搬它的架构复杂度。
