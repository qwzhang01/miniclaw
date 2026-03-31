"""
MiniClaw - 长期记忆

SQLite FTS5 全文搜索，跨会话持久化用户偏好和重要信息。
同时支持会话持久化（退出后下次可继续上次对话）。

对应 PRD：F8 记忆系统
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any

import aiosqlite

from miniclaw.utils.logging import get_logger

logger = get_logger(__name__)

DEFAULT_DB_PATH = Path.home() / ".miniclaw" / "memory.db"

# 建表 SQL
_INIT_SQL = """
CREATE TABLE IF NOT EXISTS memories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    content TEXT NOT NULL,
    category TEXT DEFAULT 'general',
    created_at TEXT NOT NULL,
    metadata TEXT DEFAULT '{}'
);

CREATE VIRTUAL TABLE IF NOT EXISTS memories_fts USING fts5(
    content,
    category,
    content_rowid='id',
    tokenize='unicode61'
);

CREATE TRIGGER IF NOT EXISTS memories_ai AFTER INSERT ON memories BEGIN
    INSERT INTO memories_fts(rowid, content, category)
    VALUES (new.id, new.content, new.category);
END;

CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,
    messages TEXT NOT NULL DEFAULT '[]',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
"""


class LongTermMemory:
    """长期记忆 — SQLite FTS5 全文搜索 + 会话持久化

    使用方式：
        memory = LongTermMemory()
        await memory.init()
        await memory.store("用户偏好：喜欢简洁回答")
        results = await memory.search("偏好")
        await memory.close()
    """

    def __init__(self, db_path: Path | None = None) -> None:
        self.db_path = db_path or DEFAULT_DB_PATH
        self._db: aiosqlite.Connection | None = None

    async def init(self) -> None:
        """初始化数据库（创建表）"""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._db = await aiosqlite.connect(str(self.db_path))
        await self._db.executescript(_INIT_SQL)
        await self._db.commit()
        logger.info("长期记忆初始化", path=str(self.db_path))

    async def store(
        self,
        content: str,
        category: str = "general",
        metadata: dict[str, Any] | None = None,
    ) -> int:
        """存储一条记忆

        Returns:
            记忆 ID
        """
        assert self._db is not None
        now = datetime.now().isoformat()
        meta_json = json.dumps(metadata or {}, ensure_ascii=False)
        cursor = await self._db.execute(
            "INSERT INTO memories (content, category, created_at, metadata) "
            "VALUES (?, ?, ?, ?)",
            (content, category, now, meta_json),
        )
        await self._db.commit()
        row_id = cursor.lastrowid or 0
        logger.debug("存储记忆", id=row_id, category=category)
        return row_id

    async def search(self, query: str, limit: int = 5) -> list[dict[str, Any]]:
        """全文搜索记忆（FTS5 + LIKE fallback）

        Returns:
            匹配的记忆列表
        """
        assert self._db is not None
        # 先尝试 FTS5 搜索
        try:
            cursor = await self._db.execute(
                "SELECT m.id, m.content, m.category, m.created_at, m.metadata "
                "FROM memories m "
                "JOIN memories_fts f ON m.id = f.rowid "
                "WHERE memories_fts MATCH ? "
                "ORDER BY rank LIMIT ?",
                (query + "*", limit),
            )
            rows = await cursor.fetchall()
            if rows:
                return self._rows_to_dicts(rows)
        except Exception:
            pass
        # Fallback: LIKE 搜索（对中文更友好）
        cursor = await self._db.execute(
            "SELECT id, content, category, created_at, metadata "
            "FROM memories WHERE content LIKE ? "
            "ORDER BY id DESC LIMIT ?",
            (f"%{query}%", limit),
        )
        rows = await cursor.fetchall()
        return self._rows_to_dicts(rows)

    @staticmethod
    def _rows_to_dicts(rows: Any) -> list[dict[str, Any]]:
        """将数据库行转为字典列表"""
        return [
            {
                "id": r[0],
                "content": r[1],
                "category": r[2],
                "created_at": r[3],
                "metadata": json.loads(r[4]) if r[4] else {},
            }
            for r in rows
        ]

    async def get_all(self, limit: int = 50) -> list[dict[str, Any]]:
        """获取所有记忆（最新优先）"""
        assert self._db is not None
        cursor = await self._db.execute(
            "SELECT id, content, category, created_at FROM memories "
            "ORDER BY id DESC LIMIT ?",
            (limit,),
        )
        rows = await cursor.fetchall()
        return [
            {"id": r[0], "content": r[1], "category": r[2], "created_at": r[3]}
            for r in rows
        ]

    # --- 会话持久化 ---

    async def save_session(
        self, session_id: str, messages: list[dict[str, Any]]
    ) -> None:
        """保存会话到 SQLite"""
        assert self._db is not None
        now = datetime.now().isoformat()
        messages_json = json.dumps(messages, ensure_ascii=False)
        await self._db.execute(
            "INSERT OR REPLACE INTO sessions (id, messages, created_at, updated_at) "
            "VALUES (?, ?, COALESCE("
            "  (SELECT created_at FROM sessions WHERE id = ?), ?), ?)",
            (session_id, messages_json, session_id, now, now),
        )
        await self._db.commit()

    async def load_session(self, session_id: str) -> list[dict[str, Any]] | None:
        """从 SQLite 加载会话"""
        assert self._db is not None
        cursor = await self._db.execute(
            "SELECT messages FROM sessions WHERE id = ?",
            (session_id,),
        )
        row = await cursor.fetchone()
        if row:
            return json.loads(row[0])  # type: ignore[no-any-return]
        return None

    async def list_sessions(self) -> list[dict[str, str]]:
        """列出所有会话"""
        assert self._db is not None
        cursor = await self._db.execute(
            "SELECT id, created_at, updated_at FROM sessions ORDER BY updated_at DESC"
        )
        rows = await cursor.fetchall()
        return [
            {"id": r[0], "created_at": r[1], "updated_at": r[2]}
            for r in rows
        ]

    async def close(self) -> None:
        """关闭数据库连接"""
        if self._db:
            await self._db.close()
            self._db = None
