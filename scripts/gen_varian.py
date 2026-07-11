"""Generate a review session for Varian chapters 1-3 using the skill's pipeline (GPT-5.5).

Generates + self-reviews per chapter (balanced coverage) and merges into one review round.
Each chapter is registered in the session's SourceStore and its cards carry that chapter's
source id, so the app's "regenerate round" works per chapter.

Usage: uv run scripts/gen_varian.py --md_dir <dir-with-chapter-md-files>
Then:  uv run ankify serve --name varian
"""

from __future__ import annotations

from pathlib import Path

import fire  # type: ignore[import-untyped]

from ankify.generate import Generator
from ankify.llm import LLM, CostTracker
from ankify.models import Card, CardSet, Source
from ankify.server.session import ReviewSession, SessionStore, SourceStore
from ankify.store import Store

CHAPTERS = {
    "01": "01-the-market.md",
    "02": "02-budget-constraint.md",
    "03": "03-preferences.md",
}


def main(
    md_dir: str,
    name: str = "varian",
    per_chapter: int = 12,
    review_rounds: int = 2,
    budget: float = 8.0,
) -> None:
    md_path = Path(md_dir)
    tracker = CostTracker(budget_usd=budget)
    gen = Generator(LLM(tracker=tracker))
    store = Store()
    store.ensure()
    sources = SourceStore(store.sources_path(name))

    all_cards: list[Card] = []
    for ch, fn in CHAPTERS.items():
        text = (md_path / fn).read_text()
        src = Source(title=f"Varian ch{ch}", kind="markdown", markdown=text)
        sources.add(src)  # generated cards carry src.sid() as their source_id
        draft = gen.generate(src, count_hint=per_chapter)
        reviewed = gen.self_review(draft, src, rounds=review_rounds)
        all_cards.extend(reviewed.cards)
        print(f"ch{ch}: {len(reviewed.cards)} cards")

    review = ReviewSession(
        notes="Varian Intermediate Microeconomics, chapters 1-3 (The Market, Budget "
        "Constraint, Preferences).",
        deck="Varian Microeconomics",
        rounds=[CardSet(cards=all_cards, round=0)],
    )
    session_path = store.session_path(name)
    SessionStore(session_path).save(review)
    print(f"\n{len(all_cards)} cards -> {session_path}\n{tracker.summary()}")


if __name__ == "__main__":
    fire.Fire(main)
