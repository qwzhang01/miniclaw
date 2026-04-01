"""
MiniClaw - 短期记忆测试
"""

from miniclaw.memory.short_term import ShortTermMemory, _estimate_tokens


class TestEstimateTokens:
    def test_empty(self):
        assert _estimate_tokens([]) == 0

    def test_basic(self):
        msgs = [{"role": "user", "content": "hello world"}]  # 11 chars
        tokens = _estimate_tokens(msgs)
        assert tokens > 0

    def test_none_content(self):
        msgs = [{"role": "assistant", "content": None}]
        assert _estimate_tokens(msgs) == 0


class TestShortTermMemory:
    def test_add_and_get(self):
        mem = ShortTermMemory()
        mem.add({"role": "user", "content": "hi"})
        assert mem.message_count == 1
        assert mem.get_messages()[0]["content"] == "hi"

    def test_clear(self):
        mem = ShortTermMemory()
        mem.add({"role": "user", "content": "hi"})
        mem.clear()
        assert mem.message_count == 0

    def test_needs_compression_small(self):
        """少量消息不需要压缩"""
        mem = ShortTermMemory(max_tokens=10000)
        mem.add({"role": "user", "content": "short message"})
        assert mem.needs_compression() is False

    def test_needs_compression_large(self):
        """大量消息需要压缩"""
        mem = ShortTermMemory(max_tokens=100)
        for i in range(50):
            mem.add({"role": "user", "content": f"message {i} " * 20})
        assert mem.needs_compression() is True

    def test_compress(self):
        """压缩应保留 system + 摘要 + 最近 4 条"""
        mem = ShortTermMemory()
        mem.add({"role": "system", "content": "system prompt"})
        for i in range(10):
            mem.add({"role": "user", "content": f"msg {i}"})

        mem.compress("这是历史摘要")
        # system + 摘要 + 最近 4 条 = 6
        assert mem.message_count == 6
        assert mem.messages[0]["role"] == "system"
        assert "历史摘要" in mem.messages[1]["content"]

    def test_compress_short_history(self):
        """历史太短不压缩"""
        mem = ShortTermMemory()
        mem.add({"role": "system", "content": "sys"})
        mem.add({"role": "user", "content": "hi"})
        old_count = mem.message_count
        mem.compress("summary")
        assert mem.message_count == old_count  # 没变

    def test_estimated_tokens(self):
        mem = ShortTermMemory()
        mem.add({"role": "user", "content": "x" * 300})
        assert mem.estimated_tokens == 100  # 300 / 3

    def test_update_system_prompt(self):
        """更新系统提示词替换 messages[0]"""
        mem = ShortTermMemory()
        mem.add({"role": "system", "content": "旧提示词"})
        mem.add({"role": "user", "content": "hello"})
        mem.update_system_prompt("新提示词")
        assert mem.messages[0]["content"] == "新提示词"
        assert mem.message_count == 2  # 没有新增

    def test_update_system_prompt_no_system(self):
        """没有 system 消息时插入到开头"""
        mem = ShortTermMemory()
        mem.add({"role": "user", "content": "hello"})
        mem.update_system_prompt("插入的提示词")
        assert mem.messages[0]["role"] == "system"
        assert mem.messages[0]["content"] == "插入的提示词"
        assert mem.message_count == 2  # 插入了一条
