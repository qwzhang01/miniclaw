# 贡献指南

感谢你对 MiniClaw 的关注！欢迎参与贡献。

## 开发环境搭建

```bash
# 1. 克隆仓库
git clone https://github.com/avinzhang/miniclaw.git
cd miniclaw

# 2. 创建虚拟环境
python3.12 -m venv .venv
source .venv/bin/activate

# 3. 安装依赖（含开发工具）
pip install -e ".[dev]"

# 4. 安装 Playwright 浏览器
playwright install chromium

# 5. 运行测试
pytest tests/ -v

# 6. 检查代码质量
ruff check src/ tests/
mypy src/miniclaw/
```

## 代码规范

- **Python 3.12+**，所有函数必须有完整的 type hints
- **每个文件 ≤ 500 行**，超了就拆
- **中文注释**（本项目是教学材料）
- **ruff + mypy strict** 必须零错误
- 详见 [代码规范](docs/conventions/conventions.md)

## 提交规范

```
feat(agent): 实现 ReAct Agent Loop 主循环
fix(llm): 修复 Anthropic tool_use 响应解析
test(desktop): 添加 MacOSController 截屏测试
docs(readme): 更新快速开始指南
```

## 分支策略

```
main       ← 稳定版本
└── dev    ← 开发分支
    └── feat/xxx
```

## PR 流程

1. Fork 仓库
2. 基于 `dev` 创建分支：`feat/your-feature`
3. 编写代码 + 测试
4. 确保 `ruff check` + `mypy` + `pytest` 全部通过
5. 提交 PR 到 `dev` 分支
