"""
MiniClaw - Skill 技能插件系统

借鉴 OpenClaw 的 SKILL.md + Plugin 分离设计。
Skill = SKILL.md（知识/SOP）+ tools.py（工具代码）

对应 PRD：F7 Skill 技能插件系统
"""

from miniclaw.skills.loader import SkillInfo, SkillLoader
from miniclaw.skills.matcher import SkillMatcher

__all__ = ["SkillInfo", "SkillLoader", "SkillMatcher"]
