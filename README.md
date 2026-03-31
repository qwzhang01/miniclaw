# 🦞 MiniClaw

**你的 Mac 上的 AI 操控者 — 一句话让 AI 操控你的电脑**

> Python 生态中**唯一**同时做到「能操控电脑 + 轻量可理解 + pip 一行安装」的 AI Agent 框架
>
> OpenClaw 的 Python 精神续作

> 🤖 **关于这个项目的开发方式**
>
> MiniClaw 是一个「人机协作」项目 —— 大部分代码由 AI（大模型）生成，由人类完成需求定义、架构决策和代码审查。
> `docs/` 目录下的文档主要服务于开发者本人和 AI 协作（需求文档、架构设计、编码规范等），供大模型理解项目上下文使用。
> 而你正在看的这份 README 是面向所有对项目感兴趣的人的，包含完整的使用指南和配置说明。

<!-- TODO: 录制后替换为真实 demo GIF -->
```
$ pip install miniclaw
$ miniclaw

🦞 你好！我是 MiniClaw，你的本地 AI 助手。

You: 帮我看看企微上有没有人找我

🦞 正在截取屏幕... [screen_capture]
🦞 正在分析屏幕内容... [screen_analyze]
🦞 检测到企业微信有 3 条未读消息：
   1. 产品群 - 张三："明天评审会改到 10 点"
   2. 技术群 - 李四："线上 CPU 告警了，@你看一下"  ⚠️ 紧急
   3. 王五（私聊）："周末打球不"
🦞 建议优先处理第 2 条，要我帮你回复吗？
```

---

## ✨ 特性

- 🖥️ **能操控电脑** — 截屏看内容、模拟鼠标键盘、操控桌面应用
- 🌐 **能操控浏览器** — Playwright 驱动，搜索、点击、填表、抓取信息
- 🧠 **四模型智能调度** — default / planner / reasoner / maker，按任务类型自动路由
- 🔌 **Skill 插件系统** — SKILL.md + Python 工具，可扩展的技能体系
- 🔒 **安全审批机制** — 高风险操作需确认，文件操作白名单限制
- 💾 **本地优先** — 数据全部存本地，不依赖云端，保护隐私
- 📦 **极致轻量** — 核心代码 < 3000 行，`pip install` 一行搞定

## 📊 与同类项目对比

| 项目 | 语言 | 能操控电脑 | 轻量程度 | 学习友好 |
|------|------|-----------|---------|---------|
| **OpenClaw** | TypeScript | ✅ | ❌ 重 (1800+插件) | ❌ 源码庞大 |
| **open-computer-use** | TS + Python | ✅ | ❌ 需 Docker VM | ❌ 架构复杂 |
| **Clawlet** | Python | ❌ 仅聊天 | ✅ | ✅ |
| **LangChain / CrewAI** | Python | ❌ | ❌ 抽象层太多 | ❌ |
| **🦞 MiniClaw** | **Python** | **✅** | **✅ pip install** | **✅ 每模块<500行** |

## 🚀 快速开始

### 1. 安装

```bash
pip install miniclaw
```

### 2. 配置

```bash
# 复制示例配置
mkdir -p ~/.miniclaw
cp config.yaml.example ~/.miniclaw/config.yaml

# 复制环境变量并填入你的 API Key
cp .env.example .env
vim .env
```

#### 核心理念

**统一 OpenAI 兼容协议**。无论你用哪个平台（DeepSeek、硅基流动、火山引擎、智谱、Moonshot、OpenAI……），配置方式完全一样 —— `.env` 里改 `base_url` + `api_key`，`config.yaml` 里只管选模型：

```bash
# .env — 切换平台只改这里
LLM_BASE_URL=https://api.siliconflow.cn/v1
LLM_API_KEY=sk-your-key
```

```yaml
# config.yaml — 不用动 base_url，只选模型
llm:
  default:
    provider: openai_compatible
    base_url: ${LLM_BASE_URL}
    api_key: ${LLM_API_KEY}
    model: deepseek-ai/DeepSeek-V3
```

> 💡 四个模型角色（default / planner / reasoner / maker）可以配成同一个模型快速上手，也可以按需分配不同模型。
> 未配置的角色自动降级到 `default`，只配一个就能用。

#### 配置示例

**最简配置（一个模型跑全部）**

```bash
# .env
LLM_BASE_URL=https://api.deepseek.com/v1
LLM_API_KEY=sk-your-key
LLM_MODEL=deepseek-chat
```

```yaml
# ~/.miniclaw/config.yaml — 基本不用改
llm:
  default:
    provider: openai_compatible
    base_url: ${LLM_BASE_URL}
    api_key: ${LLM_API_KEY}
    model: ${LLM_MODEL}
```

**不同角色用不同模型**

```bash
# .env
LLM_BASE_URL=https://api.deepseek.com/v1
LLM_API_KEY=sk-your-main-key
LLM_MODEL=deepseek-chat

LLM_BASE_URL_2=https://api.openai.com/v1
LLM_API_KEY_2=sk-your-openai-key
LLM_MODEL_2=gpt-4o
```

```yaml
llm:
  default:
    provider: openai_compatible
    base_url: ${LLM_BASE_URL}
    api_key: ${LLM_API_KEY}
    model: ${LLM_MODEL}              # deepseek-chat，日常够用

  planner:
    provider: openai_compatible
    base_url: ${LLM_BASE_URL}
    api_key: ${LLM_API_KEY}
    model: deepseek-reasoner          # 同平台不同模型，直接写死也行

  reasoner:
    provider: openai_compatible
    base_url: ${LLM_BASE_URL_2}
    api_key: ${LLM_API_KEY_2}
    model: ${LLM_MODEL_2}            # gpt-4o，多模态最强
```

**本地模型（Ollama）**

```yaml
llm:
  default:
    provider: openai_compatible
    base_url: http://localhost:11434/v1
    api_key: ollama                    # Ollama 不需要真实 Key
    model: qwen2.5:14b
```

#### 平台速查表

所有 OpenAI 兼容平台只需替换 `base_url` 和 `model`，配置方式完全相同：

| 平台 | base_url | 常用模型 | 备注 |
|------|----------|---------|------|
| DeepSeek | `https://api.deepseek.com/v1` | `deepseek-chat`, `deepseek-reasoner` | 默认推荐 |
| 硅基流动 | `https://api.siliconflow.cn/v1` | `deepseek-ai/DeepSeek-V3`, `Qwen/Qwen2.5-72B-Instruct` | 聚合平台，一个 Key 多种模型 |
| 火山引擎 | `https://ark.cn-beijing.volces.com/api/v3` | `ep-xxxxx-xxxxx` | model 填接入点 ID |
| 智谱 AI | `https://open.bigmodel.cn/api/paas/v4` | `glm-4-plus`, `glm-4v-plus` | |
| 月之暗面 | `https://api.moonshot.cn/v1` | `moonshot-v1-128k` | |
| 零一万物 | `https://api.lingyiwanwu.com/v1` | `yi-large` | |
| 百川 | `https://api.baichuan-ai.com/v1` | `Baichuan4` | |
| OpenAI | `https://api.openai.com/v1` | `gpt-4o`, `gpt-4o-mini` | |
| Ollama | `http://localhost:11434/v1` | `qwen2.5:14b`, `llama3.1` | 本地运行，无需 Key |

> ⚠️ **火山引擎**的 `model` 字段填**接入点 ID**（`ep-` 开头），不是模型名，在控制台创建接入点后获取。

#### 其他配置项

<details>
<summary>安全 / 浏览器 / 日志配置</summary>

```yaml
# 安全
security:
  auto_approve_low_risk: true       # 低风险操作自动执行
  confirm_high_risk: true           # 高风险操作需用户确认
  allowed_directories:
    - ~/git/
    - ~/Documents/

# 浏览器
browser:
  headless: false                   # true=无头模式
  use_system_chrome: true

# 日志
logging:
  level: info                       # debug / info / warning / error
  file: ~/.miniclaw/logs/miniclaw.log
```

</details>

#### 环境变量解析

配置文件中的 `${VAR_NAME}` 会自动解析为 `.env` 中的环境变量值：

```yaml
# config.yaml 中这样写
base_url: ${LLM_BASE_URL}
api_key: ${LLM_API_KEY}

# .env 中配置实际值
# LLM_BASE_URL=https://api.deepseek.com/v1
# LLM_API_KEY=sk-abc123
```

#### 配置 FAQ

| 问题 | 答案 |
|------|------|
| 四个角色必须全部配置吗？ | 不需要。未配置的角色自动降级到 `default`，只配一个就能用 |
| 切换平台需要改代码吗？ | 不需要。只改 `.env` 里的三个变量 |
| 不同角色能用不同平台吗？ | 可以。`.env` 中配置多组变量，`config.yaml` 中不同角色引用不同组 |
| 火山引擎的 model 怎么填？ | 填接入点 ID（`ep-xxxxx-xxxxx` 格式），在控制台创建 |

### 3. 启动

```bash
miniclaw
```

### 4. 开始使用

```
You: 帮我打开 Chrome 搜索 Python 3.14 新特性，整理成 Markdown

You: 帮我看看当前目录有哪些大文件

You: 截屏看看桌面上有什么应用在运行

You: 帮我写一个 FastAPI 的 hello world 项目
```

## 🏗️ 架构

```
┌──────────────────────────────────────────────────────┐
│                      MiniClaw                        │
│                                                      │
│  Channels ──▶ Gateway ──▶ Agent Runtime              │
│  (CLI/HTTP)   (路由+会话    (ReAct Loop)              │
│                +消息标准化)       │                    │
│                    ┌──────────┼──────────┐            │
│                    ▼          ▼          ▼            │
│                 Tools      Memory     Skills         │
│                  │                                    │
│       ┌──────────┼──────────┐                        │
│       ▼          ▼          ▼                        │
│     Shell    Browser    Desktop                      │
│   (subprocess) (Playwright) (pyautogui+截图+LLM)     │
│                                                      │
│  ┌────────────────────────────────────────────────┐  │
│  │       LLM Provider（四模型角色调度）              │  │
│  │  default · planner · reasoner · maker          │  │
│  │  按任务类型自动路由到最合适的模型                  │  │
│  └────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────┘
```

借鉴 [OpenClaw](https://github.com/open-claw/open-claw) 的 Gateway → Agent → Skill 架构，用 Python 重新设计实现。核心设计理念：

- **每个模块 < 500 行代码** — 如果超了，说明设计有问题
- **10 分钟能跑起来** — 不依赖 Docker / VM / 外部服务
- **先能用，再好用** — 追求可工作的代码

## 🧠 四模型智能调度

不同任务自动选择最合适的模型，兼顾效果和成本：

| 角色 | 职责 | 推荐模型 |
|------|------|---------|
| `default` | 日常对话、简单工具调用 | DeepSeek-Chat（便宜快速） |
| `planner` | 任务规划、步骤拆解 | Claude Sonnet / GPT-4o |
| `reasoner` | 逻辑推理、截屏分析 | GPT-4o（多模态最强） |
| `maker` | 代码生成、报告撰写 | Claude Sonnet（产出最优） |

```
用户："帮我调研 Python Web 框架，写份报告"

Round 1 → [planner]  拆解任务步骤
Round 2 → [default]  调用搜索工具（省钱）
Round 3 → [reasoner] 分析对比信息
Round 4 → [maker]    生成高质量报告
```

## 🔌 Skill 插件系统

每个 Skill = `SKILL.md`（知识/SOP）+ `tools.py`（工具代码）：

```
skills/
├── shell/               # 系统命令执行
├── browser-research/    # 浏览器调研
├── desktop-assistant/   # 桌面操控
├── coder/               # 编程助手
└── github/              # GitHub 操作
```

创建自定义 Skill 只需新建一个目录，写一个 `SKILL.md` 和 `tools.py`。

## 🛡️ 安全模型

```
risk_level="low"      → 自动执行（read_file, web_search）
risk_level="high"     → 需用户确认（shell_exec, write_file, 鼠标点击）
risk_level="critical" → 二次确认（rm -rf, 发送消息）

用户拒绝 → Agent 自动换方案或告知用户，不中断对话
```

## 🛣️ 路线图

- [x] 📋 项目结构 & 需求定义
- [x] 🗣️ **M1**: CLI 对话 + Shell 命令执行
- [x] 🌐 **M2**: 浏览器操控（Playwright）
- [x] 🖥️ **M3**: 桌面操控（截屏 + 视觉理解 + 鼠标键盘）
- [ ] 📦 **M4**: 完整框架 + 文档 + 发布 PyPI
- [ ] 📱 **未来**: Telegram 通道、Cron 定时任务、多 Agent 协作

## 🔧 技术栈

| 领域 | 选型 |
|------|------|
| 语言 | Python 3.12+ |
| LLM 调用 | httpx（自己封装，不依赖 SDK） |
| 浏览器 | Playwright |
| 桌面操控 | pyautogui + Pillow |
| CLI | Rich + Prompt Toolkit |
| 数据库 | SQLite (aiosqlite) |
| 配置 | Pydantic Settings + YAML |

## 📖 文档

`docs/` 目录下的文档主要供开发者和 AI 协作使用，如果你对项目内部设计感兴趣，也欢迎翻阅：

- [需求文档 (PRD)](docs/requirements/PRD-v1.md)
- [架构设计](docs/architecture/architecture.md)
- [代码规范](docs/conventions/conventions.md)
- [开发任务](docs/tasks/tasks.md)

## 🤝 贡献

MiniClaw 目前处于早期开发阶段。欢迎 Star ⭐ 关注进展！

## 📜 License

MIT License

---

<p align="center">
  <b>🦞 MiniClaw — 能动手的本地 AI</b><br>
  <i>Your Local AI That Actually Does Things</i>
</p>
