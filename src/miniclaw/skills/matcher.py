"""
MiniClaw - Skill 匹配器

根据用户输入自动匹配激活相关 Skill。
v1 使用关键词匹配，v2 可加入 LLM 意图判断。

对应 PRD：F7 Skill 技能插件系统
"""

from miniclaw.skills.loader import SkillInfo
from miniclaw.utils.logging import get_logger

logger = get_logger(__name__)


class SkillMatcher:
    """Skill 匹配器

    根据用户输入的关键词自动匹配激活相关 Skill。
    匹配规则：用户输入中包含 Skill 的任一激活关键词。
    """

    def __init__(self, skills: dict[str, SkillInfo] | None = None) -> None:
        self._skills = skills or {}

    def update_skills(self, skills: dict[str, SkillInfo]) -> None:
        """更新可用 Skill 列表"""
        self._skills = skills

    def match(self, user_input: str) -> list[SkillInfo]:
        """根据用户输入匹配激活 Skill

        Args:
            user_input: 用户输入文本

        Returns:
            匹配到的 SkillInfo 列表（按匹配度排序）
        """
        input_lower = user_input.lower()
        matched: list[tuple[int, SkillInfo]] = []

        for skill in self._skills.values():
            score = 0
            for keyword in skill.activation_keywords:
                if keyword.lower() in input_lower:
                    score += 1
            if score > 0:
                matched.append((score, skill))

        # 按匹配度降序
        matched.sort(key=lambda x: x[0], reverse=True)

        result = [info for _, info in matched]
        if result:
            logger.debug(
                "Skill 匹配",
                input=user_input[:50],
                matched=[s.name for s in result],
            )
        return result

    def match_best(self, user_input: str) -> SkillInfo | None:
        """匹配最相关的 Skill"""
        matched = self.match(user_input)
        return matched[0] if matched else None
