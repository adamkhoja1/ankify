"""Integration tests for the review API (real FastAPI app + real session file, no mocks).

Covers the no-LLM, no-Anki paths: reading a session, recording decisions, subdecks, and the
approved/pending bookkeeping that import and regenerate depend on.
"""

import pytest
from fastapi.testclient import TestClient

from ankify.models import Card, CardSet
from ankify.server.app import create_app
from ankify.server.session import ReviewSession, SessionStore


@pytest.fixture
def session_path(tmp_path):
    path = tmp_path / "session.json"
    cards = [Card(front="q1", back="a1"), Card(front="q2", back="a2")]
    SessionStore(path).save(
        ReviewSession(rounds=[CardSet(source_id="s", cards=cards)])
    )
    return path


@pytest.fixture
def client(session_path):
    # tmp media/export so tests never write into the repo's .ankify/
    return TestClient(
        create_app(
            session_path,
            media_dir=session_path.parent / "media",
            export_path=session_path.parent / "deck.apkg",
        )
    )


def test_missing_session_is_404(tmp_path):
    app = create_app(
        tmp_path / "nope.json", media_dir=tmp_path / "m", export_path=tmp_path / "x.apkg"
    )
    assert TestClient(app).get("/api/session").status_code == 404


def test_session_decision_and_approved_flow(client, session_path):
    state = client.get("/api/session").json()
    assert len(state["cards"]) == 2 and state["pending"] == 2
    c1, c2 = state["cards"]

    assert client.post("/api/decision", json={"card_id": c1["id"], "action": "accept"}).json() == {
        "pending": 1,
        "approved": 1,
    }
    r2 = client.post(
        "/api/decision",
        json={"card_id": c2["id"], "action": "discard", "feedback": "off-topic"},
    )
    assert r2.json() == {"pending": 0, "approved": 1}

    reloaded = SessionStore(session_path).load()
    assert reloaded.pending_count() == 0
    assert [c.front for c in reloaded.approved_cards()] == ["q1"]
    assert reloaded.feedback() == ["off-topic"]


def test_saved_edit_updates_card_in_place_and_records_accept(client, session_path):
    c1 = client.get("/api/session").json()["cards"][0]
    edited = {**c1, "id": "DIFFERENT", "front": "q1-edited", "back": "a1!"}
    client.post(
        "/api/decision", json={"card_id": c1["id"], "action": "edit", "edited_card": edited}
    )

    state = client.get("/api/session").json()
    card0 = next(c for c in state["cards"] if c["id"] == c1["id"])
    assert card0["front"] == "q1-edited"  # edit applied in place (same id)
    assert state["decisions"][c1["id"]]["action"] == "accept"  # not a distinct "edited" state
    approved = SessionStore(session_path).load().approved_cards()
    assert [c.front for c in approved][:1] == ["q1-edited"]


def test_requests_queue_persists_and_strips_blanks(client, session_path):
    r = client.post("/api/requests", json={"requests": ["card on X", "   ", "card on Y"]})
    assert r.json() == {"requests": ["card on X", "card on Y"]}
    assert client.get("/api/session").json()["requests"] == ["card on X", "card on Y"]
    assert SessionStore(session_path).load().requests == ["card on X", "card on Y"]


def test_regenerate_with_nothing_queued_is_400(client):
    assert client.post("/api/regenerate").status_code == 400


def test_import_with_no_approved_cards_is_400(client):
    state = client.get("/api/session").json()
    for card in state["cards"]:
        client.post("/api/decision", json={"card_id": card["id"], "action": "discard"})
    assert client.post("/api/import", json={"deck": "D"}).status_code == 400


def test_set_subdeck_does_not_decide(client):
    c1 = client.get("/api/session").json()["cards"][0]
    r = client.post("/api/subdeck", json={"card_id": c1["id"], "subdeck": "Ch01"})
    assert any(s["name"] == "Ch01" for s in r.json()["subdecks"])
    state = client.get("/api/session").json()
    card0 = next(c for c in state["cards"] if c["id"] == c1["id"])
    assert card0["subdeck"] == "Ch01"
    assert c1["id"] not in state["decisions"]  # still pending — setting a subdeck is not a decision


def test_rename_subdeck_across_round(client):
    cards = client.get("/api/session").json()["cards"]
    for card in cards:
        client.post("/api/subdeck", json={"card_id": card["id"], "subdeck": "Old"})
    rename = client.post("/api/subdeck/rename", json={"old": "Old", "new": "New"})
    assert rename.json()["renamed"] == 2
    names = {s["name"] for s in client.get("/api/session").json()["subdecks"]}
    assert "New" in names and "Old" not in names
