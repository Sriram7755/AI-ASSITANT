import sqlite3
import datetime
from pathlib import Path
from typing import List, Dict, Optional, Any
from app.config.settings import settings
from app.core.logging_config import logger

class MemoryManager:
    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or (settings.data_dir / "memory.db")
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        """Create sqlite tables for long-term facts and reminders."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS memories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    key TEXT UNIQUE NOT NULL,
                    value TEXT NOT NULL,
                    category TEXT DEFAULT 'general',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS reminders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    trigger_time TEXT NOT NULL,
                    is_completed INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()
        logger.info(f"Memory database initialized at {self.db_path}")

    def remember(self, key: str, value: str, category: str = "general") -> bool:
        """Store or update a key-value memory."""
        try:
            key_clean = key.strip().lower()
            val_clean = value.strip()
            now = datetime.datetime.now().isoformat()
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO memories (key, value, category, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT(key) DO UPDATE SET
                        value = excluded.value,
                        category = excluded.category,
                        updated_at = excluded.updated_at
                """, (key_clean, val_clean, category, now, now))
                conn.commit()
            logger.info(f"Memory saved: [{key_clean}] -> '{val_clean}'")
            return True
        except Exception as e:
            logger.error(f"Failed to save memory: {e}")
            return False

    def retrieve_memory(self, query: str) -> List[Dict[str, Any]]:
        """Search stored memories by key or content."""
        query_clean = f"%{query.strip().lower()}%"
        results = []
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT id, key, value, category, created_at FROM memories
                    WHERE LOWER(key) LIKE ? OR LOWER(value) LIKE ? OR LOWER(category) LIKE ?
                    ORDER BY updated_at DESC
                """, (query_clean, query_clean, query_clean))
                rows = cursor.fetchall()
                for row in rows:
                    results.append(dict(row))
        except Exception as e:
            logger.error(f"Failed to retrieve memory for '{query}': {e}")
        return results

    def list_memories(self) -> List[Dict[str, Any]]:
        """Retrieve all stored memories."""
        results = []
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT id, key, value, category, created_at FROM memories ORDER BY updated_at DESC")
                for row in cursor.fetchall():
                    results.append(dict(row))
        except Exception as e:
            logger.error(f"Failed to list memories: {e}")
        return results

    def forget_memory(self, key_or_id: str) -> bool:
        """Delete a memory by key or ID."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                if key_or_id.isdigit():
                    cursor.execute("DELETE FROM memories WHERE id = ?", (int(key_or_id),))
                else:
                    cursor.execute("DELETE FROM memories WHERE LOWER(key) = ?", (key_or_id.strip().lower(),))
                conn.commit()
                deleted = cursor.rowcount > 0
            if deleted:
                logger.info(f"Forgotten memory: {key_or_id}")
            return deleted
        except Exception as e:
            logger.error(f"Failed to forget memory '{key_or_id}': {e}")
            return False

    def save_reminder(self, title: str, trigger_time: str) -> int:
        """Persist a scheduled reminder."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO reminders (title, trigger_time) VALUES (?, ?)",
                (title, trigger_time)
            )
            conn.commit()
            return cursor.lastrowid

    def complete_reminder(self, reminder_id: int):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE reminders SET is_completed = 1 WHERE id = ?", (reminder_id,))
            conn.commit()
