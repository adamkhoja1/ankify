"""Manual smoke test: generate + self-review cards from a short source.

Run with: uv run scripts/smoke_generate.py   (real API spend; not collected by pytest.)
"""

from ankification.generate import Generator
from ankification.llm import LLM, CostTracker
from ankification.models import Source

SOURCE = Source(
    title="The testing effect",
    kind="markdown",
    markdown=(
        "# The testing effect\n\n"
        "The testing effect (also called retrieval practice) is the finding that "
        "actively recalling information from memory strengthens it more than re-reading. "
        "In a classic 2006 study, Roediger and Karpicke had students study prose, then "
        "either restudy it or take a free-recall test. On a final test one week later, the "
        "students who had practiced retrieval remembered about 50% more than those who "
        "restudied, even though the restudy group felt more confident. The effect is "
        "strongest when retrieval is effortful but successful, and when feedback is given "
        "after the test. It underlies why spaced-repetition flashcards work: each review "
        "is a retrieval attempt, not a re-reading."
    ),
)


def main() -> None:
    tracker = CostTracker(budget_usd=3.0)
    gen = Generator(LLM(tracker=tracker))
    draft = gen.generate(SOURCE, count_hint=6)
    print(f"=== generated {len(draft.cards)} cards ===")
    for c in draft.cards:
        print(f"  [{c.type.value}] {c.as_qa()}")
    reviewed = gen.self_review(draft, rounds=1)
    print(f"\n=== after 1 self-review round: {len(reviewed.cards)} cards ===")
    for c in reviewed.cards:
        print(f"  [{c.type.value}] {c.as_qa()}")
    print(f"\n{tracker.summary()}")


if __name__ == "__main__":
    main()
