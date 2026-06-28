"""Project-local card store under `.ankify/` (relative to the working directory).

Layout:
  .ankify/sessions/<name>.json   one ReviewSession per named deck/topic
  .ankify/media/                 images referenced by cards
  .ankify/exports/<name>.apkg    continuously-regenerated package of ACCEPTED cards

A session is addressed by a short `name` (default "default"). This is the durable, per-project
standard for stopping and resuming card sets; it is not synced anywhere by default.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

from pydantic import ValidationError

from .server.session import SessionStore

logger = logging.getLogger(__name__)

DEFAULT_ROOT = ".ankify"


@dataclass
class SessionInfo:
    name: str
    cards: int
    accepted: int
    pending: int
    modified: float  # mtime (epoch seconds)


class Store:
    """Resolves `.ankify/` paths and lists sessions."""

    def __init__(self, root: str | Path = DEFAULT_ROOT) -> None:
        self.root = Path(root)

    @property
    def sessions_dir(self) -> Path:
        return self.root / "sessions"

    @property
    def media_dir(self) -> Path:
        return self.root / "media"

    @property
    def exports_dir(self) -> Path:
        return self.root / "exports"

    def session_path(self, name: str) -> Path:
        return self.sessions_dir / f"{name}.json"

    def export_path(self, name: str) -> Path:
        return self.exports_dir / f"{name}.apkg"

    def ensure(self) -> None:
        for directory in (self.sessions_dir, self.media_dir, self.exports_dir):
            directory.mkdir(parents=True, exist_ok=True)

    def list_sessions(self) -> list[SessionInfo]:
        infos: list[SessionInfo] = []
        if not self.sessions_dir.exists():
            return infos
        for path in sorted(self.sessions_dir.glob("*.json")):
            try:
                session = SessionStore(path).load()
            except (ValidationError, ValueError, OSError) as exc:
                logger.warning("skipping unreadable session %s: %s", path, exc)
                continue
            infos.append(
                SessionInfo(
                    name=path.stem,
                    cards=len(session.current_cards()),
                    accepted=len(session.approved_cards()),
                    pending=session.pending_count(),
                    modified=path.stat().st_mtime,
                )
            )
        return infos
