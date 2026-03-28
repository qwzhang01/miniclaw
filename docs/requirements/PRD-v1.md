# MiniClaw — 轻量级 AI Agent 框架

## 产品需求文档 (PRD v1.0)

> **项目定位**：借鉴 OpenClaw 架构思想，用 Python 从零实现的轻量级自治 AI Agent 框架
>
> **作者**：avinzhang
>
> **创建日期**：2026-03-29
>
> **状态**：草稿 / 待讨论

---

## 1. 项目背景与动机

### 1.1 为什么做 MiniClaw

- **学习目的**：通过"造轮子"的方式深入理解 AI Agent 的核心设计（Agent Loop、工具调用、记忆系统、通道适配）
- **作品展示**：作为个人技术能力的证明，用于求职、技术博客、社区声望积累
- **实用价值**：最终能作为自己日常开发的辅助工具，真正跑起来干活

### 1.2 与 OpenClaw 的关系

MiniClaw **不是** OpenClaw 的 fork 或翻译，而是：

- 受 OpenClaw 架构**启发**，用 Python 重新设计实现
- 聚焦**核心机制**，去掉 1800+ 插件的复杂生态，保留最精华的设计
- 面向 **Python 开发者**，降低理解和扩展门槛

### 1.3 目标用户

| 用户角色 | 使用场景 |
|---------|---------|
| 本人（avinzhang） | 日常开发辅助、学习 Agent 架构 |
| Python 开发者 | 学习 AI Agent 开发模式的参考实现 |
| AI 爱好者 | 快速搭建自己的本地 AI Agent |

---

## 2. 核心设计理念

### 2.1 三个原则

1. **本地优先（Local-First）**：所有数据存储在本地，不依赖云端服务，保护隐私
2. **极简可理解（Minimal & Readable）**：代码量控制在可阅读范围内，每个模块都能在 30 分钟内读懂
3. **可扩展（Extensible）**：核心精简，但通过 Skill 和 Channel 机制可以灵活扩展

### 2.2 借鉴 OpenClaw 的核心架构模式

```
                    ┌─────────────────────┐
                    │    Channel Layer     │ ← 多通道接入（CLI / Telegram / HTTP）
                    │  (通道适配器)         │
                    └─────────┬───────────┘
                              │ 标准化消息
                    ┌─────────▼───────────┐
                    │      Gateway        │ ← 消息路由 + 会话管理
                    │   (网关 / 大脑)      │
                    └─────────┬───────────┘
                              │
                    ┌─────────▼───────────┐
                    │    Agent Runtime     │ ← Agent 循环：思考 → 调用工具 → 观察 → 思考...
                    │  (Agent 运行时)      │
                    └─────────┬───────────┘
                              │
                 ┌────────────┼────────────┐
                 ▼            ▼            ▼
          ┌──────────┐ ┌──────────┐ ┌──────────┐
          │  Skills   │ │  Memory  │ │  Tools   │
          │ (技能系统) │ │(记忆系统) │ │(工具系统) │
          └──────────┘ └──────────┘ └──────────┘
```

---

## 3. 功能需求

### 3.1 MVP 功能范围（第一阶段）

> 目标：能跑起来，能对话，能调用工具，能记住上下文

#### F1: Agent 核心循环（Agent Loop）

**优先级**：P0（必须）

**描述**：实现 ReAct 模式的 Agent 主循环

**功能要求**：

- [ ] 接收用户输入，组装上下文（系统提示词 + 历史消息 + 可用工具列表）
- [ ] 调用 LLM 生成响应
- [ ] 解析响应中的工具调用请求（function calling / tool use）
- [ ] 执行工具调用，获取结果
- [ ] 将工具结果注入上下文，继续循环，直到 LLM 给出最终回复
- [ ] 支持设置最大循环次数（防止死循环）
- [ ] 流式输出（streaming）支持

**验收标准**：

```
用户输入 "今天上海天气怎么样"
→ Agent 判断需要调用 web_search 工具
→ 调用工具获取天气信息
→ 组织语言回复用户
```

---

#### F2: LLM 接入层（Model Provider）

**优先级**：P0（必须）

**描述**：统一的 LLM 调用接口，支持多模型切换

**功能要求**：

- [ ] 统一的 `LLMProvider` 抽象接口（`chat()` / `chat_stream()`）
- [ ] 支持 OpenAI 兼容 API（覆盖 OpenAI / DeepSeek / Qwen / 本地模型）
- [ ] 支持 Anthropic Claude API
- [ ] 支持配置模型参数（temperature、max_tokens 等）
- [ ] 支持 Function Calling / Tool Use 协议
- [ ] 请求重试 + 错误处理

**验收标准**：

```python
provider = OpenAIProvider(api_key="...", model="deepseek-chat")
response = await provider.chat(messages=[...], tools=[...])
# response 中包含文本回复或工具调用请求
```

---

#### F3: 工具系统（Tool System）

**优先级**：P0（必须）

**描述**：可注册、可发现、可执行的工具体系

**功能要求**：

- [ ] 工具注册机制（装饰器 `@tool` 注册）
- [ ] 工具自动生成 JSON Schema（用于传给 LLM）
- [ ] 工具执行引擎（参数校验 → 执行 → 返回结果）
- [ ] 内置基础工具：
  - `shell_exec`：执行本地 Shell 命令
  - `web_search`：网页搜索（调用搜索 API）
  - `read_file` / `write_file`：文件读写
  - `http_request`：HTTP 请求
- [ ] 工具执行超时控制
- [ ] 工具执行结果格式标准化

**验收标准**：

```python
@tool(description="执行 Shell 命令")
async def shell_exec(command: str) -> str:
    """在本地执行一条 shell 命令并返回输出"""
    ...

# 自动生成的 JSON Schema 能被 LLM 正确理解和调用
```

---

#### F4: CLI 通道（CLI Channel）

**优先级**：P0（必须）

**描述**：命令行交互界面，作为最基础的交互通道

**功能要求**：

- [ ] 终端交互式对话（支持多行输入）
- [ ] 流式输出展示（打字机效果）
- [ ] 彩色输出（区分用户输入 / Agent 回复 / 工具调用 / 系统消息）
- [ ] 支持特殊命令：`/exit`、`/clear`、`/history`、`/tools`
- [ ] 会话历史持久化（退出后下次可继续）

**验收标准**：

```
$ miniclaw chat
🦞 MiniClaw v0.1.0 - 输入 /help 查看帮助

You: 帮我看一下当前目录有哪些文件
🦞: 我来帮你查看...
   [调用工具: shell_exec("ls -la")]
   当前目录下有以下文件：
   - src/          (目录)
   - docs/         (目录)
   - pyproject.toml
   - README.md
   ...
```

---

#### F5: 记忆系统（Memory）

**优先级**：P1（重要）

**描述**：让 Agent 能记住对话历史和重要信息

**功能要求**：

- [ ] 短期记忆：当前会话的对话历史（内存中）
- [ ] 长期记忆：跨会话的持久化存储（SQLite）
- [ ] 上下文窗口管理：当历史消息超过 token 限制时，自动摘要压缩
- [ ] 简单的关键信息提取（Agent 主动记住用户偏好等）

**验收标准**：

```
会话1: "我喜欢用 Python 写代码"
(退出，重新启动)
会话2: "你还记得我喜欢什么语言吗？"
Agent: "你之前说过喜欢用 Python 写代码"
```

---

#### F6: Skill 技能系统

**优先级**：P1（重要）

**描述**：通过 Markdown 文件 + Python 代码定义可复用的 Agent 能力模块

**功能要求**：

- [ ] Skill 定义格式：每个 Skill 是一个目录，包含：
  - `SKILL.md`：技能描述、使用场景、Prompt 模板
  - `tools.py`：该技能对应的工具函数
  - `config.yaml`：配置项（可选）
- [ ] Skill 加载器：启动时自动扫描 `skills/` 目录加载
- [ ] Skill 匹配：根据用户意图自动激活相关 Skill
- [ ] 内置 Skills：
  - `shell`：系统命令执行
  - `web`：网页搜索和内容抓取
  - `github`：GitHub 仓库操作（Issue、PR、代码搜索）
  - `coder`：代码生成和分析

**验收标准**：

```
skills/
├── shell/
│   ├── SKILL.md      # "你是一个系统管理员，擅长使用命令行..."
│   └── tools.py      # shell_exec, process_list, disk_usage...
├── github/
│   ├── SKILL.md      # "你是一个 GitHub 助手..."
│   └── tools.py      # list_issues, create_pr, search_code...
```

---

### 3.2 第二阶段功能（MVP 完成后）

> 这些功能在 MVP 验证可行后再开发

#### F7: Telegram 通道

**优先级**：P2

- 接入 Telegram Bot API
- 支持文本消息、图片、文件发送
- 支持群组和私聊
- 消息队列处理（防止并发冲突）

#### F8: HTTP API 通道

**优先级**：P2

- FastAPI 实现的 REST + WebSocket API
- 支持第三方系统集成
- API Key 鉴权
- 可作为其他前端界面的后端

#### F9: Cron 定时任务

**优先级**：P2

- 配置文件定义定时任务
- 支持 Cron 表达式
- 任务执行结果推送（通过已接入的 Channel）
- 任务执行日志

#### F10: 多 Agent 协作

**优先级**：P3

- Agent 之间可以互相发送消息
- 支持 Supervisor Agent 模式（一个 Agent 调度其他 Agent）
- Agent 角色定义和任务分配

---

## 4. 非功能需求

### 4.1 性能

- 工具调用响应时间 < 1s（不含网络请求）
- 支持单用户并发会话（至少 3 个）
- 内存占用 < 200MB（空载）

### 4.2 安全

- Shell 命令执行前需要用户确认（可配置自动执行白名单）
- 敏感信息（API Key 等）通过环境变量或加密配置文件管理
- 文件操作限制在配置的工作目录范围内

### 4.3 可观测性

- 结构化日志（JSON 格式，支持 log level）
- Agent 循环的每一步都有详细日志（思考 → 工具调用 → 结果）
- 可选的调试模式（输出完整的 prompt 和 LLM 响应）

### 4.4 配置管理

- 使用 YAML 配置文件（`~/.miniclaw/config.yaml`）
- 支持环境变量覆盖
- 首次运行交互式引导配置

---

## 5. 技术选型（初步）

| 领域 | 选型 | 理由 |
|------|------|------|
| 语言 | Python 3.12+ | 主力语言，AI 生态最丰富 |
| 异步框架 | asyncio + anyio | Agent 循环天然适合异步 |
| Web 框架 | FastAPI | HTTP 通道 + API 服务 |
| LLM 调用 | httpx + 原生实现 | 不依赖 openai SDK，自己实现更可控 |
| 数据存储 | SQLite (aiosqlite) | 本地优先，零配置 |
| 配置管理 | Pydantic Settings | 类型安全 + 环境变量支持 |
| CLI | Rich + Prompt Toolkit | 美观的终端交互 |
| 包管理 | uv + pyproject.toml | 现代 Python 项目标准 |
| 测试 | pytest + pytest-asyncio | 异步测试支持 |

---

## 6. 里程碑规划

### M1：能对话（第 1 周）

- [x] 项目结构搭建
- [ ] LLM Provider 实现（OpenAI 兼容）
- [ ] Agent 基础循环
- [ ] CLI 通道
- **交付**：能在终端跟 Agent 对话

### M2：能干活（第 2 周）

- [ ] 工具系统实现
- [ ] 内置工具：shell_exec, read_file, write_file, web_search
- [ ] Skill 加载系统
- [ ] 2-3 个内置 Skill
- **交付**：Agent 能调用工具完成实际任务

### M3：能记住（第 3 周）

- [ ] 记忆系统（短期 + 长期）
- [ ] 上下文窗口管理
- [ ] 会话持久化
- **交付**：Agent 能跨会话记住信息

### M4：能连接（第 4 周）

- [ ] Telegram 通道
- [ ] HTTP API 通道
- [ ] 完善文档 + README
- [ ] 示例和教程
- **交付**：完整可用的 v0.1.0 版本

---

## 7. 开放问题（待讨论）

> 以下是需要讨论确认的问题，请 review 后给出意见：

### Q1: LLM 调用是否依赖 openai SDK？

- **方案 A**：直接用 `httpx` 调用 API（更可控，更适合学习）
- **方案 B**：用 `openai` SDK + `anthropic` SDK（开发更快）
- **方案 C**：用 `litellm` 统一封装（最省事，但多了一层依赖）
- **当前倾向**：方案 A，自己实现一层薄封装

### Q2: 工具系统的安全模型怎么设计？

- 哪些工具可以自动执行？哪些需要用户确认？
- 是否需要沙箱机制？还是先用简单的白名单机制？

### Q3: 记忆系统是否需要向量搜索？

- **简单方案**：关键词匹配 + SQLite 全文搜索
- **进阶方案**：本地 embedding + 向量检索（如 chromadb）
- 对 MVP 来说，简单方案是否足够？

### Q4: Skill 的粒度怎么定？

- OpenClaw 的 Skill 是纯 Markdown（知识/SOP），Plugin 才是代码
- MiniClaw 是否要区分 Skill 和 Plugin？还是合二为一？

### Q5: 项目名和品牌

- `miniclaw` 这个名字是否最终确定？
- 是否需要一个 Logo？（可以用 AI 生成一个小龙虾图标）

---

## 附录

### A. 参考项目

| 项目 | 参考点 |
|------|--------|
| [OpenClaw](https://github.com/open-claw/open-claw) | 整体架构、Skill 系统、Channel Adapter |
| [LangChain](https://github.com/langchain-ai/langchain) | Agent 循环、工具定义模式 |
| [CrewAI](https://github.com/crewAIInc/crewAI) | 多 Agent 协作模式 |
| [Pydantic AI](https://github.com/pydantic/pydantic-ai) | 类型安全的 Agent 设计 |
| [smolagents](https://github.com/huggingface/smolagents) | 轻量级 Agent 实现参考 |

### B. 术语表

| 术语 | 含义 |
|------|------|
| Agent Loop | Agent 的主循环：接收输入 → 思考 → 调用工具 → 观察结果 → 继续思考 |
| Channel | 通道/通信渠道，如 CLI、Telegram、HTTP API |
| Gateway | 网关，负责消息路由和会话管理 |
| Skill | 技能模块，包含领域知识（Markdown）和对应工具（Python） |
| Tool | 工具，Agent 可以调用的函数（如执行命令、搜索网页） |
| Provider | LLM 服务提供方（OpenAI、Anthropic、DeepSeek 等） |
| Memory | 记忆系统，包含短期记忆（会话内）和长期记忆（跨会话） |
