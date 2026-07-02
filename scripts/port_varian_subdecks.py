"""One-off: assign `Chxx - <title>` subdecks to the Varian session from each card's source_ref.

Every card's `source_ref` encodes its chapter (e.g. "Varian ch01 §1.1", "... ch. 2, §2"), so we
classify deterministically rather than with an LLM. Re-runs are idempotent.
"""

import re

from ankify.export import to_apkg
from ankify.server.session import SessionStore

CHAPTERS = {
    1: "Ch01 - The Market",
    2: "Ch02 - Budget Constraint",
    3: "Ch03 - Preferences",
}
SESSION = ".ankify/sessions/varian.json"
EXPORT = ".ankify/exports/varian.apkg"
MEDIA = ".ankify/media"


def chapter_of(source_ref: str) -> int | None:
    match = re.search(r"\bch\.?\s*0*([1-9])", source_ref, re.IGNORECASE)
    return int(match.group(1)) if match else None


def main() -> None:
    store = SessionStore(SESSION)
    session = store.load()
    counts: dict[str, int] = {}
    unknown: list[tuple[str, str]] = []
    for card in session.current_cards():
        chapter = chapter_of(card.source_ref)
        subdeck = CHAPTERS.get(chapter) if chapter else None
        if subdeck:
            card.subdeck = subdeck
            counts[subdeck] = counts.get(subdeck, 0) + 1
        else:
            unknown.append((card.id, card.source_ref))
    store.save(session)
    to_apkg(session.approved_cards(), session.deck, MEDIA, EXPORT)

    for name in sorted(counts):
        print(f"{counts[name]:3}  {name}")
    print(f"total classified: {sum(counts.values())}/{len(session.current_cards())}")
    print(f"accepted cards exported: {len(session.approved_cards())} -> {EXPORT}")
    for cid, ref in unknown:
        print(f"  UNCLASSIFIED {cid}: {ref!r}")


if __name__ == "__main__":
    main()
