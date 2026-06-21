"""Manual smoke test: judge one bad and one good card against the real API.

Validates the llm + rubric plumbing end to end. Run with: uv run scripts/smoke_judge.py
Not collected by pytest (real API spend). Prints verdicts and total cost.
"""

from ankification.llm import LLM, CostTracker
from ankification.models import Card, CardType
from ankification.rubric import Judge

SOURCE = (
    "Chicken stock is made by simmering bones in water for hours. The collagen in the "
    "bones breaks down into gelatin, which gives the finished stock its rich body and "
    "mouthfeel. This is why stock made from bones has more body than broth made from meat."
)

BAD = Card(
    type=CardType.BASIC,
    front="What is a key thing about this approach?",  # vague, lacks context
    back="It uses bones.",
)
GOOD = Card(
    type=CardType.BASIC,
    front="In cooking stock, what protein in bones breaks down into gelatin during simmering?",
    back="Collagen.",
)


def main() -> None:
    tracker = CostTracker(budget_usd=2.0)
    judge = Judge(LLM(tracker=tracker))
    for label, card in [("BAD", BAD), ("GOOD", GOOD)]:
        verdict = judge.judge(card, source_description=SOURCE)
        failed = [p.probe.value for p in verdict.probes if p.failed]
        print(f"\n=== {label}: {card.front!r}")
        print(f"  tier={verdict.tier.value}  usable={verdict.usable}  clean={verdict.clean}")
        print(f"  failed_probes={failed}")
        print(f"  reason={verdict.reason[:200]}")
    print(f"\nspent ${tracker.spent_usd:.3f} over {tracker.n_calls} calls")


if __name__ == "__main__":
    main()
