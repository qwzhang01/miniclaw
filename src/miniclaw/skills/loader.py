"""
MiniClaw - Skill 加载器

扫描 3 个目录（内置/全局/项目），解析 SKILL.md，注册 Skill 工具。
支持 /reload 手动重载（PRD F7）。

加载顺序（后加载覆盖先加载）：
1. 内置 Skills（src/miniclaw/skills/builtin/）
2. 全局 Skills（~/.miniclaw/skills/）
3. 项目 Skills（./skills/）

对应 PRD：F7 Skill 技能插件系统
"""

import re
from dataclasses import dataclass, field
from pathlib import Path

from miniclaw.utils.logging import get_logger

logger = get_logger(__name__)

# 内置 Skills 目录
BUILTIN_SKILLS_DIR = Path(__file__).parent / "builtin"
# 全局 Skills 目录
GLOBAL_SKILLS_DIR = Path.home() / ".miniclaw" / "skills"
# 项目 Skills 目录（相对于 cwd）
PROJECT_SKILLS_DIR = Path("./skills")


@dataclass
class SkillInfo:
    """解析后的 Skill 信息"""

    name: str
    path: Path
    role: str = ""
    activation_keywords: list[str] = field(default_factory=list)
    available_tools: list[str] = field(default_factory=list)
    workflow: str = ""
    raw_content: str = ""


def _parse_skill_md(path: Path) -> SkillInfo:
    """解析 SKILL.md 文件，提取角色、激活条件、工具列表等"""
    content = path.read_text(encoding="utf-8")
    name = path.parent.name

    info = SkillInfo(name=name, path=path, raw_content=content)

    # 提取角色（## 角色 下的段落）
    role_match = re.search(r"## 角色\s*\n(.*?)(?=\n##|\Z)", content, re.DOTALL)
    if role_match:
        info.role = role_match.group(1).strip()

    # 提取激活关键词（## 激活条件 下的内容）
    act_match = re.search(r"## 激活条件\s*\n(.*?)(?=\n##|\Z)", content, re.DOTALL)
    if act_match:
        text = act_match.group(1)
        # 从 "关键词1、关键词2" 或 "keyword1, keyword2" 格式提取
        keywords = re.findall(r"[\w\u4e00-\u9fff]+", text)
        # 过滤掉常见的无意义词
        stop_words = {"当", "用户", "提到", "以下", "关键词", "时", "激活"}
        info.activation_keywords = [
            k for k in keywords if k not in stop_words and len(k) > 1
        ]

    # 提取可用工具（## 可用工具 下的列表）
    tools_match = re.search(r"## 可用工具\s*\n(.*?)(?=\n##|\Z)", content, re.DOTALL)
    if tools_match:
        tools_text = tools_match.group(1)
        info.available_tools = re.findall(r"`(\w+)`", tools_text)

    # 提取工作流程
    wf_match = re.search(r"## 工作流程\s*\n(.*?)(?=\n##|\Z)", content, re.DOTALL)
    if wf_match:
        info.workflow = wf_match.group(1).strip()

    return info


class SkillLoader:
    """Skill 加载器

    扫描目录加载 Skill，支持 /reload 手动重载。
    """

    def __init__(self) -> None:
        self._skills: dict[str, SkillInfo] = {}

    def load_all(self) -> dict[str, SkillInfo]:
        """加载所有 Skill（按优先级：内置 → 全局 → 项目）"""
        self._skills.clear()

        for directory in [BUILTIN_SKILLS_DIR, GLOBAL_SKILLS_DIR, PROJECT_SKILLS_DIR]:
            self._scan_directory(directory)

        logger.info("Skill 加载完成", count=len(self._skills),
                     names=list(self._skills.keys()))
        return dict(self._skills)

    def reload(self) -> dict[str, SkillInfo]:
        """重新加载所有 Skill（/reload 命令）"""
        logger.info("重新加载 Skill")
        return self.load_all()

    def _scan_directory(self, directory: Path) -> None:
        """扫描目录中的 Skill"""
        if not directory.exists():
            return
        for skill_dir in sorted(directory.iterdir()):
            if not skill_dir.is_dir():
                continue
            skill_md = skill_dir / "SKILL.md"
            if skill_md.exists():
                try:
                    info = _parse_skill_md(skill_md)
                    self._skills[info.name] = info
                    logger.debug("加载 Skill", name=info.name, path=str(skill_dir))
                except Exception as e:
                    logger.warning("Skill 加载失败", path=str(skill_dir), error=repr(e))

    def get(self, name: str) -> SkillInfo | None:
        """按名称获取 Skill"""
        return self._skills.get(name)

    def get_all(self) -> dict[str, SkillInfo]:
        """获取所有已加载 Skill"""
        return dict(self._skills)

    @property
    def skill_names(self) -> list[str]:
        """已加载的 Skill 名称列表"""
        return list(self._skills.keys())
