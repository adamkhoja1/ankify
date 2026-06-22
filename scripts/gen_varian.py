"""Generate a review session for Varian chapters 1-3 using the skill's pipeline (GPT-5.5).

Generates + self-reviews per chapter (balanced coverage), merges into one review round, and
keeps the full chapter text on the session source so the app's "regenerate round" works.

Usage: uv run scripts/gen_varian.py
Then:  uv run ankification serve --session .cards/varian_session.json
"""

from __future__ import annotations

from pathlib import Path

import fire  # type: ignore[import-untyped]

from ankification.generate import Generator
from ankification.llm import LLM, CostTracker
from ankification.models import CardSet, Source
from ankification.server.session import ReviewSession, SessionStore

MD_DIR = Path(
    "/Users/adam/Documents/Vault/Study/econ_study/varian_intermediate_microeconomics.md"
)
CHAPTERS = {
    "01": "01-the-market.md",
    "02": "02-budget-constraint.md",
    "03": "03-preferences.md",
}


def main(
    session: str = ".cards/varian_session.json",
    per_chapter: int = 12,
    review_rounds: int = 2,
    budget: float = 8.0,
) -> None:
    tracker = CostTracker(budget_usd=budget)
    gen = Generator(LLM(tracker=tracker))

    all_cards = []
    chapter_texts = []
    for ch, fn in CHAPTERS.items():
        text = (MD_DIR / fn).read_text()
        chapter_texts.append(f"# Chapter {ch}\n\n{text}")
        src = Source(title=f"Varian ch{ch}", kind="markdown", markdown=text)
        draft = gen.generate(src, count_hint=per_chapter)
        reviewed = gen.self_review(draft, rounds=review_rounds)
        all_cards.extend(reviewed.cards)
        print(f"ch{ch}: {len(reviewed.cards)} cards")

    combined = Source(
        title="Varian Intermediate Microeconomics — chapters 1-3",
        kind="markdown",
        markdown="\n\n".join(chapter_texts),
    )
    review = ReviewSession(
        source=combined,
        notes="Varian Intermediate Microeconomics, chapters 1-3 (The Market, Budget "
        "Constraint, Preferences).",
        deck="Varian Microeconomics",
        rounds=[CardSet(source=combined, cards=all_cards, round=0)],
    )
    SessionStore(session).save(review)
    print(f"\n{len(all_cards)} cards -> {session}\n{tracker.summary()}")


if __name__ == "__main__":
    fire.Fire(main)
