"""FastAPI backend for the card-review web app.

Serves the built React UI and a small JSON API over a `ReviewSession`: read the current
round, record accept/edit/discard/feedback, trigger a feedback-aware regeneration round, and
export the accepted cards. Accepted cards are written to a `.apkg` continuously as part of
persistence (a background task on every save), so there is always a current package to import
into Anki by double-click — no AnkiConnect needed. AnkiConnect remains an optional one-click
path. Regeneration uses the library's `Generator` (needs `OPENAI_API_KEY`).
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from ..anki import AnkiConnect, AnkiConnectError
from ..config import ModelConfig, load_config, save_config
from ..export import to_apkg
from ..generate import Generator
from ..llm import LLM
from ..models import Card, CardSet, ReviewAction, ReviewDecision
from .session import ReviewSession, SessionStore

logger = logging.getLogger(__name__)

_FRONTEND_DIST = Path(__file__).resolve().parents[3] / "frontend" / "dist"


class DecisionIn(BaseModel):
    card_id: str
    action: ReviewAction
    edited_card: Card | None = None
    feedback: str = ""


class ImportIn(BaseModel):
    deck: str
    tags: list[str] = []


class RequestsIn(BaseModel):
    requests: list[str]


class ConfigIn(BaseModel):
    provider: str
    model: str
    reasoning_effort: str = "high"
    api_key: str | None = None  # only update the stored key when non-empty


class SubdeckIn(BaseModel):
    card_id: str
    subdeck: str


class SubdeckRenameIn(BaseModel):
    old: str
    new: str


def _subdeck_counts(session: ReviewSession) -> list[dict[str, object]]:
    counts: dict[str, int] = {}
    for card in session.current_cards():
        counts[card.subdeck] = counts.get(card.subdeck, 0) + 1
    return [{"name": name, "count": n} for name, n in sorted(counts.items())]


def _regenerate(session: ReviewSession) -> CardSet:
    """Build the next round: carry over still-pending and accepted/edited cards, drop
    discards, and append requested new cards plus revisions of cards discarded with
    feedback. Pending cards are preserved so a regenerate never loses unreviewed cards."""
    carried = session.carried_cards()
    new_cards = Generator(LLM()).augment(
        session.source,
        requests=session.requests,
        revisions=session.revisions(),
        avoid=carried + session.discarded_cards(),
    )
    new_round = CardSet(
        source=session.source,
        cards=carried + new_cards,
        round=len(session.rounds),
    )
    session.rounds.append(new_round)
    session.requests = []
    return new_round


def create_app(
    session_path: str | Path,
    anki_url: str | None = None,
    media_dir: str | Path = ".ankify/media",
    export_path: str | Path | None = None,
) -> FastAPI:
    store = SessionStore(session_path)
    anki = AnkiConnect(anki_url) if anki_url else AnkiConnect()
    media_path = Path(media_dir)
    media_path.mkdir(parents=True, exist_ok=True)
    export_file = Path(export_path) if export_path else Path(session_path).with_suffix(".apkg")
    app = FastAPI(title="ankify review")

    def _require_session() -> ReviewSession:
        if not store.exists():
            raise HTTPException(404, "no review session; seed one with the skill/CLI first")
        return store.load()

    def _export(session: ReviewSession) -> None:
        try:
            to_apkg(session.approved_cards(), session.deck or "Ankify", media_path, export_file)
        except Exception as exc:  # background task: never break the request on export failure
            logger.warning("apkg export failed: %s", exc)

    def _persist(session: ReviewSession, background_tasks: BackgroundTasks) -> None:
        store.save(session)
        background_tasks.add_task(_export, session)

    @app.get("/api/session")
    def get_session() -> dict[str, object]:
        session = _require_session()
        return {
            "round": session.current.round if session.current else 0,
            "deck": session.deck,
            "pending": session.pending_count(),
            "accepted": len(session.approved_cards()),
            "export_path": str(export_file.resolve()),
            "cards": [c.model_dump() for c in session.current_cards()],
            "decisions": {k: v.model_dump() for k, v in session.decisions.items()},
            "requests": session.requests,
            "subdecks": _subdeck_counts(session),
        }

    @app.get("/api/config")
    def get_config() -> dict[str, object]:
        cfg = load_config()
        return {
            "provider": cfg.provider,
            "model": cfg.model,
            "reasoning_effort": cfg.reasoning_effort,
            "has_key": cfg.has_key(),
        }

    @app.post("/api/config")
    def post_config(body: ConfigIn) -> dict[str, object]:
        existing = load_config()
        new = ModelConfig(
            provider=body.provider,
            model=body.model,
            reasoning_effort=body.reasoning_effort,
            api_key=body.api_key or existing.api_key,  # keep existing key if none pasted
        )
        save_config(new)
        return {
            "provider": new.provider,
            "model": new.model,
            "reasoning_effort": new.reasoning_effort,
            "has_key": new.has_key(),
        }

    @app.post("/api/subdeck")
    def post_subdeck(body: SubdeckIn, background_tasks: BackgroundTasks) -> dict[str, object]:
        session = _require_session()
        if session.current:
            for i, card in enumerate(session.current.cards):
                if card.id == body.card_id:
                    session.current.cards[i] = card.model_copy(
                        update={"subdeck": body.subdeck.strip()}
                    )
                    break
        _persist(session, background_tasks)
        return {"subdecks": _subdeck_counts(session)}

    @app.post("/api/subdeck/rename")
    def post_subdeck_rename(
        body: SubdeckRenameIn, background_tasks: BackgroundTasks
    ) -> dict[str, object]:
        session = _require_session()
        renamed = 0
        if session.current:
            for i, card in enumerate(session.current.cards):
                if card.subdeck == body.old:
                    session.current.cards[i] = card.model_copy(update={"subdeck": body.new.strip()})
                    renamed += 1
        _persist(session, background_tasks)
        return {"renamed": renamed, "subdecks": _subdeck_counts(session)}

    @app.post("/api/decision")
    def post_decision(body: DecisionIn, background_tasks: BackgroundTasks) -> dict[str, object]:
        session = _require_session()
        action = body.action
        # A saved edit = the edited content applied in place, then accepted. We don't keep a
        # distinct "edited" state: the card becomes the edited version and the decision is accept.
        if action is ReviewAction.EDIT and body.edited_card is not None and session.current:
            updated = body.edited_card.model_copy(update={"id": body.card_id})
            for i, card in enumerate(session.current.cards):
                if card.id == body.card_id:
                    session.current.cards[i] = updated
                    break
            action = ReviewAction.ACCEPT
        session.decisions[body.card_id] = ReviewDecision(
            card_id=body.card_id, action=action, feedback=body.feedback
        )
        _persist(session, background_tasks)
        return {"pending": session.pending_count(), "approved": len(session.approved_cards())}

    @app.post("/api/requests")
    def post_requests(body: RequestsIn, background_tasks: BackgroundTasks) -> dict[str, object]:
        session = _require_session()
        session.requests = [r.strip() for r in body.requests if r.strip()]
        _persist(session, background_tasks)
        return {"requests": session.requests}

    @app.post("/api/regenerate")
    def post_regenerate(background_tasks: BackgroundTasks) -> dict[str, object]:
        session = _require_session()
        if not session.requests and not session.revisions():
            raise HTTPException(
                400, "Nothing to regenerate — request a new card, or discard one with feedback."
            )
        if not load_config().has_key():
            raise HTTPException(
                503, "No API key configured for the selected provider — set one in Settings."
            )
        new_round = _regenerate(session)
        _persist(session, background_tasks)
        return {"round": new_round.round, "cards": [c.model_dump() for c in new_round.cards]}

    @app.get("/api/export.apkg")
    def get_export() -> FileResponse:
        session = _require_session()
        if not session.approved_cards():
            raise HTTPException(400, "no accepted cards yet")
        _export(session)  # ensure current before serving
        return FileResponse(
            export_file, filename=export_file.name, media_type="application/octet-stream"
        )

    @app.get("/api/decks")
    def get_decks() -> dict[str, object]:
        try:
            return {"decks": anki.deck_names()}
        except AnkiConnectError:
            return {"decks": []}

    @app.post("/api/import")
    def post_import(body: ImportIn, background_tasks: BackgroundTasks) -> dict[str, object]:
        session = _require_session()
        cards = session.approved_cards()
        if not cards:
            raise HTTPException(400, "no approved cards to import")
        try:
            result = anki.import_cards(cards, body.deck, body.tags, media_dir=media_path)
            anki.sync()
        except AnkiConnectError as exc:
            raise HTTPException(503, str(exc)) from exc
        session.deck = body.deck
        _persist(session, background_tasks)
        return result.__dict__

    app.mount("/media", StaticFiles(directory=media_path), name="media")
    if _FRONTEND_DIST.exists():
        app.mount("/", StaticFiles(directory=_FRONTEND_DIST, html=True), name="frontend")

    return app


def default_app() -> FastAPI:
    from ..store import Store

    store = Store()
    name = os.environ.get("ANKIFY_NAME", "default")
    session_path = os.environ.get("ANKIFY_SESSION") or str(store.session_path(name))
    return create_app(
        session_path, media_dir=store.media_dir, export_path=store.export_path(name)
    )
