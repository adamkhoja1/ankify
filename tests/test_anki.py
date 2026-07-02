"""Offline integration tests for the AnkiConnect client, against a scripted local HTTP
server speaking the AnkiConnect protocol (real httpx, no mocks, no Anki)."""

import json
import threading
from collections.abc import Iterator
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any, ClassVar

import pytest

from ankify.anki import AnkiConnect, AnkiConnectError
from ankify.models import Card, CardSet, CardType


class _Handler(BaseHTTPRequestHandler):
    """Answers each AnkiConnect action with a canned result from `canned`."""

    canned: ClassVar[dict[str, Any]] = {}
    requests: ClassVar[list[dict[str, Any]]] = []

    def do_POST(self) -> None:
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        type(self).requests.append(body)
        payload = json.dumps(
            {"result": type(self).canned.get(body["action"]), "error": None}
        ).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A002 - stdlib signature
        pass


@pytest.fixture
def anki_server() -> Iterator[str]:
    _Handler.canned = {}
    _Handler.requests = []
    server = HTTPServer(("127.0.0.1", 0), _Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_port}"
    server.shutdown()


def test_import_classifies_duplicates_and_failures(anki_server: str) -> None:
    _Handler.canned = {
        "createDeck": 1,
        "addNotes": [1111, None, None],
        "canAddNotesWithErrorDetail": [
            {"canAdd": True},
            {"canAdd": False, "error": "cannot create note because it is a duplicate"},
            {"canAdd": False, "error": "field Front is empty-ish"},
        ],
    }
    cards = [Card(front=f"q{i}", back=f"a{i}") for i in range(3)]

    result = AnkiConnect(anki_server).import_cards(cards, "Deck")

    assert (result.added, result.duplicates, result.failed, result.total) == (1, 1, 1, 3)


def test_import_all_added_skips_error_detail_call(anki_server: str) -> None:
    _Handler.canned = {"createDeck": 1, "addNotes": [1, 2]}
    cards = [Card(front="q1", back="a1"), Card(front="q2", back="a2")]

    result = AnkiConnect(anki_server).import_cards(cards, "Deck")

    assert (result.added, result.duplicates, result.failed) == (2, 0, 0)
    assert "canAddNotesWithErrorDetail" not in [r["action"] for r in _Handler.requests]


def test_reversible_card_imports_as_two_notes(anki_server: str) -> None:
    _Handler.canned = {"createDeck": 1, "addNotes": [1, 2]}
    cards = [Card(type=CardType.REVERSIBLE, front="term", back="definition")]

    result = AnkiConnect(anki_server).import_cards(cards, "Deck")

    assert result.total == 2 and result.added == 2
    add = next(r for r in _Handler.requests if r["action"] == "addNotes")
    fronts = [n["fields"]["Front"] for n in add["params"]["notes"]]
    assert fronts == ["term", "definition"]  # forward + reverse


def test_unreachable_anki_raises_with_guidance() -> None:
    with pytest.raises(AnkiConnectError, match="Is Anki open"):
        AnkiConnect("http://127.0.0.1:1", timeout=0.2).deck_names()


def test_push_defaults_to_session_deck(anki_server: str, tmp_path: Path) -> None:
    from ankify.cli import CLI, _resolve
    from ankify.models import ReviewAction, ReviewDecision
    from ankify.server.session import ReviewSession, SessionStore

    store = str(tmp_path / ".ankify")
    session_path, _, _, _ = _resolve("t", None, store)
    card = Card(front="q", back="a")
    session = ReviewSession(deck="Varian", rounds=[CardSet(cards=[card])])
    session.decisions[card.id] = ReviewDecision(card_id=card.id, action=ReviewAction.ACCEPT)
    SessionStore(session_path).save(session)
    _Handler.canned = {"createDeck": 1, "addNotes": [1], "sync": None}

    CLI().push(name="t", store=store, anki_url=anki_server)

    create = next(r for r in _Handler.requests if r["action"] == "createDeck")
    assert create["params"]["deck"] == "Varian"  # session deck, not a hardcoded default
