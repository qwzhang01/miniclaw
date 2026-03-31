"""
MiniClaw - Skill 匹配器测试
"""

from miniclaw.skills.loader import SkillInfo
from miniclaw.skills.matcher import SkillMatcher


def _make_skill(name: str, keywords: list[str]) -> SkillInfo:
    from pathlib import Path
    return SkillInfo(
        name=name,
        path=Path("."),
        activation_keywords=keywords,
    )


class TestSkillMatcher:
    def test_match_by_keyword(self):
        """匹配包含关键词的 Skill"""
        skills = {
            "shell": _make_skill("shell", ["命令", "终端", "shell"]),
            "coder": _make_skill("coder", ["代码", "Python", "编程"]),
        }
        matcher = SkillMatcher(skills)
        result = matcher.match("帮我执行一条终端命令")
        assert len(result) == 1
        assert result[0].name == "shell"

    def test_match_multiple(self):
        """同时匹配多个 Skill"""
        skills = {
            "shell": _make_skill("shell", ["文件", "命令"]),
            "coder": _make_skill("coder", ["文件", "代码"]),
        }
        matcher = SkillMatcher(skills)
        result = matcher.match("帮我读取这个文件")
        assert len(result) == 2

    def test_match_none(self):
        """没有匹配返回空列表"""
        skills = {
            "shell": _make_skill("shell", ["命令", "终端"]),
        }
        matcher = SkillMatcher(skills)
        result = matcher.match("今天天气怎么样")
        assert result == []

    def test_match_best(self):
        """match_best 返回最佳匹配"""
        skills = {
            "shell": _make_skill("shell", ["命令"]),
            "coder": _make_skill("coder", ["代码", "Python", "调试"]),
        }
        matcher = SkillMatcher(skills)
        best = matcher.match_best("帮我调试 Python 代码")
        assert best is not None
        assert best.name == "coder"

    def test_match_best_none(self):
        """没有匹配返回 None"""
        matcher = SkillMatcher({})
        assert matcher.match_best("hello") is None

    def test_update_skills(self):
        """update_skills 更新可用 Skill"""
        matcher = SkillMatcher()
        assert matcher.match("命令") == []

        matcher.update_skills({
            "shell": _make_skill("shell", ["命令"]),
        })
        assert len(matcher.match("执行命令")) == 1

    def test_case_insensitive(self):
        """匹配不区分大小写"""
        skills = {
            "coder": _make_skill("coder", ["Python", "code"]),
        }
        matcher = SkillMatcher(skills)
        result = matcher.match("help me write python code")
        assert len(result) == 1

    def test_sort_by_score(self):
        """多关键词匹配的排在前面"""
        skills = {
            "a": _make_skill("a", ["搜索"]),
            "b": _make_skill("b", ["搜索", "浏览器", "调研"]),
        }
        matcher = SkillMatcher(skills)
        result = matcher.match("帮我用浏览器搜索调研")
        assert result[0].name == "b"  # 匹配 3 个关键词，排第一
