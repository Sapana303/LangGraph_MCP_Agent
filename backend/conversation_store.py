"""Small SQLite repository for durable conversations and messages."""

from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from uuid import uuid4

from backend.config import DATABASE_PATH
from backend.exceptions import ConversationNotFoundError


def _now() -> str:
    return datetime.now(UTC).isoformat()


class ConversationStore:
    """Use one short-lived SQLite connection per operation for simple safe access."""

    def initialize(self) -> None:
        DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS conversations (
                    id TEXT PRIMARY KEY,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    conversation_id TEXT NOT NULL,
                    role TEXT NOT NULL CHECK(role IN ('user', 'assistant')),
                    content TEXT NOT NULL,
                    artifacts TEXT,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(conversation_id) REFERENCES conversations(id)
                );
                CREATE INDEX IF NOT EXISTS idx_messages_conversation ON messages(conversation_id, id);
                """
            )
            try:
                connection.execute("ALTER TABLE messages ADD COLUMN artifacts TEXT")
            except sqlite3.OperationalError:
                pass  # Existing databases already have this migration or the column.

    def create(self) -> str:
        conversation_id = str(uuid4())
        now = _now()
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO conversations(id, created_at, updated_at) VALUES (?, ?, ?)",
                (conversation_id, now, now),
            )
        return conversation_id

    def messages(self, conversation_id: str) -> list[dict[str, object]]:
        with self._connect() as connection:
            exists = connection.execute("SELECT 1 FROM conversations WHERE id = ?", (conversation_id,)).fetchone()
            if not exists:
                raise ConversationNotFoundError("Conversation was not found.")
            rows = connection.execute(
                "SELECT role, content, artifacts FROM messages WHERE conversation_id = ? ORDER BY id",
                (conversation_id,),
            ).fetchall()
        return [
            {
                "role": row["role"],
                "content": row["content"],
                "artifacts": json.loads(row["artifacts"]) if row["artifacts"] else None,
            }
            for row in rows
        ]

    def append_pair(
        self,
        conversation_id: str,
        question: str,
        answer: str,
        artifacts: dict | None,
    ) -> None:
        now = _now()
        with self._connect() as connection:
            connection.executemany(
                "INSERT INTO messages(conversation_id, role, content, artifacts, created_at) VALUES (?, ?, ?, ?, ?)",
                [
                    (conversation_id, "user", question, None, now),
                    (
                        conversation_id,
                        "assistant",
                        answer,
                        json.dumps(artifacts) if artifacts else None,
                        now,
                    ),
                ],
            )
            connection.execute("UPDATE conversations SET updated_at = ? WHERE id = ?", (now, conversation_id))

    @staticmethod
    def _connect() -> sqlite3.Connection:
        connection = sqlite3.connect(DATABASE_PATH)
        connection.row_factory = sqlite3.Row
        return connection


store = ConversationStore()
