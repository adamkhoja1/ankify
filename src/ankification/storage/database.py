"""SQLite database operations."""

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

import aiosqlite

from ..cards.models import Card, CardStatus, card_from_dict


class Database:
    """Async SQLite database manager."""

    def __init__(self, db_path: str | Path) -> None:
        """Initialize database.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = Path(db_path)
        self._connection: aiosqlite.Connection | None = None

    async def connect(self) -> None:
        """Connect to database and initialize schema."""
        # Ensure directory exists
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # Connect to database
        self._connection = await aiosqlite.connect(str(self.db_path))
        self._connection.row_factory = aiosqlite.Row

        # Enable foreign keys
        await self._connection.execute("PRAGMA foreign_keys = ON")

        # Initialize schema
        await self._init_schema()

    async def _init_schema(self) -> None:
        """Initialize database schema."""
        schema_path = Path(__file__).parent / "schema.sql"
        with open(schema_path) as f:
            schema_sql = f.read()

        await self._connection.executescript(schema_sql)  # type: ignore
        await self._connection.commit()  # type: ignore

    async def close(self) -> None:
        """Close database connection."""
        if self._connection:
            await self._connection.close()
            self._connection = None

    async def __aenter__(self) -> "Database":
        """Async context manager entry."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit."""
        await self.close()

    # Card operations

    async def save_card(self, card: Card) -> None:
        """Save or update a card.

        Args:
            card: Card to save
        """
        if not self._connection:
            raise RuntimeError("Database not connected")

        # Serialize card content
        content_json = card.to_json()

        # Upsert card
        await self._connection.execute(
            """
            INSERT INTO cards (id, type, content, source, status, created_at, modified_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                content = excluded.content,
                status = excluded.status,
                modified_at = excluded.modified_at
            """,
            (
                card.id,
                card.type.value,
                content_json,
                card.source,
                card.status.value,
                card.created_at,
                card.modified_at,
            ),
        )

        # Update tags
        await self._connection.execute("DELETE FROM tags WHERE card_id = ?", (card.id,))
        for tag in card.tags:
            await self._connection.execute(
                "INSERT INTO tags (card_id, tag) VALUES (?, ?)", (card.id, tag)
            )

        await self._connection.commit()

    async def get_card(self, card_id: str) -> Card | None:
        """Retrieve a card by ID.

        Args:
            card_id: Card ID

        Returns:
            Card instance or None if not found
        """
        if not self._connection:
            raise RuntimeError("Database not connected")

        cursor = await self._connection.execute(
            "SELECT content FROM cards WHERE id = ?", (card_id,)
        )
        row = await cursor.fetchone()

        if not row:
            return None

        return card_from_dict(json.loads(row["content"]))

    async def get_cards_by_status(self, status: CardStatus) -> list[Card]:
        """Get all cards with a specific status.

        Args:
            status: Card status to filter by

        Returns:
            List of cards
        """
        if not self._connection:
            raise RuntimeError("Database not connected")

        cursor = await self._connection.execute(
            "SELECT content FROM cards WHERE status = ? ORDER BY created_at",
            (status.value,),
        )
        rows = await cursor.fetchall()

        return [card_from_dict(json.loads(row["content"])) for row in rows]

    async def get_cards_by_session(self, session_id: str) -> list[Card]:
        """Get all cards in a session.

        Args:
            session_id: Session ID

        Returns:
            List of cards
        """
        if not self._connection:
            raise RuntimeError("Database not connected")

        cursor = await self._connection.execute(
            """
            SELECT c.content
            FROM cards c
            JOIN session_cards sc ON c.id = sc.card_id
            WHERE sc.session_id = ?
            ORDER BY c.created_at
            """,
            (session_id,),
        )
        rows = await cursor.fetchall()

        return [card_from_dict(json.loads(row["content"])) for row in rows]

    # Session operations

    async def create_session(
        self,
        sources: list[str],
        provider: str = "openai",
        card_types: list[str] | None = None,
        count_guidance: str = "10-15",
    ) -> str:
        """Create a new session.

        Args:
            sources: List of source URLs/files
            provider: LLM provider used
            card_types: Types of cards generated
            count_guidance: Card count guidance string

        Returns:
            Session ID
        """
        if not self._connection:
            raise RuntimeError("Database not connected")

        session_id = str(uuid.uuid4())
        sources_json = json.dumps(sources)
        card_types_str = ",".join(card_types) if card_types else "basic,cloze"

        await self._connection.execute(
            """
            INSERT INTO sessions (id, sources, provider, card_types, count_guidance)
            VALUES (?, ?, ?, ?, ?)
            """,
            (session_id, sources_json, provider, card_types_str, count_guidance),
        )
        await self._connection.commit()

        return session_id

    async def add_card_to_session(self, session_id: str, card_id: str) -> None:
        """Add a card to a session.

        Args:
            session_id: Session ID
            card_id: Card ID
        """
        if not self._connection:
            raise RuntimeError("Database not connected")

        await self._connection.execute(
            "INSERT INTO session_cards (session_id, card_id) VALUES (?, ?)",
            (session_id, card_id),
        )
        await self._connection.commit()

    async def complete_session(self, session_id: str) -> None:
        """Mark a session as completed.

        Args:
            session_id: Session ID
        """
        if not self._connection:
            raise RuntimeError("Database not connected")

        await self._connection.execute(
            "UPDATE sessions SET completed_at = ? WHERE id = ?",
            (datetime.now(), session_id),
        )
        await self._connection.commit()

    async def get_sessions(self, limit: int = 100) -> list[dict[str, Any]]:
        """Get recent sessions.

        Args:
            limit: Maximum number of sessions to return

        Returns:
            List of session dictionaries
        """
        if not self._connection:
            raise RuntimeError("Database not connected")

        cursor = await self._connection.execute(
            """
            SELECT id, sources, provider, card_types, count_guidance,
                   created_at, completed_at
            FROM sessions
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (limit,),
        )
        rows = await cursor.fetchall()

        return [
            {
                "id": row["id"],
                "sources": json.loads(row["sources"]),
                "provider": row["provider"],
                "card_types": row["card_types"],
                "count_guidance": row["count_guidance"],
                "created_at": row["created_at"],
                "completed_at": row["completed_at"],
            }
            for row in rows
        ]

    # Edit history operations

    async def record_edit(
        self,
        card_id: str,
        old_content: str,
        new_content: str,
        edit_type: str,
        feedback: str | None = None,
    ) -> None:
        """Record a card edit in history.

        Args:
            card_id: Card ID
            old_content: Previous card content (JSON)
            new_content: New card content (JSON)
            edit_type: Type of edit ('manual' or 'llm_refine')
            feedback: Optional feedback for LLM refinements
        """
        if not self._connection:
            raise RuntimeError("Database not connected")

        await self._connection.execute(
            """
            INSERT INTO edit_history
            (card_id, old_content, new_content, edit_type, feedback)
            VALUES (?, ?, ?, ?, ?)
            """,
            (card_id, old_content, new_content, edit_type, feedback),
        )
        await self._connection.commit()

    async def get_edit_history(self, card_id: str) -> list[dict[str, Any]]:
        """Get edit history for a card.

        Args:
            card_id: Card ID

        Returns:
            List of edit history entries
        """
        if not self._connection:
            raise RuntimeError("Database not connected")

        cursor = await self._connection.execute(
            """
            SELECT old_content, new_content, edit_type, feedback, timestamp
            FROM edit_history
            WHERE card_id = ?
            ORDER BY timestamp DESC
            """,
            (card_id,),
        )
        rows = await cursor.fetchall()

        return [dict(row) for row in rows]

    # Statistics and queries

    async def get_card_count_by_status(self) -> dict[str, int]:
        """Get count of cards by status.

        Returns:
            Dictionary mapping status to count
        """
        if not self._connection:
            raise RuntimeError("Database not connected")

        cursor = await self._connection.execute(
            "SELECT status, COUNT(*) as count FROM cards GROUP BY status"
        )
        rows = await cursor.fetchall()

        return {row["status"]: row["count"] for row in rows}

    async def search_cards_by_tag(self, tag: str) -> list[Card]:
        """Search cards by tag.

        Args:
            tag: Tag to search for

        Returns:
            List of matching cards
        """
        if not self._connection:
            raise RuntimeError("Database not connected")

        cursor = await self._connection.execute(
            """
            SELECT c.content
            FROM cards c
            JOIN tags t ON c.id = t.card_id
            WHERE t.tag = ?
            ORDER BY c.created_at DESC
            """,
            (tag,),
        )
        rows = await cursor.fetchall()

        return [card_from_dict(json.loads(row["content"])) for row in rows]

    async def get_all_cards(self) -> list[Card]:
        """Get all cards.

        Returns:
            List of all cards
        """
        if not self._connection:
            raise RuntimeError("Database not connected")

        cursor = await self._connection.execute(
            "SELECT content FROM cards ORDER BY created_at DESC"
        )
        rows = await cursor.fetchall()

        return [card_from_dict(json.loads(row["content"])) for row in rows]

    async def delete_card(self, card_id: str) -> None:
        """Delete a card and its related data.

        Args:
            card_id: Card ID to delete
        """
        if not self._connection:
            raise RuntimeError("Database not connected")

        # Delete related records first (foreign key constraints)
        await self._connection.execute("DELETE FROM tags WHERE card_id = ?", (card_id,))
        await self._connection.execute(
            "DELETE FROM session_cards WHERE card_id = ?", (card_id,)
        )
        await self._connection.execute(
            "DELETE FROM edit_history WHERE card_id = ?", (card_id,)
        )

        # Delete the card itself
        await self._connection.execute("DELETE FROM cards WHERE id = ?", (card_id,))
        await self._connection.commit()

    async def delete_session(self, session_id: str) -> None:
        """Delete a session and unlink its cards.

        Args:
            session_id: Session ID to delete
        """
        if not self._connection:
            raise RuntimeError("Database not connected")

        # Delete session-card links
        await self._connection.execute(
            "DELETE FROM session_cards WHERE session_id = ?", (session_id,)
        )

        # Delete the session
        await self._connection.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
        await self._connection.commit()
