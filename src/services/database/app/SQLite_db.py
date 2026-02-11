# -- SQLite Unified Handler --

import sqlite3
from src.services.database.app.app_db import AppDBHandler
from datetime import datetime, timezone
from typing import Optional, List, Dict


class SQLiteAppHandler(AppDBHandler):
    """
    Unified SQLite handler for users, conversations, and messages.
    Single database with proper foreign keys and cascading deletes.
    """
    def __init__(self, db_path: str):
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row

        self.conn.execute("PRAGMA foreign_keys = ON;")
        self.create_tables()

    def create_tables(self) -> None:
        """Create all tables with proper foreign key relationships."""
        cur = self.conn.cursor()

        cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            hashed_password TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT,
            created_at TEXT NOT NULL,
            last_message_at TEXT,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        )
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            conversation_id INTEGER NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY(conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
        )
        """)

        self.conn.commit()

    # -- user --

    def create_user(self, username: str, hashed_password: str) -> int:
        """Create a new user. Returns the user ID."""
        cur = self.conn.cursor()
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        cur.execute(
            "INSERT INTO users (username, hashed_password, created_at) VALUES (?, ?, ?)",
            (username, hashed_password, now)
        )
        self.conn.commit()
        return cur.lastrowid

    def get_user_by_username(self, username: str) -> Optional[dict]:
        """Retrieve user by username. Returns None if not found."""
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM users WHERE username = ?", (username,))
        row = cur.fetchone()
        return dict(row) if row else None

    # -- conversation --

    def create_conversation(self, user_id: int) -> int:
        """Create a new conversation for a user. Returns the conversation ID."""
        cur = self.conn.cursor()
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        cur.execute(
            "INSERT INTO conversations (user_id, title, created_at, last_message_at) VALUES (?, NULL, ?, NULL)",
            (user_id, now)
        )
        self.conn.commit()
        return cur.lastrowid

    def get_conversation(self, conversation_id: int) -> Optional[Dict]:
        """Retrieve conversation by ID. Returns None if not found."""
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM conversations WHERE id = ?", (conversation_id,))
        row = cur.fetchone()
        return dict(row) if row else None

    def list_conversations(self, user_id: int) -> List[Dict]:
        """List all conversations for a user, ordered by most recent first."""
        cur = self.conn.cursor()
        cur.execute(
            """
            SELECT *
            FROM conversations
            WHERE user_id = ?
            ORDER BY COALESCE(last_message_at, created_at) DESC
            """,
            (user_id,)
        )
        rows = cur.fetchall()
        return [dict(row) for row in rows]

    def update_conversation_title(self, user_id: int, conversation_id: int, title: str) -> None:
        """Update conversation title."""
        self._verify_conversation_ownership(user_id, conversation_id)
        cur = self.conn.cursor()
        cur.execute(
            "UPDATE conversations SET title = ? WHERE id = ?",
            (title, conversation_id)
        )
        self.conn.commit()

    def delete_conversation(self, user_id: int, conversation_id: int) -> None:
        """Delete conversation. Cascades to messages."""
        self._verify_conversation_ownership(user_id, conversation_id)
        cur = self.conn.cursor()
        cur.execute("DELETE FROM conversations WHERE id = ?", (conversation_id,))
        self.conn.commit()

    def _verify_conversation_ownership(self, user_id: int, conversation_id: int) -> None:
        """Helper: Verify that user owns this conversation. Raises ValueError if not."""
        cur = self.conn.cursor()
        cur.execute("SELECT user_id FROM conversations WHERE id = ?", (conversation_id,))
        row = cur.fetchone()
        if not row or row["user_id"] != user_id:
            raise ValueError("User does not own this conversation")

    # -- message --

    def insert_message(
        self,
        user_id: int,
        conversation_id: Optional[int],
        role: str,
        content: str
    ) -> int:
        """
        Insert a message into a conversation.
        If conversation_id is None, creates a new conversation.
        Returns the conversation ID (not message ID for backward compatibility).
        """
        cur = self.conn.cursor()

        # Create conversation if needed
        if conversation_id is None:
            conversation_id = self.create_conversation(user_id)
        else:
            # Verify ownership
            self._verify_conversation_ownership(user_id, conversation_id)

        now = datetime.now(timezone.utc).isoformat(timespec="seconds")

        cur.execute(
            "INSERT INTO messages (user_id, conversation_id, role, content, created_at) VALUES (?, ?, ?, ?, ?)",
            (user_id, conversation_id, role, content, now)
        )

        cur.execute(
            "UPDATE conversations SET last_message_at = ? WHERE id = ?",
            (now, conversation_id)
        )

        self.conn.commit()
        return conversation_id

    def list_conversation_messages(
        self,
        user_id: int,
        conversation_id: int,
        limit: int = 10
    ) -> List[Dict]:
        """
        List messages in a conversation (with ownership verification).
        Returns the most recent 'limit' messages, oldest first.
        If limit=0, return all messages.
        """
        self._verify_conversation_ownership(user_id, conversation_id)
        cur = self.conn.cursor()

        if limit > 0:
            cur.execute(
                "SELECT * FROM messages WHERE conversation_id = ? ORDER BY id DESC LIMIT ?",
                (conversation_id, limit)
            )
        else:
            # No limit, get all messages
            cur.execute(
                "SELECT * FROM messages WHERE conversation_id = ? ORDER BY id DESC",
                (conversation_id,)
            )

        rows = cur.fetchall()
        # Reverse to make oldest first
        return [dict(row) for row in reversed(rows)]


    def list_messages(self, user_id: int, limit: int = 10) -> List[Dict]:
        """
        List the most recent 'limit' messages for a user, oldest first.
        If limit=0, return all messages.
        """
        cur = self.conn.cursor()

        if limit > 0:
            cur.execute(
                "SELECT * FROM messages WHERE user_id = ? ORDER BY id DESC LIMIT ?",
                (user_id, limit)
            )
        else:
            cur.execute(
                "SELECT * FROM messages WHERE user_id = ? ORDER BY id DESC",
                (user_id,)
            )

        rows = cur.fetchall()
        return [dict(row) for row in reversed(rows)]
