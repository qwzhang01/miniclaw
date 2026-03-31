"""
MiniClaw - Session 管理测试
"""

from miniclaw.gateway.session import SessionManager
from miniclaw.tools.registry import ToolRegistry


class TestSessionManager:
    def test_create_new_session(self):
        mgr = SessionManager(ToolRegistry())
        session = mgr.get_or_create("test-1")
        assert session.id == "test-1"
        assert session.context is not None

    def test_get_existing_session(self):
        mgr = SessionManager(ToolRegistry())
        s1 = mgr.get_or_create("test-1")
        s2 = mgr.get_or_create("test-1")
        assert s1 is s2

    def test_different_sessions(self):
        mgr = SessionManager(ToolRegistry())
        s1 = mgr.get_or_create("test-1")
        s2 = mgr.get_or_create("test-2")
        assert s1 is not s2

    def test_clear_session(self):
        mgr = SessionManager(ToolRegistry())
        session = mgr.get_or_create("test-1")
        session.context.add_user_message("hello")
        mgr.clear("test-1")
        # 消息应被清空（只剩系统提示）
        assert len(session.context.messages) == 1

    def test_get_nonexistent(self):
        mgr = SessionManager(ToolRegistry())
        assert mgr.get("nonexistent") is None

    def test_touch_updates_time(self):
        mgr = SessionManager(ToolRegistry())
        session = mgr.get_or_create("test-1")
        old_time = session.last_active_at
        import time

        time.sleep(0.01)
        session.touch()
        assert session.last_active_at > old_time
