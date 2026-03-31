"""
MiniClaw - Skill 加载器测试
"""

from pathlib import Path

import pytest

from miniclaw.skills.loader import SkillLoader, _parse_skill_md


class TestParseSkillMd:
    def test_parse_browser_research(self):
        """解析 browser-research SKILL.md"""
        skill_md = (
            Path(__file__).parent.parent.parent
            / "src" / "miniclaw" / "skills" / "builtin"
            / "browser-research" / "SKILL.md"
        )
        if not skill_md.exists():
            pytest.skip("SKILL.md not found")
        info = _parse_skill_md(skill_md)
        assert info.name == "browser-research"
        assert len(info.role) > 0
        assert len(info.activation_keywords) > 0
        assert "browser_open" in info.available_tools

    def test_parse_desktop_assistant(self):
        """解析 desktop-assistant SKILL.md"""
        skill_md = (
            Path(__file__).parent.parent.parent
            / "src" / "miniclaw" / "skills" / "builtin"
            / "desktop-assistant" / "SKILL.md"
        )
        if not skill_md.exists():
            pytest.skip("SKILL.md not found")
        info = _parse_skill_md(skill_md)
        assert info.name == "desktop-assistant"
        assert "screen_capture" in info.available_tools

    def test_parse_shell(self):
        """解析 shell SKILL.md"""
        skill_md = (
            Path(__file__).parent.parent.parent
            / "src" / "miniclaw" / "skills" / "builtin"
            / "shell" / "SKILL.md"
        )
        if not skill_md.exists():
            pytest.skip("SKILL.md not found")
        info = _parse_skill_md(skill_md)
        assert info.name == "shell"
        assert "shell_exec" in info.available_tools


class TestSkillLoader:
    def test_load_all_finds_builtin_skills(self):
        """load_all 应找到内置 Skills"""
        loader = SkillLoader()
        skills = loader.load_all()
        # 至少有 5 个内置 Skill
        assert len(skills) >= 5
        assert "browser-research" in skills
        assert "desktop-assistant" in skills
        assert "shell" in skills
        assert "coder" in skills
        assert "github" in skills

    def test_reload(self):
        """reload 应重新加载"""
        loader = SkillLoader()
        s1 = loader.load_all()
        s2 = loader.reload()
        assert len(s1) == len(s2)

    def test_get(self):
        """get 按名称获取"""
        loader = SkillLoader()
        loader.load_all()
        shell = loader.get("shell")
        assert shell is not None
        assert shell.name == "shell"
        assert loader.get("nonexistent") is None

    def test_skill_names(self):
        """skill_names 返回名称列表"""
        loader = SkillLoader()
        loader.load_all()
        names = loader.skill_names
        assert "shell" in names
        assert "coder" in names
