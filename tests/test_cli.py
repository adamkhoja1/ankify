"""CLI command behavior: `seed` extends a session non-destructively (no API).

Regression coverage for the footgun where seeding into an already-reviewed session created a
round of only the new cards, orphaning accepted ones and rewriting the .apkg to empty.
"""

import json
import sqlite3
import zipfile
from pathlib import Path

import pytest

from ankification.cli import CLI, _resolve
from ankification.models import Card, CardSet, ReviewAction, ReviewDecision, Source
from ankification.server.session import ReviewSession, SessionStore


def _note_count(apkg: Path) -> int:
    work = apkg.parent / "_count.anki2"
    with zipfile.ZipFile(apkg) as zf:
        work.write_bytes(zf.read("collection.anki2"))
    con = sqlite3.connect(work)
    n = con.execute("SELECT COUNT(*) FROM notes").fetchone()[0]
    con.close()
    work.unlink()
    return n


def _seed_initial_session(session_path: Path) -> tuple[str, str]:
    """Persist a session with one accepted + one pending card; return their ids."""
    accepted = Card(front="accepted q", back="a")
    pending = Card(front="pending q", back="p")
    src = Source(title="ch1-3", markdown="original source")
    review = ReviewSession(
        source=src,
        deck="Varian",
        rounds=[CardSet(source=src, cards=[accepted, pending])],
    )
    review.decisions[accepted.id] = ReviewDecision(card_id=accepted.id, action=ReviewAction.ACCEPT)
    SessionStore(session_path).save(review)
    return accepted.id, pending.id


def _write_cards(path: Path, fronts: list[str]) -> None:
    path.write_text(json.dumps([{"type": "basic", "front": f, "back": f"{f}!"} for f in fronts]))


def test_seed_extends_without_clobbering_accepted(tmp_path):
    store = str(tmp_path / ".ankify")
    session_path, _, export_path = _resolve("t", None, store)
    acc_id, _ = _seed_initial_session(session_path)

    cards_file = tmp_path / "new.json"
    _write_cards(cards_file, ["new1", "new2"])
    CLI().seed(str(cards_file), name="t", store=store)  # extend (default); no source needed

    review = SessionStore(session_path).load()
    assert len(review.rounds) == 2
    # current round = carried (accepted + pending) + the two new cards, in order
    assert [c.front for c in review.current_cards()] == ["accepted q", "pending q", "new1", "new2"]
    # the prior decision survives, so the accepted card is still in the working set + .apkg
    assert review.decisions[acc_id].action is ReviewAction.ACCEPT
    assert [c.front for c in review.approved_cards()] == ["accepted q"]
    assert review.pending_count() == 3
    assert _note_count(export_path) == 1  # .apkg NOT rewritten to empty


def test_seed_replace_resets_working_set(tmp_path):
    store = str(tmp_path / ".ankify")
    session_path, _, export_path = _resolve("t", None, store)
    _seed_initial_session(session_path)

    cards_file = tmp_path / "new.json"
    _write_cards(cards_file, ["only1", "only2"])
    CLI().seed(str(cards_file), name="t", store=store, replace=True)

    review = SessionStore(session_path).load()
    # carry-forward skipped: the round holds only the new cards
    assert [c.front for c in review.current_cards()] == ["only1", "only2"]
    assert review.approved_cards() == []  # prior accepted no longer in the current round
    assert _note_count(export_path) == 0


def test_seed_extend_keeps_existing_source_and_deck(tmp_path):
    store = str(tmp_path / ".ankify")
    session_path, _, _ = _resolve("t", None, store)
    _seed_initial_session(session_path)

    cards_file = tmp_path / "new.json"
    _write_cards(cards_file, ["new1"])
    CLI().seed(str(cards_file), name="t", store=store)  # no --source_path/--text given

    review = SessionStore(session_path).load()
    assert review.source.title == "ch1-3"  # existing source/notes not clobbered
    assert review.deck == "Varian"


def test_seed_new_session_requires_source(tmp_path):
    store = str(tmp_path / ".ankify")
    cards_file = tmp_path / "new.json"
    _write_cards(cards_file, ["c1"])
    with pytest.raises(ValueError, match="new session needs a source"):
        CLI().seed(str(cards_file), name="fresh", store=store)
