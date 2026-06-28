"""AnkiConnect client: create decks and import Basic + Cloze notes, then sync.

Python reimplementation of the old bash import script, extended to support the Cloze note
type. Talks to the AnkiConnect add-on (default http://localhost:8765). Fails fast with a
clear error if Anki isn't reachable so the caller can tell the user to open Anki.
"""

from __future__ import annotations

import base64
import logging
import re
from dataclasses import dataclass
from pathlib import Path

import httpx

from .models import Card, CardType

logger = logging.getLogger(__name__)

DEFAULT_URL = "http://localhost:8765"

# Bare Anki-style <img src="file.png"> (not a URL or data URI) — these need media upload.
_IMG_RE = re.compile(r'<img\b[^>]*?\ssrc="(?!https?:|data:|/)([^"]+)"', re.IGNORECASE)


def _referenced_media(cards: list[Card]) -> set[str]:
    files: set[str] = set()
    for card in cards:
        for field in (card.front, card.back, card.cloze_text, card.extra):
            files.update(_IMG_RE.findall(field))
    return files


class AnkiConnectError(RuntimeError):
    """AnkiConnect was unreachable or returned an error."""


@dataclass
class ImportResult:
    added: int
    duplicates: int
    failed: int
    total: int


class AnkiConnect:
    """Minimal AnkiConnect client for deck creation, note import, and sync."""

    def __init__(self, url: str = DEFAULT_URL, timeout: float = 10.0) -> None:
        self.url = url
        self.timeout = timeout

    def _invoke(self, action: str, **params: object) -> object:
        try:
            resp = httpx.post(
                self.url,
                json={"action": action, "version": 6, "params": params},
                timeout=self.timeout,
            )
            resp.raise_for_status()
            data = resp.json()
        except httpx.HTTPError as exc:
            raise AnkiConnectError(
                f"cannot reach AnkiConnect at {self.url}: {exc}. Is Anki open with the "
                "AnkiConnect add-on (code 2055492159) installed?"
            ) from exc
        if data.get("error"):
            raise AnkiConnectError(f"AnkiConnect error on {action!r}: {data['error']}")
        return data.get("result")

    def is_reachable(self) -> bool:
        try:
            self._invoke("version")
            return True
        except AnkiConnectError:
            return False

    def deck_names(self) -> list[str]:
        result = self._invoke("deckNames")
        return list(result) if isinstance(result, list) else []

    def ensure_deck(self, deck: str) -> None:
        self._invoke("createDeck", deck=deck)

    @staticmethod
    def _note(card: Card, deck: str, tags: list[str]) -> dict[str, object]:
        all_tags = sorted(set(tags) | set(card.tags))
        if card.type is CardType.CLOZE:
            fields = {"Text": card.cloze_text, "Back Extra": card.extra}
            model = "Cloze"
        else:
            fields = {"Front": card.front, "Back": card.back}
            model = "Basic"
        return {
            "deckName": f"{deck}::{card.subdeck}" if card.subdeck else deck,
            "modelName": model,
            "fields": fields,
            "tags": all_tags,
            "options": {"allowDuplicate": False},
        }

    def store_media(self, cards: list[Card], media_dir: str | Path) -> None:
        """Upload any bare <img>-referenced files from `media_dir` into Anki's collection."""
        media_dir = Path(media_dir)
        for filename in _referenced_media(cards):
            path = media_dir / filename
            if path.exists():
                data = base64.b64encode(path.read_bytes()).decode()
                self._invoke("storeMediaFile", filename=filename, data=data)
            else:
                logger.warning("media file referenced but not found: %s", path)

    def import_cards(
        self,
        cards: list[Card],
        deck: str,
        tags: list[str] | None = None,
        media_dir: str | Path | None = None,
    ) -> ImportResult:
        """Add cards to `deck` (creating it if needed). Reversible cards add two notes.

        Returns counts of added / duplicate / failed notes. Duplicates (AnkiConnect
        returns null for a skipped duplicate) are not errors. If `media_dir` is given,
        referenced image files are uploaded to Anki's media collection first.
        """
        tags = tags or []
        self.ensure_deck(deck)
        if media_dir is not None:
            self.store_media(cards, media_dir)

        notes: list[dict[str, object]] = []
        for card in cards:
            notes.append(self._note(card, deck, tags))
            if card.type is CardType.REVERSIBLE:
                reverse = Card(
                    type=CardType.BASIC,
                    front=card.back,
                    back=card.front,
                    tags=card.tags,
                    subdeck=card.subdeck,
                    source_ref=card.source_ref,
                )
                notes.append(self._note(reverse, deck, tags))

        result = self._invoke("addNotes", notes=notes)
        ids = list(result) if isinstance(result, list) else []
        added = sum(1 for i in ids if i is not None)
        skipped = len(notes) - added
        # canAddNotes distinguishes duplicates from genuine failures.
        can_add = self._invoke("canAddNotes", notes=notes)
        flags = list(can_add) if isinstance(can_add, list) else [True] * len(notes)
        duplicates = sum(
            1 for i, ok in zip(ids, flags, strict=False) if i is None and not ok
        )
        failed = skipped - duplicates
        return ImportResult(added=added, duplicates=duplicates, failed=failed, total=len(notes))

    def sync(self) -> None:
        self._invoke("sync")
