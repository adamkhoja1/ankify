"""ankification CLI (fire).

Commands:
  seed      create a review session from cards you already generated (JSON) + a source
  generate  generate + self-review cards from a source via the API, into a session
  serve     launch the review web app over a session (opens the browser)
  push      import a session's approved cards into Anki
  eval      run the verification loop on the validation set

The interactive skill generates cards in-context and `seed`s them; the `generate` command
is the programmatic path (and what the eval harness uses).
"""

from __future__ import annotations

import json
import webbrowser
from pathlib import Path

import fire  # type: ignore[import-untyped]

from .anki import AnkiConnect
from .generate import Generator
from .ingest import from_file, from_text
from .llm import LLM
from .models import Card, CardSet, Source
from .server.session import ReviewSession, SessionStore

DEFAULT_SESSION = ".cards/session.json"


def _load_source(source_path: str | None, text: str | None, title: str) -> Source:
    if source_path:
        return from_file(source_path)
    if text:
        return from_text(title, text)
    raise ValueError("provide either source_path or text")


def _write_round(session_path: str, source: Source, notes: str, cards: list[Card]) -> int:
    store = SessionStore(session_path)
    session = (
        store.load()
        if store.exists()
        else ReviewSession(source=source, notes=notes)
    )
    session.source = source
    session.notes = notes
    session.rounds.append(CardSet(source=source, cards=cards, round=len(session.rounds)))
    store.save(session)
    return len(cards)


class CLI:
    def seed(
        self,
        cards_file: str,
        source_path: str | None = None,
        text: str | None = None,
        title: str = "source",
        notes: str = "",
        session: str = DEFAULT_SESSION,
    ) -> None:
        """Create/extend a review session from a JSON list of cards you generated."""
        source = _load_source(source_path, text, title)
        raw = json.loads(Path(cards_file).read_text())
        cards = [Card.model_validate(c) for c in raw]
        n = _write_round(session, source, notes, cards)
        print(f"seeded {n} cards -> {session}")

    def generate(
        self,
        source_path: str | None = None,
        text: str | None = None,
        title: str = "source",
        notes: str = "",
        count: int | None = None,
        review_rounds: int = 2,
        session: str = DEFAULT_SESSION,
    ) -> None:
        """Generate + self-review cards from a source via the API, into a session."""
        source = _load_source(source_path, text, title)
        gen = Generator(LLM())
        draft = gen.generate(source, notes=notes, count_hint=count)
        reviewed = gen.self_review(draft, rounds=review_rounds)
        n = _write_round(session, source, notes, reviewed.cards)
        print(f"generated {n} cards -> {session}")
        print(gen.llm.tracker.summary())

    def serve(
        self,
        session: str = DEFAULT_SESSION,
        host: str = "127.0.0.1",
        port: int = 8000,
        open_browser: bool = True,
    ) -> None:
        """Launch the review web app over a session."""
        import uvicorn

        from .server.app import create_app

        app = create_app(session)
        if open_browser:
            webbrowser.open(f"http://{host}:{port}")
        uvicorn.run(app, host=host, port=port)

    def push(
        self, session: str = DEFAULT_SESSION, deck: str = "Default", sync: bool = True
    ) -> None:
        """Import a session's approved cards into Anki."""
        review = SessionStore(session).load()
        cards = review.approved_cards()
        anki = AnkiConnect()
        result = anki.import_cards(cards, deck)
        if sync:
            anki.sync()
        print(
            f"imported {result.added} (+{result.duplicates} dup, "
            f"{result.failed} failed) -> {deck}"
        )

    def eval(self, limit: int = 10, budget: float = 15.0) -> None:
        """Run the verification loop on the validation set (writes eval_runs/<ts>.md)."""
        from datetime import datetime

        from .eval.datasets import load_memory_machines
        from .eval.harness import (
            calibrate_judge,
            evaluate_generation,
            reference_ceiling,
            render_report,
        )
        from .llm import CostTracker
        from .rubric import Judge

        tracker = CostTracker(budget_usd=budget)
        llm = LLM(tracker=tracker)
        gen, judge = Generator(llm), Judge(llm)
        items = load_memory_machines(limit=limit)
        _, metrics = evaluate_generation(items, gen, judge)
        calib = calibrate_judge(items, judge)
        ceiling = reference_ceiling(items, judge)
        report = render_report(
            dataset="Memory Machines (srs-prompts)",
            gen=metrics,
            calib=calib,
            ceiling=ceiling,
            tracker=tracker,
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M"),
        )
        out = Path("eval_runs") / f"{datetime.now().strftime('%Y%m%d-%H%M%S')}.md"
        out.parent.mkdir(exist_ok=True)
        out.write_text(report)
        print(report)


def main() -> None:
    fire.Fire(CLI)
