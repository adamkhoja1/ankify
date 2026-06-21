"""Integration tests for the review API (real FastAPI app + real session file, no mocks).

Covers the no-LLM, no-Anki paths: reading a session, recording decisions, and the
approved/pending bookkeeping that the import and regenerate flows depend on.
"""

import pytest
from fastapi.testclient import TestClient

from ankification.models import Card, CardSet, Source
from ankification.server.app import create_app
from ankification.server.session import ReviewSession, SessionStore


@pytest.fixture
def session_path(tmp_path):
    path = tmp_path / "session.json"
    source = Source(title="s", markdown="body")
    cards = [Card(front="q1", back="a1"), Card(front="q2", back="a2")]
    SessionStore(path).save(
        ReviewSession(source=source, rounds=[CardSet(source=source, cards=cards)])
    )
    return path


def test_missing_session_is_404(tmp_path):
    client = TestClient(create_app(tmp_path / "nope.json"))
    assert client.get("/api/session").status_code == 404


def test_session_decision_and_approved_flow(session_path):
    client = TestClient(create_app(session_path))

    state = client.get("/api/session").json()
    assert len(state["cards"]) == 2 and state["pending"] == 2
    c1, c2 = state["cards"]

    r1 = client.post("/api/decision", json={"card_id": c1["id"], "action": "accept"})
    assert r1.json() == {"pending": 1, "approved": 1}

    r2 = client.post(
        "/api/decision",
        json={"card_id": c2["id"], "action": "discard", "feedback": "off-topic"},
    )
    assert r2.json() == {"pending": 0, "approved": 1}

    # decisions persisted to disk
    reloaded = SessionStore(session_path).load()
    assert reloaded.pending_count() == 0
    assert [c.front for c in reloaded.approved_cards()] == ["q1"]
    assert reloaded.feedback() == ["off-topic"]


def test_edit_decision_keeps_card_id_and_replaces_content(session_path):
    client = TestClient(create_app(session_path))
    c1 = client.get("/api/session").json()["cards"][0]
    edited = {**c1, "id": "DIFFERENT", "front": "q1-edited", "back": "a1!"}
    client.post(
        "/api/decision",
        json={"card_id": c1["id"], "action": "edit", "edited_card": edited},
    )
    approved = SessionStore(session_path).load().approved_cards()
    assert approved[0].front == "q1-edited"
    assert approved[0].id == c1["id"]  # server forces edited id back to the original


def test_import_with_no_approved_cards_is_400(session_path):
    client = TestClient(create_app(session_path))
    state = client.get("/api/session").json()
    for card in state["cards"]:
        client.post("/api/decision", json={"card_id": card["id"], "action": "discard"})
    assert client.post("/api/import", json={"deck": "D"}).status_code == 400
