"""
MiniClaw - Token 计数工具测试

测试 utils/tokens.py 的 token 统计功能。
"""

import logging

from miniclaw.utils.tokens import (
    RoleTokenStats,
    TokenCounter,
    TokenUsage,
    get_token_counter,
)


class TestTokenUsage:
    """测试单次调用 Token 使用量"""

    def test_total_tokens(self):
        """total_tokens 应为 input + output 之和"""
        usage = TokenUsage(input_tokens=100, output_tokens=50)
        assert usage.total_tokens == 150

    def test_default_zero(self):
        """默认值应为 0"""
        usage = TokenUsage()
        assert usage.input_tokens == 0
        assert usage.output_tokens == 0
        assert usage.total_tokens == 0


class TestRoleTokenStats:
    """测试单个角色的累计统计"""

    def test_record_single(self):
        """记录单次调用"""
        stats = RoleTokenStats(role="default")
        stats.record(TokenUsage(input_tokens=100, output_tokens=50))
        assert stats.total_input == 100
        assert stats.total_output == 50
        assert stats.total_tokens == 150
        assert stats.call_count == 1

    def test_record_multiple(self):
        """多次调用累计"""
        stats = RoleTokenStats(role="planner")
        stats.record(TokenUsage(input_tokens=100, output_tokens=50))
        stats.record(TokenUsage(input_tokens=200, output_tokens=80))
        assert stats.total_input == 300
        assert stats.total_output == 130
        assert stats.total_tokens == 430
        assert stats.call_count == 2


class TestTokenCounter:
    """测试 Token 计数器"""

    def test_record_and_get_stats(self):
        """记录后能获取角色统计"""
        counter = TokenCounter()
        counter.record("default", TokenUsage(input_tokens=100, output_tokens=50))
        stats = counter.get_stats("default")
        assert stats is not None
        assert stats.total_input == 100
        assert stats.total_output == 50

    def test_get_stats_nonexistent_role(self):
        """获取不存在的角色统计返回 None"""
        counter = TokenCounter()
        assert counter.get_stats("nonexistent") is None

    def test_multiple_roles(self):
        """支持多角色统计"""
        counter = TokenCounter()
        counter.record("default", TokenUsage(input_tokens=100, output_tokens=50))
        counter.record("planner", TokenUsage(input_tokens=200, output_tokens=80))
        counter.record("default", TokenUsage(input_tokens=150, output_tokens=60))

        assert counter.get_stats("default").total_input == 250
        assert counter.get_stats("planner").total_input == 200

    def test_total_input_output(self):
        """total_input/output 应为所有角色之和"""
        counter = TokenCounter()
        counter.record("default", TokenUsage(input_tokens=100, output_tokens=50))
        counter.record("planner", TokenUsage(input_tokens=200, output_tokens=80))
        assert counter.total_input == 300
        assert counter.total_output == 130
        assert counter.total_tokens == 430

    def test_get_all_stats(self):
        """get_all_stats 返回所有角色统计"""
        counter = TokenCounter()
        counter.record("default", TokenUsage(input_tokens=100, output_tokens=50))
        counter.record("maker", TokenUsage(input_tokens=200, output_tokens=80))
        all_stats = counter.get_all_stats()
        assert "default" in all_stats
        assert "maker" in all_stats
        assert len(all_stats) == 2

    def test_reset(self):
        """reset 应清空所有统计"""
        counter = TokenCounter()
        counter.record("default", TokenUsage(input_tokens=100, output_tokens=50))
        counter.reset()
        assert counter.total_tokens == 0
        assert counter.get_stats("default") is None

    def test_log_usage_outputs_debug(self, caplog):
        """log_usage 应以 debug 级别输出统计"""
        with caplog.at_level(logging.DEBUG):
            counter = TokenCounter()
            counter.record("default", TokenUsage(input_tokens=100, output_tokens=50))
            counter.log_usage()
        assert "token_summary" in caplog.text
        assert "token_total" in caplog.text


class TestGlobalCounter:
    """测试全局计数器单例"""

    def test_get_token_counter_returns_same_instance(self):
        """get_token_counter 应返回同一实例"""
        # 重置全局变量
        import miniclaw.utils.tokens as tokens_mod

        tokens_mod._global_counter = None

        counter1 = get_token_counter()
        counter2 = get_token_counter()
        assert counter1 is counter2
