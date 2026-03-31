"""
MiniClaw - 长期记忆测试
"""


import pytest

from miniclaw.memory.long_term import LongTermMemory


@pytest.fixture
async def memory(tmp_path):
    """创建临时数据库的长期记忆实例"""
    db_path = tmp_path / "test_memory.db"
    mem = LongTermMemory(db_path=db_path)
    await mem.init()
    yield mem
    await mem.close()


class TestLongTermMemory:
    @pytest.mark.asyncio
    async def test_store_and_search(self, memory):
        """存储后能搜索到"""
        await memory.store("用户偏好：喜欢简洁回答", category="preference")
        results = await memory.search("偏好")
        assert len(results) >= 1
        assert "简洁" in results[0]["content"]

    @pytest.mark.asyncio
    async def test_store_returns_id(self, memory):
        """store 应返回记忆 ID"""
        mem_id = await memory.store("测试内容")
        assert mem_id > 0

    @pytest.mark.asyncio
    async def test_search_no_results(self, memory):
        """搜索无结果返回空列表"""
        results = await memory.search("不存在的内容xyz")
        assert results == []

    @pytest.mark.asyncio
    async def test_get_all(self, memory):
        """get_all 返回所有记忆"""
        await memory.store("记忆1")
        await memory.store("记忆2")
        all_mems = await memory.get_all()
        assert len(all_mems) == 2

    @pytest.mark.asyncio
    async def test_get_all_order(self, memory):
        """get_all 最新优先"""
        await memory.store("旧的")
        await memory.store("新的")
        all_mems = await memory.get_all()
        assert "新的" in all_mems[0]["content"]

    @pytest.mark.asyncio
    async def test_store_with_metadata(self, memory):
        """支持 metadata"""
        await memory.store(
            "重要信息",
            category="important",
            metadata={"source": "user"},
        )
        results = await memory.search("重要信息")
        assert results[0]["metadata"]["source"] == "user"


class TestSessionPersistence:
    @pytest.mark.asyncio
    async def test_save_and_load_session(self, memory):
        """保存会话后能加载"""
        messages = [
            {"role": "user", "content": "hello"},
            {"role": "assistant", "content": "hi"},
        ]
        await memory.save_session("test-session-1", messages)
        loaded = await memory.load_session("test-session-1")
        assert loaded is not None
        assert len(loaded) == 2
        assert loaded[0]["content"] == "hello"

    @pytest.mark.asyncio
    async def test_load_nonexistent_session(self, memory):
        """加载不存在的会话返回 None"""
        result = await memory.load_session("nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_update_session(self, memory):
        """更新已有会话"""
        await memory.save_session("s1", [{"role": "user", "content": "v1"}])
        await memory.save_session("s1", [
            {"role": "user", "content": "v1"},
            {"role": "assistant", "content": "v2"},
        ])
        loaded = await memory.load_session("s1")
        assert loaded is not None
        assert len(loaded) == 2

    @pytest.mark.asyncio
    async def test_list_sessions(self, memory):
        """列出所有会话"""
        await memory.save_session("s1", [])
        await memory.save_session("s2", [])
        sessions = await memory.list_sessions()
        assert len(sessions) == 2
