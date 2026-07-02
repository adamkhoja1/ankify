"""Tests for the .ankify/ store path resolution and session listing."""

from pathlib import Path

from ankify.models import Card, CardSet, ReviewAction, ReviewDecision, Source
from ankify.server.session import ReviewSession, SessionStore, SourceStore
from ankify.store import Store


def test_store_paths(tmp_path: Path) -> None:
    store = Store(tmp_path / ".ankify")
    assert store.session_path("x").name == "x.json"
    assert store.session_path("x").parent.name == "sessions"
    assert store.export_path("x").name == "x.apkg"
    assert store.export_path("x").parent.name == "exports"
    assert store.media_dir.name == "media"


def test_store_lists_sessions_with_counts(tmp_path: Path) -> None:
    store = Store(tmp_path / ".ankify")
    store.ensure()
    cards = [Card(front=f"q{i}", back=str(i)) for i in range(3)]
    session = ReviewSession(rounds=[CardSet(cards=cards)])
    session.decisions[cards[0].id] = ReviewDecision(
        card_id=cards[0].id, action=ReviewAction.ACCEPT
    )
    SessionStore(store.session_path("varian")).save(session)

    infos = store.list_sessions()
    assert len(infos) == 1
    info = infos[0]
    assert info.name == "varian"
    assert info.cards == 3 and info.accepted == 1 and info.pending == 2


def test_source_store_dedupes_by_content(tmp_path: Path) -> None:
    store = SourceStore(tmp_path / "sources.json")
    a1 = store.add(Source(title="A", markdown="body one"))
    a2 = store.add(Source(title="A", markdown="body one"))  # identical content
    b = store.add(Source(title="B", markdown="body two"))
    assert a1 == a2 != b  # same content -> same id; different content -> different id
    assert set(store.load()) == {a1, b}  # each distinct source stored exactly once
    stored = store.get(a1)
    assert stored is not None and stored.markdown == "body one"
    assert store.get("missing") is None
