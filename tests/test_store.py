"""Tests for the .ankify/ store path resolution and session listing."""

from ankify.models import Card, CardSet, ReviewAction, ReviewDecision, Source
from ankify.server.session import ReviewSession, SessionStore
from ankify.store import Store


def test_store_paths(tmp_path):
    store = Store(tmp_path / ".ankify")
    assert store.session_path("x").name == "x.json"
    assert store.session_path("x").parent.name == "sessions"
    assert store.export_path("x").name == "x.apkg"
    assert store.export_path("x").parent.name == "exports"
    assert store.media_dir.name == "media"


def test_store_lists_sessions_with_counts(tmp_path):
    store = Store(tmp_path / ".ankify")
    store.ensure()
    src = Source(title="s")
    cards = [Card(front=f"q{i}", back=str(i)) for i in range(3)]
    session = ReviewSession(source=src, rounds=[CardSet(source=src, cards=cards)])
    session.decisions[cards[0].id] = ReviewDecision(
        card_id=cards[0].id, action=ReviewAction.ACCEPT
    )
    SessionStore(store.session_path("varian")).save(session)

    infos = store.list_sessions()
    assert len(infos) == 1
    info = infos[0]
    assert info.name == "varian"
    assert info.cards == 3 and info.accepted == 1 and info.pending == 2
