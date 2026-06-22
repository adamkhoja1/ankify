"""ankification CLI (fire).

Cards live in a project-local store under `.ankify/` (relative to the current directory):
  .ankify/sessions/<name>.json   one review session per named deck/topic
  .ankify/media/                 images referenced by cards
  .ankify/exports/<name>.apkg    accepted cards, regenerated as you review (double-click to
                                 import into Anki — no AnkiConnect needed)

Commands:
  seed      create a review session from cards you already generated (JSON) + a source
  generate  generate + self-review cards from a source via the API, into a session
  serve     launch the review web app over a session (opens the browser)
  sessions  list the review sessions in the store (name, accepted, pending)
  export    (re)write a session's accepted cards to its .apkg
  push      import a session's accepted cards into Anki via AnkiConnect (optional)
  eval      run the verification loop on the validation set

Address a session with `--name <name>` (default "default"); `--session <path>` overrides with
an explicit file. The interactive skill generates cards in-context and `seed`s them.
"""

from __future__ import annotations

import json
import webbrowser
from datetime import datetime
from pathlib import Path

import fire  # type: ignore[import-untyped]

from .anki import AnkiConnect
from .export import to_apkg
from .generate import Generator
from .ingest import from_file, from_text
from .llm import LLM
from .models import Card, CardSet, Source
from .server.session import ReviewSession, SessionStore
from .store import Store


def _load_source(source_path: str | None, text: str | None, title: str) -> Source:
    if source_path:
        return from_file(source_path)
    if text:
        return from_text(title, text)
    raise ValueError("provide either source_path or text")


def _resolve(name: str, session: str | None, store: str) -> tuple[Path, Path, Path]:
    """Return (session_path, media_dir, export_path). `--session` overrides the named store."""
    if session:
        path = Path(session)
        return path, path.parent / "media", path.with_suffix(".apkg")
    st = Store(store)
    st.ensure()
    return st.session_path(name), st.media_dir, st.export_path(name)


def _write_round(
    session_path: Path,
    source: Source,
    notes: str,
    cards: list[Card],
    media_dir: Path,
    export_path: Path,
    deck: str,
) -> int:
    store = SessionStore(session_path)
    review = store.load() if store.exists() else ReviewSession(source=source, notes=notes)
    review.source = source
    review.notes = notes
    if deck:
        review.deck = deck
    review.rounds.append(CardSet(source=source, cards=cards, round=len(review.rounds)))
    store.save(review)
    to_apkg(review.approved_cards(), review.deck or "Ankify", media_dir, export_path)
    return len(cards)


class CLI:
    def seed(
        self,
        cards_file: str,
        source_path: str | None = None,
        text: str | None = None,
        title: str = "source",
        notes: str = "",
        deck: str = "",
        name: str = "default",
        session: str | None = None,
        store: str = ".ankify",
    ) -> None:
        """Create/extend a review session from a JSON list of cards you generated."""
        session_path, media_dir, export_path = _resolve(name, session, store)
        source = _load_source(source_path, text, title)
        raw = json.loads(Path(cards_file).read_text())
        cards = [Card.model_validate(c) for c in raw]
        n = _write_round(session_path, source, notes, cards, media_dir, export_path, deck)
        print(f"seeded {n} cards -> {session_path}")

    def generate(
        self,
        source_path: str | None = None,
        text: str | None = None,
        title: str = "source",
        notes: str = "",
        deck: str = "",
        count: int | None = None,
        review_rounds: int = 2,
        name: str = "default",
        session: str | None = None,
        store: str = ".ankify",
    ) -> None:
        """Generate + self-review cards from a source via the API, into a session."""
        session_path, media_dir, export_path = _resolve(name, session, store)
        source = _load_source(source_path, text, title)
        gen = Generator(LLM())
        draft = gen.generate(source, notes=notes, count_hint=count)
        reviewed = gen.self_review(draft, rounds=review_rounds)
        n = _write_round(session_path, source, notes, reviewed.cards, media_dir, export_path, deck)
        print(f"generated {n} cards -> {session_path}")
        print(gen.llm.tracker.summary())

    def serve(
        self,
        name: str = "default",
        session: str | None = None,
        store: str = ".ankify",
        host: str = "127.0.0.1",
        port: int = 8000,
        open_browser: bool = True,
    ) -> None:
        """Launch the review web app over a session."""
        import uvicorn

        from .server.app import create_app

        session_path, media_dir, export_path = _resolve(name, session, store)
        app = create_app(str(session_path), media_dir=str(media_dir), export_path=str(export_path))
        if open_browser:
            webbrowser.open(f"http://{host}:{port}")
        uvicorn.run(app, host=host, port=port)

    def sessions(self, store: str = ".ankify") -> None:
        """List the review sessions in the store."""
        st = Store(store)
        infos = st.list_sessions()
        if not infos:
            print(f"no sessions in {st.sessions_dir}")
            return
        for info in infos:
            when = datetime.fromtimestamp(info.modified).strftime("%Y-%m-%d %H:%M")
            print(
                f"{info.name:24} {info.accepted:>4} accepted  {info.pending:>4} pending  "
                f"{info.cards:>4} cards   {when}"
            )

    def export(
        self,
        name: str = "default",
        session: str | None = None,
        store: str = ".ankify",
        deck: str | None = None,
    ) -> None:
        """(Re)write a session's accepted cards to its .apkg."""
        session_path, media_dir, export_path = _resolve(name, session, store)
        review = SessionStore(session_path).load()
        cards = review.approved_cards()
        out = to_apkg(cards, deck or review.deck or "Ankify", media_dir, export_path)
        print(f"exported {len(cards)} accepted cards -> {out}")

    def push(
        self,
        name: str = "default",
        session: str | None = None,
        store: str = ".ankify",
        deck: str = "Default",
        sync: bool = True,
    ) -> None:
        """Import a session's accepted cards into Anki via AnkiConnect (optional path)."""
        session_path, media_dir, _ = _resolve(name, session, store)
        review = SessionStore(session_path).load()
        cards = review.approved_cards()
        anki = AnkiConnect()
        result = anki.import_cards(cards, deck, media_dir=media_dir)
        if sync:
            anki.sync()
        print(
            f"imported {result.added} (+{result.duplicates} dup, "
            f"{result.failed} failed) -> {deck}"
        )

    def eval(self, limit: int = 10, budget: float = 15.0) -> None:
        """Run the verification loop on the validation set (writes eval_runs/<ts>.md)."""
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
