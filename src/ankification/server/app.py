"""FastAPI backend for the card-review web app.

Serves the built React UI and a small JSON API over a `ReviewSession`: read the current
round, record accept/edit/discard/feedback, trigger a feedback-aware regeneration round,
and import the approved cards into Anki. Regeneration uses the library's `Generator` (needs
`OPENAI_API_KEY`); review and import work without it.
"""

from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from ..anki import AnkiConnect, AnkiConnectError
from ..generate import Generator
from ..llm import LLM
from ..models import Card, CardSet, ReviewAction, ReviewDecision
from .session import ReviewSession, SessionStore

_FRONTEND_DIST = Path(__file__).resolve().parents[3] / "frontend" / "dist"


class DecisionIn(BaseModel):
    card_id: str
    action: ReviewAction
    edited_card: Card | None = None
    feedback: str = ""


class ImportIn(BaseModel):
    deck: str
    tags: list[str] = []


def _regenerate(session: ReviewSession) -> CardSet:
    approved = session.approved_cards()
    parts = [session.notes] if session.notes else []
    if approved:
        joined = "\n".join(f"- {c.as_qa()}" for c in approved)
        parts.append(f"Already-approved cards (do NOT duplicate these):\n{joined}")
    if discarded := session.discarded_cards():
        joined = "\n".join(f"- {c.as_qa()}" for c in discarded)
        parts.append(f"The user discarded these as poor; avoid similar cards:\n{joined}")
    if fb := session.feedback():
        parts.append("User feedback to address:\n" + "\n".join(f"- {f}" for f in fb))

    generator = Generator(LLM())
    draft = generator.generate(session.source, notes="\n\n".join(parts))
    reviewed = generator.self_review(draft, rounds=1)
    new_round = CardSet(
        source=session.source,
        cards=approved + reviewed.cards,
        round=len(session.rounds),
    )
    session.rounds.append(new_round)
    return new_round


def create_app(session_path: str | Path, anki_url: str | None = None) -> FastAPI:
    store = SessionStore(session_path)
    anki = AnkiConnect(anki_url) if anki_url else AnkiConnect()
    app = FastAPI(title="ankify review")

    def _require_session() -> ReviewSession:
        if not store.exists():
            raise HTTPException(404, "no review session; seed one with the skill/CLI first")
        return store.load()

    @app.get("/api/session")
    def get_session() -> dict[str, object]:
        session = _require_session()
        return {
            "round": session.current.round if session.current else 0,
            "deck": session.deck,
            "pending": session.pending_count(),
            "cards": [c.model_dump() for c in session.current_cards()],
            "decisions": {k: v.model_dump() for k, v in session.decisions.items()},
        }

    @app.post("/api/decision")
    def post_decision(body: DecisionIn) -> dict[str, object]:
        session = _require_session()
        edited = body.edited_card
        if body.action is ReviewAction.EDIT and edited is not None:
            edited = edited.model_copy(update={"id": body.card_id})
        session.decisions[body.card_id] = ReviewDecision(
            card_id=body.card_id, action=body.action, edited_card=edited, feedback=body.feedback
        )
        store.save(session)
        return {"pending": session.pending_count(), "approved": len(session.approved_cards())}

    @app.post("/api/regenerate")
    def post_regenerate() -> dict[str, object]:
        session = _require_session()
        if not os.environ.get("OPENAI_API_KEY"):
            raise HTTPException(503, "OPENAI_API_KEY not set; cannot regenerate")
        new_round = _regenerate(session)
        store.save(session)
        return {"round": new_round.round, "cards": [c.model_dump() for c in new_round.cards]}

    @app.get("/api/decks")
    def get_decks() -> dict[str, object]:
        try:
            return {"decks": anki.deck_names()}
        except AnkiConnectError:
            return {"decks": []}

    @app.post("/api/import")
    def post_import(body: ImportIn) -> dict[str, object]:
        session = _require_session()
        cards = session.approved_cards()
        if not cards:
            raise HTTPException(400, "no approved cards to import")
        try:
            result = anki.import_cards(cards, body.deck, body.tags)
            anki.sync()
        except AnkiConnectError as exc:
            raise HTTPException(503, str(exc)) from exc
        session.deck = body.deck
        store.save(session)
        return result.__dict__

    if _FRONTEND_DIST.exists():
        app.mount("/", StaticFiles(directory=_FRONTEND_DIST, html=True), name="frontend")

    return app


def default_app() -> FastAPI:
    return create_app(os.environ.get("ANKIFICATION_SESSION", ".cards/session.json"))
