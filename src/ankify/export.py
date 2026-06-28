"""Export accepted cards to a .apkg for direct Anki import (no AnkiConnect needed).

Uses genanki with the built-in, stable-id Basic / Cloze / Basic-and-reversed models. Each
note's GUID is derived from the card's persisted id, so re-importing the regenerated package
*updates* the matching note instead of creating a duplicate. Image files referenced by the
cards are bundled into the package. Double-click the .apkg (or File -> Import) to import.
"""

from __future__ import annotations

import zlib
from collections.abc import Sequence
from pathlib import Path

import genanki  # type: ignore[import-untyped]

from .anki import _referenced_media
from .models import Card, CardType


def _deck_id(deck_name: str) -> int:
    """A stable per-deck id so re-imports land in the same deck."""
    return zlib.crc32(deck_name.encode()) % (1 << 31) or 1


def _note(card: Card, tags: list[str]) -> genanki.Note:
    all_tags = sorted(set(tags) | set(card.tags))
    guid = genanki.guid_for(card.id)
    if card.type is CardType.CLOZE:
        return genanki.Note(
            model=genanki.CLOZE_MODEL,
            fields=[card.cloze_text, card.extra],
            tags=all_tags,
            guid=guid,
        )
    model = (
        genanki.BASIC_AND_REVERSED_CARD_MODEL
        if card.type is CardType.REVERSIBLE
        else genanki.BASIC_MODEL
    )
    return genanki.Note(model=model, fields=[card.front, card.back], tags=all_tags, guid=guid)


def to_apkg(
    cards: Sequence[Card],
    deck_name: str,
    media_dir: str | Path,
    out_path: str | Path,
    tags: Sequence[str] = (),
) -> Path:
    """Write `cards` to a .apkg, one Anki deck per `deck::subdeck`, bundling referenced media.

    Cards with a `subdeck` land in `deck_name::<subdeck>`; Anki creates the parent on import.
    Returns the output path.
    """
    deck_name = deck_name or "Ankify"
    groups: dict[str, list[Card]] = {}
    for card in cards:
        full = f"{deck_name}::{card.subdeck}" if card.subdeck else deck_name
        groups.setdefault(full, []).append(card)

    decks = []
    for full, group in sorted(groups.items()):
        deck = genanki.Deck(_deck_id(full), full)
        for card in group:
            deck.add_note(_note(card, list(tags)))
        decks.append(deck)
    if not decks:  # no accepted cards yet — still write a (placeholder) package
        decks = [genanki.Deck(_deck_id(deck_name), deck_name)]

    package = genanki.Package(decks)
    media_dir = Path(media_dir)
    package.media_files = [
        str(media_dir / name)
        for name in sorted(_referenced_media(list(cards)))
        if (media_dir / name).exists()
    ]
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    package.write_to_file(str(out_path))
    return out_path
